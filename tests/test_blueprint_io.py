"""Tests for manifest.io.blueprint_io (load/save)."""
import json
from pathlib import Path

import pytest

from manifest.audit.entity_schema import empty_blueprint_root, PROJECT_ROOT_ID, empty_entity
from manifest.io.blueprint_io import load_blueprint, load_code_blueprint, save_blueprint
from manifest.audit.blueprint.manifest_filenames import BLUEPRINT_DESIGN_FILE, BLUEPRINT_CODE_FILE


def test_load_blueprint_missing_returns_empty_root(tmp_path: Path) -> None:
    data = load_blueprint(tmp_path)
    assert data.get("version") == "1.0"
    assert data.get("entities") == []
    assert "root_id" in data


def test_load_code_blueprint_missing_returns_empty_root(tmp_path: Path) -> None:
    data = load_code_blueprint(tmp_path)
    assert data.get("version") == "1.0"
    assert data.get("entities") == []


def test_save_and_load_blueprint(tmp_path: Path) -> None:
    root = empty_blueprint_root()
    root["root_id"] = PROJECT_ROOT_ID
    root["entities"] = [dict(empty_entity(PROJECT_ROOT_ID))]
    ok = save_blueprint(tmp_path, root)
    assert ok is True
    path = tmp_path / BLUEPRINT_DESIGN_FILE
    assert path.exists()
    data = load_blueprint(tmp_path)
    assert data.get("root_id") == PROJECT_ROOT_ID
    assert len(data.get("entities") or []) == 1


def test_save_blueprint_rejects_invalid(tmp_path: Path) -> None:
    invalid = {"version": "1.0", "entities": [{"id": "e1", "children": "not-a-list"}]}
    ok = save_blueprint(tmp_path, invalid)
    assert ok is False
    assert not (tmp_path / BLUEPRINT_DESIGN_FILE).exists()
