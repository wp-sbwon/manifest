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

## Three blueprint docs (design, code, view)

| File | Role | Created by |
|------|------|------------|
| **blueprint_design.json** | Design (top-down). Intent filled, reality empty. | Architect / design agents |
| **blueprint_code.json** | Code (bottom-up). Reality filled, intent empty. | CodeExtractor |
| **blueprint_view.json** | Comparison output: plan/actual pairs + validation. | `build_view_schema` on refresh |

**Design and code:** Same shape: `version`, `root_id`, `entities`; per entity: `id`, `children`, `dependencies`, `intent`, `reality`, `outgoing_contracts`.

**View schema:** `view_schema.build_view_schema` → `blueprint_view.json`.

---

## state.json

**Used for:** Sidebar "Project Health" (health_metrics), Inspector "Last Output" / "Shadow Trace" (shadow-* state).

| Key | Purpose |
|-----|---------|
| `health_metrics` | code_quality, test_coverage, binary_size |
| shadow-* | Execution / shadow run output for Inspector |

**Created by:** Bottom-up pipeline writes `health_metrics`; execution writes shadow state.

---

## tasks.json

**Used for:** Sidebar "Tasks".

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

- **Canonical schema:** `src/manifest/audit/entity_schema.py` (Entity, Intent, Reality). Blueprint = version, root_id, entities only. No `null`; required keys enforced.
- **Validation:** `entity_validation.py` — `validate_blueprint_data`, `validate_blueprint_file`, `normalize_for_schema`. Used before every write; writers must emit valid entity format or save fails.

---

## Summary: who creates what

| File | Top-down | Bottom-up |
|------|----------|------------|
| architecture.json | ✓ Agents | (architecture_code.json is separate) |
| blueprint_design.json | ✓ Agents | |
| blueprint_code.json | | ✓ CodeExtractor / run_bottom_up_docs.py |
| blueprint_view.json | | (comparison output) |
| state.json (health_metrics) | | ✓ Pipeline |
| tasks.json | ✓ Core/agents | |
| diagram_config.json | Config | |
