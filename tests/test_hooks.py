"""Tests for hatch_nodejs_build.hooks module."""

from unittest.mock import patch

from hatch_nodejs_build.hooks import hatch_register_build_hook
from hatch_nodejs_build.plugin import NodeJsBuildHook


class TestHatchRegisterBuildHook:
    """Test cases for the hatch_register_build_hook function."""

    @patch("hatch_nodejs_build.hooks.NodeJsBuildHook")
    def test_hatch_register_build_hook(self, mock_node_js_build_hook):
        """Test that hatch_register_build_hook returns the correct hook class."""
        result = hatch_register_build_hook()

        assert result == mock_node_js_build_hook
        # Ensure the hook class was not instantiated
        mock_node_js_build_hook.assert_not_called()

    def test_hatch_register_build_hook_direct(self):
        """Test hatch_register_build_hook without mocking."""
        result = hatch_register_build_hook()

        assert result == NodeJsBuildHook
        assert callable(result)
        assert issubclass(result, NodeJsBuildHook.__bases__[0])
