# Manifest

**AI-Native Orchestration IDE** - Solve Code Blindness by elevating developers to Conductors.

## Documentation

All documentation is in [`docs/`](docs/). See [docs/README.md](docs/README.md) for the index.

**Quick links:** [Project structure](docs/PROJECT_STRUCTURE.md) · [UI redesign plan](docs/UI_REDESIGN_PLAN.md) · [Worker squad](docs/WORKER_SQUAD_AND_AGENTS.md). **Target architecture:** [Redesign architecture and intent](docs/REDESIGN_ARCHITECTURE_AND_INTENT.md); [implementation status](docs/NEW_ARCHITECTURE_IMPLEMENTATION_STATUS-2026-01-28.md). Older docs are in [docs/archive/](docs/archive/).

## Execution backend

The project supports **multiple backends** for chat, terminal, and LLM execution; the **primary** one is OpenCode. The backend is configured via `agent.execution_backend` (default: `opencode`). Additional backends can be added by implementing the executor interface and registering them in the executor factory.

- **Chat and terminal** — Provided by the configured backend; the View app is visualization-only.
- **LLM execution** — Agent execution goes through the configured backend.
- **Tool execution** — Tools (including bash) are executed by the backend.

## Quick Start

Then: `./scripts/setup.sh`, `source venv/bin/activate`, `PYTHONPATH=src python -m manifest`.

## Root directory (what’s what)

| Path | Purpose |
|------|--------|
| `src/`, `tests/`, `scripts/`, `docs/` | Source, tests, scripts, documentation |
| `.manifest/` | Runtime data (tasks, state, blueprints); created at run time |
| `.rules/` | Project rules (task granularity, PRD template, code style) |
| (no htmlcov) | We do not run pytest with coverage; test quality is based on actual failproof checklist, not line coverage. |
| `reference/` | Reference materials (e.g. implementation plan, PDF) |
| `AGENTS.md.example` | Example for project-level AGENTS.md (OpenCode convention) |

# Manifest Development Environment

This document provides an overview of the development environment setup for the Manifest project.

## Prerequisites

- Python 3.9 or higher
- **OpenCode** and **Podman** are required but **you do not install or run them yourself**: the setup script and the launcher install and start them when missing.

## Quick Start

### Option 1: Python Virtual Environment (Recommended for Development)

1. **Setup the environment (OpenCode and Podman are installed automatically when missing):**
   ```bash
   chmod +x scripts/setup.sh
   ./scripts/setup.sh
   ```

2. **Activate the virtual environment:**
   ```bash
   source venv/bin/activate
   ```

3. **Run the application:**
   ```bash
   PYTHONPATH=src python -m manifest
   ```
   Or after `pip install -e .`:
   ```bash
   manifest
   ```
   This starts **OpenCode** (chat/commands) and the **Manifest View** (blueprint, drift, tasks). If OpenCode or Podman are missing, the launcher will try to install and start them; no manual install needed.

4. **Deactivate when done:**
   ```bash
   deactivate
   ```

### Option 2: Docker Compose (optional / alternative deployment)

The main app requires **Podman** (see Option 1). If you use Docker Compose for deployment:

1. **Install Docker Desktop or Podman** and ensure the runtime is running.

2. **Setup and run:**
   ```bash
   chmod +x setup-docker.sh
   ./setup-docker.sh
   docker-compose up
   ```

3. **Stop:** `docker-compose down`

## Project Structure

```
manifest/
├── src/
│   └── manifest/       # Main package (src layout)
│       ├── core/       # Core modules (config, state_manager)
│       ├── ui/         # UI modules (app, widgets, bootstrap_ui)
│       ├── agents/     # Agent modules (coordinator, context_provider, task_scoper)
│       ├── bridge/     # Bridge modules (agent_bridge)
│       └── audit/      # Audit modules (drift_auditor)
├── tests/              # Test files
├── docs/               # Documentation files
├── scripts/            # Setup and utility scripts
├── .manifest/          # Application data and configuration
├── venv/               # Python virtual environment (gitignored)
├── requirements.txt    # Python dependencies
├── pytest.ini          # Pytest configuration
├── Dockerfile          # Docker image configuration
├── docker-compose.yml  # Docker Compose configuration
└── README.md           # This file
```

## Dependencies

### Python Dependencies
- `textual>=0.40.0` - Terminal UI framework

See `requirements.txt` for the complete list.

### Optional Dependencies

**OpenCode Integration** (Optional):
- Manifest can optionally use OpenCode for terminal command execution
- If OpenCode is already installed in your environment, Manifest will automatically detect and use it
- If OpenCode is not available, Manifest falls back to its internal implementation
- To explicitly enable OpenCode integration, install with: `pip install opencode>=1.0.0`
- No conflicts: Manifest works seamlessly whether OpenCode is installed or not

**Skills System**:
- Configure skills for individual agents in `.manifest/agent_config.json`
- Configure project-scoped skills in `AGENTS.md` (OpenCode convention)
- Skills are automatically loaded from `.rules/` directory
- See [docs/archive/superseded-2026/SKILLS.md](docs/archive/superseded-2026/SKILLS.md) for detailed documentation

## Git hooks (optional)

- **Bottom-up docs on every commit:** After each commit, Manifest can refresh `blueprint_code.json` from code and generate `intent_code.json` / `architecture_code.json` via the OpenCode session. To enable:
  `ln -sf ../../scripts/post_commit_bottom_up.sh .git/hooks/post-commit`
  Requires OpenCode running (or auto-started) for LLM-based intent/architecture; blueprint_code is always refreshed.
- **CI checks before push:** See `scripts/pre_push_ci_check.sh` and `.pre-commit-config.yaml` (pre-push stage).

## Development Workflow

### Using Virtual Environment

1. Always activate the virtual environment before working:
   ```bash
   source venv/bin/activate
   ```

2. Install new dependencies:
   ```bash
   pip install <package-name>
   pip freeze > requirements.txt
   ```

3. Run tests or the application:
   ```bash
   python -m manifest
   ```

### Using Docker

1. Build the image:
   ```bash
   docker-compose build
   ```

2. Run the container:
   ```bash
   docker-compose up
   ```

3. For development with live code changes, the volume is mounted automatically.

## Troubleshooting

### Python Virtual Environment Issues

- **Virtual environment not found:** Run `./setup.sh` again
- **Package installation fails:** Ensure pip is upgraded: `pip install --upgrade pip`

### Container runtime issues

- **Podman not running:** The launcher starts it automatically. To start manually: on macOS run `podman machine start`; on Linux run `sudo systemctl start podman.socket`.
- **Permission denied:** Ensure the container runtime has proper permissions.
- **Port conflicts:** Modify ports in `docker-compose.yml` if needed.

## Environment Variables

Create a `.env` file in the project root for environment-specific variables (this file is gitignored).

## Notes

- The virtual environment (`venv/`) should not be committed to version control
- Container images are built automatically on first run when using Docker Compose
- Both environments are configured for development with hot-reload capabilities
