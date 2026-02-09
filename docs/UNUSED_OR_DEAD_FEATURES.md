# Unused or Dead Features

Summary of features, code paths, and modules that are no longer used or unreachable in the current implementation. Use this for cleanup or handoff.

---

## 1. View app – unused imports and dead UI paths

### 1.1 Imports never called in `app.py`

These are imported from `views_content` in `src/manifest/view/app.py` but **never called** in the app:

| Import | Used? | Note |
|--------|--------|------|
| `render_intent_summary` | No | Legacy (intent.json shape). Prefer `render_features_summary_from_blueprint`. |
| `load_setup_md` | No | Loads `.manifest/setup.md` / logic.md / how_it_works.md. |
| `render_deviation_summary` | No | Deviation summary text. |
| `render_modules_and_methods` | No | Table of modules/methods from blueprint_code. |
| `render_prd_summary` | No | PRD summary text. |
| `render_blueprint_diagram` | No | Blueprint diagram render. |
| `render_design_history_short` | No | Short design history. |
| `render_features_summary_from_blueprint` | No | Features from blueprint. |

**Used:** `_progress_bar`, `_status_*`, `_task_status_*`, `_entities_for_display`, `_item_display_name`, `_component_type_color`, `_status_color_tag`, `_blueprint_component_names`, `_order_entities_by_flow`, `_feature_status_from_entities`, `_blueprint_features_by_component`, `_box` (if anywhere), `_single_line_node`.

**Suggestion:** Remove the unused imports and, if nothing else uses them, consider deleting or consolidating the corresponding functions in `views_content.py` (or keep for tests/docs).

### 1.2 Dead view types (no tab, no content)

- **`ViewType.ARCHITECT`** and **`ViewType.BLUEPRINT`**
  - In `action_switch_view` map and `_get_sidebar_viz` name map.
  - **Not** in the tab bar (only 1–4: Diagram, Files, Timeline, Mission).
  - No key binding switches to them.
  - `_get_current_view_content()` does not handle them → returns `Panel("Unknown view")`.
  - **Effect:** Unreachable from UI; dead.

### 1.3 Dead method: `_load_history_view`

- **`_load_history_view()`** in `app.py` builds a rich History view (design history table + Git commits).
- **Never called** from the running app. Timeline/History content comes from **`_load_timeline_view()`** (and for HISTORY alias, same).
- Only referenced in tests (`test_view.py`, `test_view_app_smoke.py`, `test_view_app.py`) and docs.
- **Effect:** Dead in production; tests still call it.

### 1.4 Inspector mode (Visual/Data/Deviation/Detail) – unreachable in UI

- **`_load_inspector_view()`** implements alternate right-panel content for `InspectorMode.VISUAL`, `DATA`, `DEVIATION`, `DETAIL`.
- The **live** right panel always uses **`_get_info_hub_content()`** (node/root/feature inspector + D = diff).
- **`_load_inspector_view()`** is never called from the normal UI flow; only from tests.
- **`action_switch_inspector_mode()`** exists but has **no key binding** in the app, so users cannot switch to Visual/Data/Deviation/Detail.
- **Effect:** Inspector modes other than DESIGN (and the diff toggle D) are dead in the UI; code and tests still exercise them.

---

## 2. Legacy / deprecated modules

### 2.1 `manifest.ui` — **Removed**

- Was: `src/manifest/ui/` (stub only). Removed for design alignment; visualization is in `manifest.view` only.

### 2.2 `SettingsManager` (core) — **Removed**

- Was: `src/manifest/core/settings_manager.py`. Removed for design alignment; no settings UI in View; config via ConfigManager + OpenCode/CLI.

### 2.3 `render_intent_summary` (views_content)

- Documented as legacy: “Prefer `render_features_summary_from_blueprint`.”
- Only referenced in `app.py` as an unused import and in docs.
- **Effect:** Legacy; can be removed from app imports and possibly from `views_content` if no other caller.

---

## 3. CI / workflows (disabled)

- **`.github/workflows/test.yml`** and **`.github/workflows/lint.yml`** have **`if: false`** on the job, so push/PR do not run tests or lint on GitHub.
- **Effect:** Intentionally disabled; re-enable when the suite is stable.

---

## 4. Features that are used (for reference)

- **Worker Squad / Container API:** Used via `POST /api/worker_squad/run`, `ToolExecutor._run_squad_via_container_api`, and container manager (which starts `manifest.agents.runner` in containers).
- **SprintExecutor, FailureRecoveryManager:** Used by `AgentCoordinator` and `WorkerSquadExecutor`.
- **runner.py:** Used by `ContainerManager` when starting agent containers.
- **ci_monitor:** Used by `scripts/check_ci_status.py` and pre-commit (`verify_ci_readiness`).
- **doc_set:** Used by `blueprint_synchronizer`.
- **task_status_observer:** Used in `app.py` for task list with status.
- **design_history:** Used by View (timeline), architect tool, blueprint_loader, prd_manager.

---

## 5. Cleanup done (2026-02)

- **View app:** Dropped unused `views_content` imports from `app.py`. Removed `ViewType.ARCHITECT` and `ViewType.BLUEPRINT` and their map entries. Removed `_load_history_view()`. Tests updated to use main views only where content is a string.
- **Legacy:** Removed `render_intent_summary()` from `views_content.py` and its unused import from `app.py`.
- **Second pass:** Removed unused imports `box`, `blueprint_features_by_component` from `app.py`. Removed dead functions from `views_content.py`: `render_blueprint_diagram`, `render_features_summary_from_blueprint`, `load_setup_md`, `render_modules_and_methods`, `render_deviation_summary`, `render_design_history_short`, `render_prd_summary`. Removed unused imports from `views_content.py`: `json`, `Table`, `RenderableType`, `root_intent`.

## 6. Removed for design alignment (2026-02)

- **manifest.ui** — Removed. Chat TUI was deprecated by redesign; visualization is in `manifest.view` only. Package `src/manifest/ui/` deleted.
- **SettingsManager** — Removed. Design: View is visualization-only; config via ConfigManager + OpenCode/CLI. Module `src/manifest/core/settings_manager.py` deleted. (Archived tests that referenced it will fail if run.)

## 7. Remaining (optional follow-up)

- **Inspector modes** — `_load_inspector_view()` and Visual/Data/Deviation/Detail have no key binding; only tests call them. Optionally add a binding or document as test-only.
- **CI workflows** — `.github/workflows` use `if: false`. Re-enable when the suite is stable.

---

*Generated from codebase analysis; no doc assumptions.*
