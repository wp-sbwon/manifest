# Diagram: intent and implementation

## 1. What the diagram is meant to look like (intent)

- **One title box** at the top: “ARCHITECTURE FLOW” (or configurable title), with a single color (entity color).
- **Layer 1 (L1): top-level entities**
  Direct children of the blueprint root. Each is one **box** with:
  - Left: status marker (■) colored by status (healthy=green, planned=gray, partial=yellow, deviation=red).
  - Right: entity **label** (name or role/symbol from entity).
  - Box border and label use the **entity** color (e.g. blue).
- **Layer 2 (L2): children of each L1**
  Under each L1 box, optionally a **row of smaller boxes** (one per child entity), with:
  - Same status ■ and label per child.
  - These use the **child** color (e.g. cyan) to distinguish from L1.
- **Flow**
  Under an L1 box we can show “──► target1, target2” when there are edges (from `outgoing_contracts`) to other L1 nodes.
- **Layouts**
  - **STACK (default):** L1 boxes stacked vertically; under each, optional L2 row then optional flow line then ▼; then next L1.
  - **FLOW:** L1 as a horizontal row (box ──► box ──► …); below that, each L1’s L2 row if present.
  - **GRID:** L1 nodes placed in a grid from `intent.blueprint.topology` (dimensions + map with areas).

So the intended look is: **one clear title**, then **a vertical or horizontal list of “entity boxes”**, each with status + name, and under each entity optional **child boxes** in a row and optional **flow targets**, with **two colors** (entity vs child) and **status colors** for the ■.

---

## 2. How it’s implemented

### 2.1 Data flow

1. **Blueprint**
   `blueprint_design.json` / `blueprint_code.json`: `root_id`, `entities` (each with `id`, `children`, `intent`, `reality`, `outgoing_contracts`).
2. **View app**
   In `_ensure_diagram_components()` we take `entities` and `root_id`, optionally prefer code blueprint if it has entities. We compute `comp_status` (per-entity status: healthy/planned/partial/deviation) from blueprint sync.
3. **Spec**
   `build_diagram_spec(entities, comp_status, root_id, ...)` in `view/diagram/builder.py`:
   - Takes direct children of `root_id` as L1 (filtering out test-only components if desired).
   - For each L1 entity, builds a **node** with `id`, `label`, `status`, and **row**: list of L2 nodes (same shape: label, status) from that entity’s children.
   - Builds **edges** from entities’ `outgoing_contracts` (from/to between L1 ids).
   - Reads **layout_type** (STACK / FLOW / GRID) and **layout_topology** from root’s `intent.blueprint`; default STACK.
   - Returns a **spec** dict: `title`, `nodes` (each with optional `row`), `edges`, `layout_type`, `layout_topology`.
4. **Config**
   `load_diagram_config(manifest_dir)` loads `.manifest/diagram_config.json` or package default: `title`, `box_width`, **colors** (`entity`, `child`, `status` map).
5. **Render**
   `render_diagram(spec, config)` in `view/diagram/renderer.py`:
   - Produces a **string** of lines (ASCII boxes, │, ─, ┌, └, ▼, ──►).
   - Every line uses **markup** for color: `[#hex]...[/]` for entity color, child color, and status colors (e.g. `[green]■[/]`).
   - STACK: title box, then for each node either a single box or a “module + methods” style block (L1 header row + L2 row of boxes), then flow line, then ▼ between nodes.
   - FLOW: one horizontal row of L1 boxes with ──► between, then ▼, then each node’s L2 row.
   - GRID: fill a grid from `layout_topology.map` (id → area) and draw one box per cell.
6. **Display**
   In the view app, `_load_diagram_view()` returns `Content.from_markup(diagram_str)` so the **same markup string** is parsed by **Textual’s** Content/markup pipeline (not Rich’s). That way the Static widget that shows the diagram gets Textual-native content and can render **colors** (entity, child, status) correctly.

### 2.2 Why it can look “messy”

- **Label length:** Labels are truncated to fixed widths (e.g. `box_width - 6`, or 12–14 for L2). Long names get cut off and alignment can look off if widths don’t match.
- **L2 row width:** The “row” of L2 boxes is built from a fixed formula (e.g. `mw * len(methods) + spacing`). Many children or long names make the row wide or cramped.
- **Flow line:** “──► target1, target2” is appended under each L1; with many targets the line is long and can wrap or overlap in a narrow panel.
- **No scaling:** Box and character widths are fixed; there’s no responsive scaling to container size, so on small screens the diagram can look crowded or misaligned.
- **STACK spacing:** Vertical spacing is fixed (│, ▼). With many L1 nodes the diagram gets long and may feel cluttered.

So “messy” usually comes from: fixed widths, long labels, many L2 items or flow targets, and no layout scaling—all of which are limitations of the current ASCII + fixed-width implementation.

---

## 3. Color fix (what changed)

Diagram markup uses tags like `[#58a6ff]` and `[green]`. For the **main content** area we were returning **Rich’s `Text.from_markup(diagram_str)`**. Textual’s Static can show Rich renderables, but in practice color was not showing.

**Change:** Use **Textual’s `Content.from_markup(diagram_str)`** instead of Rich’s `Text`. The diagram string is unchanged; only the object passed to `Static.update()` is different. Textual then parses that string with its **own** markup (which supports `[#hex]` and named colors) and builds its internal Content with correct style spans, so the diagram colors (entity, child, status) should display as intended.

If color still doesn’t show, the next place to check is whether the **Static** that holds the diagram has `markup=True` and isn’t being overridden by a parent style (e.g. `color: ...` in CSS that forces a single color).
