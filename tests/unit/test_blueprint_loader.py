"""Unit tests for BlueprintLoader."""
import json
from pathlib import Path

import pytest

from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_blueprint_root, empty_entity


@pytest.mark.unit
def test_load_blueprint_missing_returns_empty_structure(tmp_path: Path) -> None:
    """Load when blueprint_design.json is missing returns empty blueprint structure."""
    data = BlueprintLoader.load_blueprint(tmp_path)
    assert data.get("version") == "1.0"
    assert "entities" in data
    assert (data.get("entities") or []) == []


@pytest.mark.unit
def test_load_blueprint_valid_returns_entities(tmp_path: Path) -> None:
    """Load when file exists returns normalized blueprint."""
    design = {
        "version": "1.0",
        "root_id": PROJECT_ROOT_ID,
        "entities": [
            dict(empty_entity(PROJECT_ROOT_ID)),
            {"id": "a", "children": [], "dependencies": [], "intent": {}, "reality": {}, "outgoing_contracts": []},
        ],
    }
    design["entities"][0]["children"] = ["a"]
    path = tmp_path / "blueprint_design.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(design, f, indent=2)
    data = BlueprintLoader.load_blueprint(tmp_path)
    assert data.get("root_id") == PROJECT_ROOT_ID
    assert len(data.get("entities") or []) >= 2
    ids = {e.get("id") for e in data.get("entities") or []}
    assert PROJECT_ROOT_ID in ids
    assert "a" in ids


@pytest.mark.unit
def test_load_code_blueprint_missing_returns_empty_structure(tmp_path: Path) -> None:
    """Load code blueprint when missing returns empty structure with metadata."""
    data = BlueprintLoader.load_code_blueprint(tmp_path)
    assert "version" in data
    assert "entities" in data
    assert (data.get("entities") or []) == []
