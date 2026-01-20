# Manifest Policy

This is the foundational policy document that is injected into every agent context.

## Core Principles

1. **Blueprint-First Development**: All code changes must align with the blueprint.json specification
2. **Structural Spec Compliance**: File system changes must be proposed in blueprint.json before execution
3. **Visual Truth**: Agents must respect the current state of components (GHOST, ACTIVE, etc.)
4. **Tiered Context**: Agents receive context based on their mission stage and role

## Development Rules

- Never modify architecture without updating blueprint.json first
- Always check component status before attempting to use dependencies
- Report structural drift immediately
- Follow the tiered context system for efficient operation

## Validation

All agent actions are validated against the blueprint.json schema. Actions that don't match will be rejected.