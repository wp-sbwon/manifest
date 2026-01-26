# Manifest Documentation

Welcome to the Manifest documentation! This directory contains comprehensive documentation for the Manifest project.

## Documentation Index

### Project Manifest (Strict Doc > View)
- [`project-manifest/`](project-manifest/) - Manifest 프로젝트 자체의 구조화된 문서
  - `project.json` - 프로젝트 아키텍처 및 상태
  - `documentation.json` - 프로젝트 문서 통합본
  - `visualization.md` - 아키텍처 시각화

### Getting Started

- **[User Guide](./USER_GUIDE.md)** - Complete guide for using Manifest
  - Installation and setup
  - User interface overview
  - Commands and navigation
  - Working with missions and agents
  - Troubleshooting

- **[Development Setup](./DEV_SETUP.md)** - Developer environment setup
  - Prerequisites
  - Python virtual environment setup
  - Docker setup
  - Project structure
  - Development workflow

### Technical Documentation

- **[Architecture](./ARCHITECTURE.md)** - System architecture overview
  - Project vision and core values
  - Implementation status
  - Module structure
  - Data flow and dependencies

- **[API Documentation](./API.md)** - API reference
  - Package structure
  - Core modules API
  - UI modules API
  - Agent modules API
  - Bridge modules API
  - Audit modules API
  - Data structures
  - Examples

- **[Module Documentation](./MODULES.md)** - Detailed module documentation
  - Core modules (`manifest.core`)
  - UI modules (`manifest.ui`)
  - Agent modules (`manifest.agents`)
  - Bridge modules (`manifest.bridge`)
  - Audit modules (`manifest.audit`)
  - Module dependencies

### Project Information

- **[Project Status](./PROJECT_STATUS.md)** - Current project status
  - Completed features
  - In-progress features
  - Planned features
  - Code statistics
  - Performance metrics

- **[Project Structure](./PROJECT_STRUCTURE.md)** - Project structure overview
  - Component organization by zones
  - Module structure
  - Dependency graph
  - Update methods

### Contributing

- **[Contributing Guide](./CONTRIBUTING.md)** - How to contribute
  - Development workflow
  - Code style guidelines
  - Testing requirements
  - Pull request process
  - Code review guidelines

### Setup Guides

- **[GitHub Setup](./SETUP_GITHUB.md)** - GitHub repository setup
  - GitHub CLI installation
  - Repository creation
  - Branch management

### Project History

- **[Refactoring Notes](./REFACTORING.md)** - Project refactoring history
  - Package structure changes
  - src/ layout migration
  - Import path updates

### Policies

- **[Documentation Policy](./DOCUMENTATION_POLICY.md)** - Documentation guidelines
  - Document location rules
  - File naming conventions
  - Writing guidelines

### Planning

- **[Next Steps](./NEXT_STEPS.md)** - Immediate next steps and roadmap
  - Completed tasks
  - Immediate next steps
  - Short-term goals
  - Known issues

## Quick Links

### For Users
1. Start with [User Guide](./USER_GUIDE.md)
2. Check [Development Setup](./DEV_SETUP.md) for installation
3. Refer to [Architecture](./ARCHITECTURE.md) for system understanding

### For Developers
1. Read [Development Setup](./DEV_SETUP.md)
2. Review [Architecture](./ARCHITECTURE.md)
3. Study [Module Documentation](./MODULES.md)
4. Check [API Documentation](./API.md) for reference
5. Follow [Contributing Guide](./CONTRIBUTING.md)

### For Contributors
1. Read [Contributing Guide](./CONTRIBUTING.md)
2. Review [Module Documentation](./MODULES.md)
3. Check [Project Status](./PROJECT_STATUS.md) for current state
4. Follow development workflow

## Documentation Structure

```
docs/
├── README.md                    # This file - documentation index
├── USER_GUIDE.md                # User guide
├── DEV_SETUP.md                 # Development setup
├── ARCHITECTURE.md              # Architecture overview
├── API.md                       # API reference
├── MODULES.md                   # Module documentation
├── PROJECT_STATUS.md            # Project status
├── IMPLEMENTATION_SUMMARY.md    # Implementation summary
├── CONTRIBUTING.md              # Contributing guide
├── SETUP_GITHUB.md              # GitHub setup
├── REFACTORING.md               # Refactoring history
├── DOCUMENTATION_POLICY.md      # Documentation policy
├── NEXT_STEPS.md                # Next steps and roadmap
└── archive/                     # Archived documents (v1.0)
    └── README.md                # Archive index
```

## Documentation Principles

1. **Strict Doc > View**: Primary documentation is in JSON format
   - Runtime project docs: `.manifest/intent.json`, `.manifest/blueprint.json`, `.manifest/architecture.json`
   - Manifest project docs: `docs/project-manifest/project.json`, `docs/project-manifest/documentation.json`
2. **Markdown for Reference**: Markdown files serve as human-readable references
3. **Keep Updated**: Documentation should be updated with code changes
4. **Clear Examples**: Include practical examples where helpful
5. **Cross-Reference**: Link related documentation sections

## Finding Information

### By Topic

- **Installation**: [DEV_SETUP.md](./DEV_SETUP.md)
- **Usage**: [USER_GUIDE.md](./USER_GUIDE.md)
- **Architecture**: [ARCHITECTURE.md](./ARCHITECTURE.md)
- **API Reference**: [API.md](./API.md)
- **Module Details**: [MODULES.md](./MODULES.md)
- **Contributing**: [CONTRIBUTING.md](./CONTRIBUTING.md)

### By Audience

- **End Users**: [USER_GUIDE.md](./USER_GUIDE.md)
- **Developers**: [DEV_SETUP.md](./DEV_SETUP.md), [MODULES.md](./MODULES.md)
- **Contributors**: [CONTRIBUTING.md](./CONTRIBUTING.md)
- **Architects**: [ARCHITECTURE.md](./ARCHITECTURE.md)

## Updating Documentation

When updating documentation:

1. Update the relevant Markdown file
2. Update JSON documentation:
   - Runtime project docs: `.manifest/` (for user projects)
   - Manifest project docs: `docs/project-manifest/` (for Manifest project itself)
3. Update this index if adding new documents
4. Ensure cross-references are correct
5. Test any code examples

## Questions?

- Check the relevant documentation file
- Review [Architecture](./ARCHITECTURE.md) for system understanding
- See [Contributing](./CONTRIBUTING.md) for contribution process
- Open an issue for documentation improvements
