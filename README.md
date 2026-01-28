# Manifest

**AI-Native Orchestration IDE** - Solve Code Blindness by elevating developers to Conductors.

## Documentation

All documentation is in [`docs/`](docs/). See [docs/README.md](docs/README.md) for the index.

**Quick links:** [Project structure](docs/PROJECT_STRUCTURE.md) · [OpenCode setup](docs/OPENCODE_SETUP.md) · [OpenCode agent](docs/OPENCODE_AGENT_SETUP.md) · [UI redesign plan](docs/UI_REDESIGN_PLAN.md) · [Worker squad](docs/WORKER_SQUAD_AND_AGENTS.md). Older docs are in [docs/archive/](docs/archive/).

## Quick Start

See [OpenCode setup](docs/OPENCODE_SETUP.md). Then: `./scripts/setup.sh`, `source venv/bin/activate`, `PYTHONPATH=src python -m manifest`.

## Root directory (what’s what)

| Path | Purpose |
|------|--------|
| `src/`, `tests/`, `scripts/`, `docs/` | Source, tests, scripts, documentation |
| `.manifest/` | Runtime data (tasks, state, blueprints); created at run time |
| `.opencode/` | OpenCode agent configs (e.g. manifest-orchestrator) |
| (no htmlcov) | We do not run pytest with coverage; test quality is based on actual failproof checklist, not line coverage. |
| `reference/` | Reference materials (e.g. implementation plan, PDF) |
| `AGENTS.md.example` | Example for project-level AGENTS.md (OpenCode convention) |

# Manifest Development Environment

This document provides an overview of the development environment setup for the Manifest project.

## Prerequisites

- Python 3.9 or higher
- Docker Desktop (for macOS/Windows) or Docker Engine (for Linux)

## Quick Start

### Option 1: Python Virtual Environment (Recommended for Development)

1. **Setup the environment (Docker is required; install it during setup if missing):**
   ```bash
   chmod +x scripts/setup.sh
   ./scripts/setup.sh
   ```
   To install Docker automatically on macOS/Linux: `INSTALL_DOCKER=1 ./scripts/setup.sh`

2. **Activate the virtual environment:**
   ```bash
   source venv/bin/activate
   ```

3. **Run the application:**
   ```bash
   PYTHONPATH=src python -m manifest
   ```
   또는 `pip install -e .` 후:
   ```bash
   manifest
   ```
   이렇게 하면 **OpenCode 터미널**과 **상시 시각화 View**(blueprint·구조·drift·태스크)가 함께 실행됩니다. 채팅/입력은 OpenCode에서 합니다. OpenCode 설치 및 PATH 설정이 필요하며, OpenCode에 `manifest-orchestrator` 에이전트를 설정해 두어야 합니다.

4. **Deactivate when done:**
   ```bash
   deactivate
   ```

### Option 2: Docker

1. **Install Docker Desktop:**
   - macOS: Download from [Docker Desktop](https://www.docker.com/products/docker-desktop)
   - Start Docker Desktop

2. **Setup Docker environment:**
   ```bash
   chmod +x setup-docker.sh
   ./setup-docker.sh
   ```

3. **Run the application:**
   ```bash
   docker-compose up
   ```

4. **Stop the application:**
   ```bash
   docker-compose down
   ```

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
- Skills are automatically loaded from `.claude/rules/` directory
- See [docs/archive/superseded-2026/SKILLS.md](docs/archive/superseded-2026/SKILLS.md) for detailed documentation

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

### Docker Issues

- **Docker not running:** Start Docker Desktop
- **Permission denied:** Ensure Docker Desktop has proper permissions
- **Port conflicts:** Modify ports in `docker-compose.yml` if needed

## Environment Variables

Create a `.env` file in the project root for environment-specific variables (this file is gitignored).

## Notes

- The virtual environment (`venv/`) should not be committed to version control
- Docker images are built automatically on first run
- Both environments are configured for development with hot-reload capabilities
