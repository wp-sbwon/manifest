# Contributing to Manifest

Thank you for your interest in contributing to Manifest! This document provides guidelines and instructions for contributing.

## Development Setup

See [DEV_SETUP.md](./DEV_SETUP.md) for detailed setup instructions.

### Quick Setup

```bash
# Clone the repository
git clone <repository-url>
cd manifest

# Setup environment
./scripts/setup.sh
source venv/bin/activate

# Install development dependencies
pip install -r requirements.txt
```

## Project Structure

```
manifest/
├── src/
│   └── manifest/       # Source code (src layout)
│       ├── core/       # Core modules
│       ├── ui/         # UI modules
│       ├── agents/     # Agent modules
│       ├── bridge/     # Bridge modules
│       └── audit/      # Audit modules
├── tests/              # Test files
├── docs/               # Documentation
├── scripts/            # Utility scripts
└── .manifest/          # Application data
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 2. Make Changes

- Follow the existing code style
- Write tests for new features
- Update documentation as needed

### 3. Run Tests

```bash
# Run all tests
./scripts/run_tests.sh

# Run specific test file
PYTHONPATH=src pytest tests/test_specific.py -v
```

### 4. Check Code Quality

```bash
# Ensure imports work
PYTHONPATH=src python3 -c "from manifest.ui.app import ManifestApp"

# Run linter (if configured)
# Add linting commands here
```

### 5. Commit Changes

Follow conventional commit messages:
- `feat: add new feature`
- `fix: fix bug in X`
- `docs: update documentation`
- `test: add tests for Y`
- `refactor: refactor Z module`

### 6. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

## Code Style

### Python Style

- Follow PEP 8 style guide
- Use type hints where appropriate
- Keep functions focused and small
- Add docstrings to public functions/classes

### Import Organization

```python
# Standard library imports
import asyncio
from pathlib import Path

# Third-party imports
from textual.app import App

# Local imports
from manifest.core.config import get_config_manager
```

### Naming Conventions

- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private: prefix with `_`

## Testing

### Writing Tests

- Place tests in `tests/` directory
- Name test files: `test_<module_name>.py`
- Use pytest fixtures for setup
- Test both success and failure cases

### Test Structure

```python
import pytest
from manifest.core.state_manager import StateManager

def test_state_manager_save():
    """Test that state can be saved."""
    manager = StateManager()
    # Test implementation
    assert result == expected
```

### Running Tests

```bash
# All tests
PYTHONPATH=src pytest tests/ -v

# Specific test
PYTHONPATH=src pytest tests/test_state_manager.py::test_save -v

# With coverage
PYTHONPATH=src pytest tests/ --cov=src/manifest
```

## Documentation

### Code Documentation

- Add docstrings to all public functions and classes
- Use Google-style docstrings:

```python
def function_name(param1: str, param2: int) -> bool:
    """Brief description.

    Longer description if needed.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: When something goes wrong
    """
    pass
```

### Documentation Files

- Update relevant docs in `docs/` when adding features
- Keep [API.md](./API.md) up to date
- Update [USER_GUIDE.md](./USER_GUIDE.md) for user-facing changes

## Module Guidelines

### Core Modules (`manifest.core`)

- Should have minimal dependencies
- Focus on data management and configuration
- No UI dependencies

### UI Modules (`manifest.ui`)

- Use Textual framework
- Keep widgets reusable
- Separate concerns (app, widgets, bootstrap)

### Agent Modules (`manifest.agents`)

- Coordinate agent lifecycle
- Manage context provisioning
- Scope tasks appropriately

### Bridge Modules (`manifest.bridge`)

- Handle IPC communication
- Abstract agent system protocol
- Manage process lifecycle

### Audit Modules (`manifest.audit`)

- Detect architecture drift
- Compare code against blueprint
- Report conflicts clearly

## Pull Request Process

1. **Fork and Clone**: Fork the repository and clone your fork

2. **Create Branch**: Create a feature branch from `dev`

3. **Make Changes**: Implement your changes with tests

4. **Test**: Ensure all tests pass

5. **Document**: Update relevant documentation

6. **Submit PR**: Create pull request to `dev` branch

7. **Review**: Address review comments

8. **Merge**: Maintainer will merge when ready

## PR Checklist

- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] No linter errors
- [ ] PR description explains changes

## Issue Reporting

When reporting issues, include:

- **Description**: Clear description of the issue
- **Steps to Reproduce**: How to reproduce the issue
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Environment**: Python version, OS, etc.
- **Logs**: Relevant error messages or logs

## Feature Requests

For feature requests:

- Describe the feature clearly
- Explain the use case
- Discuss potential implementation
- Consider alternatives

## Code Review Guidelines

### For Contributors

- Be open to feedback
- Address all comments
- Keep PRs focused and small
- Respond promptly to reviews

### For Reviewers

- Be constructive and kind
- Focus on code, not person
- Explain reasoning
- Approve when satisfied

## Questions?

- Check existing documentation
- Open an issue for discussion
- Ask in pull request comments

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
