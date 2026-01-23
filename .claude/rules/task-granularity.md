# Task Granularity Rules

This document defines rules for breaking down work into appropriately sized tasks. The Orchestrator must follow these rules when creating tasks, but may adjust based on context.

## Core Principles

1. **Single Responsibility**: Each task should have one clear, focused objective
2. **Manageable Scope**: Tasks should be completable by a Worker Squad in a reasonable time
3. **Minimal Dependencies**: Tasks should have minimal dependencies on other tasks
4. **Testable**: Each task should produce testable outcomes

## Size Guidelines

### Maximum File Modifications
- **Small Task**: 1-3 files
- **Medium Task**: 4-7 files
- **Large Task**: 8-12 files
- **Avoid**: Tasks that modify more than 12 files (consider splitting)

### Component Scope
- **Single Component**: One task per component is ideal
- **Related Components**: If components are tightly coupled, they can be in one task
- **Avoid**: Tasks that span multiple unrelated components

### Time Estimate
- **Target**: 2-8 hours of work per task
- **Small**: 2-4 hours
- **Medium**: 4-6 hours
- **Large**: 6-8 hours
- **Avoid**: Tasks estimated to take more than 8 hours (must be split)

## Dependency Rules

### Parallel Execution Requirements
For tasks to be executed in parallel within a Sprint:
- No file overlap (different files)
- No direct component dependencies
- No shared state modifications
- Independent test execution

### Sequential Execution Required
Tasks must be executed sequentially if:
- They modify the same files
- One task's output is another's input
- They share critical state
- They have component dependencies

## Task Breakdown Strategy

### When to Split a Task
1. **Too Many Files**: More than 12 files to modify
2. **Multiple Components**: Unrelated components in one task
3. **Complex Dependencies**: Task has many prerequisites
4. **Long Time Estimate**: Estimated more than 8 hours
5. **Mixed Concerns**: Task mixes different types of work (e.g., UI + backend)

### When to Combine Tasks
1. **Tightly Coupled**: Tasks are so related they can't be separated
2. **Small Tasks**: Multiple small tasks (< 2 hours each) that are related
3. **Single Feature**: Tasks that together form one complete feature

## Examples

### Good Task Granularity
```
Task 1: Implement User Authentication API
- Files: auth_service.py, auth_models.py, auth_tests.py
- Components: AuthService, AuthModel
- Estimate: 4 hours
- Dependencies: None

Task 2: Implement User Registration UI
- Files: registration_form.py, registration_view.py, registration_tests.py
- Components: RegistrationForm, RegistrationView
- Estimate: 3 hours
- Dependencies: Task 1 (uses AuthService)
```

### Bad Task Granularity
```
Task 1: Implement Entire User System
- Files: 25+ files across multiple components
- Components: Auth, Profile, Settings, Preferences
- Estimate: 20 hours
- Dependencies: Many
- Problem: Too large, too many components, too long
```

## Orchestrator Guidelines

When creating tasks, the Orchestrator should:
1. Start with the granularity rules as a baseline
2. Consider the specific context (project size, complexity, team capacity)
3. Adjust granularity based on:
   - Project maturity (new projects can have larger tasks)
   - Component complexity (simple components can be combined)
   - Risk level (high-risk work should be smaller tasks)
4. Verify parallel execution feasibility
5. Document any deviations from standard rules with justification

## Validation

Before finalizing a Sprint plan, verify:
- [ ] All tasks follow size guidelines
- [ ] Tasks marked for parallel execution meet dependency rules
- [ ] No task exceeds maximum file modification limit
- [ ] Task estimates are reasonable
- [ ] Dependencies are clearly identified
