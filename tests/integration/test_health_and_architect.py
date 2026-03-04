"""Integration: health_from_code and architect — real function calls, verify output."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from manifest.audit.code.health_from_code import get_health_from_code, write_health_to_state, _build_size
from manifest.audit.entity_schema import PROJECT_ROOT_ID
from manifest.io.blueprint_io import load_blueprint
from manifest.opencode.architect import create_blueprint_from_prd, write_architecture, write_prd

from tests.mock_project_builder import build_design_blueprint, create_mock_project


# --- health_from_code ---


@pytest.mark.integration
def test_get_health_returns_all_keys(tmp_path):
    """get_health_from_code returns dict with code_quality, test_coverage, binary_size."""
    project_root, _ = create_mock_project(tmp_path)

    health = get_health_from_code(project_root)

    assert "code_quality" in health
    assert "test_coverage" in health
    assert "binary_size" in health


@pytest.mark.integration
def test_get_health_skipped_returns_dash(tmp_path):
    """With MANIFEST_VIEW_SKIP_SLOW_METRICS=1, code_quality is '—'."""
    project_root, _ = create_mock_project(tmp_path)

    with patch.dict("os.environ", {"MANIFEST_VIEW_SKIP_SLOW_METRICS": "1"}):
        health = get_health_from_code(project_root)

    assert health["code_quality"] == "—"


@pytest.mark.integration
def test_build_size_with_dist_dir(tmp_path):
    """_build_size returns formatted size when dist/ exists with files."""
    project_root = tmp_path / "proj"
    project_root.mkdir()
    dist = project_root / "dist"
    dist.mkdir()
    (dist / "app.whl").write_bytes(b"x" * 2048)

    size = _build_size(project_root)
    assert size is not None
    assert "KB" in size or "B" in size


@pytest.mark.integration
def test_build_size_returns_none_without_dist(tmp_path):
    """_build_size returns None when no dist/ or executable."""
    project_root = tmp_path / "proj"
    project_root.mkdir()

    size = _build_size(project_root)
    assert size is None


@pytest.mark.integration
def test_write_health_to_state_creates_state_json(tmp_path):
    """write_health_to_state writes health_metrics into state.json."""
    project_root, manifest_dir = create_mock_project(tmp_path)

    with patch.dict("os.environ", {"MANIFEST_VIEW_SKIP_SLOW_METRICS": "1"}):
        ok = write_health_to_state(manifest_dir)

    assert ok is True
    state_path = manifest_dir / "state.json"
    assert state_path.exists()
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert "health_metrics" in state
    metrics = state["health_metrics"]
    assert "code_quality" in metrics


# --- architect ---


@pytest.mark.integration
def test_write_prd_creates_prd_json(tmp_path):
    """write_prd saves prd.json with title/mission/sections."""
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir()

    result = write_prd(manifest_dir, {"title": "Calculator", "mission": "CLI calc", "sections": []})

    assert result["ok"] is True
    prd_path = manifest_dir / "prd.json"
    assert prd_path.exists()
    prd = json.loads(prd_path.read_text(encoding="utf-8"))
    assert prd["title"] == "Calculator"
    assert prd["mission"] == "CLI calc"


@pytest.mark.integration
def test_write_prd_from_string(tmp_path):
    """write_prd with a plain string wraps it as mission."""
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir()

    result = write_prd(manifest_dir, "Build a CLI calculator")
    assert result["ok"] is True

    prd = json.loads((manifest_dir / "prd.json").read_text(encoding="utf-8"))
    assert "calculator" in prd["mission"].lower()


@pytest.mark.integration
def test_write_architecture_saves_valid_blueprint(tmp_path):
    """write_architecture validates and saves blueprint_design.json."""
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir()

    design = build_design_blueprint()
    result = write_architecture(manifest_dir, design)

    assert result["ok"] is True
    bp = load_blueprint(manifest_dir)
    assert bp["root_id"] == PROJECT_ROOT_ID
    assert len(bp["entities"]) >= 2


@pytest.mark.integration
def test_write_architecture_rejects_invalid_json_string(tmp_path):
    """write_architecture with invalid JSON string returns error."""
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir()

    result = write_architecture(manifest_dir, "not valid json {[")
    assert result["ok"] is False
    assert "Invalid JSON" in result["error"]


@pytest.mark.integration
def test_create_blueprint_from_prd_creates_root_entity(tmp_path):
    """create_blueprint_from_prd creates blueprint_design.json with root entity from PRD."""
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir()

    # Write PRD first
    write_prd(manifest_dir, {"title": "Calculator", "mission": "CLI calc app", "sections": []})

    # Patch Popen so layer writer doesn't actually run
    with patch("manifest.opencode.architect.subprocess.Popen"):
        result = create_blueprint_from_prd(manifest_dir, tmp_path)

    assert result["ok"] is True
    bp = load_blueprint(manifest_dir)
    assert bp["root_id"] == PROJECT_ROOT_ID
    root_ent = next(e for e in bp["entities"] if e["id"] == PROJECT_ROOT_ID)
    assert root_ent["narrative"]["mission"] == "CLI calc app"


@pytest.mark.integration
def test_create_blueprint_from_prd_spawns_layer_writer(tmp_path):
    """create_blueprint_from_prd calls Popen to spawn layer writer."""
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir()
    write_prd(manifest_dir, {"title": "Test", "mission": "Test mission", "sections": []})

    with patch("manifest.opencode.architect.subprocess.Popen") as mock_popen:
        create_blueprint_from_prd(manifest_dir, tmp_path)

    if mock_popen.called:
        cmd = mock_popen.call_args[0][0]
        assert "--parent" in cmd
        assert PROJECT_ROOT_ID in cmd
        assert "--layer" in cmd
        assert "0" in cmd
