"""
Single smoke test: ensures the app starts up okay.

Run: pytest tests/test_startup.py -v
"""
import subprocess
import sys
from pathlib import Path

# Ensure src is on path (same as running from repo root with PYTHONPATH=src)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def test_app_starts_up():
    """App package imports and exposes runnable entry point (python -m manifest)."""
    import manifest  # noqa: F401
    import manifest.__main__ as main_module
    assert hasattr(main_module, "main")
    assert callable(main_module.main)


def test_app_entry_point_runs():
    """Running the entry point does not crash (import/runtime). Exit 1 for missing OpenCode is OK. Timeout = app started and handed off to OpenCode. No view window (MANIFEST_VIEW_NO_WINDOW) so tests do not pop up a process/window."""
    env = {
        "PYTHONPATH": str(ROOT / "src"),
        "MANIFEST_VIEW_NO_WINDOW": "1",
    }
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "manifest"],
            cwd=ROOT,
            env={**__import__("os").environ, **env},
            capture_output=True,
            text=True,
            timeout=15,
        )
    except subprocess.TimeoutExpired:
        return
    if proc.returncode == 0:
        return
    if proc.returncode != 1:
        raise AssertionError(
            f"manifest exited with {proc.returncode}, expected 0 or 1.\nstderr: {proc.stderr!r}\nstdout: {proc.stdout!r}"
        )
    err = (proc.stderr or "") + (proc.stdout or "")
    if "OpenCode" in err or "opencode" in err:
        return
    raise AssertionError(
        f"manifest exited 1 but stderr does not mention OpenCode.\nstderr: {proc.stderr!r}\nstdout: {proc.stdout!r}"
    )


def test_manifest_view_runs():
    """View app starts (run with short timeout; timeout or exit 0 is success)."""
    env = {"PYTHONPATH": str(ROOT / "src")}
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "manifest.view.app", "--manifest-dir", str(ROOT / "tmp" / ".manifest")],
            cwd=ROOT,
            env={**__import__("os").environ, **env},
            capture_output=True,
            text=True,
            timeout=5,
        )
    except subprocess.TimeoutExpired:
        return  # App was running (TUI blocks until quit)
    assert proc.returncode == 0, f"view app failed: {proc.stderr!r} {proc.stdout!r}"
