# MVP Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove all dead code, fix legacy references, unify the calculator fixture, and tighten the public API — leaving a clean, minimal MVP codebase.

**Architecture:** Surgical deletions and consolidations. No new features. Every change is a removal or simplification. Tests run green after each task.

**Tech Stack:** Python 3.10+, pytest, Textual TUI

---

## Task 1: Remove dead dataclasses from entity_schema.py

**Files:**
- Modify: `src/manifest/audit/entity_schema.py:8-72,88-93`

Remove `ProtocolItem`, `TopologyMapItem`, `Entity`, `Contract`, `Validation`, `BlueprintRoot` dataclasses. Remove `from dataclasses import dataclass, field`. Keep dict-based helpers.

## Task 2: Remove dead methods and imports from app.py

**Files:**
- Modify: `src/manifest/view/app.py`
- Modify: `src/manifest/view/content/header_content.py:50`

Remove: `_get_sidebar_viz()`, `_load_inspector_view()`, `_get_design_and_code_for_status()`, `ViewType.HISTORY`, `ViewType.INSPECTOR`, `InspectorMode.DESIGN`, `InspectorMode.DATA`, unused imports (`Group`, `Set`, `get_sidebar_viz_text`).

## Task 3: Remove dead functions and variables across codebase

**Files:**
- `sidebar_content.py:56-58` — delete `get_sidebar_viz_text()`
- `views_content.py:8-10` — delete unused logger
- `logger.py:99-100` — delete `_core_logger`
- `state_manager.py:42-43` — delete `get_health_metrics()`
- `manifest_filenames.py:6` — delete `TEST_RESULTS_FILE`
- `blueprint_metadata.py:11` — delete unused `read_json_or_default` import
- `file_watcher.py:19,43,53-57` — delete `WATCH_DIR` and `conflicts` references
- `content/__init__.py` — trim `__all__` and imports

## Task 4: Consolidate duplicate status_label logic

**Files:**
- Modify: `src/manifest/view/content/header_content.py`

Replace inline status if/elif with `status_label`/`status_color_tag` from `views_content.py`.

## Task 5: Move blueprint_status.py to test tree

**Files:**
- Move: `src/manifest/audit/blueprint/blueprint_status.py` → `tests/blueprint_helpers_status.py`
- Modify: test imports in `test_blueprint_status.py`, `test_design_code_alignment.py`

## Task 6: Consolidate duplicate load_blueprint

**Files:**
- Modify: `src/manifest/audit/blueprint/blueprint_loader.py`

Make `BlueprintLoader` delegate to `blueprint_io.load_blueprint`/`load_code_blueprint` instead of reimplementing.

## Task 7: Fix pyproject.toml

**Files:**
- Modify: `pyproject.toml:47-49`

Remove non-existent `opencode-ai>=1.0.0` optional dependency.

## Task 8: Unify calculator fixture

**Files:**
- Modify: `scripts/create_mock_project_data.py`
- Delete: diverged `tmp/calculator/` source files
- Modify: `.gitignore`

Copy source files from `tests/fixtures/calculator/` to `tmp/calculator/` in the script. Delete stale `tmp/calculator/blueprint_view.json`.

## Task 9: Add governance assertions to calculator

**Files:**
- Modify: `scripts/create_mock_project_data.py`

Add meaningful `governance.assertions` to all 5 entities missing them.

## Task 10: Final verification

Full test suite, ruff lint, headless TUI smoke test.
