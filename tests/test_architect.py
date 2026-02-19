"""Tests for manifest.opencode.architect (write_architecture, write_prd)."""
from pathlib import Path

import pytest

from manifest.opencode.architect import write_architecture, write_prd
from manifest.audit.entity_schema import empty_blueprint_root, PROJECT_ROOT_ID, empty_entity


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
    import json
    out = write_architecture(tmp_path, json.dumps(root))
    assert out.get("ok") is True


def test_write_architecture_invalid_json_string(tmp_path: Path) -> None:
    out = write_architecture(tmp_path, "{ invalid")
    assert out.get("ok") is False
    assert "error" in out


def test_write_prd_creates_minimal_blueprint(tmp_path: Path) -> None:
    out = write_prd(tmp_path, "Build a minimal app.")
    assert out.get("ok") is True
    from manifest.io.blueprint_io import load_blueprint
    data = load_blueprint(tmp_path)
    assert len(data.get("entities") or []) == 1
    mission = (data["entities"][0].get("intent") or {}).get("narrative") or {}
    assert "minimal app" in (mission.get("mission") or "")
