# Test Structure Documentation

## Overview

This document describes the test structure and organization for the Manifest project.

## Test Organization

### Directory Structure

```
tests/
├── unit/              # Unit tests for individual components
├── integration/       # Integration tests for end-to-end scenarios
├── conftest.py        # Shared pytest fixtures and configuration
└── TEST_STRUCTURE.md  # This file
```

### Test Categories

#### Unit Tests (`tests/unit/`)
- Test individual components in isolation
- Fast execution (< 1 second per test typically)
- Use mocks and fixtures extensively
- Examples:
  - `test_opencode_llm_adapter.py` - OpenCode adapter unit tests
  - `test_executor_factory.py` - ExecutorFactory unit tests

#### Integration Tests (`tests/integration/`)
- Test multiple components working together
- May require external services (e.g., OpenCode server)
- Slower execution
- Marked with `@pytest.mark.integration`
- Examples:
  - `test_opencode_integration.py` - OpenCode server integration tests

## Test Markers

### Available Markers

- `@pytest.mark.unit` - Unit test (default for tests/unit/)
- `@pytest.mark.integration` - Integration test (default for tests/integration/)
- `@pytest.mark.slow` - Slow-running test
- `@pytest.mark.skip` - Skip this test

### Usage

```python
@pytest.mark.integration
async def test_opencode_server_connection():
    # Integration test code
    pass
```

## Running Tests

### Using pytest directly

```bash
# Run all tests
pytest tests/

# Run unit tests only
pytest tests/unit/

# Run integration tests only
pytest tests/integration/

# Run with coverage
pytest --cov=src/manifest --cov-report=html tests/

# Run specific test file
pytest tests/unit/test_opencode_llm_adapter.py

# Run specific test
pytest tests/unit/test_opencode_llm_adapter.py::test_ensure_server_running_when_running

# Skip integration tests
pytest -m "not integration" tests/
```

### Using test runner script

```bash
# Run all tests
./scripts/run_tests.sh

# Run unit tests only
./scripts/run_tests.sh -t unit

# Run with coverage
./scripts/run_tests.sh -c

# Run with verbose output
./scripts/run_tests.sh -v

# Run with specific marker
./scripts/run_tests.sh -m "not integration"
```

## Test Fixtures

Common fixtures are defined in `tests/conftest.py`:

- `mock_config_manager` - Mock ConfigManager instance
- `mock_state_manager` - Mock StateManager instance
- `tmp_path` - Temporary directory (pytest built-in)

## Test Coverage Goals

- **Unit Tests**: > 80% coverage for core modules
- **Integration Tests**: Cover critical user workflows
- **Critical Paths**: 100% coverage (error handling, edge cases)

## Writing New Tests

### Unit Test Template

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from manifest.module import Component

@pytest.fixture
def component():
    return Component()

@pytest.mark.asyncio
async def test_component_behavior(component):
    # Arrange
    expected = "expected_value"

    # Act
    result = await component.do_something()

    # Assert
    assert result == expected
```

### Integration Test Template

```python
import pytest

@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_workflow():
    # Test full workflow
    pass
```

## Test Best Practices

1. **Isolation**: Each test should be independent
2. **Naming**: Use descriptive test names (`test_what_when_expected`)
3. **AAA Pattern**: Arrange, Act, Assert
4. **Mocks**: Use mocks for external dependencies
5. **Fixtures**: Reuse common setup via fixtures
6. **Async**: Use `@pytest.mark.asyncio` for async tests
7. **Cleanup**: Clean up resources in fixtures or teardown

## Current Test Statistics

- **Total Test Files**: ~20+
- **Total Test Cases**: ~150+
- **Unit Tests**: ~140+
- **Integration Tests**: ~10+
- **Test Coverage**: Check with `pytest --cov`

## CI/CD Integration

Tests are automatically run in GitHub Actions:
- `.github/workflows/lint.yml` - Runs tests on push/PR
- Pre-commit hooks may run quick tests

## Troubleshooting

### Tests failing locally but passing in CI
- Check Python version compatibility
- Verify dependencies are installed
- Check environment variables

### Slow tests
- Use `pytest --durations=10` to identify slow tests
- Consider marking slow tests with `@pytest.mark.slow`

### Import errors
- Ensure `src/` is in Python path
- Check `pytest.ini` configuration
- Verify virtual environment is activated
