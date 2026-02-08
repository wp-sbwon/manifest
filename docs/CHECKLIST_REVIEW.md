# Checklist Review (Blueprint-only, New Schema)

Review date: 2026-02-05. Criteria: new schema only, 3 files (top down / bottom up / comparison), diagram behavior, inspector, drill-down, granularity, entity types, layout data, no legacy, no unnecessary docstrings.

---

## 1. 모든 프로젝트 정보가 신규 데이터 스키마 기준으로, 3개의 파일(top down, bottom up, comparison)에만 기록·이용되는가? → **YES (with minor cleanup)**

- **Top-down:** `blueprint_design.json` (entity graph). Loaded via `BlueprintLoader.load_blueprint(manifest_dir)`. Root intent holds mission, goals, interface; root's children = features.
- **Bottom-up:** `blueprint_code.json` (same schema, from code). Loaded via `BlueprintLoader.load_code_blueprint(manifest_dir)`.
- **Comparison:** `blueprint_view.json` from `build_view_schema` / `write_view_schema` (plan vs actual, validation).
- **No other sources:** No `architecture.json` read or written. View, context provider, sync, agents use blueprint only.
- **Cleanup:** `doc_set` still names doc type `"architecture"` and `TOP_DOWN_FILES["architecture"] = "architecture.json"` but **loads** design blueprint; `file_watcher.WATCH_FILES` still lists `"architecture.json"`. Recommend: remove `architecture.json` from WATCH_FILES; in doc_set, document that `"architecture"` doc type returns design/code blueprint (no file named architecture.json).

---

## 2. Diagram 기본 뷰가 최상위 entity layer, 그들의 관계/플로우, 각 entity의 direct(1-layer) sub-entity를 보여주는가? → **YES**

- **builder.build_diagram_spec:** Root = `root_id` (PROJECT_ROOT or drilled entity). **Layer 1:** direct children of root (`root.get("children")`). **Layer 2:** under each L1 node, a **row** of that node's direct children (`node.get("children")`). So: top-layer entities + each entity's direct (1-layer) sub-entities are shown.
- **Relationships/flow (arrows):** Edges are derived from entities' `outgoing_contracts` (from → to) and passed in the spec as `edges`. The renderer draws **──► target1, target2** under each L1 box when that node has contracts to other L1 nodes, so flow/dependency between siblings is visible. Vertical **▼** still indicates parent→children. So both hierarchy and flow arrows are shown.

---

## 3. 한 layer의 entity를 key press로 cycle하고, 선택된 entity의 모든 정보가 inspector에 나오는가? → **YES**

- **Key bindings:** Tab / Shift+Tab and **n** / **p** → `select_next_node` / `select_prev_node` (cycle through `_diagram_selectable_nodes`). Selection is 1-based index `_selected_node_index`.
- **Inspector:** Right panel shows `_get_info_hub_content()`: for **root** → Goal Intent, Interface, Logic Style, Rules (from `root_intent(blueprint)`). For **node** (entity) → `_get_info_hub_node`: id, children, dependencies, intent (role, mission, blueprint.type, protocol, profile, governance), reality (symbol, profile, dependencies, traits, preview), outgoing_contracts, validation. For **feature** (top-layer entity) → name, id, status, requirements, children. So selected entity’s full info is shown in the inspector.

---

## 4. 선택된 entity를 "확정"하면 해당 entity 세부로 zoom in 되는가? → **YES**

- **Drill down:** **Enter** → `action_drill_down`. If current selection is a **node** (entity), sets `_diagram_root_id = nid`, pushes previous root to `_diagram_root_stack`, then `_ensure_diagram_components()` and refresh. Diagram is rebuilt with the selected entity as the new root, so its direct children become the new top layer (zoom in).
- **Drill up:** **Backspace** → `action_drill_up` pops `_diagram_root_stack` and restores previous root.

---

## 5. Granularity (layer depth, 어디까지 쪼갤지)가 잘 정의되어 있는가? → **PARTIAL**

- **Entity/layer depth:** No explicit **max depth** or **layer limit** in code. Diagram can drill arbitrarily deep (root → child → grandchild …) as long as entities have `children`. So granularity is **unbounded by code**; it’s defined by how deep the blueprint tree is.
- **Task granularity:** `.rules/task-granularity.md` and `task_scoper.validate_task_granularity` define **task** granularity (size of work items), not entity tree depth.
- **Recommendation:** Document in docs that entity layer depth is defined by the blueprint (designer/agent decides how deep to decompose); optionally add a configurable max depth for the diagram if desired.

---

## 6. 명시적 entity type 없이 frontend/backend entity를 잘 표현할 수 있는가? → **YES**

- **Schema:** Entity has `intent` (narrative.role, mission, blueprint.type, profile.platform/io_model/state_model, governance) and `reality` (symbol, profile, dependencies, traits, topology_actual). There is **no** required field like `type: "frontend"|"backend"`.
- **Differentiation:** Frontend vs backend can be expressed via e.g. `profile.platform` (e.g. "web", "api"), `reality.symbol` (file path), narrative role, or naming. Same recursive structure (id, children, intent, reality, outgoing_contracts) works for both; no explicit type declaration needed.

---

## 7. (웹 페이지 등) entity의 세부 entity들이 어떻게 배치되어야 하는지 정보가 잘 담겨 있고, diagram이 그 구조를 정확히 표현하는가? → **DATA YES, RENDER PARTIAL**

- **Data:** `intent.blueprint` has `type` (e.g. GRID | STACK | FLOW) and `topology` (dimensions, map with `area` = [start_row, start_col, row_span, col_span]). So **layout/placement** is in the schema (per entity). Backend entity can use same structure for structure/flow.
- **Diagram renderer:** `build_diagram_spec` / `render_diagram` do **not** use `topology` or `blueprint.type` for spatial layout. They show: L1 nodes in list order, each with a **row** of L2 children (horizontal row of boxes). So the **hierarchy** (who is under whom) is accurate; **exact placement** (grid position, span) from topology is not yet used to draw the diagram. So: data is there for accurate representation; diagram is accurate for structure, not yet for topology-based layout.

---

## 8. Legacy 코드/기능, reference, backward compatibility, conversion logic이 있는가? → **NO (after cleanup)**

- **Conversion/backward compat:** Removed: `architecture_from_blueprint`, `ensure_architecture_metadata`, `load_architecture_with_metadata`, `save_architecture_with_metadata`. No code path reads `architecture.json` or converts blueprint → architecture dict.
- **Remaining legacy references (to clean):**
  - **app.py:** Fixed: message "add goals in architecture.json" → "add goals in blueprint root intent".
  - **context_provider:** `architecture_file = self.manifest_dir / "architecture.json"` and docstring "Path to architecture.json (Tier 1)" — unused; can remove or rename to avoid confusion.
  - **doc_set:** Docstring still says "Architecture: top-down = architecture.json, bottom-up = architecture_code.json". Now both load blueprint; should say "architecture doc type = design/code blueprint".
  - **doc_set TOP_DOWN_FILES["architecture"] = "architecture.json"** — misleading (we don’t read that file). Can set to `blueprint_design.json` for consistency or keep key and document.
  - **architect_tool:** Docstring "Writes only to … architecture.json" — should say blueprint_design.json only.
  - **file_watcher.WATCH_FILES:** Contains `"architecture.json"` — should be removed.
  - **design_history:** Comment "design docs (prd.json, architecture.json, blueprint_design.json)" — remove architecture.json.
  - **structure_manager:** `self.architecture_file = ...` — attribute only, not used for load; can remove or repurpose.

---

## 9. Docstring/comment에 불필요한 내용이 있는가? → **MINOR CLEANUP**

- **Unnecessary:** Legacy file names in docstrings (architecture.json, architecture_code.json) where we no longer use those files — see §8.
- **Useful to keep:** Short module docstrings that state "New schema only", "No architecture.json", "Blueprint only" (e.g. architecture_metadata, metadata __init__) are appropriate.
- **Recommendation:** Remove or update docstrings/comments that refer to architecture.json or old architecture dict; keep concise descriptions of current behavior.

---

## Summary

| # | Criterion | Result |
|---|-----------|--------|
| 1 | All info from 3 files (top down, bottom up, comparison) only | **YES** (minor doc/file-list cleanup) |
| 2 | Diagram: top-layer entities, relations/flow, direct sub-entities | **YES** (structure + flow arrows from outgoing_contracts) |
| 3 | Key cycle + selected entity full info in inspector | **YES** |
| 4 | Confirm selection zooms in (new layer) | **YES** |
| 5 | Granularity / layer depth defined | **PARTIAL** (depth = blueprint tree; task granularity separate) |
| 6 | Frontend/backend without explicit type | **YES** |
| 7 | Layout/placement data + diagram accuracy | **DATA YES**, **RENDER** hierarchy yes, topology layout not yet |
| 8 | No legacy / backward compat / conversion | **NO** (after listed cleanups) |
| 9 | No unnecessary docstrings/comments | **MINOR** (remove legacy file refs) |

**Code fixes applied:** `_render_detail_content`: feature entity uses `children` (not `entity_ids`). Mission empty message: "architecture.json" → "blueprint root intent". Legacy refs removed: WATCH_FILES, doc_set, context_provider, architect_tool, design_history, structure_manager. **Arrows:** Diagram now includes flow edges from `outgoing_contracts`; builder adds `edges` to spec, renderer draws `──► target1, target2` under each L1 box when that entity has contracts to other L1 entities (so "why are there no arrows?" is addressed).

**Why arrows were missing:** The diagram only showed vertical **▼** (parent→children). Flow/dependency between same-layer entities (from `outgoing_contracts`) was not drawn. Now edges are computed in the builder and rendered as horizontal **──►** lines under each box.

**Remaining follow-ups:** (1) Optionally use `intent.blueprint.topology` in diagram renderer for spatial layout. (2) Document entity layer depth in docs (see §5).
