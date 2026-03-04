"""Integration: run bin/run_bottom_up_docs.py as real subprocess — verify output files."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.mock_project_builder import create_mock_project

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BIN_BOTTOM_UP = REPO_ROOT / "bin" / "run_bottom_up_docs.py"


def _run_bottom_up(project_root, manifest_dir, env_extra=None):
    """Run the bottom-up CLI script as a real subprocess."""
    import os
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    # Skip slow metrics (ruff/pytest) in CI — we test those separately
    env["MANIFEST_VIEW_SKIP_SLOW_METRICS"] = "1"
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(BIN_BOTTOM_UP),
         "--project-root", str(project_root),
         "--manifest-dir", str(manifest_dir)],
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )


@pytest.mark.integration
def test_bottom_up_creates_blueprint_code(tmp_path):
    """CLI creates blueprint_code.json from code extraction."""
    project_root, manifest_dir = create_mock_project(tmp_path)

    result = _run_bottom_up(project_root, manifest_dir)
    assert result.returncode == 0, f"stderr: {result.stderr}"

    bp_code = manifest_dir / "blueprint_code.json"
    assert bp_code.exists(), "blueprint_code.json should be created"
    data = json.loads(bp_code.read_text(encoding="utf-8"))
    assert len(data.get("entities") or []) >= 2


@pytest.mark.integration
def test_bottom_up_creates_blueprint_view(tmp_path):
    """CLI creates blueprint_view.json with view schema."""
    project_root, manifest_dir = create_mock_project(tmp_path)

    result = _run_bottom_up(project_root, manifest_dir)
    assert result.returncode == 0, f"stderr: {result.stderr}"

    bp_view = manifest_dir / "blueprint_view.json"
    assert bp_view.exists(), "blueprint_view.json should be created"
    data = json.loads(bp_view.read_text(encoding="utf-8"))
    assert "entities" in data
    assert data.get("root_id")


@pytest.mark.integration
def test_bottom_up_creates_state_json(tmp_path):
    """CLI writes health metrics to state.json."""
    project_root, manifest_dir = create_mock_project(tmp_path)

    result = _run_bottom_up(project_root, manifest_dir)
    assert result.returncode == 0, f"stderr: {result.stderr}"

    state_path = manifest_dir / "state.json"
    assert state_path.exists(), "state.json should be created"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert "health_metrics" in state


@pytest.mark.integration
def test_bottom_up_fails_without_design_blueprint(tmp_path):
    """CLI exits 1 when blueprint_design.json is missing."""
    project_root = tmp_path / "empty_project"
    project_root.mkdir()
    manifest_dir = project_root / ".manifest"
    manifest_dir.mkdir()
    # Write a .py file so mtime > 0
    (project_root / "main.py").write_text("x = 1\n", encoding="utf-8")

    result = _run_bottom_up(project_root, manifest_dir)
    assert result.returncode == 1


@pytest.mark.integration
def test_bottom_up_stderr_reports_progress(tmp_path):
    """CLI prints progress to stderr (not stdout)."""
    project_root, manifest_dir = create_mock_project(tmp_path)

    result = _run_bottom_up(project_root, manifest_dir)
    assert result.returncode == 0
    assert "blueprint_code" in result.stderr.lower() or "updated" in result.stderr.lower()
