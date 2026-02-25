"""Tests for manifest.opencode.architect."""
from pathlib import Path
from unittest.mock import patch
import json
import pytest

from manifest.opencode.architect import write_architecture, write_prd, create_blueprint_from_prd
from manifest.audit.entity_schema import empty_blueprint_root, PROJECT_ROOT_ID, empty_entity
from manifest.io.prd_io import load_prd


def test_write_architecture_valid(tmp_path: Path) -> None:
    root = empty_blueprint_root()
    root["root_id"] = PROJECT_ROOT_ID
    root["entities"] = [dict(empty_entity(PROJECT_ROOT_ID))]
    out = write_architecture(tmp_path, root)
    assert out.get("ok") is True
    assert (tmp_path / "blueprint_design.json").exists()


def test_write_architecture_json_string(tmp_path: Path) -> None:
    root = empty_blueprint_root()
    root["root_id"] = PROJECT_ROOT_ID
    root["entities"] = []
    out = write_architecture(tmp_path, json.dumps(root))
    assert out.get("ok") is True


def test_write_architecture_invalid_json_string(tmp_path: Path) -> None:
    out = write_architecture(tmp_path, "{ invalid")
    assert out.get("ok") is False
    assert "error" in out


def test_write_prd_saves_prd_json_only(tmp_path: Path) -> None:
    """write_prd saves prd.json in fixed format; blueprint_design is not written."""
    out = write_prd(tmp_path, "Build a minimal app.")
    assert out.get("ok") is True
    assert (tmp_path / "prd.json").exists()
    assert not (tmp_path / "blueprint_design.json").exists()
    prd = load_prd(tmp_path)
    assert "minimal app" in (prd.get("mission") or "")


def test_write_prd_accepts_dict(tmp_path: Path) -> None:
    out = write_prd(tmp_path, {"title": "My Product", "mission": "Goal here.", "sections": []})
    assert out.get("ok") is True
    prd = load_prd(tmp_path)
    assert prd.get("title") == "My Product"
    assert prd.get("mission") == "Goal here."
    assert prd.get("sections") == []


def test_create_blueprint_from_prd_creates_blueprint_and_starts_expansion(tmp_path: Path) -> None:
    """create_blueprint_from_prd builds blueprint from PRD and spawns layer writer for expansion."""
    from manifest.io.prd_io import save_prd
    save_prd(tmp_path, {"title": "App", "mission": "A small CLI app.", "sections": []})
    with patch("manifest.opencode.architect.subprocess.Popen") as mock_popen:
        out = create_blueprint_from_prd(tmp_path, project_root=tmp_path)
    assert out.get("ok") is True
    from manifest.io.blueprint_io import load_blueprint
    data = load_blueprint(tmp_path)
    assert len(data.get("entities") or []) == 1
    mission = (data["entities"][0].get("narrative") or {}).get("mission") or ""
    assert "small CLI app" in mission
    mock_popen.assert_called_once()
    call_args = mock_popen.call_args[0][0]
    assert "--parent" in call_args and "PROJECT_ROOT" in call_args
    assert "--layer" in call_args and "0" in call_args
