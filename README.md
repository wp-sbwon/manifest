# Manifest

**AI-Native Orchestration IDE** — Reduce code blindness by making design and code visible and comparable in one place. Developers act as conductors: plan (top-down blueprint) and verify (bottom-up code) share the same entity schema; the View shows drift and status.

## Intent

- **Blueprint-based alignment:** Design and code use the same entity shape (`id`, `children`, `dependencies`, `narrative`, `blueprint`, `protocol`, `profile`, `governance`, `symbol`, `traits`, `topology_actual`, `preview`, `outgoing_contracts`). Top-down agents write `blueprint_design.json`; bottom-up: CodeExtractor produces an outline, then a deterministic merge maps extraction to design by symbol and combines design (narrative, governance) with extraction (symbol, protocol, dependencies) to produce `blueprint_code.json`. The view builds `blueprint_view.json` from both (plan vs actual, per-entity status and deviations).
- **Single surface:** The Manifest View TUI shows diagram, files, timeline, mission, and inspector. All data comes from `.manifest/`. Chat, terminal, and LLM execution are provided by **OpenCode**; the View is visualization-only and does not execute tools.
- **Bottom-up on commit:** When a commit is made (via the app’s GitManager or an optional git post-commit hook), the pipeline runs `bin/run_bottom_up_docs.py`: CodeExtractor produces an outline; a deterministic merge with blueprint_design produces `blueprint_code.json`, then view build and health metrics. The View refreshes when `.manifest` files change.

## Implementation

- **Launcher** (`python -m manifest`): Ensures OpenCode is on PATH; starts the Manifest View (TUI) in a separate window/process, then execs OpenCode for the project directory. When running from the manifest repo with `MANIFEST_DEV=1`, uses `tmp/<name>` as project dir; default name is `calculator` (override with `MANIFEST_DEV_PROJECT`).
- **View** (`manifest.view.app`): Textual TUI. Reads `blueprint_design.json`, `blueprint_code.json`, `blueprint_view.json`, `state.json`, and related files from `.manifest/`. Renders diagram (with status), files, timeline, mission; inspector shows selected node and plan vs code. Status (Planned / Healthy / Partial / Deviation) comes from the blueprint view (design vs code). A file watcher (watchdog) refreshes when `.manifest` files change.
- **Audit:** Entity schema and validation (`audit/entity_schema.py`, `entity_validation.py`); blueprint load, compare, sync (`audit/blueprint/`); code extraction and code blueprint (`audit/code/`); CodeWatcher and `bin/run_bottom_up_docs.py` for bottom-up. GitManager calls the bottom-up script after `create_commit()`.
- **OpenCode:** Required. Used for chat, terminal, and agent execution. Bottom-up uses CodeExtractor and deterministic merge only; no agent for blueprint_code.

## Documentation

All documentation is in [`docs/`](docs/). See [docs/README.md](docs/README.md) for the index.

Quick links: [View app](docs/view-app.md) · [Manifest data](docs/manifest-data.md) · [Scripts and pipelines](docs/scripts-and-pipelines.md).

## Quick Start

1. **Setup (installs venv, OpenCode if missing):**
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

   This starts **OpenCode** (chat/terminal) and the **Manifest View** (blueprint, drift, tasks). The app uses the **current working directory** as the project; from the manifest repo in dev, set `MANIFEST_DEV=1` to use `tmp/calculator` (or `tmp/<MANIFEST_DEV_PROJECT>`) as the project so the View doesn’t load the manifest codebase. Override with `MANIFEST_PROJECT_DIR` for any path.

## Prerequisites

- **Python 3.10+**
- **OpenCode** — required. The launcher checks for it and exits with a hint if missing.

## Root directory

| Path | Purpose |
|------|--------|
| `src/`, `tests/`, `bin/`, `scripts/`, `docs/` | Source, tests, app runnables, dev/CI scripts, documentation |
| `.manifest/` | Runtime data (state, blueprints). Commit `.manifest/*.json` (except secrets/conflicts) to version design and progress. |
| `.rules/` | Project rules (task granularity, PRD template, code style) |
| `tmp/` | Holds mock projects (e.g. `tmp/calculator/`). When `MANIFEST_DEV=1`, view loads `tmp/<name>/.manifest` (default name: `calculator`; set `MANIFEST_DEV_PROJECT` to pick one). |
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
│   ├── opencode/            # Architect, layer_writer
│   └── io/                  # Blueprint I/O
├── tests/
├── docs/
├── bin/                     # App runnables: run_bottom_up_docs.py, run_doc_layer_writer.py, setup_opencode_agent.py
├── scripts/                 # Dev/CI/setup: setup.sh, check_ci_status.py, pre_push_ci_check.sh, ...
├── .manifest/               # Created at run time; blueprint_*.json, state.json, ...
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Dependencies

- See `requirements.txt` and `pyproject.toml`. Key: `textual` (TUI), `opencode-ai` (required), `GitPython`, etc.
- **OpenCode** is a required dependency; the launcher does not fall back to another backend.

## Git hooks (optional)

- **Bottom-up after commit:** Commits made via the app’s GitManager already trigger `bin/run_bottom_up_docs.py`. For commits made with `git commit` in the terminal, install the hook:
  ```bash
  ln -sf ../../scripts/post_commit_bottom_up.sh .git/hooks/post-commit
  ```
- **CI before push:** `scripts/pre_push_ci_check.sh` and pre-commit pre-push (see `.pre-commit-config.yaml`).

## Development

- Run tests: `PYTHONPATH=src pytest` or `PYTHONPATH=src python scripts/check_ci_status.py`.
- View only (e.g. with mock data): `PYTHONPATH=src python -m manifest.view.app --manifest-dir tmp/calculator/.manifest`
- Mock data for default project: `PYTHONPATH=src python scripts/create_mock_project_data.py` (writes to `tmp/calculator/.manifest`). For another project: `scripts/create_mock_project_data.py myproject` → `tmp/myproject/.manifest`.

## Docker (optional)

A single `Dockerfile` is provided. The default `CMD` runs `python -m manifest`, which requires `opencode` on PATH; the image does not install it. For view-only: override with `python -m manifest.view.app --manifest-dir /path/to/.manifest`.

## Troubleshooting

- **OpenCode not found:** Install so `opencode` is on PATH (e.g. via `scripts/setup.sh` or `pip install opencode-ai`).
- **View not updating:** Bottom-up runs on commit; the View refreshes when `.manifest` files change (watchdog). Ensure `blueprint_design.json` exists and, after a commit, that `bin/run_bottom_up_docs.py` has run (check for updated `blueprint_code.json`).
