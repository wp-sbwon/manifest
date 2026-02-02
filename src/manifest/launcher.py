"""
Manifest launcher: starts View and the chat/terminal backend.

Supports multiple backends; the primary one is OpenCode. Requires the configured backend and Podman (for containers) to be installed and running. The launcher does not install them; it checks, warns if missing, and exits.
"""
import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path
from typing import Optional

from manifest.core.logger import get_logger

logger = get_logger(__name__)

DEFAULT_AGENT = "manifest-orchestrator"
CONTAINER_API_PORT = 4097

# Project directory: cwd when running from a target project; in dev (manifest repo) use a temp dir inside the repo.
# Override with MANIFEST_PROJECT_DIR (e.g. export MANIFEST_PROJECT_DIR=/path/to/project).
DEV_PROJECT_DIR_NAME = "tmp"


def _is_manifest_repo(path: Path) -> bool:
    """True if path looks like the manifest repo (dev environment)."""
    return (path / "src" / "manifest").is_dir()


def _get_default_project_dir() -> Path:
    """Return the session project directory. In dev (manifest repo) use tmp/ inside repo; else cwd."""
    if os.environ.get("MANIFEST_PROJECT_DIR"):
        p = Path(os.environ.get("MANIFEST_PROJECT_DIR", "")).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p
    cwd = Path.cwd()
    if _is_manifest_repo(cwd):
        p = cwd / DEV_PROJECT_DIR_NAME
        p.mkdir(parents=True, exist_ok=True)
        return p
    return cwd


def _get_session_manifest_dir() -> Path:
    """Return the .manifest directory for the session project (state, View, logs). Ensures it exists."""
    d = _get_default_project_dir() / ".manifest"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _get_manifest_dir() -> Path:
    """Return manifest dir for current session (project's .manifest)."""
    return _get_session_manifest_dir()


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


def _get_opencode_path() -> Optional[str]:
    return shutil.which("opencode")


def _is_opencode_available() -> bool:
    path = _get_opencode_path()
    if not path:
        return False
    try:
        r = subprocess.run(
            [path, "--version"],
            capture_output=True,
            timeout=5,
        )
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def _get_podman_docker_host() -> Optional[str]:
    """Discover Podman API socket and return DOCKER_HOST value (unix:// or npipe://), or None."""
    podman = shutil.which("podman")
    if not podman:
        return None
    system = platform.system()
    env = os.environ.copy()
    try:
        if system == "Darwin":
            r = subprocess.run(
                [podman, "machine", "inspect", "--format", "{{.ConnectionInfo.PodmanSocket.Path}}"],
                capture_output=True,
                text=True,
                timeout=10,
                env=env,
            )
            if r.returncode != 0 or not r.stdout or not r.stdout.strip():
                return None
            path = r.stdout.strip()
            return f"unix://{path}" if path and not path.startswith("unix://") else path or None
        if system == "Windows":
            r = subprocess.run(
                [podman, "machine", "inspect", "--format", "{{.ConnectionInfo.PodmanPipe.Path}}"],
                capture_output=True,
                text=True,
                timeout=10,
                env=env,
            )
            if r.returncode != 0 or not r.stdout or not r.stdout.strip():
                return None
            path = r.stdout.strip()
            return f"npipe://{path}" if path and not path.startswith("npipe://") else path or None
        r = subprocess.run(
            [podman, "info", "--format", "{{.Host.RemoteSocket.Path}}"],
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        if r.returncode != 0 or not r.stdout or not r.stdout.strip():
            return None
        path = r.stdout.strip()
        return f"unix://{path}" if path and not path.startswith("unix://") else path or None
    except (subprocess.TimeoutExpired, Exception):
        return None


def _is_container_runtime_available() -> bool:
    """Check if Podman is running and Docker-compatible API is reachable."""
    docker_host = _get_podman_docker_host()
    if not docker_host:
        return False
    prev = os.environ.get("DOCKER_HOST")
    try:
        os.environ["DOCKER_HOST"] = docker_host
        import docker
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False
    finally:
        if prev is None:
            os.environ.pop("DOCKER_HOST", None)
        else:
            os.environ["DOCKER_HOST"] = prev


def _start_view() -> Optional[subprocess.Popen]:
    """Start the View app so the TUI is visible. On macOS opens a new Terminal window; otherwise runs in background with log."""
    manifest_dir = _get_manifest_dir()
    cwd = os.getcwd()
    src_root = Path(__file__).resolve().parent.parent
    pypath = os.environ.get("PYTHONPATH", "") or str(src_root)
    try:
        if platform.system() == "Darwin":
            manifest_dir.mkdir(parents=True, exist_ok=True)
            launch_script = manifest_dir / "view_launch.sh"
            script_lines = [
                "#!/bin/bash",
                f'cd "{cwd}"',
                "[ -f venv/bin/activate ] && source venv/bin/activate",
                f'export PYTHONPATH="{pypath}"',
                f'exec python -m manifest.view.app --manifest-dir "{manifest_dir}"',
            ]
            launch_script.write_text("\n".join(script_lines), encoding="utf-8")
            launch_script.chmod(0o755)
            subprocess.Popen(
                ["open", "-a", "Terminal.app", str(launch_script)],
                cwd=cwd,
                env=os.environ,
            )
            logger.info("View launched in new Terminal window: %s", launch_script)
            print("Manifest View opened in a new Terminal window.", file=sys.stderr)
            return None
        view_log = manifest_dir.parent / ".manifest_view.log"
        env = {**os.environ, "PYTHONPATH": pypath}
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
                cwd=cwd,
                env=env,
            )
        logger.info("View process started: pid=%s, log=%s", proc.pid, view_log)
        print(f"Manifest View started in background (PID: {proc.pid}, log: {view_log})", file=sys.stderr)
        return proc
    except Exception as e:
        logger.error("Could not start Manifest View: %s", e, exc_info=True)
        print(f"Warning: Could not start Manifest View: {e}", file=sys.stderr)
        return None


def _start_container_api() -> Optional[subprocess.Popen]:
    """Start Container API in a subprocess when Podman is available."""
    if not _is_container_runtime_available():
        return None
    try:
        manifest_dir = _get_manifest_dir()
        api_log = manifest_dir / "container_api.log"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, "PYTHONPATH": os.environ.get("PYTHONPATH", "") or str(Path(__file__).resolve().parent.parent)}
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
                env=env,
            )
        logger.info("Container API started: pid=%s, port=%s", proc.pid, CONTAINER_API_PORT)
        return proc
    except Exception as e:
        logger.warning("Could not start Container API: %s", e)
        return None


def _get_opencode_config_path() -> Optional[Path]:
    """Path to opencode.json so OpenCode finds manifest-orchestrator when run in scratch. Prefer cwd, then manifest app root."""
    for candidate in [Path.cwd() / "opencode.json", Path(__file__).resolve().parent.parent.parent / "opencode.json"]:
        if candidate.exists():
            return candidate.resolve()
    return None


def run_opencode() -> int:
    """Run OpenCode in the current process (exec). Uses scratch project dir for a clean session."""
    opencode_path = _get_opencode_path()
    if not opencode_path:
        sys.stderr.write("opencode not found on PATH.\n")
        return 127
    project_dir = _get_default_project_dir()
    opencode_config = _get_opencode_config_path()
    env = os.environ.copy()
    if opencode_config:
        env["OPENCODE_CONFIG"] = str(opencode_config)
    agent = _get_agent_name()
    argv = [opencode_path, str(project_dir), "-c"]
    if agent:
        argv.extend(["--agent", agent])
    print(f"Starting OpenCode in project: {project_dir}", file=sys.stderr)
    if agent:
        print(f"  Agent: {agent}", file=sys.stderr)
    try:
        os.execve(opencode_path, argv, env)
    except OSError as e:
        sys.stderr.write(f"opencode exec failed: {e}\n")
        return 127
    return 127


def _opencode_hint() -> str:
    """Install hint for OpenCode."""
    system = platform.system()
    if system == "Darwin":
        return "Install OpenCode: brew install opencode  (or see https://opencode.ai/docs)"
    if system == "Windows":
        return "Install OpenCode: winget install OpenCode.OpenCode  (or see https://opencode.ai/docs)"
    return "Install OpenCode: npm install -g opencode-ai  (or see https://opencode.ai/docs)"


def _podman_hint() -> str:
    """Install/start hint for Podman."""
    system = platform.system()
    if shutil.which("podman"):
        if system == "Darwin":
            return "Podman is installed but not running. Start it: podman machine start"
        if system == "Windows":
            return "Podman is installed but not running. Start it: podman machine start"
        return "Podman is installed but not running. Start it: sudo systemctl start podman.socket"
    if system == "Darwin":
        return "Install Podman: brew install podman  (then run: podman machine init --now)"
    if system == "Windows":
        return "Install Podman: winget install RedHat.Podman  (then run: podman machine init)"
    return "Install Podman: sudo apt-get install podman  or  sudo dnf install podman  (see https://podman.io)"


def main() -> int:
    """Check OpenCode and Podman; if both available, start View and OpenCode. Otherwise warn and exit."""
    if not _is_opencode_available():
        sys.stderr.write("OpenCode is required but not found.\n")
        sys.stderr.write(f"  {_opencode_hint()}\n")
        return 1
    docker_host = _get_podman_docker_host()
    if not docker_host:
        sys.stderr.write("Podman is required but not found or not running.\n")
        sys.stderr.write(f"  {_podman_hint()}\n")
        return 1
    if not _is_container_runtime_available():
        sys.stderr.write("Podman is required but the Docker API is not reachable.\n")
        sys.stderr.write(f"  {_podman_hint()}\n")
        return 1
    os.environ["DOCKER_HOST"] = docker_host
    _start_view()
    _start_container_api()
    return run_opencode()


if __name__ == "__main__":
    sys.exit(main())
