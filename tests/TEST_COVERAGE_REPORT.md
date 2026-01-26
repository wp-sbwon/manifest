# Test Coverage Report

Generated: $(date)

## Test Statistics

### Overall
- **Total Test Files**: Check with `pytest --co`
- **Total Test Cases**: Check with `pytest --co`
- **Test Execution Time**: Check with `pytest --durations=10`

### By Category
- **Unit Tests**: Located in `tests/unit/`
- **Integration Tests**: Located in `tests/integration/`

## Module Coverage

### Runtime Components

#### ✅ Well Tested
- `opencode_llm_adapter.py` - Comprehensive unit tests in `test_opencode_llm_adapter.py`
- `executor_factory.py` - Unit tests in `test_executor_factory.py`

#### ⚠️ Needs More Coverage
- `agent/core/executor.py` - Direct executor implementation
- `agent/core/base_executor.py` - Base class interface
- `tools/tool_executor.py` - Tool execution logic

### Core Components

#### ✅ Well Tested
- Configuration management (via mocks in tests)

#### ⚠️ Needs More Coverage
- State management
- Logger utilities
- Exception handling

## Test Quality Metrics

### Coverage Goals
- **Target**: > 80% for core modules
- **Critical Paths**: 100% coverage
- **Error Handling**: All error paths tested

### Test Types
- **Unit Tests**: Fast, isolated, mocked dependencies
- **Integration Tests**: End-to-end scenarios, real services

## Running Coverage Report

```bash
# Generate HTML coverage report
pytest --cov=src/manifest --cov-report=html tests/

# View in browser
open htmlcov/index.html

# Terminal report
pytest --cov=src/manifest --cov-report=term-missing tests/
```

## Missing Test Areas

### High Priority
1. **AgentExecutor** - Direct LLM executor needs unit tests
2. **Tool Execution** - Tool executor needs comprehensive tests
3. **Error Handling** - Exception paths need coverage
4. **State Management** - State persistence needs tests

### Medium Priority
1. **Configuration** - ConfigManager edge cases
2. **Logging** - Logger utilities
3. **Workflow Components** - Workflow execution

### Low Priority
1. **UI Components** - Textual UI widgets
2. **Bridge Components** - Agent bridge integration

## Test Execution Commands

```bash
# Quick test run
pytest tests/ -q

# Full test run with coverage
pytest --cov=src/manifest --cov-report=html tests/

# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Specific module
pytest tests/unit/test_opencode_llm_adapter.py
```

## CI/CD Integration

Tests run automatically:
- On every push to GitHub
- In pre-commit hooks (if configured)
- In GitHub Actions workflows

## Notes

- Update this report after major test additions
- Run coverage regularly to track progress
- Focus on critical paths first
