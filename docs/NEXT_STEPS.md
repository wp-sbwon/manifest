# Next Steps

This document outlines the immediate next steps for the Manifest project after the refactoring to `src/` layout and documentation organization.

## Completed ✅

1. **Project Structure Refactoring**
   - Migrated to `src/` layout
   - Organized modules into logical packages (core, ui, agents, bridge, audit)
   - Updated all imports and test paths

2. **Documentation Organization**
   - All documentation moved to `docs/` directory
   - Created comprehensive documentation (API, User Guide, Modules, Contributing)
   - Established documentation policy

3. **Import Verification**
   - All core imports verified and working
   - Module structure validated

## Immediate Next Steps

### 1. Test Suite Verification
- [ ] Install pytest in virtual environment
- [ ] Run full test suite to verify refactoring didn't break anything
- [ ] Fix any import or path issues in tests
- [ ] Verify test coverage

### 2. Git Commit
- [ ] Stage all refactoring changes
- [ ] Create meaningful commit message
- [ ] Commit to `dev` branch
- [ ] Verify no broken imports or missing files

### 3. Dependency Verification
- [ ] Ensure all dependencies are in `requirements.txt`
- [ ] Verify pytest is included
- [ ] Check for any missing dependencies

## Short-term Goals

### 1. Test Infrastructure
- Ensure all tests pass with new structure
- Add tests for new modules (agents, context_provider, task_scoper)
- Improve test coverage

### 2. Documentation Updates
- Update any outdated file paths in documentation
- Ensure all examples use correct import paths
- Verify all cross-references work

### 3. CI/CD Setup (Optional)
- Consider adding GitHub Actions for automated testing
- Set up pre-commit hooks
- Automated documentation checks

## Known Issues to Address

### High Priority
1. **Bootstrap UI Nested App Issue**
   - Status: Open
   - Workaround: Manual key configuration
   - Need: Fix event loop conflict

### Medium Priority
1. **Test Coverage**
   - Current: ~70%
   - Target: >80%
   - Focus: UI modules, agent modules

2. **Documentation Completeness**
   - Some modules need more detailed examples
   - API documentation could include more use cases

## Development Workflow

### Before Starting Work
1. Ensure virtual environment is activated
2. Set `PYTHONPATH=src` for development
3. Run tests to verify current state

### During Development
1. Write tests first (TDD approach)
2. Update documentation as needed
3. Keep documentation in `docs/` directory
4. Follow code style guidelines

### Before Committing
1. Run full test suite
2. Verify all imports work
3. Check documentation is updated
4. Ensure no files in wrong locations

## Testing Checklist

- [ ] All imports resolve correctly
- [ ] All tests pass
- [ ] No linter errors
- [ ] Documentation is up to date
- [ ] No files in project root (except README.md)

## File Structure Verification

Verify the following structure:
```
manifest/
├── README.md              # Only .md in root
├── docs/                  # All documentation
├── src/                   # All source code
├── tests/                 # All tests
├── scripts/               # Utility scripts
└── .manifest/             # Application data
```

## Next Major Features

Based on project status, these are the planned features:

1. **Multi-Agent System** (High Priority)
   - Complete agent coordination
   - Context injection hooks
   - Enhanced OMOC protocol

2. **Structural Spec-First Management** (Medium Priority)
   - Blueprint-based file system management
   - Structural drift detection

3. **Shadow Manager** (Medium Priority)
   - Sandbox operations
   - Safe promotion logic

## Notes

- All documentation should be in `docs/` directory
- Follow `DOCUMENTATION_POLICY.md` for new documentation
- Use `src/` layout for all source code
- Keep project root clean
