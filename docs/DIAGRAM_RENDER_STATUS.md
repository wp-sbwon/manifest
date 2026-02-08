# Diagram render – current state vs intent

## Intent (목표)

- **Single shared schema** for frontend and backend: same entity shape (`intent.blueprint`, `reality.topology_actual`, etc.).
- **Renderer is data-driven:** Renders front/back **only according to data** (e.g. `intent.blueprint.type` + `intent.blueprint.topology`). No hardcoded layout for “front” vs “back”.

---

## Schema (현재 – 공유 스키마 있음)

- **Entity** (same for front/back): `id`, `children`, `dependencies`, `intent`, `reality`, `outgoing_contracts`.
- **intent.blueprint:** `type` (e.g. `"FLOW"` | `"STACK"` | `"GRID"`), `topology`: `{ "dimensions": { "rows", "cols" }, "map": [ { "id", "area": [start_row, start_col, row_span, col_span], "label" } ] }`.
- **reality.topology_actual:** `type`, `map` (actual/code side layout).

So the **data spec** already describes how children should be laid out (flow vs stack vs grid and where each child sits). Frontend page = same schema with GRID + map; backend module flow = same schema with FLOW.

---

## Builder (현재 – topology/type 반영됨)

- **Input:** `nodes` (entities), `comp_status`, `root_id`.
- **Uses:** `root.get("children")`, `node.get("children")`, `outgoing_contracts` → L1, `row` (L2), `edges`. **And** `root.get("intent").get("blueprint")` → `layout_type`, `layout_topology`.
- **Result:** Spec includes `layout_type` (`"STACK"` | `"FLOW"` | `"GRID"`, default STACK) and `layout_topology` (dimensions + map for GRID). Same schema; layout comes from data.

Builder is **data-driven** for layout.

---

## Renderer (현재 – 데이터 기반 분기)

- **Input:** `spec` (nodes, edges, **layout_type**, **layout_topology**), `config`.
- **Behavior:** Branches on `layout_type`:
  - **STACK:** Vertical list of L1 boxes, each with flow line (──► targets) and optional row of L2 below (▼). Same as before.
  - **FLOW:** L1 as one horizontal row of boxes with ──► between them; then ▼ and each node’s L2 row.
  - **GRID:** Uses `layout_topology.dimensions` (rows, cols) and `layout_topology.map` (id → area [row, col, …]); draws a grid of cells, each cell = one L1 node by position.
- **One code path** for front/back: no separate “front” vs “back” renderer; data (type + topology) decides.

Renderer is **data-driven**; topology and type are reflected.

---

## Summary (정확한 상태)

| Layer        | Same spec (shared schema) | Data-driven (type + topology) |
|-------------|----------------------------|--------------------------------|
| **Schema**  | ✅ Yes                      | N/A                            |
| **Builder** | N/A                        | ✅ Yes – reads intent.blueprint |
| **Renderer**| N/A                        | ✅ Yes – STACK/FLOW/GRID       |

- **지금 render:** 동일 스키마로 front/back 공유. **데이터만 보고** 레이아웃 결정 (root의 intent.blueprint.type + topology).
- **Intent 충족:** Same spec of data (shared schema for back and front); renderer renders front/back **according to data** only.
