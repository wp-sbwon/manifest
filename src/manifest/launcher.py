"""Start View TUI and OpenCode. Uses tmp/ as project dir when MANIFEST_DEV=1 in repo."""
import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path
from typing import Optional

DEV_PROJECT_DIR_NAME = "tmp"


def _is_manifest_repo(path: Path) -> bool:
    return (path / "src" / "manifest").is_dir()


def _get_project_dir() -> Path:
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


def _get_manifest_dir() -> Path:
    d = _get_project_dir() / ".manifest"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _get_opencode_path() -> Optional[str]:
    return shutil.which("opencode")


def _is_opencode_available() -> bool:
    path = _get_opencode_path()
    if not path:
        return False
    try:
        r = subprocess.run([path, "--version"], capture_output=True, timeout=5)
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def _start_view(manifest_dir: Path) -> None:
    if os.environ.get("MANIFEST_VIEW_NO_WINDOW"):
        return
    cwd = os.getcwd()
    src_root = Path(__file__).resolve().parent.parent
    pypath = os.environ.get("PYTHONPATH", "") or str(src_root)
    try:
        if platform.system() == "Darwin":
            manifest_dir.mkdir(parents=True, exist_ok=True)
            script = manifest_dir / "view_launch.sh"
            script.write_text(
                "#!/bin/bash\n"
                "unset NO_COLOR\n"
                'export TERM="${TERM:-xterm-256color}"\n'
                f'cd "{cwd}"\n'
                "[ -f venv/bin/activate ] && source venv/bin/activate\n"
                f'export PYTHONPATH="{pypath}"\n'
                f'exec python -m manifest.view.app --manifest-dir "{manifest_dir}"\n',
                encoding="utf-8",
            )
            script.chmod(0o755)
            subprocess.Popen(["open", "-a", "Terminal.app", str(script)], cwd=cwd, env=os.environ)
            print("Manifest View opened in a new Terminal window.", file=sys.stderr)
            return
        log_path = manifest_dir.parent / ".manifest_view.log"
        env = {**os.environ, "PYTHONPATH": pypath}
        with open(log_path, "w") as log_file:
            subprocess.Popen(
                [sys.executable, "-m", "manifest.view.app", "--manifest-dir", str(manifest_dir)],
                stdin=subprocess.DEVNULL,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                cwd=cwd,
                env=env,
            )
        print(f"Manifest View started in background (log: {log_path})", file=sys.stderr)
    except Exception as e:
        print(f"Warning: Could not start View: {e}", file=sys.stderr)


def _get_opencode_config_path() -> Optional[Path]:
    for candidate in [Path.cwd() / "opencode.json", Path(__file__).resolve().parent.parent.parent / "opencode.json"]:
        if candidate.exists():
            return candidate.resolve()
    return None


def _run_opencode() -> int:
    path = _get_opencode_path()
    if not path:
        sys.stderr.write("opencode not found on PATH.\n")
        return 127
    project_dir = _get_project_dir()
    env = os.environ.copy()
    config = _get_opencode_config_path()
    if config:
        env["OPENCODE_CONFIG"] = str(config)
    agent = os.environ.get("MANIFEST_OPENCODE_AGENT", "architect")
    argv = [path, str(project_dir), "-c", "--agent", agent]
    print(f"Starting OpenCode in project: {project_dir}", file=sys.stderr)
    try:
        os.execve(path, argv, env)
    except OSError as e:
        sys.stderr.write(f"opencode exec failed: {e}\n")
        return 127
    return 127


def main() -> int:
    if not _is_opencode_available():
        sys.stderr.write("OpenCode is required but not found.\n")
        return 1
    _start_view(_get_manifest_dir())
    return _run_opencode()


if __name__ == "__main__":
    sys.exit(main())
