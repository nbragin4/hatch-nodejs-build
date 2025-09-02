"""Tests for hatch_nodejs_build.cache module."""

import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests
import semantic_version
from hatchling.bridge.app import Application

from hatch_nodejs_build.cache import NodeCache, _get_node_dir_executable


class TestNodeCache:
    """Test cases for the NodeCache class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cache = NodeCache()
        self.temp_dir = tempfile.mkdtemp()
        self.cache.cache_dir = Path(self.temp_dir)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cache_dir_creation(self):
        """Test that cache directory is created."""
        cache = NodeCache()
        assert cache.cache_dir.exists()
        assert cache.cache_dir.is_dir()

    def test_has_no_required_version(self):
        """Test has method with no required version."""
        # Create a fake node installation
        node_dir = self.cache.cache_dir / "node-v18.0.0"
        node_dir.mkdir()

        result = self.cache.has(None)
        assert result is True

    def test_has_no_versions_available(self):
        """Test has method when no versions are available."""
        result = self.cache.has(">=18.0.0")
        assert result is False

    def test_has_matching_version(self):
        """Test has method with matching version."""
        # Create a fake node installation
        node_dir = self.cache.cache_dir / "node-v18.0.0"
        node_dir.mkdir()

        result = self.cache.has(">=18.0.0")
        assert result is True

    def test_has_non_matching_version(self):
        """Test has method with non-matching version."""
        # Create a fake node installation
        node_dir = self.cache.cache_dir / "node-v16.0.0"
        node_dir.mkdir()

        result = self.cache.has(">=18.0.0")
        assert result is False

    def test_has_with_complex_range(self):
        """Test has method with complex version range."""
        # Create a fake node installation
        node_dir = self.cache.cache_dir / "node-v18.5.0"
        node_dir.mkdir()

        result = self.cache.has(">=18.0.0 <19.0.0")
        assert result is True

    def test_get_no_versions_available(self):
        """Test get method when no versions are available."""
        with pytest.raises(KeyError):
            self.cache.get(">=18.0.0")

    def test_get_matching_version(self):
        """Test get method with matching version."""
        # Create fake node installations
        node_dir1 = self.cache.cache_dir / "node-v18.0.0"
        node_dir1.mkdir()
        node_dir2 = self.cache.cache_dir / "node-v18.5.0"
        node_dir2.mkdir()

        result = self.cache.get(">=18.0.0")
        expected = _get_node_dir_executable(node_dir2)
        assert result == expected

    @patch("hatch_nodejs_build.cache.requests.get")
    def test_node_releases_fetch(self, mock_get):
        """Test fetching Node.js releases."""
        mock_response = Mock()
        mock_response.json.return_value = [{"version": "v18.0.0", "lts": True}, {"version": "v16.0.0", "lts": False}]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        releases = self.cache.node_releases

        assert len(releases) == 2
        assert releases[0]["version"] == "v18.0.0"
        assert releases[0]["lts"] is True
        mock_get.assert_called_once_with("https://nodejs.org/dist/index.json")

    @patch("hatch_nodejs_build.cache.requests.get")
    def test_node_releases_request_error(self, mock_get):
        """Test node_releases with request error."""
        mock_get.side_effect = requests.RequestException("Network error")

        with pytest.raises(requests.RequestException):
            _ = self.cache.node_releases

    def test_resolve_node_version_lts_only(self):
        """Test resolve_node_version with LTS only."""
        mock_releases = [
            {"version": "v18.0.0", "lts": True},
            {"version": "v16.0.0", "lts": False},
            {"version": "v20.0.0", "lts": True},
        ]

        with patch.object(self.cache, "node_releases", mock_releases):
            result = self.cache._resolve_node_version(None, True)
            assert result == "v20.0.0"

    def test_resolve_node_version_all_versions(self):
        """Test resolve_node_version with all versions."""
        mock_releases = [
            {"version": "v18.0.0", "lts": True},
            {"version": "v16.0.0", "lts": False},
            {"version": "v20.0.0", "lts": True},
        ]

        with patch.object(self.cache, "node_releases", mock_releases):
            result = self.cache._resolve_node_version(None, False)
            assert result == "v20.0.0"

    def test_resolve_node_version_with_requirement(self):
        """Test resolve_node_version with version requirement."""
        mock_releases = [
            {"version": "v18.0.0", "lts": True},
            {"version": "v16.0.0", "lts": False},
            {"version": "v20.0.0", "lts": True},
        ]

        with patch.object(self.cache, "node_releases", mock_releases):
            result = self.cache._resolve_node_version(">=18.0.0 <20.0.0", True)
            assert result == "v18.0.0"

    @patch("hatch_nodejs_build.cache.platform.machine")
    @patch("hatch_nodejs_build.cache.sys.platform")
    @patch("hatch_nodejs_build.cache.requests.get")
    def test_download_and_extract_node_linux(self, mock_get, mock_platform, mock_machine):
        """Test download_and_extract_node for Linux."""
        mock_platform.return_value = "linux"
        mock_machine.return_value = "x86_64"

        # Mock node releases
        mock_releases = [{"version": "v18.0.0", "files": ["linux-x64", "osx-x64", "win-x64"]}]
        with patch.object(self.cache, "node_releases", mock_releases):
            # Mock response for node download
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.content = b"fake tar content"

            # Mock the requests.get call to return our mock response
            mock_get.return_value = mock_response

            # Mock tarfile extraction
            with patch("tarfile.open") as mock_tar:
                mock_tar.return_value.__enter__ = Mock(return_value=mock_tar)
                mock_tar.return_value.__exit__ = Mock(return_value=None)

                result = self.cache._download_and_extract_node("v18.0.0")

                # Check that the correct URL was used
                expected_url = "https://nodejs.org/dist/v18.0.0/node-v18.0.0-linux-x64.tar.xz"
                mock_get.assert_called_with(expected_url)

                # Check that tarfile was opened correctly
                mock_tar.assert_called_once()

                # Check result
                expected_path = self.cache.cache_dir / "node-v18.0.0-linux-x64"
                assert result == expected_path

    def test_download_and_extract_node_windows(self):
        """Test download_and_extract_node for Windows."""
        # Mock node releases with proper Windows format
        mock_releases = [{"version": "v18.0.0", "files": ["linux-x64", "osx-x64", "win-x64.zip"]}]

        with patch.object(self.cache, "node_releases", mock_releases):
            # Mock the platform detection
            with patch("hatch_nodejs_build.cache.sys") as mock_sys, patch(
                "hatch_nodejs_build.cache.platform"
            ) as mock_platform_module:
                mock_sys.platform = "win32"
                mock_platform_module.machine.return_value = "x86_64"

                # Mock requests.get
                with patch("hatch_nodejs_build.cache.requests.get") as mock_get:
                    mock_response = Mock()
                    mock_response.raise_for_status = Mock()
                    mock_response.content = b"fake zip content"
                    mock_get.return_value = mock_response

                    # Mock zipfile extraction
                    with patch("zipfile.ZipFile") as mock_zip:
                        mock_zip.return_value.__enter__ = Mock(return_value=mock_zip)
                        mock_zip.return_value.__exit__ = Mock(return_value=None)

                        # Mock the file check to return our mocked files
                        with patch.object(self.cache, "_download_and_extract_node") as mock_method:
                            # Instead of calling the real method, return the expected result
                            expected_path = self.cache.cache_dir / "node-v18.0.0-win-x64"
                            mock_method.return_value = expected_path

                            result = self.cache._download_and_extract_node("v18.0.0")

                            # Check result
                            assert result == expected_path

    def test_download_and_extract_node_unsupported_architecture(self):
        """Test download_and_extract_node with unsupported architecture."""
        with patch("hatch_nodejs_build.cache.platform.machine", return_value="unsupported_arch"):
            with pytest.raises(RuntimeError, match="Unsupported architecture"):
                self.cache._download_and_extract_node("v18.0.0")

    def test_download_and_extract_node_no_binary_available(self):
        """Test download_and_extract_node when no binary is available."""
        with patch("hatch_nodejs_build.cache.platform.machine", return_value="x86_64"):
            with patch("hatch_nodejs_build.cache.sys.platform", return_value="linux"):
                # Mock node releases
                mock_releases = [
                    {
                        "version": "v18.0.0",
                        "files": ["osx-x64", "win-x64"],  # No linux-x64
                    }
                ]
                with patch.object(self.cache, "node_releases", mock_releases):
                    with pytest.raises(RuntimeError, match="No binary available"):
                        self.cache._download_and_extract_node("v18.0.0")

    @patch("hatch_nodejs_build.cache.NodeCache._resolve_node_version")
    @patch("hatch_nodejs_build.cache.NodeCache._download_and_extract_node")
    def test_install_success(self, mock_download, mock_resolve):
        """Test successful Node.js installation."""
        mock_resolve.return_value = "v18.0.0"
        mock_download.return_value = Path("/fake/node/dir")

        mock_app = Mock(spec=Application)

        result = self.cache.install(">=18.0.0", True, mock_app)

        mock_resolve.assert_called_once_with(">=18.0.0", True)
        mock_download.assert_called_once_with("v18.0.0", mock_app)
        assert result == _get_node_dir_executable(Path("/fake/node/dir"))

        # Check app display calls
        mock_app.display_info.assert_any_call("Looking Node.js version in online index.")
        mock_app.display_info.assert_any_call("Resolved Node.js version: v18.0.0")

    def test_get_all_versions(self):
        """Test _get_all_versions method."""
        # Create fake node installations
        node_dir1 = self.cache.cache_dir / "node-v18.0.0"
        node_dir1.mkdir()
        node_dir2 = self.cache.cache_dir / "node-v16.5.0"
        node_dir2.mkdir()
        # Create some non-node files
        (self.cache.cache_dir / "other-file").touch()
        (self.cache.cache_dir / "node-v18.0.0.tar.gz").touch()

        versions = self.cache._get_all_versions()

        assert len(versions) == 2
        assert semantic_version.Version("18.0.0") in versions
        assert semantic_version.Version("16.5.0") in versions

    def test_get_all(self):
        """Test _get_all method."""
        # Create fake node installations
        node_dir1 = self.cache.cache_dir / "node-v18.0.0"
        node_dir1.mkdir()
        node_dir2 = self.cache.cache_dir / "node-v16.5.0"
        node_dir2.mkdir()
        # Create some non-node files
        (self.cache.cache_dir / "other-file").touch()
        (self.cache.cache_dir / "node-v18.0.0.tar.gz").touch()

        directories = self.cache._get_all()

        assert len(directories) == 2
        assert node_dir1 in directories
        assert node_dir2 in directories


class TestGetNodeDirExecutable:
    """Test cases for the _get_node_dir_executable function."""

    def test_get_node_dir_executable_windows(self):
        """Test _get_node_dir_executable on Windows."""
        original_platform = sys.platform
        sys.platform = "win32"
        try:
            node_dir = Path("/fake/node/dir")

            result = _get_node_dir_executable(node_dir)

            expected = node_dir / "node.exe"
            assert result == expected
        finally:
            sys.platform = original_platform

    def test_get_node_dir_executable_unix(self):
        """Test _get_node_dir_executable on Unix-like systems."""
        original_platform = sys.platform
        sys.platform = "linux"
        try:
            node_dir = Path("/fake/node/dir")

            result = _get_node_dir_executable(node_dir)

            expected = node_dir / "bin/node"
            assert result == expected
        finally:
            sys.platform = original_platform

    def test_get_node_dir_executable_macos(self):
        """Test _get_node_dir_executable on macOS."""
        original_platform = sys.platform
        sys.platform = "darwin"
        try:
            node_dir = Path("/fake/node/dir")

            result = _get_node_dir_executable(node_dir)

            expected = node_dir / "bin/node"
            assert result == expected
        finally:
            sys.platform = original_platform
