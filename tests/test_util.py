"""Tests for hatch_nodejs_build._util module."""

from subprocess import CalledProcessError
from unittest.mock import patch

from semantic_version import Version

from hatch_nodejs_build._util import get_node_executable_version, node_matches


class TestNodeMatches:
    """Test cases for the node_matches function."""

    def test_node_matches_no_requirement(self):
        """Test that node_matches returns True when no requirement is specified."""
        result = node_matches("18.0.0", None)
        assert result is True

    def test_node_matches_with_version_object(self):
        """Test node_matches with a Version object."""
        version = Version("18.0.0")
        result = node_matches(version, ">=18.0.0")
        assert result is True

    def test_node_matches_matching_version(self):
        """Test node_matches with a matching version."""
        result = node_matches("18.0.0", ">=18.0.0")
        assert result is True

    def test_node_matches_non_matching_version(self):
        """Test node_matches with a non-matching version."""
        result = node_matches("16.0.0", ">=18.0.0")
        assert result is False

    def test_node_matches_complex_range(self):
        """Test node_matches with a complex version range."""
        result = node_matches("18.5.0", ">=18.0.0 <19.0.0")
        assert result is True

    def test_node_matches_exact_version(self):
        """Test node_matches with an exact version requirement."""
        result = node_matches("18.0.0", "18.0.0")
        assert result is True

    def test_node_matches_prerelease_version(self):
        """Test node_matches with a prerelease version."""
        result = node_matches("18.0.0-beta.1", ">=18.0.0")
        assert result is False  # Prerelease versions are typically considered less than release versions


class TestGetNodeExecutableVersion:
    """Test cases for the get_node_executable_version function."""

    @patch("hatch_nodejs_build._util.run")
    def test_get_node_executable_version_success(self, mock_run):
        """Test successful version retrieval."""
        mock_run.return_value.stdout = b"v18.0.0\n"

        result = get_node_executable_version("node")

        assert result == "18.0.0"
        mock_run.assert_called_once_with(["node", "--version"], check=True, capture_output=True)

    @patch("hatch_nodejs_build._util.run")
    def test_get_node_executable_version_file_not_found(self, mock_run):
        """Test version retrieval when executable is not found."""
        mock_run.side_effect = FileNotFoundError()

        result = get_node_executable_version("nonexistent")

        assert result is None

    @patch("hatch_nodejs_build._util.run")
    def test_get_node_executable_version_called_process_error(self, mock_run):
        """Test version retrieval when process fails."""
        mock_run.side_effect = CalledProcessError(1, "node")

        result = get_node_executable_version("node")

        assert result is None

    @patch("hatch_nodejs_build._util.run")
    def test_get_node_executable_version_empty_output(self, mock_run):
        """Test version retrieval with empty output."""
        mock_run.return_value.stdout = b""

        result = get_node_executable_version("node")

        assert result == ""

    @patch("hatch_nodejs_build._util.run")
    def test_get_node_executable_version_malformed_output(self, mock_run):
        """Test version retrieval with malformed output."""
        mock_run.return_value.stdout = b"vinvalid version"

        result = get_node_executable_version("node")

        assert result == "invalid version"

    @patch("hatch_nodejs_build._util.run")
    def test_get_node_executable_version_with_spaces(self, mock_run):
        """Test version retrieval with output containing spaces."""
        mock_run.return_value.stdout = b"  v18.0.0  \n"

        result = get_node_executable_version("node")

        assert result == "18.0.0"
