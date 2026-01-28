"""
Manifest launcher: starts View and OpenCode.

On run: (1) starts the View process (visualization dashboard), (2) execs OpenCode.
Docker is required for container features; if unavailable, launcher attempts
to install or start it instead of exiting.
"""
import os
import sys
import shutil
import subprocess
import time
import platform
from pathlib import Path
from typing import Optional

from manifest.core.logger import get_logger

logger = get_logger(__name__)

DEFAULT_AGENT = "manifest-orchestrator"

# Seconds to wait for Docker to become available after start/install attempt
DOCKER_WAIT_SECONDS = 30

# Container API port (Launcher starts API on this port when Docker is available).
CONTAINER_API_PORT = 4097


def _get_manifest_dir() -> Path:
    return (Path.cwd() / ".manifest").resolve()


def _get_agent_name() -> str:
    env_agent = os.environ.get("MANIFEST_OPENCODE_AGENT")
    if env_agent:
        return env_agent
    try:
        from manifest.core.config import get_config_manager
        cm = get_config_manager()
        cm.manifest_dir = _get_manifest_dir()
        return cm.get_setting("opencode.agent", DEFAULT_AGENT) or DEFAULT_AGENT
    except Exception:
        return DEFAULT_AGENT


def _is_opencode_available() -> bool:
    if shutil.which("opencode"):
        return True
    try:
        r = subprocess.run(
            ["opencode", "--version"],
            capture_output=True,
            timeout=5,
        )
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def _is_docker_available() -> bool:
    """Check if Docker daemon is running (required like OpenCode)."""
    try:
        import docker
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


def _try_start_docker() -> bool:
    """Try to start Docker daemon (Desktop on macOS/Windows, systemd on Linux). Returns True if start was attempted."""
    system = platform.system()
    try:
        if system == "Darwin":
            for app_path in ["/Applications/Docker.app", "/Applications/Docker Desktop.app"]:
                if Path(app_path).exists():
                    logger.info("Starting Docker Desktop from %s", app_path)
                    subprocess.Popen(
                        ["open", "-a", app_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    return True
            return False
        if system == "Linux":
            try:
                subprocess.run(
                    ["docker", "--version"],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                r = subprocess.run(
                    ["sudo", "systemctl", "start", "docker"],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=5,
                )
                return r.returncode == 0
            except (FileNotFoundError, subprocess.TimeoutExpired):
                return False
        if system == "Windows":
            for p in [
                "C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe",
                "C:\\Program Files (x86)\\Docker\\Docker\\Docker Desktop.exe",
            ]:
                if Path(p).exists():
                    subprocess.Popen([p], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    return True
        return False
    except Exception as e:
        logger.warning("Error starting Docker: %s", e)
        return False


def _try_install_docker() -> bool:
    """Try to install Docker if not in PATH (e.g. brew on macOS). Returns True if install was attempted."""
    if shutil.which("docker"):
        return False
    system = platform.system()
    try:
        if system == "Darwin" and shutil.which("brew"):
            logger.info("Attempting to install Docker via Homebrew...")
            r = subprocess.run(
                ["brew", "install", "--cask", "docker"],
                capture_output=True,
                timeout=300,
            )
            if r.returncode == 0:
                return True
            # Even if brew failed, we tried
            return False
        # Open install page as fallback so user can install manually
        if system == "Darwin":
            subprocess.Popen(["open", "https://www.docker.com/products/docker-desktop"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif system == "Windows":
            subprocess.Popen(["start", "https://www.docker.com/products/docker-desktop"], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            logger.info("Install Docker: https://docs.docker.com/engine/install/")
        return False
    except Exception as e:
        logger.warning("Error attempting Docker install: %s", e)
        return False


def _ensure_docker_available() -> bool:
    """
    Ensure Docker is available: try install (if missing) and start (if not running), then wait.
    Does not exit; returns True if Docker is available, False otherwise.
    """
    if _is_docker_available():
        return True
    # If docker binary missing, try install once
    if not shutil.which("docker"):
        _try_install_docker()
        time.sleep(2)
    _try_start_docker()
    deadline = time.monotonic() + DOCKER_WAIT_SECONDS
    while time.monotonic() < deadline:
        if _is_docker_available():
            return True
        time.sleep(1)
    return False


def _start_view() -> Optional[subprocess.Popen]:
    """Start the View app in a subprocess. Returns the Popen or None on failure."""
    manifest_dir = _get_manifest_dir()
    try:
        # Use a log file for View output (for debugging)
        view_log = manifest_dir.parent / ".manifest_view.log"
        with open(view_log, "w") as log_file:
            proc = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "manifest.view.app",
                    "--manifest-dir",
                    str(manifest_dir),
                ],
                stdin=subprocess.DEVNULL,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                cwd=os.getcwd(),
                env={**os.environ, "PYTHONPATH": os.environ.get("PYTHONPATH", "") or str(Path(__file__).resolve().parent.parent)},
            )
        logger.info("View process started: pid=%s, log=%s", proc.pid, view_log)
        print(f"Manifest View started (PID: {proc.pid}, log: {view_log})", file=sys.stderr)
        return proc
    except Exception as e:
        logger.error("Could not start View: %s", e, exc_info=True)
        print(f"Warning: Could not start Manifest View: {e}", file=sys.stderr)
        return None


def _start_container_api() -> Optional[subprocess.Popen]:
    """Start Container API in a subprocess when Docker is available."""
    if not _is_docker_available():
        return None
    try:
        manifest_dir = _get_manifest_dir()
        api_log = manifest_dir / "container_api.log"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        with open(api_log, "w") as log_file:
            proc = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "manifest.agents.container_api:app",
                    "--host",
                    "0.0.0.0",
                    "--port",
                    str(CONTAINER_API_PORT),
                ],
                stdin=subprocess.DEVNULL,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                cwd=os.getcwd(),
                env={**os.environ, "PYTHONPATH": os.environ.get("PYTHONPATH", "") or str(Path(__file__).resolve().parent.parent)},
            )
        logger.info("Container API started: pid=%s, port=%s", proc.pid, CONTAINER_API_PORT)
        return proc
    except Exception as e:
        logger.warning("Could not start Container API: %s", e)
        return None


def run_opencode() -> int:
    """Run OpenCode in the current process (exec). Returns only on exec failure."""
    agent = _get_agent_name()
    cwd = str(Path.cwd())

    # Try with agent first, fallback to no agent if it fails
    # OpenCode may not have the agent registered, so we'll let user select in UI
    argv = ["opencode", ".", "-c"]

    # Add agent if specified (but don't fail if agent doesn't exist)
    if agent:
        argv.extend(["--agent", agent])
        print(f"Starting OpenCode with agent: {agent}", file=sys.stderr)
        print(f"If agent '{agent}' is not found, you can select it in OpenCode UI.", file=sys.stderr)
    else:
        print("Starting OpenCode (no agent specified)", file=sys.stderr)

    try:
        os.execvp("opencode", argv)
    except OSError as e:
        sys.stderr.write(f"opencode exec failed: {e}\n")
        return 127
    return 127


def main() -> int:
    """Start View then OpenCode. OpenCode is required; Docker is required but we try to install/start it instead of exiting."""
    if not _is_opencode_available():
        sys.stderr.write(
            "opencode not found. Install OpenCode and ensure 'opencode' is on PATH.\n"
        )
        return 1
    if not _ensure_docker_available():
        sys.stderr.write(
            "Warning: Docker is not available. Manifest will run; container features may be limited. "
            "Install/start Docker and restart if you need containers.\n"
        )
    _start_view()
    _start_container_api()
    return run_opencode()


if __name__ == "__main__":
    sys.exit(main())
