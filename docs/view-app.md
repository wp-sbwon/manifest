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
| STATUS (Deviation / Partial / Healthy / Planned) | `comp_status` from BlueprintSynchronizer (blueprint_design vs blueprint_code) |
| TIME | Local time |

---

## Tabs and main

- **1:DIAGRAM** – Architecture flow diagram
- **2:FILES** – File list
- **3:TIMELINE** – Design history + Git by time
- **4:MISSION** – Goals (from blueprint root intent)

---

## Diagram

Top-left: **Status legend** (■ Planned, ■ Healthy, ■ Partial, ■ Deviation). One flow arrow (──►) between boxes on the label row.

| Shown | Data source |
|-------|-------------|
| Title | Blueprint root → `diagram_title` or default "ARCHITECTURE FLOW" |
| Nodes | `get_entities_for_view()`: entity-tree (root_id, children) or flat component list from blueprint. Components/entities from blueprint or blueprint_code. |
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
| Goal Intent | Blueprint root intent → `mission` |
| Interface Contract | Blueprint root intent → `interface` |
| Logic Style | Blueprint root intent → `architecture_style` |
| Dependencies / Side Effects / Complexity | — (fixed "—") |
| Last Output, Shadow Trace | State (shadow-*) |
| Essential Rules | Blueprint root intent → `global_rules` |

### Component (design view)

| Section | Data source |
|--------|-------------|
| Goal Intent, Interface Contract, Logic Style, Essential Rules | `blueprint_design.json` (BlueprintLoader), component matched by id |
| Actual Code (dependencies, side_effects, complexity, detected_interface) | `blueprint_code.json` (BlueprintLoader.load_code_blueprint), match by id then name |
| Last Output, Shadow Trace | State (shadow-*) |

### Diff view (Planned | Code)

| Column | Data source |
|--------|-------------|
| Planned | Same as component design: `blueprint_design.json` |
| Code | Same as Actual Code: `blueprint_code.json` (id then name fallback) |

---

## Entity model integration

The view loads design and code blueprints, runs comparison, and attaches validation per entity via `get_entities_for_view(manifest_dir)` (`src/manifest/view/entity_model.py`). That returns blueprint, code_blueprint, comp_status, validation_by_id (entity_id → { status, deviations }), view_schema, and conflicts. Validation (status, deviations) exists only in the integrated view, not in persisted blueprint/blueprint_code files.

**Diagram** shows structure (root → L1 → L2), labels (name / role / symbol), status, edges from outgoing_contracts, and layout from root intent.blueprint (type, topology). **Inspector (Design)** shows all entity fields: Identity (id, children, dependencies), Intent (design): narrative, blueprint (type, topology), protocol, profile, governance, Reality (code): symbol, protocol, profile, dependencies, traits, topology_actual, preview, plus Outgoing contracts and Validation. **Inspector (Differences)** shows plan vs code for role, mission, blueprint.type, protocol, profile.language, governance.rules, symbol, dependencies, traits.

---

## Data mapping summary

| Where | What | Source | Created by |
|-------|------|--------|------------|
| Header | STATUS | comp_status (sync) | Bottom-up (comparison) |
| Diagram | Nodes, title | blueprint | Top-down |
| Diagram | Status ■, colors | comp_status + diagram_config | Bottom-up + config |
| Inspector root | Goal, Interface, Style, Rules | blueprint (root intent) | Top-down |
| Inspector component | Design | blueprint.json | Top-down |
| Inspector component / Diff | Actual Code | blueprint_code.json | Bottom-up |
| Sidebar Health | Metrics | state.json | Bottom-up |
| Sidebar Tasks | List | tasks.json | Core/agents |

Detailed file fields: [Manifest data](manifest-data.md). How to refresh: [Scripts and pipelines](scripts-and-pipelines.md).

---

## Diagram color: previous process, what changed, why it may not show

**Previous process (when color worked):**

1. **Config:** `diagram_config.json` (or package default) had `colors.gateway`, `colors.module`, `colors.method`, and `colors.status.*`. All diagram colors came from config (no hardcoded hex in renderer).
2. **Renderer:** `render_diagram(spec, config)` in `src/manifest/view/diagram/render/tui.py` produces a **single string** of lines. Each line uses Rich/Textual markup tags, e.g. `[#58a6ff]...[/]`, `[green]■[/]`, `[#8b949e]...[/]`. The header uses `[white]` for the top box.
3. **App:** `_load_diagram_view()` returned that string. `_get_current_view_content()` returned it for the Diagram tab. `_refresh_main_content()` did `main_w.update(self._get_current_view_content())` where `main_w` is the `Static` with `id="main-content"`. The Static was created with `yield Static("", id="main-content")` (no `markup=False`), so **markup defaulted to True** and the string was parsed as markup and rendered with colors.

**What changed:**

- **Diagram (commit fc6f2d5 and later):** L1 and L2 nodes. Config keys `colors.entity` and `colors.child`; `load_diagram_config()` merges defaults. Same flow: `render_diagram()` → string → `_load_diagram_view()` → `_get_current_view_content()` → `main_w.update(...)`.
- **Current behavior:** For the Diagram tab, `_get_current_view_content()` calls `_load_diagram_view()`; when the result is a string, it returns `Text.from_markup(raw)` so the main content receives a Rich `Text` with markup applied. The main-content `Static` then displays that renderable.

**Why it might show no color now (no assumptions):**

- **Markup parsing:** Textual’s Static uses `markup=True` by default. If any **label or text from data** contains `]` or `[`, it can break tag boundaries (e.g. `[#58a6ff]label]rest[/]` closes the tag early). Escaping `[` and `]` in user-facing strings in the renderer would avoid that.
- **Widget creation:** The main-content Static is never given `markup=False`; it is created once at compose. So update() should still interpret the string as markup unless the widget’s markup flag is changed elsewhere (not done in current code).
- **CSS/theme (root cause):** The app had `Screen { background: #0d1117; color: #c9d1d9; }`. Textual merges the widget’s computed style (including `color`) with every content segment when rendering. That base style overrode markup colors, so the whole view showed only grey/white/black. **Fix:** do not set `color` on Screen; only set `background`. Content markup (diagram, sidebar, inspector) then keeps its colors.

**Summary:** Removing `color` from the Screen rule fixes app-wide color. If colors still don’t show, the terminal may not support 256/true color (check TERM, COLORTERM) or the driver may be limiting the color system.
