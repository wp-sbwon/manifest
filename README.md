# Manifest

**AI-Native Orchestration IDE** — Reduce code blindness by making design and code visible and comparable in one place. Developers act as conductors: plan (top-down blueprint) and verify (bottom-up code) share the same entity schema; the View shows drift and status.

## Intent

- **Blueprint-based alignment:** Design (intent) and code (reality) use the same entity shape (`id`, `children`, `intent`, `reality`, `outgoing_contracts`). Top-down agents write `blueprint_design.json`; bottom-up extraction and enricher produce `blueprint_code.json`. Both are compared to build `blueprint_view.json` (plan vs actual, per-entity deviations).
- **Single surface:** The Manifest View TUI shows diagram, files, timeline, mission, and inspector. All data comes from `.manifest/`. Chat, terminal, and LLM execution are provided by **OpenCode**; the View is visualization-only and does not execute tools.
- **Bottom-up on commit:** When a commit is made (via the app’s GitManager or an optional git post-commit hook), the pipeline runs `run_bottom_up_docs.py`: CodeExtractor → merge with design → opencode enricher → `blueprint_code.json`, then view build and health metrics. The View refreshes when `.manifest` files change.

## Implementation

- **Launcher** (`python -m manifest`): Ensures OpenCode is on PATH; starts the Manifest View (TUI) in a separate window/process, then execs OpenCode for the project directory. Uses `tmp/` as project dir when running from the manifest repo with `MANIFEST_DEV=1`.
- **View** (`manifest.view.app`): Textual TUI. Reads `blueprint_design.json`, `blueprint_code.json`, `blueprint_view.json`, `state.json`, and related files from `.manifest/`. Renders diagram (with status), files, timeline, mission; inspector shows selected node’s design and actual code. Status (Planned / Healthy / Partial / Deviation) is computed by BlueprintSynchronizer (design vs code). A file watcher (watchdog) refreshes when `.manifest` files change.
- **Audit:** Entity schema and validation (`audit/entity_schema.py`, `entity_validation.py`); blueprint load, compare, sync (`audit/blueprint/`); code extraction and code blueprint (`audit/code/`); CodeWatcher and `run_bottom_up_docs.py` for bottom-up. GitManager calls the bottom-up script after `create_commit()`.
- **OpenCode:** Required. Used for chat, terminal, and agent execution. Enricher fills intent from code for the code blueprint.

## Documentation

All documentation is in [`docs/`](docs/). See [docs/README.md](docs/README.md) for the index.

Quick links: [View app](docs/view-app.md) · [Manifest data](docs/manifest-data.md) · [Scripts and pipelines](docs/scripts-and-pipelines.md).

## Quick Start

1. **Setup (installs venv, OpenCode, Podman if missing):**
   ```bash
   chmod +x scripts/setup.sh
   ./scripts/setup.sh
   ```

2. **Activate and run:**
   ```bash
   source venv/bin/activate
   PYTHONPATH=src python -m manifest
   ```
   Or after `pip install -e .`: `manifest`

   This starts **OpenCode** (chat/terminal) and the **Manifest View** (blueprint, drift, tasks). The app uses the **current working directory** as the project; from the manifest repo in dev, set `MANIFEST_DEV=1` to use `tmp/` as the project so the View doesn’t load the manifest codebase. Override with `MANIFEST_PROJECT_DIR` if needed.

## Prerequisites

- **Python 3.10+**
- **OpenCode** — required. The launcher checks for it and exits with a hint if missing.

## Root directory

| Path | Purpose |
|------|--------|
| `src/`, `tests/`, `scripts/`, `docs/` | Source, tests, scripts, documentation |
| `.manifest/` | Runtime data (state, blueprints). Commit `.manifest/*.json` (except secrets/conflicts) to version design and progress. |
| `.rules/` | Project rules (task granularity, PRD template, code style) |
| `tmp/` | Dev mock project when `MANIFEST_DEV=1`; view loads `tmp/.manifest` instead of repo `.manifest`. |
| `reference/` | Reference materials |
| `AGENTS.md.example` | Example for project-level AGENTS.md (OpenCode convention) |

## Project structure

```
manifest/
├── src/manifest/
│   ├── launcher.py          # Entry: start View, then exec OpenCode
│   ├── view/                # TUI: app, diagram, entity_model, file_watcher
│   ├── audit/               # Entity schema, blueprint load/compare/sync, code extraction, monitoring
│   ├── core/                # State, git, paths, logger, constants
│   ├── opencode/            # Architect, code_blueprint_enricher
│   └── io/                  # Blueprint I/O
├── tests/
├── docs/
├── scripts/                 # setup.sh, run_bottom_up_docs.py, check_ci_status.py, ...
├── .manifest/               # Created at run time; blueprint_*.json, state.json, ...
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Dependencies

- See `requirements.txt` and `pyproject.toml`. Key: `textual` (TUI), `opencode-ai` (required), `GitPython`, etc.
- **OpenCode** is a required dependency; the launcher does not fall back to another backend.

## Git hooks (optional)

- **Bottom-up after commit:** Commits made via the app’s GitManager already trigger `run_bottom_up_docs.py`. For commits made with `git commit` in the terminal, install the hook:
  ```bash
  ln -sf ../../scripts/post_commit_bottom_up.sh .git/hooks/post-commit
  ```
- **CI before push:** `scripts/pre_push_ci_check.sh` and pre-commit pre-push (see `.pre-commit-config.yaml`).

## Development

- Run tests: `PYTHONPATH=src pytest` or `PYTHONPATH=src python scripts/check_ci_status.py`.
- View only (e.g. with mock data): `PYTHONPATH=src python -m manifest.view.app --manifest-dir tmp/.manifest`
- Mock data for tmp: `PYTHONPATH=src python scripts/create_mock_project_data.py tmp/.manifest`

## Docker (optional)

If you use Docker Compose for deployment: ensure a container runtime (e.g. Podman) is available. The launcher can start Podman when needed. See `scripts/setup-docker.sh` and `docker-compose.yml`.

## Troubleshooting

- **OpenCode not found:** Install so `opencode` is on PATH (e.g. via `scripts/setup.sh` or `pip install opencode-ai`).
- **View not updating:** Bottom-up runs on commit; the View refreshes when `.manifest` files change (watchdog). Ensure `blueprint_design.json` exists and, after a commit, that `run_bottom_up_docs.py` has run (check for updated `blueprint_code.json`).
- **Podman:** On macOS run `podman machine start`; on Linux `sudo systemctl start podman.socket` if the launcher doesn’t start it.
