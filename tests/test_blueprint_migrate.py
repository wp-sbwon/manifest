"""Tests for blueprint migration (old components + contracts -> new entities format)."""
import json
import tempfile
from pathlib import Path

import pytest

from manifest.audit.blueprint_migrate import (
    migrate_blueprint_data,
    migrate_file,
    migrate_manifest_dir,
)
from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_intent, empty_reality
from manifest.audit.entity_validation import (
    validate_blueprint_data,
    is_legacy_format,
)


def test_migrate_plan_old_to_new():
    """Legacy plan (components + contracts) -> new format (entities, root_id)."""
    old = {
        "version": "1.0",
        "components": [
            {"id": "comp-a", "name": "ServiceA", "description": "Does A", "interface": "run()"},
            {"id": "comp-b", "name": "ServiceB", "description": "Does B"},
        ],
        "contracts": [
            {"from": "comp-a", "to": "comp-b", "type": "call"},
        ],
        "zones": {"server": ["comp-a"], "client": ["comp-b"]},
    }
    assert is_legacy_format(old) is True
    new = migrate_blueprint_data(old, is_plan=True)
    assert is_legacy_format(new) is False
    assert "entities" in new
    assert new.get("root_id") == PROJECT_ROOT_ID
    assert "contracts" in new
    entities = new["entities"]
    root = next((e for e in entities if e.get("id") == PROJECT_ROOT_ID), None)
    assert root is not None
    assert set(root.get("children", [])) >= {"comp-a", "comp-b"}
    comp_a = next((e for e in entities if e.get("id") == "comp-a"), None)
    assert comp_a is not None
    assert comp_a.get("intent", {}).get("narrative", {}).get("role") == "ServiceA"
    assert comp_a.get("reality", {}).get("symbol") == ""
    assert comp_a.get("dependencies") == ["comp-b"]


def test_migrate_actual_old_to_new():
    """Legacy actual (components + contracts) -> new format (reality filled)."""
    old = {
        "version": "1.0",
        "components": [
            {
                "id": "comp-x",
                "name": "Handler",
                "file": "src/handler.py",
                "module_path": "src.handler",
                "detected_interface": "handle(req)",
                "dependencies": ["external-logging"],
                "side_effects": ["logging"],
                "complexity": "O(n)",
            },
        ],
        "contracts": [{"from": "comp-x", "to": "external-logging", "type": "dependency"}],
    }
    new = migrate_blueprint_data(old, is_plan=False)
    assert "entities" in new
    comp_x = next((e for e in new["entities"] if e.get("id") == "comp-x"), None)
    assert comp_x is not None
    assert comp_x.get("reality", {}).get("symbol") == "src/handler.py"
    assert "logging" in (comp_x.get("reality", {}).get("traits") or [])
    assert comp_x.get("intent", {}).get("narrative", {}).get("role") == ""


def test_migrate_result_validates():
    """Migrated data passes validate_blueprint_data."""
    old = {
        "version": "1.0",
        "components": [
            {"id": "c1", "name": "C1"},
        ],
        "contracts": [],
        "zones": {},
    }
    new = migrate_blueprint_data(old, is_plan=True)
    valid, errors = validate_blueprint_data(new)
    assert valid is True, errors


def test_migrate_file_skips_new_format():
    """migrate_file does not overwrite when file already has entities (new format)."""
    data = {
        "version": "1.0",
        "root_id": PROJECT_ROOT_ID,
        "entities": [
            {"id": PROJECT_ROOT_ID, "children": [], "dependencies": [], "intent": empty_intent(), "reality": empty_reality()},
        ],
        "contracts": [],
    }
    path = Path(tempfile.mkdtemp()) / "blueprint.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    try:
        result = migrate_file(path, is_plan=True)
        assert result is False
        with open(path, encoding="utf-8") as rf:
            still = json.load(rf)
        assert still.get("entities") is not None
        assert len(still["entities"]) == 1
    finally:
        path.unlink(missing_ok=True)
        path.parent.rmdir()


def test_migrate_manifest_dir_no_files():
    """migrate_manifest_dir with empty dir does not crash."""
    with tempfile.TemporaryDirectory() as tmp:
        results = migrate_manifest_dir(Path(tmp))
        assert "blueprint.json" in results
        assert "blueprint_code.json" in results
        assert results["blueprint.json"] is False
        assert results["blueprint_code.json"] is False
