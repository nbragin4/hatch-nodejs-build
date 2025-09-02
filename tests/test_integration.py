"""Integration tests for hatch_nodejs_build."""

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from hatch_nodejs_build.plugin import NodeJsBuildHook


class TestNodeJsBuildIntegration:
    """Integration tests for the complete Node.js build process."""

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

        # Create mock build config
        self.mock_build_config = Mock()
        self.mock_build_config.builder = Mock()
        self.mock_build_config.builder.metadata = Mock()
        self.mock_build_config.builder.metadata.core = Mock()
        self.mock_build_config.builder.metadata.core.name = "test-project"

        # Create test directory structure
        self.setup_test_project()

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def setup_test_project(self):
        """Set up a test project structure."""
        # Create source directory
        self.source_dir = self.root_dir / "browser"
        self.source_dir.mkdir()

        # Create package.json
        self.package_json = self.source_dir / "package.json"
        self.package_json.write_text(
            json.dumps(
                {
                    "name": "test-app",
                    "version": "1.0.0",
                    "engines": {"node": ">=18.0.0"},
                    "scripts": {"install": "echo 'install complete'", "build": "echo 'build complete'"},
                    "dependencies": {"react": "^18.0.0"},
                }
            )
        )

        # Create source files
        src_dir = self.source_dir / "src"
        src_dir.mkdir()

        (src_dir / "index.js").write_text("""
        console.log('Hello, World!');
        """)

        # Create artifact directory
        self.artifact_dir = self.source_dir / "dist"
        self.artifact_dir.mkdir()

    def create_hook(self, config=None):
        """Create a hook instance with given configuration."""
        if config is None:
            config = {
                "require-node": True,
                "source-dir": "browser",
                "artifact-dir": "dist",
                "bundle-dir": "bundle",
                "install-command": "npm,install",
                "build-command": "npm,run,build",
            }

        mock_metadata = Mock()
        hook = NodeJsBuildHook(
            root=str(self.root_dir),
            config=config,
            build_config=self.mock_build_config,
            metadata=mock_metadata,
            directory=".",
            target_name="wheel",
        )
        # Mock the app property
        hook._app = self.mock_app

        return hook

    def test_complete_build_workflow(self):
        """Test the complete build workflow."""
        # Create some fake artifacts
        (self.artifact_dir / "bundle.js").write_text("console.log('Hello, World!');")
        (self.artifact_dir / "bundle.css").write_text("body { margin: 0; }")

        hook = self.create_hook()
        build_data = {"artifacts": []}

        # Mock the file system operations to avoid path issues
        with patch.object(hook, "require_node") as mock_require, patch.object(
            hook, "run_install_command"
        ) as mock_install, patch.object(hook, "run_build_command") as mock_build, patch(
            "shutil.copytree"
        ) as mock_copytree, patch("glob.glob") as mock_glob:
            # Mock glob to return our artifact files
            mock_glob.return_value = [
                str(self.artifact_dir / "bundle.js"),
                str(self.artifact_dir / "bundle.css"),
                str(self.artifact_dir),  # Directory itself
            ]

            hook.initialize("1.0.0", build_data)

        # Verify the workflow was called
        mock_require.assert_called_once()
        mock_install.assert_called_once()
        mock_build.assert_called_once()

        # Verify copytree was called with correct paths
        mock_copytree.assert_called_once()

        # Verify artifacts were added to build_data
        assert len(build_data["artifacts"]) == 1
        bundle_dir = build_data["artifacts"][0]
        assert bundle_dir.name == "bundle"

    def test_build_workflow_with_inline_bundle(self):
        """Test build workflow with inline bundle."""
        # Create artifacts and index template
        (self.artifact_dir / "bundle.js").write_text("console.log('Hello, World!');")
        (self.artifact_dir / "bundle.css").write_text("body { margin: 0; }")

        index_template = self.source_dir / "index.html"
        index_template.write_text("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test App</title>
            <style data-bundle-css></style>
        </head>
        <body>
            <div id="root"></div>
            <script data-bundle-js></script>
        </body>
        </html>
        """)

        config = {
            "require-node": True,
            "source-dir": "browser",
            "artifact-dir": "dist",
            "bundle-dir": "bundle",
            "install-command": "npm,install",
            "build-command": "npm,run,build",
            "inline-bundle": True,
        }

        hook = self.create_hook(config)
        build_data = {"artifacts": []}

        # Mock all file system operations
        with patch.object(hook, "require_node"), patch.object(hook, "run_install_command"), patch.object(
            hook, "run_build_command"
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
                    return "console.log('Hello, World!');"
                elif "bundle.css" in path_str:
                    return "body { margin: 0; }"
                elif "index.html" in path_str:
                    return """
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Test App</title>
                        <style data-bundle-css></style>
                    </head>
                    <body>
                        <div id="root"></div>
                        <script data-bundle-js></script>
                    </body>
                    </html>
                    """
                return ""

            mock_read.side_effect = mock_read_side_effect
            mock_exists.return_value = True

            hook.initialize("1.0.0", build_data)

        # Verify copytree was called
        mock_copytree.assert_called_once()

        # Verify artifacts were added
        assert len(build_data["artifacts"]) == 1

    def test_build_workflow_with_custom_directories(self):
        """Test build workflow with custom directory configuration."""
        # Create custom directory structure
        custom_source = self.root_dir / "src" / "web"
        custom_source.mkdir(parents=True)

        custom_artifact = custom_source / "out"
        custom_artifact.mkdir()

        # Create package.json in custom location
        (custom_source / "package.json").write_text(
            json.dumps({"name": "custom-app", "version": "1.0.0", "scripts": {"build": "echo 'custom build'"}})
        )

        # Create artifacts
        (custom_artifact / "app.js").write_text("console.log('Custom app');")

        config = {
            "require-node": False,  # Skip Node.js requirement for simplicity
            "source-dir": "src/web",
            "artifact-dir": "out",
            "bundle-dir": "web",
            "install-command": "npm,install",
            "build-command": "npm,run,build",
        }

        hook = self.create_hook(config)
        build_data = {"artifacts": []}

        # Mock file system operations
        with patch.object(hook, "run_install_command"), patch.object(hook, "run_build_command"), patch(
            "shutil.copytree"
        ) as mock_copytree, patch("glob.glob") as mock_glob:
            # Mock glob to return artifact files
            mock_glob.return_value = [str(custom_artifact / "app.js"), str(custom_artifact)]

            hook.initialize("1.0.0", build_data)

        # Verify copytree was called
        mock_copytree.assert_called_once()

        # Verify artifacts were copied to custom location
        assert len(build_data["artifacts"]) == 1
        web_dir = build_data["artifacts"][0]
        assert web_dir.name == "web"

    def test_build_workflow_with_yarn(self):
        """Test build workflow using Yarn instead of npm."""
        (self.artifact_dir / "bundle.js").write_text("console.log('Yarn build');")

        config = {
            "require-node": True,
            "source-dir": "browser",
            "artifact-dir": "dist",
            "bundle-dir": "bundle",
            "install-command": "yarn,install",
            "build-command": "yarn,build",
        }

        hook = self.create_hook(config)
        build_data = {"artifacts": []}

        # Mock file system operations and command execution
        with patch.object(hook, "require_node"), patch.object(hook, "_run_command") as mock_run, patch(
            "shutil.copytree"
        ) as mock_copytree, patch("glob.glob") as mock_glob:
            # Mock glob to return artifact files
            mock_glob.return_value = [str(self.artifact_dir / "bundle.js"), str(self.artifact_dir)]

            hook.initialize("1.0.0", build_data)

        # Verify Yarn commands were used
        install_call = mock_run.call_args_list[0]
        build_call = mock_run.call_args_list[1]

        assert "yarn" in install_call[0][1][0]
        assert "install" in install_call[0][1]
        assert "yarn" in build_call[0][1][0]
        assert "build" in build_call[0][1]

    def test_build_workflow_error_handling(self):
        """Test error handling in build workflow."""
        hook = self.create_hook()
        build_data = {"artifacts": []}

        # Mock package.json reading, command execution, and glob to simulate no artifacts
        with patch.object(hook, "get_package_json") as mock_get_package, patch.object(
            hook, "run_install_command"
        ), patch.object(hook, "run_build_command"), patch("glob.glob") as mock_glob:
            mock_get_package.return_value = {"name": "test", "version": "1.0.0"}
            mock_glob.return_value = []

            with pytest.raises(RuntimeError, match="no artifacts found"):
                hook.initialize("1.0.0", build_data)

    def test_build_workflow_with_project_name_hyphens(self):
        """Test build workflow with project name containing hyphens."""
        self.mock_build_config.builder.metadata.core.name = "my-test-project"

        (self.artifact_dir / "bundle.js").write_text("console.log('Hyphen test');")

        hook = self.create_hook()
        build_data = {"artifacts": []}

        # Mock file system operations
        with patch.object(hook, "require_node"), patch.object(hook, "run_install_command"), patch.object(
            hook, "run_build_command"
        ), patch("shutil.copytree") as mock_copytree, patch("glob.glob") as mock_glob:
            # Mock glob to return artifact files
            mock_glob.return_value = [str(self.artifact_dir / "bundle.js"), str(self.artifact_dir)]

            hook.initialize("1.0.0", build_data)

        # Verify hyphens were converted to underscores
        bundle_dir = build_data["artifacts"][0]
        assert "my_test_project" in str(bundle_dir)

    def test_build_workflow_empty_artifact_directory(self):
        """Test build workflow with empty artifact directory."""
        hook = self.create_hook()
        build_data = {"artifacts": []}

        # Mock package.json reading, command execution, and glob to simulate no artifacts
        with patch.object(hook, "get_package_json") as mock_get_package, patch.object(
            hook, "run_install_command"
        ), patch.object(hook, "run_build_command"), patch("glob.glob") as mock_glob:
            mock_get_package.return_value = {"name": "test", "version": "1.0.0"}
            mock_glob.return_value = []

            with pytest.raises(RuntimeError, match="no artifacts found"):
                hook.initialize("1.0.0", build_data)

    def test_build_workflow_nested_artifacts(self):
        """Test build workflow with nested artifact structure."""
        # Create nested artifact structure
        nested_dir = self.artifact_dir / "static" / "js"
        nested_dir.mkdir(parents=True)

        (nested_dir / "app.js").write_text("console.log('Nested app');")
        (self.artifact_dir / "styles.css").write_text("body { color: blue; }")

        hook = self.create_hook()
        build_data = {"artifacts": []}

        # Mock file system operations
        with patch.object(hook, "require_node"), patch.object(hook, "run_install_command"), patch.object(
            hook, "run_build_command"
        ), patch("shutil.copytree") as mock_copytree, patch("glob.glob") as mock_glob:
            # Mock glob to return artifact files including nested ones
            mock_glob.return_value = [
                str(nested_dir / "app.js"),
                str(self.artifact_dir / "styles.css"),
                str(self.artifact_dir),
                str(nested_dir),
                str(self.artifact_dir / "static"),
            ]

            hook.initialize("1.0.0", build_data)

        # Verify copytree was called
        mock_copytree.assert_called_once()

        # Verify artifacts were added
        assert len(build_data["artifacts"]) == 1
