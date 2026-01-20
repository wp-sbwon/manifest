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
   python test.py
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
├── venv/                 # Python virtual environment (gitignored)
├── test.py              # Main application file
├── requirements.txt     # Python dependencies
├── Dockerfile          # Docker image configuration
├── docker-compose.yml  # Docker Compose configuration
├── setup.sh            # Python environment setup script
├── setup-docker.sh     # Docker environment setup script
└── README.md           # This file
```

## Dependencies

### Python Dependencies
- `textual>=0.40.0` - Terminal UI framework

See `requirements.txt` for the complete list.

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
   python test.py
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