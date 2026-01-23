# Manifest

**AI-Native Orchestration IDE** - Solve Code Blindness by elevating developers to Conductors.

## Documentation

All documentation is located in the [`docs/`](docs/) directory. See [docs/README.md](docs/README.md) for the complete documentation index.

**Quick Links:**
- [User Guide](docs/USER_GUIDE.md) - How to use Manifest
- [API Documentation](docs/API.md) - API reference
- [Module Documentation](docs/MODULES.md) - Detailed module docs
- [Architecture](docs/ARCHITECTURE.md) - System architecture
- [Development Setup](docs/DEV_SETUP.md) - Setup instructions
- [Contributing](docs/CONTRIBUTING.md) - Contribution guidelines
- [Refactoring Notes](docs/REFACTORING.md) - Project refactoring history

## Quick Start

See [DEV_SETUP.md](docs/DEV_SETUP.md) for detailed setup instructions.

# Manifest Development Environment

This document provides an overview of the development environment setup for the Manifest project.

## Prerequisites

- Python 3.9 or higher
- Docker Desktop (for macOS/Windows) or Docker Engine (for Linux)

## Quick Start

### Option 1: Python Virtual Environment (Recommended for Development)

1. **Setup the environment:**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

2. **Activate the virtual environment:**
   ```bash
   source venv/bin/activate
   ```

3. **Run the application:**
   ```bash
   PYTHONPATH=src python -m manifest
   ```
   또는 개발 환경에서:
   ```bash
   export PYTHONPATH=src
   python -m manifest
   ```

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
- See [docs/SKILLS.md](docs/SKILLS.md) for detailed documentation

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