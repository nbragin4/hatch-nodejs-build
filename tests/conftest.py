"""Pytest configuration and shared fixtures."""

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from hatch_nodejs_build.cache import NodeCache
from hatch_nodejs_build.plugin import NodeJsBuildHook


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_app():
    """Create a mock Hatch application."""
    app = Mock()
    app.display_mini_header = Mock()
    app.display_info = Mock()
    app.display_debug = Mock()
    app.display_waiting = Mock()
    app.display_warning = Mock()
    app.display_success = Mock()
    return app


@pytest.fixture
def mock_build_config():
    """Create a mock build configuration."""
    config = Mock()
    config.builder = Mock()
    config.builder.metadata = Mock()
    config.builder.metadata.core = Mock()
    config.builder.metadata.core.name = "test-project"
    return config


@pytest.fixture
def sample_package_json():
    """Sample package.json content."""
    return {
        "name": "test-app",
        "version": "1.0.0",
        "engines": {"node": ">=18.0.0"},
        "scripts": {"install": "echo 'install complete'", "build": "echo 'build complete'"},
        "dependencies": {"react": "^18.0.0"},
    }


@pytest.fixture
def basic_project_structure(temp_dir, sample_package_json):
    """Create a basic project structure."""
    # Create source directory
    source_dir = temp_dir / "browser"
    source_dir.mkdir()

    # Create package.json
    package_json = source_dir / "package.json"
    package_json.write_text(json.dumps(sample_package_json))

    # Create source files
    src_dir = source_dir / "src"
    src_dir.mkdir()

    (src_dir / "index.js").write_text("""
    console.log('Hello, World!');
    """)

    # Create artifact directory
    artifact_dir = source_dir / "dist"
    artifact_dir.mkdir()

    # Create some artifacts
    (artifact_dir / "bundle.js").write_text("console.log('Hello, World!');")
    (artifact_dir / "bundle.css").write_text("body { margin: 0; }")

    return {"root_dir": temp_dir, "source_dir": source_dir, "artifact_dir": artifact_dir, "package_json": package_json}


@pytest.fixture
def sample_config():
    """Sample configuration for the hook."""
    return {
        "require-node": True,
        "source-dir": "browser",
        "artifact-dir": "dist",
        "bundle-dir": "bundle",
        "install-command": "npm,install",
        "build-command": "npm,run,build",
    }


@pytest.fixture
def node_hook(mock_app, mock_build_config, sample_config, temp_dir):
    """Create a NodeJsBuildHook instance with mock dependencies."""
    mock_metadata = Mock()
    hook = NodeJsBuildHook(
        root=str(temp_dir),
        config=sample_config,
        build_config=mock_build_config,
        metadata=mock_metadata,
        directory=".",
        target_name="wheel",
    )
    hook.app = mock_app
    return hook


@pytest.fixture
def node_cache():
    """Create a NodeCache instance."""
    return NodeCache()


@pytest.fixture
def sample_node_releases():
    """Sample Node.js releases data."""
    return [
        {"version": "v20.0.0", "lts": True, "files": ["linux-x64", "darwin-x64", "win-x64"]},
        {"version": "v18.0.0", "lts": True, "files": ["linux-x64", "darwin-x64", "win-x64"]},
        {"version": "v16.0.0", "lts": False, "files": ["linux-x64", "darwin-x64", "win-x64"]},
    ]


@pytest.fixture
def inline_bundle_project(temp_dir, sample_package_json):
    """Create a project structure for testing inline bundle."""
    # Create source directory
    source_dir = temp_dir / "browser"
    source_dir.mkdir()

    # Create package.json
    package_json = source_dir / "package.json"
    package_json.write_text(json.dumps(sample_package_json))

    # Create artifact directory
    artifact_dir = source_dir / "dist"
    artifact_dir.mkdir()

    # Create artifacts
    (artifact_dir / "bundle.js").write_text("console.log('Hello, World!');")
    (artifact_dir / "bundle.css").write_text("body { margin: 0; }")

    # Create index template
    index_template = source_dir / "index.html"
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

    return {
        "root_dir": temp_dir,
        "source_dir": source_dir,
        "artifact_dir": artifact_dir,
        "index_template": index_template,
    }
