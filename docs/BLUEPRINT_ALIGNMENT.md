# Blueprint alignment: design vs code

For deviation calculation to be meaningful, top-down (design) and bottom-up (code) blueprints must **come to the same point**: they must be comparable in identity and schema.

## Canonical identity

- **Rule:** For any component, its `id` and `name` in `blueprint.json` (design) must match the same component’s `id` and `name` in `blueprint_code.json` (code).
- **Why:** The blueprint comparator matches components by `name`. If design says `"CLI (main)"` and code says `"main"`, they are treated as different components and deviation is inflated.
- **Human-friendly text:** Put descriptions in `description`, not in `name`. Keep `name` as the exact symbol name from the codebase (e.g. `main`, `add`, `format_result`).

## Enforcement

When saving the design blueprint (`blueprint.json`), Manifest:

1. Loads `blueprint_code.json` (if present).
2. For each design component whose `id` exists in the code blueprint, checks that `name` matches.
3. If it does not match, **auto-corrects** the design component’s `name` to the code component’s `name` and logs a debug message.

So design and code docs stay aligned on identity without manual edits after code extraction.

## Schema

Both blueprints use the same component shape for comparable fields:

- **Identity:** `id`, `name`
- **Design-only (planning):** `description`, `interface`, `logic_style`, `project_rules`, etc.
- **Code-only (extraction):** `type`, `file`, `line`, `module_path`, `dependencies`, `side_effects`, etc.

The comparator only flags real differences (e.g. methods, contracts, structural fields when both sides have values). Design can omit `type`; code can omit `description`.

## References

- `src/manifest/audit/blueprint/design_identity.py` – validation and name alignment.
- `src/manifest/audit/blueprint/blueprint_metadata.py` – calls alignment when saving design blueprint.
- `src/manifest/audit/blueprint/blueprint_comparator.py` – compares by `name`; type mismatch only when both have type.
