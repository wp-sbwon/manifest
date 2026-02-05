# View app

The Manifest view is a TUI: Header, Sidebar (Health, Tasks), Main (Diagram / Files / Timeline / Mission), Inspector (right). Everything on screen comes from [.manifest data](manifest-data.md).

## Layout

- **Header:** Manifest View, [ Planning ] / [ Differences ], STATUS, TIME
- **Left sidebar:** Project Health, Tasks
- **Main:** Tab content (Diagram, Files, Timeline, Mission)
- **Right panel (Inspector):** Selected node’s design + actual code (or root), [D] toggles Diff view

Keys: **n** next node, **p** previous node, **D** Differences, **Tab** next tab, **S** refresh.

---

## Header

| Shown | Data source |
|-------|-------------|
| Planning / Differences | App state (Inspector mode) |
| STATUS (Deviation / Partial / Healthy / Planned) | `comp_status` from BlueprintSynchronizer (blueprint vs blueprint_code vs architecture) |
| TIME | Local time |

---

## Tabs and main

- **1:DIAGRAM** – Architecture flow diagram
- **2:FILES** – File list
- **3:TIMELINE** – Design history + Git by time
- **4:MISSION** – Goals (from architecture)

---

## Diagram

| Shown | Data source |
|-------|-------------|
| Title | `architecture.json` → `diagram_title` or default "ARCHITECTURE FLOW" |
| Nodes | `get_entities_for_view()`: when architecture has features, uses features + blueprint components; else entity-tree (root_id, children) or flat component list from blueprint. Components/entities from blueprint or blueprint_code. |
| Node status (■) | `comp_status` from BlueprintSynchronizer (same as header) |
| Colors | `diagram_config.json` |

Selectable nodes: root (PROJECT_ROOT) then each diagram component. Inspector shows the selected node. View uses a single integration source (`get_entities_for_view`) for blueprint, code_blueprint, comp_status, and per-entity validation (status, deviations).

---

## Sidebar

| Section | Data source |
|---------|-------------|
| Project Health | `state.json` → `health_metrics` (code_quality, test_coverage, binary_size) |
| Tasks | `tasks.json` |

---

## Inspector

Selection: **Root** (System Core) or **Component** (diagram node). **[D]** toggles Design view vs **Differences** (Planned | Code).

### Root (PROJECT_ROOT)

| Section | Data source |
|--------|-------------|
| Goal Intent | `architecture.json` → `mission` |
| Interface Contract | `architecture.json` → `interface` |
| Logic Style | `architecture.json` → `architecture_style` |
| Dependencies / Side Effects / Complexity | — (fixed "—") |
| Last Output, Shadow Trace | State (shadow-*) |
| Essential Rules | `architecture.json` → `global_rules` |

### Component (design view)

| Section | Data source |
|--------|-------------|
| Goal Intent, Interface Contract, Logic Style, Essential Rules | `blueprint.json` (BlueprintLoader), component matched by id |
| Actual Code (dependencies, side_effects, complexity, detected_interface) | `blueprint_code.json` (BlueprintLoader.load_code_blueprint), match by id then name |
| Last Output, Shadow Trace | State (shadow-*) |

### Diff view (Planned | Code)

| Column | Data source |
|--------|-------------|
| Planned | Same as component design: `blueprint.json` |
| Code | Same as Actual Code: `blueprint_code.json` (id then name fallback) |

---

## Entity model integration

The view loads design and code blueprints, runs comparison, and attaches validation per entity via `get_entities_for_view(manifest_dir)` (`src/manifest/view/entity_model.py`). That returns blueprint, code_blueprint, comp_status, validation_by_id (entity_id → { status, deviations }), architecture, and conflicts. Validation (status, deviations) exists only in the integrated view, not in persisted blueprint/blueprint_code files.

---

## Data mapping summary

| Where | What | Source | Created by |
|-------|------|--------|------------|
| Header | STATUS | comp_status (sync) | Bottom-up (comparison) |
| Diagram | Nodes, title | architecture + blueprint | Top-down |
| Diagram | Status ■, colors | comp_status + diagram_config | Bottom-up + config |
| Inspector root | Goal, Interface, Style, Rules | architecture.json | Top-down |
| Inspector component | Design | blueprint.json | Top-down |
| Inspector component / Diff | Actual Code | blueprint_code.json | Bottom-up |
| Sidebar Health | Metrics | state.json | Bottom-up |
| Sidebar Tasks | List | tasks.json | Core/agents |

Detailed file fields: [Manifest data](manifest-data.md). How to refresh: [Scripts and pipelines](scripts-and-pipelines.md).
