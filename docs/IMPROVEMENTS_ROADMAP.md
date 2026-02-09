# What we can improve

Prioritized list of improvements based on current docs and codebase. Each is optional; implement when it adds value.

---

## 1. High impact

### 1.1 Externalize key hardcoded values

- **Ports/hosts:** Move default Container API port (4097) and host API port (8000) to a single place (e.g. `core/config.py` or env) so `tool_executor` and `launcher` share one source of truth.
- **Default provider/model:** Keep defaults in config but document that `agent_config.json` overrides them; ensure no duplicate defaults (e.g. `anthropic` in both config and opencode_llm_adapter).
- **Timeouts:** Add config keys for the most important timeouts (Container API call, worker squad stages, OpenCode server start) so operators can tune without code changes.

Ref: `docs/HARDCODED_CONTENTS.md`.

### 1.2 Re-enable CI when the suite is stable

- GitHub Actions test and lint workflows use `if: false`. Current local CI runs only `tests/test_startup.py`; full suite lives under `tests/archive/`.
- **Options:** (a) Gradually promote a subset of archive tests into the main tree and re-enable workflows; (b) Keep archive as-is and document that “CI” = local `check_ci_status.py` + startup test only.

Ref: `docs/UNUSED_OR_DEAD_FEATURES.md` §3, `scripts/check_ci_status.py`.

### 1.3 Remove or wire up dead View code

- **Unused imports:** Already removed from `app.py`. Any remaining dead helpers in `views_content.py` (e.g. `render_intent_summary`, `render_blueprint_diagram`) can be deleted if nothing else uses them.
- **Dead view types:** `ViewType.ARCHITECT` and `ViewType.BLUEPRINT` are in maps but have no tab/key; either remove from maps or add a tab/key.
- **Inspector modes:** `_load_inspector_view()` and Visual/Data/Deviation/Detail modes have no key binding; add a binding for `action_switch_inspector_mode()` or remove the dead branch and document that only DESIGN + diff (D) are supported.

Ref: `docs/UNUSED_OR_DEAD_FEATURES.md` §1.

---

## 2. Medium impact

### 2.1 Single source for manifest file names

- Blueprint names live in `audit/blueprint/manifest_filenames.py`; `state.json`, `agent_config.json`, `tasks.json` are scattered. Consider a small `core/manifest_filenames.py` (or extend the existing one) that exports all canonical manifest file names so paths stay consistent.

### 2.2 Document archived tests policy

- Rule: do not edit `tests/archive/` (`.cursor/rules/no-edit-archived-tests.mdc`). Some archived tests (e.g. `test_settings_manager.py`) import removed modules and will fail if run. Add a short note in `tests/archive/README.md` that archive may contain tests for removed features and are kept for history only.

### 2.3 Context size calculator maintenance

- `MODEL_TOKEN_LIMITS` in `context_size_calculator.py` is a hardcoded map. New models will need manual updates. Consider loading from a JSON file or documenting that this file must be updated when adding provider support.

---

## 3. Lower priority / polish

### 3.1 View version

- `APP_VERSION = "0.0"` in `view/app.py`; tie to a single version source (e.g. `pyproject.toml` or `src/manifest/__init__.py`) if you want consistent versioning.

### 3.2 Runner / container paths

- Container paths (`/app`, `/app/.manifest`, `PYTHONPATH=/app/src`) are fixed by the container image. Only worth making configurable if you support multiple layouts.

### 3.3 Dead method `_load_history_view`

- Still present; only tests and docs reference it. Either remove it and adjust tests (outside archive) or document that it’s kept for tests.

---

## 4. Summary table

| Area              | Action |
|-------------------|--------|
| Hardcoded values  | Centralize ports, document overrides; optional config for timeouts. |
| CI                | Re-enable GitHub workflows when test suite is stable; or document current “startup-only” CI. |
| View dead code    | Remove unused view types or add UI; add inspector key or remove alternate modes. |
| File names        | Single module for all manifest file names. |
| Archive tests     | Document that archive may reference removed code. |
| Token limits      | Document or externalize model list for context size. |
| Version           | Single source for app version if needed. |
