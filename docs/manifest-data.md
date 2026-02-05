# Manifest data (.manifest)

The view app reads from the project’s `.manifest/` directory. This page lists each file, what the app uses it for, and who creates it (top-down vs bottom-up).

## architecture.json

**Used for:** Diagram (features, nodes), Inspector root (Goal, Interface, Logic Style, Rules), Mission (goals), status.

| Field | Purpose |
|-------|---------|
| `mission` | Root Inspector: Goal Intent |
| `interface` | Root Inspector: Interface Contract |
| `architecture_style` | Root Inspector: Logic Style |
| `global_rules` | Root Inspector: Essential Rules |
| `features` | Diagram nodes; each has id, name, components[], status, requirements |
| `goals` | Mission tab (id, name, description, status) |
| `diagram_title` | Diagram title (optional) |

**Created by:** Top-down (Architect / agents). Core may fix metadata on load (e.g. goals shape).

---

## blueprint.json (plan)

**Used for:** Diagram (entity list, ordering via root_id/children/contracts), Inspector design (intent), Diff view “Planned” column.

**Format (new entity schema):** Top-level `version`, `root_id` (e.g. `PROJECT_ROOT`), `entities`, `contracts`. No null; use empty string/list/object.

**Per entity:** `id`, `children` (list of child entity IDs), `dependencies` (list of entity IDs), `intent` (narrative, blueprint, protocol, profile, governance), `reality` (empty defaults for plan). Plan file: intent filled, reality empty.

**Contracts:** Array of `{ "from", "to", "type", "file?", "symbols?" }` (same keys in both files).

**Created by:** Top-down (Architect / design agents). All writers must emit this format; validation runs before save. Legacy format (components instead of entities) is migrated on load or via `python -m manifest.audit.blueprint_migrate --manifest-dir .manifest`.

---

## blueprint_code.json (actual)

**Used for:** Diagram/header status (via sync comparison), Inspector “Actual Code” and Diff view “Code” column.

**Format:** Same top-level shape as blueprint.json (key symmetry). Per entity: `reality` filled (symbol, protocol, traits, dependencies), `intent` empty defaults (Phase 1).

**Created by:** Bottom-up only (CodeExtractor / run_bottom_up_docs.py). Do not hand-write. Validated before save.

---

## state.json

**Used for:** Sidebar “Project Health” (health_metrics), Inspector “Last Output” / “Shadow Trace” (shadow-* state).

| Key | Purpose |
|-----|---------|
| `health_metrics` | code_quality, test_coverage, binary_size |
| shadow-* | Execution / shadow run output for Inspector |

**Created by:** Bottom-up pipeline writes `health_metrics`; execution writes shadow state.

---

## tasks.json

**Used for:** Sidebar “Tasks”.

**Created by:** Core / task agents.

---

## diagram_config.json

**Used for:** Diagram colors and styling (gateway, module, method, status colors).

**Created by:** Config (edit as needed). Optional; defaults in code if missing.

---

## Other .manifest files

- **intent.json** – Top-down intent; not directly shown in Diagram/Inspector.
- **intent_code.json**, **architecture_code.json** – Bottom-up (LLM from code); created by same script as blueprint_code, not hand-written.
- **design_history.json** – Timeline; design history merged with Git by time.

---

## Schema and validation

- **Canonical schema:** `src/manifest/audit/entity_schema.py` (Entity, Intent, Reality, BlueprintRoot). No `null`; required keys enforced.
- **Validation:** `entity_validation.py` — `validate_blueprint_data`, `validate_blueprint_file`, `normalize_for_schema` (null → defaults). Used before every write and on read.
- **Migration:** One-time conversion from legacy (flat `components`, `zones`) to new format: `python -m manifest.audit.blueprint_migrate --manifest-dir .manifest`. Loader can run migration in place when legacy is detected.

---

## Summary: who creates what

| File | Top-down | Bottom-up |
|------|----------|------------|
| architecture.json | ✓ Agents | (architecture_code.json is separate) |
| blueprint.json | ✓ Agents | |
| blueprint_code.json | | ✓ CodeExtractor / run_bottom_up_docs.py |
| state.json (health_metrics) | | ✓ Pipeline |
| tasks.json | ✓ Core/agents | |
| diagram_config.json | Config | |
