# Refactor Review

Code review for refactoring opportunities: duplication, large files, inconsistent patterns, and separation of concerns.

---

## 1. View app – repeated “root description” (app.py)

**Pattern repeated 4+ times:**
```python
blueprint = BlueprintLoader.load_blueprint(self.manifest_dir, with_metadata=False)
root_desc = (root_intent(blueprint).get("narrative") or {}).get("mission") or ""
root_desc = (root_desc or "").strip() or "Project root."
```

**Locations:** ~607, 631, 664, and when building root node for selectable list.

**Refactor:** Add a small helper and reuse.
- **Option A:** In `entity_schema`: `mission_from_blueprint(blueprint) -> str` (and optionally `root_description_for_display(blueprint, fallback="Project root.")`).
- **Option B:** In app.py: `_get_root_description(self) -> str` that uses cached `_view_data["blueprint"]` when available, else loads and returns mission or fallback.

**Impact:** Removes duplication and one place to change if we add narrative fields later.

---

## 2. View app – duplicate load + status in `_selected_node_is_deviating` (app.py)

**Current:** For both `kind == "feature"` and the component branch we do:
```python
top_down = BlueprintLoader.load_blueprint(...)
bottom_up = BlueprintLoader.load_code_blueprint(self.manifest_dir)
status_info = self._get_blueprint_sync().calculate_implementation_status(top_down, bottom_up)
comp_status = status_info.get("node_statuses", {})
```

So we load and compute twice when checking deviation for a non-root node.

**Refactor:** Compute once at the start of the method when `kind != "root"`:
```python
if kind == "root":
    return False
top_down = BlueprintLoader.load_blueprint(...)
bottom_up = BlueprintLoader.load_code_blueprint(self.manifest_dir)
status_info = self._get_blueprint_sync().calculate_implementation_status(top_down, bottom_up)
comp_status = status_info.get("node_statuses", {})
if kind == "feature":
    feat_status = _feature_status_from_entities(top_down, comp_status)
    return feat_status.get(nid) == "deviation"
return comp_status.get(nid) == "deviation"
```

**Impact:** One load + one status calculation per call instead of two.

---

## 3. BlueprintSyncTool – repeated load of both blueprints (blueprint_sync.py)

**Pattern repeated in 3 methods:** `compare_blueprints`, `detect_deviation`, `sync_blueprint` each do:
```python
top_down = BlueprintLoader.load_blueprint(self.manifest_dir, ...)
bottom_up = BlueprintLoader.load_code_blueprint(self.manifest_dir)
```

**Refactor:** Add a private helper and reuse:
```python
def _load_both_blueprints(self, with_metadata: bool = True) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    top = BlueprintLoader.load_blueprint(
        self.manifest_dir,
        with_metadata=with_metadata,
        default_source="llm_design" if with_metadata else None,
    )
    bottom = BlueprintLoader.load_code_blueprint(self.manifest_dir)
    return top, bottom
```
Then `compare_blueprints`, `detect_deviation`, and `sync_blueprint` call `_load_both_blueprints(with_metadata=...)` and use the result.

**Impact:** Single place for load logic and options (e.g. with_metadata); easier to add caching later if needed.

---

## 4. View app size and separation (app.py ~1650 lines) — **DONE**

**Done:** Stateless view content builders were extracted into `view/views_content.py`:
- **views_content.py:** Pure functions for display (entities_for_display, blueprint_component_names, status_label, status_color_tag, progress_bar, render_blueprint_diagram, render_deviation_summary, render_prd_summary, load_setup_md, render_modules_and_methods, render_design_history_short, render_intent_summary, render_features_summary_from_blueprint, item_display_name, component_type_color, etc.). No app state; only manifest_dir, blueprint, or dicts.
- **app.py:** Imports these from `views_content` (with `_` aliases so call sites unchanged). Keeps ViewType, InspectorMode, ManifestViewApp (lifecycle, state, compose, bindings), _load_* methods that delegate to views_content or use self, and run_view.

**Impact:** app.py is smaller; view content is testable in isolation; app focused on wiring and UI lifecycle.

---

## 5. Intent “features” vs blueprint (consistency)

**Current:** `_render_intent_summary` (app.py) uses `intent.get("features", [])` and `f.get("entity_ids", [])` – i.e. the **intent.json** shape (legacy “features” list with entity_ids). Elsewhere we use blueprint and `top_layer_entities` for “features”.

**Refactor (optional):** If the Mission/summary view should be blueprint-only, derive the same summary from blueprint (e.g. `top_layer_entities(blueprint)` + entity `children`) and drop dependency on intent.json “features”. If intent is still the source of truth for that screen, document it and leave as is.

**Impact:** Clarifies single source of truth and avoids two parallel notions of “features”.

---

## 6. entity_schema – optional display helpers — **partially done**

**Current:** Callers often do `root_intent(blueprint).get("narrative") or {}` then `.get("mission")` or `.get("role")`, and similar for goals, profile, governance.

**Refactor:** Add thin helpers to keep entity_schema the single place for “how to read intent”:
- `mission_from_blueprint(blueprint) -> str` — **done**
- `goals_from_blueprint(blueprint) -> List` — **done** (used in Mission view)
- `interface_from_blueprint(blueprint)` (role) — optional, add if used in multiple places

**Impact:** Less repeated dict chains; one place to adjust if intent shape changes.

---

## 7. Diagram renderer – FLOW/GRID

**Current:** `_render_flow` and `_render_grid` were added for data-driven layout. FLOW row alignment (padding under each L1 box) and GRID placement are correct for the spec; no structural duplication found.

**Refactor:** None required for duplication. Optional: share a single “draw a row of boxes” helper between STACK row, FLOW L1 row, and GRID row to reduce box-drawing duplication if we add more layout types.

---

## Summary table

| # | Area | Issue | Refactor | Priority |
|---|------|--------|----------|----------|
| 1 | app.py | Root description repeated 4x | Helper (entity_schema or app) | High |
| 2 | app.py | Load + status 2x in _selected_node_is_deviating | Compute once, branch on kind | High |
| 3 | blueprint_sync.py | Load both blueprints 3x | _load_both_blueprints() | Medium |
| 4 | app.py | ~1650 lines, many _load_* | Extract view content module(s) | **Done** (views_content.py) |
| 5 | app.py / intent | intent “features” vs blueprint features | Unify or document source | Low |
| 6 | entity_schema | Repeated intent dict chains | mission_from_blueprint, goals_from_blueprint | **Done** (role optional) |
| 7 | diagram/renderer | FLOW/GRID | Optional shared row helper | Low |

---

## Recommended order

1. **Quick wins (done):** (1) `mission_from_blueprint` in entity_schema + use in app, (2) Single load+status in `_selected_node_is_deviating`, (3) `_load_both_blueprints` in BlueprintSyncTool.
2. **Next:** (6) More entity_schema display helpers if call sites grow.
3. **Larger:** (4) Split view content from app.py; (5) decide intent vs blueprint for Mission/summary.
