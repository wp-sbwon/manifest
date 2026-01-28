# Current State Analysis (code-only)

Analyzed without relying on docs. Summary of what the project is, feature completeness, and what needs to be done.

**Note:** For up-to-date implementation status (what is done vs remaining), use **[New Architecture Implementation Status](./NEW_ARCHITECTURE_IMPLEMENTATION_STATUS.md)**. This analysis may describe an older state (e.g. before run_squad via Container API, tool_approval, design history, resources UI).

**Assess implementation and legacy against [Redesign Architecture and Intent](./REDESIGN_ARCHITECTURE_AND_INTENT.md)** for the target architecture and feature list from the redesign.

---

## Feature / functionality completeness — are we done?

**Short answer: No.** The main user flow works (View + OpenCode), but several features are either not wired into that flow or are stubbed.

### What is wired and used in the main flow

1. **Launcher** — Starts View (subprocess) and execs `opencode . -c [--agent manifest-orchestrator]`. Requires `opencode` on PATH.
2. **View** — Textual TUI over `.manifest/` (tasks, blueprint, architect, history, inspector). Reads `tasks.json`, `state.json`, `blueprint.json`, etc.; ViewFileWatcher refreshes on change. No agent execution from View.
3. **OpenCode tools** — `task_management`, `sprint_management`, `worker_squad_spawn`, `blueprint_sync`, `drift_check` exist and read/write `.manifest/`. They are used when OpenCode (or something that uses ToolExecutor) calls them. If OpenCode discovers and invokes these tools, tasks/sprints/blueprint stay in sync with View.
4. **.rules/** — Loaded by skills_manager, context_provider, task_scoper, orchestrator prompts. No UI to edit; files are static.

### What is built but not wired to the main flow

1. **AgentCoordinator + AgentBridge + WorkerSquadExecutor + SprintExecutor** — In-process multi-agent (orchestrator → planner → coder → test → debug). Only instantiated in **tests** (archived). There is no production entry (no CLI, no API) that creates AgentCoordinator and runs missions. So the “full” in-process agent stack is not reachable from `manifest` or View.
2. **Container API** (`container_api.create_container_api`) — FastAPI app for container↔host communication. Only used in tests. No `uvicorn` or script runs this server, so containerized agents (runner.py) have no host API to connect to by default.
3. **channel_manager** — AgentBridge expects an optional channel_manager for UI updates when agents run. View does not provide it; the in-process agent path is not connected to View.

### Incomplete or stubbed

1. **worker_squad_spawn** — Does not actually spawn OpenCode agent processes. It writes a synthetic `agent_process_id` and logs to `.manifest/worker_spawns.json`. Comment in code: “When OpenCode API is available, call it here to start the agent process.”
2. **Permission “ask”** — FileManager/read-write: when permission is `"ask"`, code logs “approval not implemented” and allows the operation. No real approval flow.
3. **Agent configs** — `.opencode/` was removed. User must configure OpenCode (agents, model) separately; launcher only passes `--agent manifest-orchestrator` by default.

### Summary

| Area | Status |
|------|--------|
| View + launcher + OpenCode CLI | Wired; main flow works if OpenCode is installed. |
| OpenCode tools (task/sprint/blueprint/drift) | Implemented; used when OpenCode (or ToolExecutor) calls them. |
| In-process multi-agent (Coordinator/Bridge/WorkerSquad) | Built but not started from any production entry. |
| Container API + runner.py agents | Built but no server runs the API; container path is not wired. |
| worker_squad_spawn | Stub: logs only, does not spawn workers. |
| Permission “ask” | Not implemented; always allow. |

So we are **not** done with all features: the dashboard + OpenCode path works; the in-process and container agent paths are not wired end-to-end, and two areas are stubbed (spawn, permission ask).

---

## What the project is

- **Entry**: `python -m manifest` → `__main__.main()` → `launcher.main()`.
- **Launcher**: (1) Starts **View** (Textual TUI) as subprocess (`manifest.view.app`), (2) **exec**s `opencode . -c [--agent manifest-orchestrator]`. Requires `opencode` on PATH and prefers Docker (tries to install/start if missing).
- **View** (`manifest.view.app`): Dashboard over `.manifest/` (tasks, blueprint, architect, history, inspector, mission). Reads `tasks.json`, `state.json`, `blueprint.json`, `architecture.json`, `intent.json`; uses StateManager, TaskManager, BlueprintSynchronizer, ViewFileWatcher.
- **Rules**: `.rules/` holds task-granularity, prd-template, code-style. Loaded by skills_manager, context_provider, task_scoper, orchestrator prompts. No `.opencode/` or `.claude/` (removed).
- **Runtime**: Agents (orchestrator, planner, coder, test, debug, approver), executor_factory, opencode tools (task_management, sprint_management, worker_squad_spawn, blueprint_sync), opencode_llm_adapter, permissions, terminal_router. All under `src/manifest/`.
- **Tests**: One smoke test, `tests/test_startup.py` (import manifest + `manifest.__main__.main` callable). Full suite archived under `tests/archive/`. GitHub Actions removed (no workflows).
- **CI**: `scripts/check_ci_status.py` runs local import/syntax checks and `pytest tests/test_startup.py`. No remote CI.

---

## What needs to be done

### 1. **Pytest discovery** — fixed

- `testpaths = tests` and `norecursedirs` includes `tests/archive`; default run only runs `tests/test_startup.py`.

### 2. **Dependency consistency**

- **Issue**: `pyproject.toml` has `opencode-ai>=1.0.0`; `requirements.txt` does not (opencode commented as optional). `scripts/setup.sh` installs from `requirements.txt`. If users only use requirements.txt, they don't get opencode-ai; launcher still expects `opencode` CLI.
- **Fix**: Either add opencode-ai to requirements.txt to match pyproject, or document that OpenCode is installed separately and remove from pyproject optional.

### 3. **Cursor rule (ci-before-commit-push)**

- **Issue**: Rule says "GitHub Actions runs the same tests after push." GitHub Actions are disabled; there is no remote CI.
- **Fix**: Update rule to say only the local check runs (startup test + import/syntax), and that there is no remote CI until workflows are re-added.

### 4. **docs/PROJECT_STRUCTURE.md**

- **Issue**: Bullet list still describes `tests/unit/`, `tests/integration/`, `tests/e2e/` as current layout. Intro already says "Single startup test; full suite in tests/archive/."
- **Fix**: Update the bullet list to "One smoke test: tests/test_startup.py; full suite in tests/archive/" (or similar) so it matches reality.

### 5. **Optional / later**

- **.manifest on first run**: StateManager creates `.manifest` on first save; View can run with missing dir and show empty state. Optionally have launcher or View create `.manifest` at startup if missing.
- **Legacy `manifest.ui`**: `src/manifest/ui/` is a stub ("채팅 TUI 제거됨"). Safe to leave or remove when cleaning dead code.
- **Re-adding CI**: When tests are expanded again, add a minimal workflow that runs e.g. `pytest tests/test_startup.py` (or the chosen test set).

---

## Already consistent

- Launcher and View: no references to `.opencode/` or `.claude/` in code paths; agent name comes from config/env.
- Source uses `.rules/` and `rules_dir`; no remaining `.claude` in active code.
- `check_ci_status.py` runs only `tests/test_startup.py`; local checks pass.
- View app and StateManager/TaskManager/BlueprintLoader exist and are wired; `.manifest` is created when state is saved.
