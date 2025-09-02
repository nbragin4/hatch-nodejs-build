"""Tests for hatch_nodejs_build.config module."""

from pathlib import Path
from typing import List

import pytest
from pydantic import ValidationError

from hatch_nodejs_build.config import NodeJsBuildConfiguration, validate_and_split


class TestValidateAndSplit:
    """Test cases for the validate_and_split function."""

    def test_validate_and_split_valid_string(self):
        """Test validate_and_split with a valid string."""
        result = validate_and_split("npm,install")
        assert result == ["npm", "install"]
        assert isinstance(result, List)

    def test_validate_and_split_single_item(self):
        """Test validate_and_split with a single item."""
        result = validate_and_split("npm")
        assert result == ["npm"]
        assert isinstance(result, List)

    def test_validate_and_split_with_spaces(self):
        """Test validate_and_split with spaces around commas."""
        result = validate_and_split("npm, install, run")
        assert result == ["npm", " install", " run"]
        assert isinstance(result, List)

    def test_validate_and_split_empty_string(self):
        """Test validate_and_split with an empty string."""
        with pytest.raises(ValueError, match="Cannot be empty"):
            validate_and_split("")

    def test_validate_and_split_whitespace_only(self):
        """Test validate_and_split with whitespace only."""
        with pytest.raises(ValueError, match="Cannot be empty"):
            validate_and_split("   ")

    def test_validate_and_split_non_string_input(self):
        """Test validate_and_split with non-string input."""
        with pytest.raises(ValueError, match="Must be a string"):
            validate_and_split(123)


class TestNodeJsBuildConfiguration:
    """Test cases for the NodeJsBuildConfiguration class."""

    def test_default_configuration(self):
        """Test default configuration values."""
        config = NodeJsBuildConfiguration()

        assert config.dependencies == []
        assert config.require_node is True
        assert config.node_executable is None
        assert config.lts is True
        assert config.install_command == ["{npm}", "install"]
        assert config.build_command == ["{npm}", "run", "build"]
        assert config.source_dir == Path("./browser")
        assert config.artifact_dir == Path("./dist")
        assert config.bundle_dir == Path("./bundle")
        assert config.inline_bundle is False

    def test_custom_configuration(self):
        """Test configuration with custom values."""
        config = NodeJsBuildConfiguration(
            dependencies=["npm", "node"],
            **{
                "require-node": False,
                "node-executable": "/custom/node",
                "lts": False,
                "install-command": "yarn,install",
                "build-command": "yarn,build",
                "source-dir": "./src/web",
                "artifact-dir": "./out",
                "bundle-dir": "./static",
                "inline-bundle": True,
            },
        )

        assert config.dependencies == ["npm", "node"]
        assert config.require_node is False
        assert config.node_executable == "/custom/node"
        assert config.lts is False
        assert config.install_command == ["yarn", "install"]
        assert config.build_command == ["yarn", "build"]
        assert config.source_dir == Path("./src/web")
        assert config.artifact_dir == Path("./out")
        assert config.bundle_dir == Path("./static")
        assert config.inline_bundle is True

    def test_configuration_with_kebab_case_keys(self):
        """Test configuration with kebab-case keys (pydantic alias)."""
        config = NodeJsBuildConfiguration(
            **{
                "require-node": False,
                "node-executable": "/custom/node",
                "install-command": "yarn,install",
                "build-command": "yarn,build",
                "source-dir": "./src/web",
                "artifact-dir": "./out",
                "bundle-dir": "./static",
                "inline-bundle": True,
            }
        )

        assert config.require_node is False
        assert config.node_executable == "/custom/node"
        assert config.install_command == ["yarn", "install"]
        assert config.build_command == ["yarn", "build"]
        assert config.source_dir == Path("./src/web")
        assert config.artifact_dir == Path("./out")
        assert config.bundle_dir == Path("./static")
        assert config.inline_bundle is True

    def test_configuration_extra_fields_forbidden(self):
        """Test that extra fields raise ValidationError."""
        with pytest.raises(ValidationError):
            NodeJsBuildConfiguration(invalid_field="should_raise_error")

    def test_configuration_invalid_command_type(self):
        """Test configuration with invalid command type."""
        with pytest.raises(ValidationError):
            NodeJsBuildConfiguration(
                install_command=123  # Should be string or list
            )

    def test_configuration_invalid_path_type(self):
        """Test configuration with invalid path type."""
        with pytest.raises(ValidationError):
            NodeJsBuildConfiguration(
                source_dir=123  # Should be Path or string
            )

    def test_configuration_model_dump_json(self):
        """Test that model_dump_json works correctly."""
        config = NodeJsBuildConfiguration(**{"require-node": False, "node-executable": "/custom/node"})

        json_str = config.model_dump_json(by_alias=True)
        assert "require-node" in json_str
        assert "node-executable" in json_str

    def test_configuration_model_dump(self):
        """Test that model_dump works correctly."""
        config = NodeJsBuildConfiguration(**{"require-node": False, "node-executable": "/custom/node"})

        data = config.model_dump(by_alias=True)
        assert data["require-node"] is False
        assert data["node-executable"] == "/custom/node"

    def test_configuration_path_conversion(self):
        """Test that string paths are converted to Path objects."""
        config = NodeJsBuildConfiguration(
            **{"source-dir": "./custom/source", "artifact-dir": "./custom/artifact", "bundle-dir": "./custom/bundle"}
        )

        assert isinstance(config.source_dir, Path)
        assert isinstance(config.artifact_dir, Path)
        assert isinstance(config.bundle_dir, Path)
        assert config.source_dir == Path("./custom/source")
        assert config.artifact_dir == Path("./custom/artifact")
        assert config.bundle_dir == Path("./custom/bundle")
