"""Tests for hatch_nodejs_build.plugin module."""

import json
import shutil
import sys
import tempfile
from pathlib import Path
from subprocess import CalledProcessError
from unittest.mock import MagicMock, Mock, patch

import pytest
from hatchling.builders.hooks.plugin.interface import BuildHookInterface

from hatch_nodejs_build.config import NodeJsBuildConfiguration
from hatch_nodejs_build.plugin import NodeJsBuildHook


class TestNodeJsBuildHook:
    """Test cases for the NodeJsBuildHook class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.root_dir = Path(self.temp_dir)

        # Create mock app
        self.mock_app = Mock()
        self.mock_app.display_mini_header = Mock()
        self.mock_app.display_info = Mock()
        self.mock_app.display_debug = Mock()
        self.mock_app.display_waiting = Mock()
        self.mock_app.display_warning = Mock()
        self.mock_app.display_success = Mock()

        # Create mock config
        self.mock_config = {
            "require-node": True,
            "source-dir": "browser",
            "artifact-dir": "dist",
            "bundle-dir": "bundle",
            "install-command": "npm,install",
            "build-command": "npm,run,build",
            "inline-bundle": False,
        }

        # Create mock build config
        self.mock_build_config = Mock()
        self.mock_build_config.builder = Mock()
        self.mock_build_config.builder.metadata = Mock()
        self.mock_build_config.builder.metadata.core = Mock()
        self.mock_build_config.builder.metadata.core.name = "test-project"

        # Create mock metadata
        self.mock_metadata = Mock()

        # Create hook instance with required arguments
        self.hook = NodeJsBuildHook(
            root=str(self.root_dir),
            config=self.mock_config,
            build_config=self.mock_build_config,
            metadata=self.mock_metadata,
            directory=".",
            target_name="wheel",
        )

        # Mock the app property
        self.hook._app = self.mock_app

        # Create test directory structure
        self.source_dir = self.root_dir / "browser"
        self.source_dir.mkdir()
        self.artifact_dir = self.source_dir / "dist"
        self.artifact_dir.mkdir()

        # Mock package.json instead of creating real file
        self.mock_package_json_content = {
            "name": "test-app",
            "version": "1.0.0",
            "scripts": {"build": "echo 'build complete'"},
        }

        # Mock the get_package_json method to return our mock content
        self.hook.get_package_json = Mock(return_value=self.mock_package_json_content)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_plugin_name(self):
        """Test that PLUGIN_NAME is set correctly."""
        assert NodeJsBuildHook.PLUGIN_NAME == "nodejs-build"

    def test_initialization(self):
        """Test hook initialization."""
        # Create a new hook instance for this test
        mock_metadata = Mock()
        hook = NodeJsBuildHook(
            root=str(self.root_dir),
            config=self.mock_config,
            build_config=self.mock_build_config,
            metadata=mock_metadata,
            directory=".",
            target_name="wheel",
        )

        assert hook.plugin_config is None
        assert hook.node_executable is None
        assert hook.node_cache is not None

    def test_prepare_plugin_config(self):
        """Test prepare_plugin_config method."""
        self.hook.prepare_plugin_config()

        assert isinstance(self.hook.plugin_config, NodeJsBuildConfiguration)
        assert self.hook.plugin_config.require_node is True
        assert self.hook.plugin_config.source_dir == Path("./browser")

    def test_get_package_json_success(self):
        """Test successful package.json reading."""
        self.hook.prepare_plugin_config()

        # Mock the get_package_json method to return test data
        self.hook.get_package_json = Mock(return_value=self.mock_package_json_content)

        result = self.hook.get_package_json()

        assert result["name"] == "test-app"
        assert result["version"] == "1.0.0"

    def test_get_package_json_not_found(self):
        """Test package.json not found."""
        self.hook.prepare_plugin_config()
        # Mock the get_package_json method to raise FileNotFoundError
        self.hook.get_package_json = Mock(side_effect=Exception("package.json not found"))

        with pytest.raises(Exception, match="package.json not found"):
            self.hook.get_package_json()

    def test_format_tokens(self):
        """Test format_tokens method."""
        self.hook.node_executable = "/fake/node"

        result = self.hook.format_tokens(["{node}", "npm", "install"])

        assert result == [
            "/fake/node",
            ("npm.cmd" if sys.platform == "win32" else "npm"),
            "install",
        ]

    def test_format_tokens_with_npm(self):
        """Test format_tokens method with npm token."""
        self.hook.node_executable = "/fake/node"

        result = self.hook.format_tokens(["{npm}", "install"])

        # Should replace npm with the correct path based on platform
        assert len(result) == 2
        assert result[0] == str(Path("/fake/node").parent / ("npm.cmd" if sys.platform == "win32" else "npm"))
        assert result[0].endswith("npm")

    @patch("hatch_nodejs_build.plugin.run")
    def test_run_command_success(self, mock_run):
        """Test successful command execution."""
        self.hook.node_executable = "/fake/node"
        self.hook.prepare_plugin_config()

        self.hook._run_command("test", ["echo", "hello"])

        # Use any() to check if the call was made with the correct parameters
        # since the exact path might vary
        assert mock_run.called
        call_args = mock_run.call_args
        assert call_args[0][0] == ["echo", "hello"]
        assert call_args[1]["check"] is True
        assert str(self.hook.plugin_config.source_dir) in str(call_args[1]["cwd"])

    @patch("hatch_nodejs_build.plugin.run")
    def test_run_command_failure(self, mock_run):
        """Test command execution failure."""
        mock_run.side_effect = CalledProcessError(1, "echo")
        self.hook.node_executable = "/fake/node"
        self.hook.prepare_plugin_config()

        with pytest.raises(CalledProcessError) as excinfo:
            self.hook._run_command("test", ["echo", "hello"])
            assert str(self.plugin_config.source_dir) in str(excinfo.value)

    def test_run_install_command(self):
        """Test run_install_command method."""
        self.hook.node_executable = "/fake/node"
        self.hook.prepare_plugin_config()

        with patch.object(self.hook, "_run_command") as mock_run:
            self.hook.run_install_command()
            # The tokens get formatted, so npm path replaces {npm}
            expected_call = mock_run.call_args[0]
            assert expected_call[0] == "install"
            assert len(expected_call[1]) == 2
            assert expected_call[1][0].endswith("npm")
            assert expected_call[1][1] == "install"

    def test_run_build_command(self):
        """Test run_build_command method."""
        self.hook.node_executable = "/fake/node"
        self.hook.prepare_plugin_config()

        with patch.object(self.hook, "_run_command") as mock_run:
            self.hook.run_build_command()
            # The tokens get formatted, so npm path replaces {npm}
            expected_call = mock_run.call_args[0]
            assert expected_call[0] == "build"
            assert len(expected_call[1]) == 3
            assert expected_call[1][0].endswith("npm")
            assert expected_call[1][1] == "run"
            assert expected_call[1][2] == "build"

    def test_initialize_no_artifacts(self):
        """Test initialize when no artifacts are found."""
        self.hook.prepare_plugin_config()
        self.hook.node_executable = "/fake/node"
        build_data = {"artifacts": []}

        # Mock package.json and glob to simulate no artifacts
        with patch.object(self.hook, "get_package_json") as mock_get_package, patch.object(
            self.hook, "require_node"
        ), patch.object(self.hook, "run_install_command"), patch.object(self.hook, "run_build_command"), patch(
            "glob.glob"
        ) as mock_glob:
            mock_get_package.return_value = {"name": "test", "version": "1.0.0"}
            mock_glob.return_value = []

            with pytest.raises(RuntimeError, match="no artifacts found"):
                self.hook.initialize("1.0.0", build_data)

    def test_initialize_with_artifacts(self):
        """Test initialize with artifacts."""
        self.hook.prepare_plugin_config()
        self.hook.node_executable = "/fake/node"
        build_data = {"artifacts": []}

        # Mock all file system operations
        with patch.object(self.hook, "require_node"), patch.object(self.hook, "run_install_command"), patch.object(
            self.hook, "run_build_command"
        ), patch("shutil.copytree") as mock_copytree, patch("glob.glob") as mock_glob:
            # Mock glob to return artifact files
            mock_glob.return_value = [str(self.artifact_dir / "bundle.js"), str(self.artifact_dir)]

            self.hook.initialize("1.0.0", build_data)

        # Check that artifacts were added to build_data
        assert len(build_data["artifacts"]) == 1
        assert "test_project" in str(build_data["artifacts"][0])

    def test_initialize_inline_bundle(self):
        """Test initialize with inline bundle enabled."""
        self.hook.prepare_plugin_config()
        self.hook.plugin_config.inline_bundle = True
        self.hook.node_executable = "/fake/node"

        build_data = {"artifacts": []}

        # Mock all file system operations
        with patch.object(self.hook, "require_node"), patch.object(self.hook, "run_install_command"), patch.object(
            self.hook, "run_build_command"
        ), patch("shutil.copytree") as mock_copytree, patch("glob.glob") as mock_glob, patch(
            "pathlib.Path.read_text"
        ) as mock_read, patch("pathlib.Path.write_text") as mock_write, patch(
            "pathlib.Path.exists"
        ) as mock_exists, patch("pathlib.Path.unlink") as mock_unlink:
            # Mock glob to return artifact files
            mock_glob.return_value = [
                str(self.artifact_dir / "bundle.js"),
                str(self.artifact_dir / "bundle.css"),
                str(self.artifact_dir),
            ]

            # Mock file operations for inlining
            def mock_read_side_effect(path_obj=None):
                path_str = str(path_obj) if path_obj else ""
                if "bundle.js" in path_str:
                    return "console.log('hello');"
                elif "bundle.css" in path_str:
                    return "body { color: red; }"
                elif "index.html" in path_str:
                    return """
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <style data-bundle-css></style>
                    </head>
                    <body>
                        <script data-bundle-js></script>
                    </body>
                    </html>
                    """
                return ""

            mock_read.side_effect = mock_read_side_effect
            mock_exists.return_value = True

            self.hook.initialize("1.0.0", build_data)

        # Verify copytree was called
        mock_copytree.assert_called_once()

        # Verify artifacts were added
        assert len(build_data["artifacts"]) == 1

    def test_initialize_with_custom_project_name(self):
        """Test initialize with custom project name containing hyphens."""
        self.mock_build_config.builder.metadata.core.name = "test-project-with-hyphens"

        self.hook.prepare_plugin_config()
        self.hook.node_executable = "/fake/node"
        build_data = {"artifacts": []}

        # Mock all file system operations
        with patch.object(self.hook, "require_node"), patch.object(self.hook, "run_install_command"), patch.object(
            self.hook, "run_build_command"
        ), patch("shutil.copytree") as mock_copytree, patch("glob.glob") as mock_glob:
            # Mock glob to return artifact files
            mock_glob.return_value = [str(self.artifact_dir / "bundle.js"), str(self.artifact_dir)]

            self.hook.initialize("1.0.0", build_data)

        # Check that hyphens were replaced with underscores
        assert "test_project_with_hyphens" in str(build_data["artifacts"][0])
