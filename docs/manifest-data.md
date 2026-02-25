# Manifest data (.manifest)

The view app reads from the project’s `.manifest/` directory. This page lists each file, what the app uses it for, and who creates it (top-down vs bottom-up).

## Blueprint

**Source of truth (design):** `blueprint_design.json`. Root intent holds mission, goals, interface; root's children = top layer (e.g. modules).

**Alignment rule:** `blueprint_design.json` and `blueprint_code.json` use the **same schema** so they can be compared mechanically. Diagram and Inspector data come from the **comparison output**, not from design or code alone.

**Depth / granularity:** No fixed max depth. Diagram can drill (Enter/Backspace). Task-level granularity is separate (`.rules/task-granularity.md`).

**Entity shape:** Same keys at every level (`id`, `children`, `intent`, `reality`, etc.). No explicit type or layer label in the schema. Any distinction (e.g. goal-oriented near root, implementation-oriented deeper) is by context and by the content writers produce, not by a "layer type" or index in doc creation.

---

## Three blueprint docs (design, code, view)

| File | Role | Created by |
|------|------|------------|
| **blueprint_design.json** | Design (top-down). Intent filled, reality from design or empty. | Architect / design agents |
| **blueprint_code.json** | Code (bottom-up). Same schema and entity ids as design; reality from CodeExtractor; intent from opencode enricher (ground truth from code). | bin/run_bottom_up_docs.py (on commit) |
| **blueprint_view.json** | **Final blueprint for the view.** Same keys as design/code; each comparable value is a pair plus deviation: `{ "plan", "actual", "deviates" }`. Validation (status, deviations) per entity. | `build_view_schema` (on view refresh, mock script, or bin/run_bottom_up_docs) |

**Design and code:** Same shape: `version`, `root_id`, `entities`; per entity: `id`, `children`, `dependencies`, `intent`, `reality`, `outgoing_contracts`. Both files must align to this schema for comparison.

**View:** View schema has the **same keys** as blueprint_design/blueprint_code. Values are not single values but `{ "plan": <design>, "actual": <code>, "deviates": <bool> }` so the view can show one spec and flag deviations. The pipeline loads design and code, validates, compares mechanically, builds this view schema, and writes `blueprint_view.json`. The view uses that (and in-memory `view_schema` from `get_entities_for_view`) as its reference.

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
| blueprint_code.json | | ✓ bin/run_bottom_up_docs.py (on commit) |
| blueprint_view.json | | Comparison output (view refresh; also scripts/create_mock_project_data.py, bin/run_bottom_up_docs.py) |
| state.json (health_metrics) | | ✓ Pipeline |
| tasks.json | ✓ Core/agents | |
| diagram_config.json | Config | |
