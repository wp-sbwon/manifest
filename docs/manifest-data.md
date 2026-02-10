# Manifest data (.manifest)

The view app reads from the project’s `.manifest/` directory. This page lists each file, what the app uses it for, and who creates it (top-down vs bottom-up).

## Blueprint

**Source of truth (design):** `blueprint_design.json`. Root intent holds mission, goals, interface; root's children = top layer (features).

**Alignment rule:** `blueprint_design.json` and `blueprint_code.json` use the **same schema** so they can be compared mechanically. Diagram and Inspector data come from the **comparison output**, not from design or code alone.

**Depth / granularity:** No fixed max depth. Diagram can drill (Enter/Backspace). Task-level granularity is separate (`.rules/task-granularity.md`).

---

## Three blueprint docs (design, code, view)

| File | Role | Created by |
|------|------|------------|
| **blueprint_design.json** | Design (top-down). Intent filled, reality from design or empty. | Architect / design agents |
| **blueprint_code.json** | Code (bottom-up). **Exact reflection of the actual code** — produced by CodeExtractor from the codebase; same schema as design so the two are mechanically comparable. | CodeExtractor + optional LLM (e.g. `generate_higher_level_docs_from_code`) |
| **blueprint_view.json** | **Final blueprint for the view.** Mechanical comparison of design vs code + schema validation. Plan/actual pairs and validation per entity. This is the file the view side references. | `build_view_schema` on refresh (after validation) |

**Design and code:** Same shape: `version`, `root_id`, `entities`; per entity: `id`, `children`, `dependencies`, `intent`, `reality`, `outgoing_contracts`. Both files must align to this schema for comparison.

**View:** The view reads from the comparison pipeline output. That pipeline loads design and code blueprints, validates them against the schema, compares them mechanically, builds the integrated view schema (plan/actual + validation), and writes `blueprint_view.json`. The view uses that result (and the in-memory `view_schema` from `get_entities_for_view`) as its reference.

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

- **design_history.json** – Timeline; design history merged with Git by time.

---

## Schema and validation

- **Canonical schema:** `src/manifest/audit/entity_schema.py` (Entity, Intent, Reality). Blueprint = version, root_id, entities only. No `null`; required keys enforced.
- **Validation:** `entity_validation.py` — `validate_blueprint_data`, `validate_blueprint_file`, `normalize_for_schema`. Used before every write; writers must emit valid entity format or save fails.

---

## Summary: who creates what

| File | Top-down | Bottom-up |
|------|----------|------------|
| blueprint_design.json | ✓ Agents | |
| blueprint_code.json | | ✓ CodeExtractor / run_bottom_up_docs.py |
| blueprint_view.json | | (comparison output) |
| state.json (health_metrics) | | ✓ Pipeline |
| tasks.json | ✓ Core/agents | |
| diagram_config.json | Config | |
