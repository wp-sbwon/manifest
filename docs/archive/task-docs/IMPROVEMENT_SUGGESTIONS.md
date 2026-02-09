# Improvement Suggestions (from codebase inspection)

Suggestions from reviewing the code and project structure only (no prior doc assumptions).

---

## 1. Version and dependency consistency

- **Done:** `__init__.py` set to `__version__ = "0.1.0"` to match `pyproject.toml`. `requirements.txt` comment updated for opencode (optional install).
- **Remaining:** Python version: `requires-python = ">=3.10"` in pyproject; ensure dev/CI use 3.10+. If you need 3.9, relax requires-python and test on 3.9.

---

## 2. CI and tests

- **GitHub Actions** (`.github/workflows/test.yml`): test job has `if: false`, so push/PR do not run tests. Re-enable when the suite is stable (e.g. set `if: true` or remove the condition).
- **Local CI** (`scripts/check_ci_status.py`) runs only `pytest tests/test_startup.py`. The workflow, when enabled, runs `pytest tests/` (excluding `tests/archive/`). Consider aligning: e.g. run the same subset in CI, or add a few critical tests to the pre-push run so regressions are caught earlier.
- **`core/ci_monitor.py`**: `check_ci_status_local()` runs `pytest tests/ -q` (full tree); `check_ci_status.py` runs only `test_startup.py`. Two different “local CI” definitions. Prefer one: e.g. have `check_ci_status.py` call into ci_monitor with a single test command/spec.
- **`ci_monitor.check_imports()`** lists both `("manifest.runtime.agent.core.executor_factory", "ExecutorFactory")` and `("manifest.runtime.agent.core", "ExecutorFactory")`. The second covers the first (lazy `__getattr__`). Remove the duplicate to avoid confusion.

---

## 3. Error handling and logging — **partially done**

- **Done:** Replaced silent `except: pass` with `logger.debug(..., e)` in: view/app.py (detail merge, timeline/history git, state.json health, info hub), views_content.py (blueprint_component_names, load_setup_md, render_modules_and_methods, render_design_history_short), core/config.py (get_api_keys, _load_agent_config, validate_key, get_setting, set_setting), core/settings_manager.py (get_spec_first_settings, get_shadow_settings), core/design_history.py (load), audit/blueprint/blueprint_synchronizer.py (build_conflict_report), core/ci_monitor.py (get_github_repo_info).
- **Remaining:** Other modules (context_provider, file_watcher, tool_executor, launcher, etc.) still have silent catches; add logging there as you touch those paths. Scripts: consider logging in `check_ci_status.py` for get_github_repo_info/get_github_token failures.

---

## 4. Test suite and coverage

- **Active tests:** Only `tests/test_startup.py` and `tests/test_entity_schema_validation.py` are in the main tree; the rest are under `tests/archive/` (and excluded by `norecursedirs` in pytest).
- **Suggestion:** Gradually re-enable a small set of fast, stable tests (e.g. unit tests for entity_schema, blueprint_loader, views_content) in the main tree and run them in pre-push and CI. Leave heavy/integration tests in archive until they are stable.
- **Coverage:** No coverage gate is run in the current pre-push or in the disabled workflow. When re-enabling CI, consider `pytest --cov=src/manifest --cov-fail-under=...` (even with a low threshold) to avoid coverage regression.

---

## 5. Duplication and single responsibility

- **Blueprint loading:** `BlueprintLoader.load_blueprint` (and sometimes `load_blueprint` + `load_code_blueprint`) appears in many places (app.py, views_content, blueprint_sync, doc_set, structure_manager, context_provider, entity_model, etc.). Already improved with `_load_both_blueprints` in blueprint_sync. Elsewhere, consider passing a pre-loaded blueprint or a small “manifest context” (manifest_dir + design/code blueprints) into view/build logic to avoid repeated loads in the same request or refresh.
- **Default paths:** Several modules use `manifest_dir or Path.cwd() / ".manifest"` or `project_root or Path.cwd()`. A single helper (e.g. in `core.config` or `core.paths`) like `default_manifest_dir()`, `default_project_root()` would make defaults and overrides consistent.

### 5a. Blueprint / view caching (detail for decision)

**Where:** View app refresh cycle: `_ensure_diagram_components`, `_load_diagram_view`, `_load_files_view`, `_load_timeline_view`, `_load_mission_control_view`, `_load_inspector_view`, `_get_sidebar_health`, `_get_sidebar_tasks`, `_get_info_hub_content`, and header/tab bar. Each can trigger one or more `BlueprintLoader.load_blueprint(manifest_dir, ...)` or `load_blueprint` + `load_code_blueprint`.

**What to cache:** Last-loaded design blueprint and last-loaded code blueprint (and optionally `calculate_implementation_status` result) keyed by `manifest_dir` (and optionally file mtimes of blueprint files).

**Expected benefit:** Fewer disk reads per refresh. On a typical refresh, today there can be 5–15+ full blueprint loads (JSON read + parse). Caching for the duration of one refresh (e.g. "load once per refresh") would cut that to 1–2 loads per refresh. Benefit is largest when: (1) user leaves the app open and auto-refresh or 1s header interval runs often, (2) blueprint files are large or on slow storage. Benefit is small when: (1) user refreshes rarely, (2) files are tiny and fast.

**TTL / invalidation options:**
- **Per-refresh:** No TTL. At start of each `refresh_view()` (or each `_refresh_sidebar` / `_refresh_main_content`), clear cache and load once; all code paths in that refresh use the same cached blueprints. Simple; no stale data within a refresh.
- **Time TTL:** Cache valid for e.g. 2–5 seconds. No explicit clear; next refresh after TTL re-loads. Risk: if user edits a blueprint file and refreshes before TTL, they might see old data.
- **File mtime:** Cache key includes mtime of `blueprint_design.json` and `blueprint_code.json`. Invalidate when mtime changes (e.g. on `ViewFileWatcher` change or before each load). More accurate; slightly more code (read mtimes or subscribe to watcher).

**Recommendation:** Start with **per-refresh** caching: in `ManifestViewApp`, at the start of `refresh_view()` (and `_ensure_diagram_components` if it's the first loader), load design + code blueprint once, store in `self._cached_blueprint_design` / `_cached_blueprint_code`, and have all `_load_*` / `_get_*` methods use these when available instead of calling `BlueprintLoader.load_blueprint` again. Clear cache at the start of every `refresh_view()`. That gives one load per refresh with minimal code and no staleness. If later you add file watcher or want to avoid reload on every keypress, add mtime-based invalidation.

---

## 6. Configuration and environment

- **`check_ci_status.py`** sets `PYTHONPATH` to `str(Path(__file__).parent.parent / "src")`; some tests or scripts may assume `PYTHONPATH=src` from repo root. Document the expected working directory and PYTHONPATH (e.g. in README or CONTRIBUTING) so all scripts and CI use the same convention.

### 6a. What does what: config.py vs settings_manager.py

**`core/config.py` — ConfigManager**

- **Role:** Low-level, manifest-dir–scoped configuration and secrets.
- **Owns:** `.manifest/` paths: `keys.json` (encrypted API keys), `.key` (Fernet key), `settings.json` (tool_approval, agent backend, opencode server, resource_limits), `agent_config.json` (agent models, API keys per agent, agent_permissions, agent_skills refs).
- **Responsibilities:** Load/save encrypted API keys; env fallback for keys; validate keys (e.g. Anthropic/OpenAI test request); get/set settings via dot notation (`get_setting("agent.execution_backend")`); load/save agent model config and permissions; create default `settings.json` if missing.
- **Does not:** Know about project root, AGENTS.md, .rules/policy, or SkillsManager.

**`core/settings_manager.py` — SettingsManager**

- **Role:** Unified interface for UI and programmatic access to “all” settings.
- **Owns:** Holds `manifest_dir` and `project_root`; composes `ConfigManager(manifest_dir)` and `SkillsManager(manifest_dir, project_root)`; defines paths for `.rules/manifest-policy.md`, `AGENTS.md`, and optional files like `spec_first_settings.json`, `shadow_settings.json`.
- **Responsibilities:** Delegates API keys and agent models to ConfigManager; delegates skills to SkillsManager; policy/AGENTS.md read/write; spec-first and shadow settings; `get_all_settings()` for UI; validation across keys/models.
- **Does not:** Implement encryption or dot-notation settings itself; that stays in ConfigManager.

**Summary:** ConfigManager = single source for keys, settings.json, and agent_config.json under `.manifest/`. SettingsManager = facade over Config + Skills + policy/AGENTS/spec-first/shadow, with a project_root-aware view. Overlap: both touch `agent_config.json` (ConfigManager reads/writes it; SettingsManager delegates and also writes for default_models, agent_skills). That’s intentional: SettingsManager is the public API; ConfigManager remains the implementation for .manifest-backed config.

---

## 7. Structure and discoverability

- **Entry points:** `python -m manifest` → `__main__.main()` → `launcher.main()`. Clear. Consider listing supported commands (e.g. view-only, opencode-only) in `__main__.py` or launcher docstring.
- **View vs runtime:** `view/` (TUI, diagram, views_content) and `runtime/` (agents, opencode tools, orchestrator) are separate; shared concepts (e.g. “manifest dir”, “blueprint”) are in `audit/` and `core/`. This is coherent; keep boundaries clear and avoid view code importing runtime agents (or vice versa) except via narrow interfaces.

---

## 8. Security and robustness — **further explanation**

**Path validation**

- **Risk:** If a path comes from user input, LLM output, or config (e.g. “read this file”, “write output here”), an attacker or bug could send something like `../../etc/passwd` or an absolute path outside the project. Without validation, code might read or write outside the intended directory.
- **What to do:** For any path that is derived from user/LLM/config:
  1. Resolve it (e.g. `path.resolve()`) and resolve the allowed base (e.g. `project_root.resolve()` or `manifest_dir.resolve()`).
  2. Check that the resolved path is under the base, e.g. `resolved_path.is_relative_to(base)` (Python 3.9+) or `str(resolved_path).startswith(str(base))` with careful handling of trailing slashes.
  3. If not under base, reject: log, return error, or raise; do not open the path.
- **Where it matters most:** Tools that accept file paths from the LLM (e.g. file_manager, tool_executor when executing “read file X” or “write to Y”), launcher/CLI that take `--manifest-dir` or similar, and any code that builds paths from config (e.g. custom output dir). View app currently uses `self.manifest_dir` from constructor; if that ever came from user input, it should be validated once at startup.

**Subprocess**

- **Current state:** Scripts and ci_monitor run fixed commands: `git remote get-url`, `git rev-parse`, `gh auth token`, `pytest tests/...`. No user input is concatenated into the command string; no `shell=True`. That is safe.
- **If you add dynamic commands later:** (1) Use an allowlist: only allow specific commands (e.g. `git`, `pytest`, `docker`) with specific sub-commands/args. (2) Pass arguments as a list to `subprocess.run(..., shell=False)` so the shell does not interpret them. (3) Do not pass unsanitized user/LLM input into the command or args; if you must (e.g. “run pytest on this file”), validate the argument (e.g. file path under project root, or allowlisted test name) before passing. (4) Avoid `shell=True`; if you ever need it, do not interpolate user input into the shell string.

---

## 9. Performance and scale

- **View app:** Diagram and sidebar refresh on interval and on change; multiple `BlueprintLoader.load_blueprint` calls per refresh. Caching the last-loaded blueprint (or a short TTL) per refresh cycle could reduce I/O when nothing changed.
- **Agents/runtime:** No obvious hot path reviewed in detail; if mission or task lists grow large, consider pagination or lazy loading in UI and in APIs that return full lists.

---

## 10. Maintainability — **further explanation**

**Type hints**

- **Goal:** Catch type errors at edit/check time and make interfaces clear. mypy is configured with `disallow_untyped_defs = false`, so untyped code is allowed but typed code is checked.
- **Where to add first:** (1) **entity_schema:** function signatures like `get_root_entity(blueprint: Dict[str, Any]) -> Optional[Dict[str, Any]]`, `mission_from_blueprint(blueprint: Dict[str, Any], fallback: str = "") -> str`, `goals_from_blueprint(blueprint: Dict[str, Any]) -> List[Any]`. (2) **blueprint_loader:** `load_blueprint(manifest_dir: Path, ...) -> Dict[str, Any]`. (3) **views_content:** all public functions (entities_for_display, blueprint_component_names, …, render_prd_summary) have dict/list/Path/str types. Many already have partial hints; add return types and any missing argument types.
- **How:** Run mypy on the package (`mypy src/manifest`) and fix reported errors; add `# type: ignore` only where necessary (e.g. third-party or dynamic code). Prefer `from __future__ import annotations` in new files to avoid forward-reference issues.

**CHANGELOG**

- **Goal:** One place to see what changed between releases so users and maintainers don’t have to dig through commits.
- **Format (Keep a Changelog style):** One file `CHANGELOG.md` at repo root. Sections: `## [Unreleased]`, `## [0.1.0] - 2025-02-05` (example). Under each version: subsections `### Added`, `### Changed`, `### Fixed`, `### Removed`. Bullet points per change, e.g. “- View app: extracted stateless helpers to views_content.py”, “- entity_schema: added goals_from_blueprint”.
- **When to update:** On release (or in the same PR that bumps version). Optionally add a line under `[Unreleased]` when merging a notable feature or fix; then on release move those under the new version and clear `[Unreleased]`.
- **Alternative:** If you prefer not to maintain a file, use GitHub Releases with a short “What’s in this release” in the release body; less discoverable than a single CHANGELOG.md but still useful.

---

## Summary (prioritized)

| Priority | Area | Action |
|----------|------|--------|
| High | Version | **Done:** __version__ = 0.1.0; requirements comment. Remain: Python 3.10+ in dev/CI |
| High | CI | Re-enable GitHub test job when ready; align local check_ci_status with CI test set |
| Medium | Error handling | **Done:** logging in app, views_content, config, settings_manager, design_history, blueprint_sync, ci_monitor. Remain: other modules |
| Medium | Tests | Re-enable a small set of unit tests from archive; add coverage to CI |
| Medium | Deps | Sync requirements.txt and pyproject.toml (opencode, pytest-timeout) |
| Low | Config | **Done:** Section 6a documents config.py vs settings_manager.py. Remain: single default path helper |
| Low | Caching | Section 5a: blueprint caching benefit, TTL, invalidation, recommendation |
| Low | Security | Section 8: path validation and subprocess explained |
| Low | Maintainability | Section 10: type hints where, CHANGELOG format explained |
