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
from typing import Optional, Tuple

from manifest.core.logger import get_logger
from manifest.core.constants import CONTAINER_API_PORT

logger = get_logger(__name__)

DEFAULT_AGENT = "orchestrator"

# Project directory: cwd for actual app use. Override with MANIFEST_PROJECT_DIR.
# In dev (manifest repo), set MANIFEST_DEV=1 to use tmp/ inside repo; otherwise cwd is used.
DEV_PROJECT_DIR_NAME = "tmp"


def _is_manifest_repo(path: Path) -> bool:
    """True if path looks like the manifest repo (dev environment)."""
    return (path / "src" / "manifest").is_dir()


def _get_default_project_dir() -> Path:
    """Return the session project directory. Uses MANIFEST_PROJECT_DIR if set; else cwd.
    In dev (manifest repo), set MANIFEST_DEV=1 to use tmp/ inside repo."""
    if os.environ.get("MANIFEST_PROJECT_DIR"):
        p = Path(os.environ.get("MANIFEST_PROJECT_DIR", "")).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p
    cwd = Path.cwd()
    if _is_manifest_repo(cwd) and os.environ.get("MANIFEST_DEV"):
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
    except Exception as e:
        logger.debug("_get_agent_from_config failed: %s", e)
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
    return _get_podman_docker_host_impl(verbose=False)


def _get_podman_docker_host_impl(verbose: bool = False) -> Optional[str]:
    """Implementation; when verbose=True, print each step to stderr."""
    def _log(msg: str) -> None:
        if verbose:
            sys.stderr.write(f"  {msg}\n")
            sys.stderr.flush()

    podman = shutil.which("podman")
    if not podman:
        _log("podman: not found in PATH")
        return None
    _log(f"podman: found at {podman}")
    system = platform.system()
    env = os.environ.copy()
    try:
        if system == "Darwin":
            import stat
            home = os.environ.get("HOME", str(Path.home()))
            _log("trying: default socket paths (stable when machine is running)")
            for rel in (
                ".local/share/containers/podman/machine/podman.sock",
                ".local/share/containers/podman/machine/podman-machine-default/podman.sock",
            ):
                p = Path(home) / rel
                try:
                    if p.exists() and stat.S_ISSOCK(p.stat().st_mode):
                        _log(f"  -> ok: unix://{p}")
                        return f"unix://{p}"
                except OSError:
                    pass
            try:
                if Path("/var/run/docker.sock").exists() and stat.S_ISSOCK(Path("/var/run/docker.sock").stat().st_mode):
                    return "unix:///var/run/docker.sock"
            except OSError:
                pass

            _log("trying: podman machine inspect")
            r = subprocess.run(
                [podman, "machine", "inspect", "--format", "{{.ConnectionInfo.PodmanSocket.Path}}"],
                capture_output=True,
                text=True,
                timeout=10,
                env=env,
            )
            if r.returncode == 0 and r.stdout and r.stdout.strip():
                path = r.stdout.strip()
                p = Path(path)
                if p.exists() and stat.S_ISSOCK(p.stat().st_mode):
                    out = f"unix://{path}" if not path.startswith("unix://") else path
                    _log(f"  -> ok: {out}")
                    return out
            _log("trying: podman info")
            r2 = subprocess.run(
                [podman, "info", "--format", "{{.Host.RemoteSocket.Path}}"],
                capture_output=True,
                text=True,
                timeout=10,
                env=env,
            )
            if r2.returncode == 0 and r2.stdout and r2.stdout.strip():
                path = r2.stdout.strip()
                p = Path(path)
                if p.exists() and stat.S_ISSOCK(p.stat().st_mode):
                    return f"unix://{path}" if not path.startswith("unix://") else path
            _log("  -> no socket found")
            return None
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
    except (subprocess.TimeoutExpired, Exception) as e:
        if verbose:
            sys.stderr.write(f"  exception: {e}\n")
        return None


def _print_podman_diagnostic() -> None:
    """Print step-by-step Podman detection so we can see exactly what is failing."""
    sys.stderr.write("Podman diagnostic (what we tried):\n")
    docker_host = _get_podman_docker_host_impl(verbose=True)
    if docker_host:
        sys.stderr.write("  trying Docker API ping with DOCKER_HOST=%s\n" % (docker_host[:60] + "..." if len(docker_host) > 60 else docker_host))
        prev = os.environ.get("DOCKER_HOST")
        try:
            os.environ["DOCKER_HOST"] = docker_host
            import docker
            client = docker.from_env()
            client.ping()
            sys.stderr.write("  -> Docker API ping: ok\n")
        except Exception as e:
            sys.stderr.write("  -> Docker API ping failed: %s\n" % (e,))
        finally:
            if prev is None:
                os.environ.pop("DOCKER_HOST", None)
            else:
                os.environ["DOCKER_HOST"] = prev
    else:
        sys.stderr.write("  no socket found from any method\n")
    sys.stderr.flush()


def _start_podman_machine() -> Tuple[bool, str]:
    """If Podman is installed but machine not running, start it (or init+start if no machine).
    Returns (True, "") if API is now reachable, else (False, error_message)."""
    podman = shutil.which("podman")
    if not podman:
        return False, "podman not found"
    system = platform.system()
    if system in ("Darwin", "Windows"):
        try:
            r = subprocess.run(
                [podman, "machine", "start"],
                capture_output=True,
                text=True,
                timeout=120,
                env=os.environ,
            )
            if r.returncode != 0:
                out = (r.stderr or "") + (r.stdout or "")
                if "already running" in out.lower():
                    # Machine is running; proceed to wait for API (socket may not be ready yet)
                    pass
                elif "does not exist" in out or "no machine" in out.lower():
                    r2 = subprocess.run(
                        [podman, "machine", "init", "--now"],
                        capture_output=True,
                        text=True,
                        timeout=300,
                        env=os.environ,
                    )
                    if r2.returncode != 0:
                        err = (r2.stderr or "").strip() or (r2.stdout or "").strip() or "unknown"
                        logger.debug("podman machine init --now failed: %s %s", r2.stdout, r2.stderr)
                        return False, f"podman machine init --now failed: {err[:200]}"
                else:
                    err = (r.stderr or "").strip() or (r.stdout or "").strip() or "unknown"
                    logger.debug("podman machine start failed: %s %s", r.stdout, r.stderr)
                    return False, f"podman machine start failed: {err[:200]}"
            import time
            time.sleep(2)  # give socket time to appear after start
            wait_seconds = 20
            bar_width = 20
            for i in range(wait_seconds):
                if _get_podman_docker_host() and _is_container_runtime_available():
                    sys.stderr.write("\n")
                    return True, ""
                filled = int((i + 1) / wait_seconds * bar_width)
                bar = "=" * filled + ">" * (1 if filled < bar_width else 0) + " " * (bar_width - filled - 1)
                sys.stderr.write(f"\r  [{bar}] {i + 1}/{wait_seconds}s ")
                sys.stderr.flush()
                time.sleep(1)
            sys.stderr.write("\n")
            return False, f"Podman API did not become reachable within {wait_seconds}s (try: podman machine start)"
        except subprocess.TimeoutExpired:
            return False, "podman machine start timed out"
        except Exception as e:
            logger.debug("podman machine start error: %s", e)
            return False, str(e)[:200]
    if system == "Linux":
        try:
            r = subprocess.run(
                ["systemctl", "--user", "start", "podman.socket"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if r.returncode != 0:
                r = subprocess.run(
                    ["sudo", "systemctl", "start", "podman.socket"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
            if r.returncode == 0:
                import time
                time.sleep(2)
                if _get_podman_docker_host() and _is_container_runtime_available():
                    return True, ""
            return False, "podman.socket failed to start or API not reachable"
        except Exception as e:
            return False, str(e)[:200]
    return False, "unsupported platform"


def _is_podman_machine_running() -> bool:
    """True if podman machine is running (e.g. 'podman info' or 'podman machine list' succeeds)."""
    podman = shutil.which("podman")
    if not podman or platform.system() not in ("Darwin", "Windows"):
        return False
    r = subprocess.run(
        [podman, "machine", "list", "--format", "{{.Running}}"],
        capture_output=True,
        text=True,
        timeout=10,
        env=os.environ,
    )
    if r.returncode == 0 and r.stdout:
        return "true" in r.stdout.lower()
    r2 = subprocess.run([podman, "info"], capture_output=True, text=True, timeout=10, env=os.environ)
    return r2.returncode == 0


def _restart_podman_machine() -> Tuple[bool, str]:
    """Stop then start Podman machine and wait for API. Returns (True, "") if reachable."""
    podman = shutil.which("podman")
    if not podman or platform.system() not in ("Darwin", "Windows"):
        return False, ""
    import time
    r = subprocess.run(
        [podman, "machine", "stop"],
        capture_output=True,
        text=True,
        timeout=60,
        env=os.environ,
    )
    if r.returncode != 0 and "not running" not in (r.stderr or "").lower():
        return False, (r.stderr or r.stdout or "").strip()[:150]
    time.sleep(2)
    ok, err = _start_podman_machine()
    return ok, err


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
    except Exception as e:
        logger.debug("_is_container_runtime_available failed: %s", e)
        return False
    finally:
        if prev is None:
            os.environ.pop("DOCKER_HOST", None)
        else:
            os.environ["DOCKER_HOST"] = prev


def _start_view() -> Optional[subprocess.Popen]:
    """Start the View app so the TUI is visible. On macOS opens a new Terminal window; otherwise runs in background with log. Set MANIFEST_VIEW_NO_WINDOW=1 to skip (e.g. in tests)."""
    if os.environ.get("MANIFEST_VIEW_NO_WINDOW"):
        return None
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
                "unset NO_COLOR",
                'export TERM="${TERM:-xterm-256color}"',
                'export TEXTUAL_COLOR_SYSTEM="${TEXTUAL_COLOR_SYSTEM:-truecolor}"',
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
        try:
            from manifest.core.config import ConfigManager
            port = ConfigManager(manifest_dir).get_setting("container_api.port", CONTAINER_API_PORT) or CONTAINER_API_PORT
        except Exception:
            port = CONTAINER_API_PORT
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
                    str(port),
                ],
                stdin=subprocess.DEVNULL,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                cwd=os.getcwd(),
                env=env,
            )
        logger.info("Container API started: pid=%s, port=%s", proc.pid, port)
        return proc
    except Exception as e:
        logger.warning("Could not start Container API: %s", e)
        return None


def _get_opencode_config_path() -> Optional[Path]:
    """Path to opencode.json so OpenCode finds orchestrator when run in scratch. Prefer cwd, then manifest app root."""
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


# Worker agent types that can be configured via config worker-model (and /worker-model slash command).
WORKER_AGENT_TYPES = ("planner", "coder", "test", "review")


WORKER_MODEL_HELP = """manifest config worker-model — set or list worker squad models

Usage:
  manifest config worker-model                    List current models (default = backend default)
  manifest config worker-model <agent>             Clear model for agent (use backend default)
  manifest config worker-model <agent> <p> <m>     Set model (e.g. anthropic claude-sonnet-4-5)
  manifest config worker-model <agent> <p>/<m>    Set model (e.g. anthropic/claude-sonnet-4-5)

Agents: planner, coder, test, review. Config: .manifest/agent_config.json
"""


def _run_config_worker_model(argv: list) -> int:
    """CLI: manifest config worker-model [agent_type] [provider] [model]. Uses .manifest in cwd."""
    args = [a for a in argv if a.strip()]

    if args and args[0] in ("--help", "-h"):
        print(WORKER_MODEL_HELP.strip())
        return 0

    manifest_dir = Path.cwd() / ".manifest"
    if not manifest_dir.is_dir():
        sys.stderr.write("No .manifest directory in current directory. Run from project root.\n")
        return 1
    try:
        from manifest.core.config import ConfigManager
        cm = ConfigManager(manifest_dir)
    except Exception as e:
        sys.stderr.write(f"Config error: {e}\n")
        return 1

    if not args:
        # List current worker models and show usage hint
        lines = ["Worker squad models (empty = use OpenCode/backend default):"]
        for agent_type in WORKER_AGENT_TYPES:
            cfg = cm.get_agent_model_config(agent_type)
            provider = cfg.get("provider", "anthropic")
            model = cfg.get("model")
            value = f"{provider}/{model}" if model else "(default)"
            lines.append(f"  {agent_type}: {value}")
        lines.append("")
        lines.append("Usage: manifest config worker-model [agent] [provider] [model]  |  --help")
        print("\n".join(lines))
        return 0

    agent_type = args[0].lower()
    if agent_type not in WORKER_AGENT_TYPES:
        sys.stderr.write(
            f"Unknown agent type {agent_type!r}. Use one of: {', '.join(WORKER_AGENT_TYPES)}\n"
        )
        return 1

    if len(args) == 1:
        # Clear model for this agent (use backend default)
        cfg = cm.get_agent_model_config(agent_type)
        provider = cfg.get("provider", "anthropic")
        ok = cm.set_agent_model_config(agent_type, provider, None, None, True)
        if not ok:
            sys.stderr.write(f"Failed to save config for {agent_type}.\n")
            return 1
        print(f"{agent_type}: cleared model (using OpenCode/backend default)")
        return 0

    if len(args) == 2:
        # Allow "provider/model" as single arg
        part = args[1]
        if "/" in part:
            provider, model = part.split("/", 1)
        else:
            sys.stderr.write("Use: manifest config worker-model <agent> <provider> <model> or <agent> provider/model\n")
            return 1
    elif len(args) >= 3:
        provider = args[1]
        model = args[2]
    else:
        sys.stderr.write("Use: manifest config worker-model [agent] [provider] [model]\n")
        return 1

    ok = cm.set_agent_model_config(agent_type, provider, model, None, True)
    if not ok:
        sys.stderr.write(f"Failed to save config for {agent_type}.\n")
        return 1
    print(f"{agent_type}: {provider}/{model}")
    return 0


def main() -> int:
    """Entry point: dispatch config subcommands, view-only, or start View + OpenCode."""
    argv = sys.argv[1:]
    if len(argv) >= 2 and argv[0] == "config" and argv[1] == "worker-model":
        return _run_config_worker_model(argv[2:])
    if len(argv) >= 1 and argv[0] == "view":
        _start_view()
        return 0

    if not _is_opencode_available():
        sys.stderr.write("OpenCode is required but not found.\n")
        sys.stderr.write(f"  {_opencode_hint()}\n")
        return 1
    docker_host = _get_podman_docker_host()
    api_ok = docker_host and _is_container_runtime_available()
    if not api_ok and shutil.which("podman") and not os.environ.get("MANIFEST_SKIP_PODMAN_AUTOSTART"):
        machine_running = _is_podman_machine_running()
        if not docker_host:
            if machine_running:
                sys.stderr.write("Podman is running but we couldn't reach it (e.g. after sleep).\n")
                sys.stderr.write("Restarting the machine now to get a fresh connection...\n")
                ok, err = _restart_podman_machine()
            else:
                sys.stderr.write("Podman isn't running yet.\n")
                sys.stderr.write("Starting the machine now...\n")
                ok, err = _start_podman_machine()
            if ok:
                docker_host = _get_podman_docker_host()
                api_ok = docker_host and _is_container_runtime_available()
            elif err:
                sys.stderr.write(f"  Result: {err}\n")
        else:
            sys.stderr.write("We found a Podman socket but the connection didn't respond.\n")
            sys.stderr.write("Restarting the machine now to get a fresh connection...\n")
            ok, err = _restart_podman_machine()
            if ok:
                docker_host = _get_podman_docker_host()
                api_ok = docker_host and _is_container_runtime_available()
            elif err:
                sys.stderr.write(f"  Result: {err}\n")
    if not docker_host:
        if os.environ.get("MANIFEST_PODMAN_DEBUG"):
            _print_podman_diagnostic()
        if _is_podman_machine_running():
            sys.stderr.write("Podman is running but the connection could not be established.\n")
            sys.stderr.write("  Try: podman machine stop && podman machine start\n")
        else:
            sys.stderr.write("Podman is not running.\n")
            sys.stderr.write("  Try: podman machine start\n")
        return 1
    if not _is_container_runtime_available():
        if os.environ.get("MANIFEST_PODMAN_DEBUG"):
            _print_podman_diagnostic()
        sys.stderr.write("Podman could not be reached after starting/restarting the machine.\n")
        sys.stderr.write("  Try: podman machine stop && podman machine start\n")
        return 1
    os.environ["DOCKER_HOST"] = docker_host
    _start_view()
    _start_container_api()
    return run_opencode()


if __name__ == "__main__":
    sys.exit(main())
