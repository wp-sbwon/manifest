# Documentation Policy

## Document Location

**All project documentation must be placed in the `docs/` directory.**

### Rules

1. **No documentation files in project root**
   - All `.md` files (except `README.md` in root) should be in `docs/`
   - This keeps the project root clean and organized

2. **Root README.md exception**
   - `README.md` in project root is allowed for quick project overview
   - It should link to `docs/` for detailed documentation

3. **Documentation types in `docs/`**
   - User guides
   - API documentation
   - Architecture documentation
   - Development guides
   - Contributing guides
   - Setup instructions
   - Project history (refactoring, changelog, etc.)

## File Naming

- Use `UPPER_SNAKE_CASE.md` for documentation files
- Examples: `USER_GUIDE.md`, `API.md`, `DEV_SETUP.md`
- Keep names descriptive and consistent

## Documentation Index

- `docs/README.md` serves as the documentation index
- Update it when adding new documentation files
- Include all new documents in the index

## Writing New Documentation

When creating new documentation:

1. **Place in `docs/` directory**
   ```bash
   # ✅ Correct
   docs/NEW_DOCUMENT.md

   # ❌ Wrong
   NEW_DOCUMENT.md  # in project root
   ```

2. **Update `docs/README.md`**
   - Add entry to documentation index
   - Include brief description
   - Link appropriately

3. **Update root `README.md` if needed**
   - Add link if it's important for quick access
   - Keep root README concise

4. **Follow existing structure**
   - Use consistent formatting
   - Include table of contents for long documents
   - Cross-reference related documents

## Examples

### ✅ Good Practice

```
manifest/
├── README.md              # Brief overview, links to docs/
├── docs/
│   ├── README.md          # Documentation index
│   ├── USER_GUIDE.md
│   ├── API.md
│   └── NEW_FEATURE.md     # New documentation
└── src/                   # Source code
```

### ❌ Bad Practice

```
manifest/
├── README.md
├── USER_GUIDE.md         # ❌ Should be in docs/
├── API.md                # ❌ Should be in docs/
├── docs/
│   └── README.md
└── src/
```

## Enforcement

- Code reviews should check documentation location
- New documentation in wrong location should be moved
- Update this policy if patterns change

## Rationale

1. **Clean project root**: Keeps root directory focused on essential files
2. **Easy navigation**: All documentation in one place
3. **Better organization**: Clear separation of code and documentation
4. **Scalability**: Easy to add documentation without cluttering root
