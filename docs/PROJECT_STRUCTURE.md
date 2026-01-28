# Project Structure (OpenCode-First)

Current layout after the OpenCode-first redesign. Entry: `python -m manifest` → launcher → View (TUI) + OpenCode.

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
├── .opencode/
│   └── agents/          # OpenCode agent configs
│       └── manifest-orchestrator.json
├── src/manifest/        # Package
├── tests/
├── docs/                # Active docs (archive/ = superseded)
├── scripts/
├── reference/           # Reference materials (implementation_plan, PDF)
├── htmlcov/             # GENERATED: pytest-cov HTML report (safe to delete; .gitignore)
├── coverage.json        # GENERATED: coverage data (safe to delete; .gitignore)
└── pyproject.toml, requirements.txt, pytest.ini, README.md
```

**Generated / ignore:** `htmlcov/` is the HTML coverage report from `pytest --cov` (open `htmlcov/index.html` in a browser). `coverage.json`, `.coverage`, `coverage.xml` are coverage data. All are in `.gitignore`; safe to delete.

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
| **ui/** | **Deprecated stub** – use `manifest.view` |

## Data flow

- **Task Management**: Orchestrator uses `task_management` / `sprint_management` tools → `.manifest/tasks.json` → ViewFileWatcher → View refresh.
- **Drift**: CodeWatcher (on timer) → `.manifest/blueprint_code.json` → ViewFileWatcher → Blueprint/Drift views.
- **View**: Reads `.manifest/` (tasks.json, state.json, blueprints); prefers `tasks.json` for tasks/sprints when present.

## Tests

- `tests/unit/` – unit tests (view, opencode tools, tool_executor, code_watcher, …).
- `tests/integration/` – integration (view_app, state_manager, opencode_integration, …).
- `tests/e2e/` – e2e (permission, mission, blueprint sync, …).

## Docs

- **Active**: `docs/README.md`, `docs/UI_REDESIGN_PLAN.md`, `docs/OPENCODE_AGENT_SETUP.md`, `docs/OPENCODE_SETUP.md`, `docs/WORKER_SQUAD_AND_AGENTS.md`, `docs/PROJECT_STRUCTURE.md` (this file).
- **Archive**: `docs/archive/superseded-2026/`, `docs/archive/v1.0/` – superseded planning and status docs.
