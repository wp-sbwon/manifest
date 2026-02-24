"""
Health stats from code: lint result, test coverage %, build size.
"""
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from manifest.core.logger import get_logger

logger = get_logger(__name__)


def get_health_from_code(project_root: Path) -> Dict[str, Any]:
    """
    Get health stats from the code on disk.
    project_root: parent of .manifest. Returns: code_quality, test_coverage, binary_size.
    """
    out: Dict[str, Any] = {"code_quality": None, "test_coverage": None, "binary_size": None}
    project_root = Path(project_root).resolve()
    if not project_root.is_dir():
        return out
    skip_slow = os.environ.get("MANIFEST_VIEW_SKIP_SLOW_METRICS", "").strip() == "1"

    if not skip_slow:
        quality_str, quality_tag = _lint_quality(project_root)
        out["code_quality"] = quality_str
        out["_quality_tag"] = quality_tag
        out["test_coverage"] = _pytest_coverage(project_root)
    else:
        out["code_quality"] = "—"
        out["_quality_tag"] = "dim"

    out["binary_size"] = _build_size(project_root)
    return out


def write_health_to_state(manifest_dir: Path) -> bool:
    """
    Run health-from-code and write results to state.json (health_metrics).
    View reads health from state.
    """
    manifest_dir = Path(manifest_dir).resolve()
    project_root = manifest_dir.parent
    try:
        health = get_health_from_code(project_root)
        metrics = {
            "code_quality": health.get("code_quality"),
            "test_coverage": health.get("test_coverage"),
            "binary_size": health.get("binary_size"),
        }
        from manifest.core.state_manager import StateManager
        state_mgr = StateManager(manifest_dir)
        state_mgr.set_health_metrics(metrics)
        return state_mgr.save_state_sync()
    except Exception as e:
        logger.debug("write_health_to_state failed: %s", e)
        return False


def _lint_quality(project_root: Path) -> Tuple[str, str]:
    """Run ruff; return (label, color)."""
    try:
        check_dir = project_root / "src"
        if not check_dir.is_dir():
            check_dir = project_root
        result = subprocess.run(
            ["ruff", "check", "--format", "json", str(check_dir)],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            timeout=10,
        )
        count = 0
        if result.stdout:
            try:
                import json as _json
                data = _json.loads(result.stdout)
                count = len(data) if isinstance(data, list) else 0
            except Exception:
                pass
        if count == 0:
            return "Excellent", "green"
        if count <= 5:
            return "Good", "green"
        if count <= 20:
            return f"{count} issues", "yellow"
        return f"{count} issues", "red"
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        logger.debug("Lint failed: %s", e)
        return "—", "dim"


def _pytest_coverage(project_root: Path) -> Optional[int]:
    """Run pytest --cov; return % or None."""
    try:
        env = os.environ.copy()
        src_dir = project_root / "src"
        env["PYTHONPATH"] = str(src_dir if src_dir.is_dir() else project_root)
        if not (project_root / "tests").is_dir():
            return None
        cov_target = "src" if src_dir.is_dir() else ("calc" if (project_root / "calc").is_dir() else "src")
        result = subprocess.run(
            [
                "python", "-m", "pytest",
                "tests/",
                f"--cov={cov_target}",
                "--cov-report=term-missing",
                "--no-cov-on-fail",
                "-q",
                "--tb=no",
            ],
            capture_output=True,
            text=True,
            cwd=str(project_root),
            env=env,
            timeout=45,
        )
        for line in (result.stdout or "").splitlines():
            if "TOTAL" in line.upper():
                m = re.search(r"(\d+)%", line)
                if m:
                    return int(m.group(1))
        for line in (result.stdout or "").splitlines()[::-1]:
            m = re.search(r"(\d+)%", line)
            if m:
                return int(m.group(1))
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        logger.debug("Coverage failed: %s", e)
        return None


def _build_size(project_root: Path) -> Optional[str]:
    """Size of dist/ or a single exe at root; else None."""
    try:
        dist = project_root / "dist"
        if dist.is_dir():
            total = sum(f.stat().st_size for f in dist.rglob("*") if f.is_file())
            if total >= 1024 * 1024:
                return f"{total / (1024 * 1024):.1f} MB"
            if total >= 1024:
                return f"{total / 1024:.1f} KB"
            return f"{total} B"
        for name in ("main", "app", "run"):
            exe = project_root / name
            if exe.is_file() and os.access(exe, os.X_OK):
                size = exe.stat().st_size
                if size >= 1024 * 1024:
                    return f"{size / (1024 * 1024):.1f} MB"
                return f"{size / 1024:.1f} KB"
        return None
    except Exception as e:
        logger.debug("Build size failed: %s", e)
        return None
