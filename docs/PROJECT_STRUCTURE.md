# Project Structure (multi-backend; primary: OpenCode)

Architecture supports multiple execution backends; the primary one is OpenCode. Entry: `python -m manifest` → launcher → View (TUI) + configured backend (e.g. OpenCode).

**Assess the codebase against [Redesign Architecture and Intent](./REDESIGN_ARCHITECTURE_AND_INTENT.md)** for target architecture, feature list, and legacy removal/alter list.

## Root

```
manifest/
├── .manifest/           # Runtime data (tasks, state, blueprints)
│   ├── tasks.json       # Tasks + sprints (Task Management Tool)
│   ├── state.json       # StateManager state
│   ├── blueprint.json   # Top-down blueprint
│   ├── blueprint_code.json  # Bottom-up (CodeWatcher)
│   ├── architecture.json
│   └── worker_spawns.json   # Worker spawn log
├── .rules/              # Project rules (task-granularity, prd-template, code-style)
├── src/manifest/        # Package
├── tests/               # Single startup test; full suite in tests/archive/
├── docs/                # Active docs (archive/ = superseded)
├── scripts/
├── reference/           # Reference materials (implementation_plan, PDF)
└── pyproject.toml, requirements.txt, pytest.ini, README.md
```

**Tests:** One smoke test (`tests/test_startup.py`) ensures the app starts. Full test suite is archived under `tests/archive/`. GitHub Actions are disabled; add testing later.

**OpenCode config:** Project root `opencode.json` defines agents (orchestrator, architect, full-test), default agent, and an input placeholder (`tui.placeholder`) for OpenCode’s chat: "Mission or task for Manifest. /help, /models, /worker-model". If your OpenCode version does not support `tui.placeholder`, the default may still appear; support is version-dependent.

## Source (`src/manifest/`)

| Path | Role |
|------|------|
| `__main__.py` | Entry → launcher |
| `launcher.py` | View + OpenCode (or View only) |
| **view/** | **TUI (ManifestViewApp)** – dashboard, tasks, blueprint, drift |
| `view/app.py` | ManifestViewApp |
| `view/file_watcher.py` | ViewFileWatcher (.manifest/ poll) |
| **runtime/opencode/** | **OpenCode tools** (orchestrator) |
| `runtime/opencode/tools/task_management.py` | .manifest/tasks.json |
| `runtime/opencode/tools/sprint_management.py` | Sprints in tasks.json |
| `runtime/opencode/tools/worker_squad_spawn.py` | Worker spawn log |
| `runtime/opencode/tools/blueprint_sync.py` | BlueprintSyncTool, DriftCheckTool |
| `runtime/tools/` | tool_definitions, tool_executor (bash, edit, read, task_management, …) |
| `runtime/agent/` | Executors, agents (planner, coder, test, …) |
| `runtime/router/terminal_router.py` | Bash execution |
| **audit/monitoring/** | **Drift / code watch** |
| `audit/monitoring/code_watcher.py` | CodeWatcher → blueprint_code.json |
| `audit/monitoring/drift_monitor.py` | DriftMonitor (drives CodeWatcher) |
| `audit/monitoring/file_watcher.py` | Git-based file watcher (audit) |
| `audit/blueprint/` | BlueprintLoader, BlueprintSynchronizer, BlueprintComparator |
| `audit/code/` | CodeExtractor, DriftAuditor |
| `core/` | StateManager, TaskManager, SprintManager, Config, … |
| `agents/` | AgentCoordinator, ContextProvider, WorkerSquadExecutor, … |
| `bridge/` | AgentBridge |
| **ui/** | Stub – use `manifest.view` |

## Data flow

- **Task Management**: Orchestrator uses `task_management` / `sprint_management` tools → `.manifest/tasks.json` → ViewFileWatcher → View refresh.
- **Drift**: CodeWatcher (on timer) → `.manifest/blueprint_code.json` → ViewFileWatcher → Blueprint/Drift views.
- **View**: Reads `.manifest/` (tasks.json, state.json, blueprints); prefers `tasks.json` for tasks/sprints when present.

## Tests

- One smoke test: `tests/test_startup.py` (app starts). Full suite archived under `tests/archive/`.

## Docs

- **Active**: `docs/README.md`, `docs/REDESIGN_ARCHITECTURE_AND_INTENT.md`, `docs/UI_REDESIGN_PLAN.md`, `docs/WORKER_SQUAD_AND_AGENTS.md`, `docs/PROJECT_STRUCTURE.md` (this file). Snapshot docs use `NAME-YYYY-MM-DD.md`: e.g. `NEW_ARCHITECTURE_IMPLEMENTATION_STATUS-2026-01-28.md`, `REFACTORING-2026-01-28.md`.
- **Archive**: `docs/archive/superseded-2026/`, `docs/archive/v1.0/` – superseded planning and status docs.
