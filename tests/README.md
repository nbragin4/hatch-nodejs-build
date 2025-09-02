# Test Suite for hatch-nodejs-build

This directory contains comprehensive unit tests and integration tests for the hatch-nodejs-build plugin.

## Test Structure

The test suite is organized as follows:

- `test_util.py` - Tests for utility functions in `_util.py`
- `test_config.py` - Tests for configuration handling in `config.py`
- `test_cache.py` - Tests for Node.js caching functionality in `cache.py`
- `test_plugin.py` - Tests for the main plugin functionality in `plugin.py`
- `test_hooks.py` - Tests for hook registration in `hooks.py`
- `test_integration.py` - Integration tests for the complete build workflow
- `conftest.py` - Shared pytest fixtures and configuration

## Running Tests

### Prerequisites

Make sure you have `uv` installed and the project dependencies installed:

```bash
# Install uv (if not already installed)
pip install uv

# Install project dependencies
uv sync
```

### Running All Tests

```bash
# Run all tests with coverage
uv run pytest

# Run all tests with verbose output
uv run pytest -v

# Run tests with coverage report
uv run pytest --cov=hatch_nodejs_build --cov-report=html
```

### Running Specific Tests

```bash
# Run specific test file
uv run pytest tests/test_util.py

# Run specific test class
uv run pytest tests/test_config.py::TestNodeJsBuildConfiguration

# Run specific test method
uv run pytest tests/test_plugin.py::TestNodeJsBuildHook::test_initialize_with_artifacts

# Run tests with specific marker
uv run pytest -m unit          # Run only unit tests
uv run pytest -m integration   # Run only integration tests
uv run pytest -m "not slow"    # Exclude slow tests
```

### Running Tests with Different Options

```bash
# Run tests with coverage (minimum 80% required)
uv run pytest --cov=hatch_nodejs_build --cov-fail-under=80

# Run tests with HTML coverage report
uv run pytest --cov=hatch_nodejs_build --cov-report=html

# Run tests with XML coverage report (for CI)
uv run pytest --cov=hatch_nodejs_build --cov-report=xml

# Run tests with duration information
uv run pytest --durations=10

# Run tests with specific Python version
uv run pytest --python=3.11
```

## Test Coverage

The test suite aims for comprehensive coverage of all code paths:

- **Unit Tests**: Test individual functions and methods in isolation
- **Integration Tests**: Test the complete build workflow
- **Error Handling**: Test error conditions and edge cases
- **Configuration**: Test various configuration options
- **Platform Compatibility**: Test behavior on different platforms (via mocking)

### Coverage Targets

- Minimum coverage: 80%
- Target coverage: 90%+
- Critical paths: 100%

## Test Categories

### Unit Tests

Unit tests focus on individual components:

- **Utility Functions**: Version matching, executable detection
- **Configuration**: Pydantic model validation, default values
- **Cache**: Node.js version resolution, download, extraction
- **Plugin**: Individual methods and functionality

### Integration Tests

Integration tests verify the complete workflow:

- **Build Process**: End-to-end build execution
- **Inline Bundle**: HTML/CSS/JS inlining functionality
- **Custom Configuration**: Different directory structures and commands
- **Error Handling**: Graceful failure scenarios

### Mocking Strategy

The test suite uses extensive mocking to:

- Avoid network calls during testing
- Simulate different Node.js versions and platforms
- Test error conditions without side effects
- Ensure deterministic test behavior

## Writing New Tests

### Guidelines

1. **Follow PEP 8**: Use standard Python naming conventions
2. **Use Descriptive Names**: Test names should clearly describe what they test
3. **Arrange-Act-Assert**: Structure tests clearly
4. **Mock External Dependencies**: Avoid real network calls or file system operations
5. **Test Edge Cases**: Include error conditions and unusual inputs
6. **Use Fixtures**: Leverage shared fixtures in `conftest.py`

### Example Test Structure

```python
def test_specific_functionality():
    """Test description of what this test verifies."""
    # Arrange
    setup_test_data()
    
    # Act
    result = function_under_test()
    
    # Assert
    assert result == expected_value
```

### Adding Fixtures

Add shared fixtures to `conftest.py`:

```python
@pytest.fixture
def my_fixture():
    """Description of the fixture."""
    setup_data()
    yield data
    cleanup_data()
```

## Continuous Integration

The test suite is designed to run in CI environments:

- Uses `uv` for dependency management
- Generates coverage reports in multiple formats
- Supports parallel test execution
- Handles platform-specific tests via mocking

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure all dependencies are installed with `uv sync`
2. **Permission Errors**: Ensure the test environment has proper permissions
3. **Network Tests**: Mark network-dependent tests with `@pytest.mark.network`
4. **Slow Tests**: Mark slow tests with `@pytest.mark.slow`

### Debugging Tests

```bash
# Run tests with debugging
uv run pytest --pdb

# Run tests with verbose output
uv run pytest -v -s

# Run specific test with debugging
uv run pytest tests/test_file.py::TestClass::test_method --pdb
```

## Contributing

When adding new features:

1. Write comprehensive tests for the new functionality
2. Ensure all existing tests continue to pass
3. Maintain or improve test coverage
4. Add appropriate fixtures to `conftest.py` if needed
5. Update this README if adding new test categories