# Development Environment Setup Guide

## Overview

This project supports two development environments:
1. **Python Virtual Environment (venv)** - Recommended for local development
2. **Docker** - For containerized development and deployment

## Python Virtual Environment Setup

### Prerequisites
- Python 3.9 or higher (✅ Detected: Python 3.9.6)

### Quick Setup
```bash
./setup.sh
```

### Manual Setup
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Usage
```bash
# Activate environment
source venv/bin/activate

# Run application (with src/ layout)
PYTHONPATH=src python -m manifest

# Deactivate when done
deactivate
```

## Docker Setup

### Prerequisites
- Docker Desktop (macOS/Windows) or Docker Engine (Linux)

### Installation

#### macOS
1. Download Docker Desktop from: https://www.docker.com/products/docker-desktop
2. Install and start Docker Desktop
3. Verify installation:
   ```bash
   docker --version
   docker-compose --version
   ```

#### Linux
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install docker.io docker-compose

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker
```

### Quick Setup
```bash
./setup-docker.sh
```

### Manual Setup
```bash
# Build Docker image
docker-compose build

# Run container
docker-compose up

# Run in detached mode
docker-compose up -d

# Stop container
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
│       ├── bridge/     # Bridge modules (omoc_bridge)
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
└── README.md           # Project overview
```

## Dependencies

### Python Dependencies
- `textual>=0.40.0` - Terminal UI framework for Python

All dependencies are listed in `requirements.txt`.

## Development Workflow

### Using Virtual Environment (Recommended)

1. **Activate environment:**
   ```bash
   source venv/bin/activate
   ```

2. **Install new packages:**
   ```bash
   pip install <package-name>
   pip freeze > requirements.txt
   ```

3. **Run application:**
   ```bash
   PYTHONPATH=src python -m manifest
   ```

4. **Deactivate:**
   ```bash
   deactivate
   ```

### Using Docker

1. **Build image:**
   ```bash
   docker-compose build
   ```

2. **Run container:**
   ```bash
   docker-compose up
   ```

3. **View logs:**
   ```bash
   docker-compose logs -f
   ```

4. **Stop container:**
   ```bash
   docker-compose down
   ```

## Troubleshooting

### Python Virtual Environment

**Issue: Virtual environment not found**
```bash
# Recreate virtual environment
rm -rf venv
./setup.sh
```

**Issue: Package installation fails**
```bash
# Upgrade pip
pip install --upgrade pip

# Clear pip cache
pip cache purge

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

**Issue: Permission errors**
```bash
# Use python3 explicitly
python3 -m venv venv
```

### Docker

**Issue: Docker not running**
- macOS/Windows: Start Docker Desktop application
- Linux: `sudo systemctl start docker`

**Issue: Permission denied**
- macOS/Windows: Ensure Docker Desktop has proper permissions
- Linux: Add user to docker group:
  ```bash
  sudo usermod -aG docker $USER
  # Log out and log back in
  ```

**Issue: Port conflicts**
- Modify ports in `docker-compose.yml` if needed

**Issue: Build fails**
```bash
# Clean build
docker-compose down
docker system prune -a
docker-compose build --no-cache
```

## Environment Variables

Create a `.env` file in the project root for environment-specific variables:
```bash
# .env
PYTHONUNBUFFERED=1
DEBUG=True
```

Note: `.env` files are gitignored and should not be committed.

## Best Practices

1. **Always use virtual environment for local development**
   - Keeps dependencies isolated
   - Prevents conflicts with system packages

2. **Use Docker for consistent environments**
   - Ensures same environment across team
   - Easy deployment

3. **Keep requirements.txt updated**
   ```bash
   pip freeze > requirements.txt
   ```

4. **Commit setup scripts**
   - Makes onboarding easier
   - Ensures consistent setup

## Verification

### Verify Python Environment
```bash
source venv/bin/activate
python --version
pip list
PYTHONPATH=src python -m manifest
```

### Verify Docker Environment
```bash
docker --version
docker-compose --version
docker-compose build
docker-compose up
```

## Next Steps

1. ✅ Python virtual environment created
2. ✅ Dependencies installed
3. ⏳ Install Docker Desktop (if not installed)
4. ⏳ Test Docker setup (after Docker installation)
5. ⏳ Run application in both environments

## Support

For issues or questions:
1. Check this documentation
2. Review error messages carefully
3. Check Docker/Python logs
4. Verify prerequisites are met