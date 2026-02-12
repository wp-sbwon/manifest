"""Tests for entity schema and mechanical validation (Option B)."""
import json
import tempfile
from pathlib import Path

import pytest

from manifest.schema.entity_schema import (
    PROJECT_ROOT_ID,
    empty_intent,
    empty_reality,
    empty_entity,
    empty_blueprint_root,
)
from manifest.schema.entity_validation import (
    normalize_for_schema,
    validate_entity,
    validate_blueprint_data,
    validate_blueprint_file,
)


# --- Schema: required keys, no null ---


def test_empty_intent_has_no_none():
    intent = empty_intent()
    assert intent is not None
    assert "narrative" in intent
    assert None not in (intent.get("narrative") or {}).values()
    assert intent.get("narrative", {}).get("role") == ""
    assert intent.get("narrative", {}).get("mission") == ""


def test_empty_reality_has_no_none():
    reality = empty_reality()
    assert reality is not None
    assert "symbol" in reality
    assert reality.get("symbol") == ""
    assert reality.get("dependencies") == []
    assert None not in (reality.get("protocol") or {}).values()


def test_project_root_id_constant():
    assert PROJECT_ROOT_ID == "PROJECT_ROOT"


def test_empty_entity_has_required_keys():
    ent = empty_entity()
    assert ent.get("id") == ""
    assert "children" in ent and ent["children"] == []
    assert "dependencies" in ent and ent["dependencies"] == []
    assert "intent" in ent and isinstance(ent["intent"], dict)
    assert "reality" in ent and isinstance(ent["reality"], dict)
    assert "outgoing_contracts" in ent and ent["outgoing_contracts"] == []
    assert None not in (ent.get("intent") or {}).values()
    assert None not in (ent.get("reality") or {}).values()


def test_empty_blueprint_root_has_required_keys():
    root = empty_blueprint_root()
    assert "version" in root
    assert "entities" in root and root["entities"] == []
    assert "root_id" in root
    assert "contracts" not in root
    assert None not in [root.get("version"), root.get("entities")]


# --- Validation: validate_entity ---


def test_validate_entity_valid():
    ent = {
        "id": "comp-1",
        "children": [],
        "dependencies": [],
        "intent": empty_intent(),
        "reality": empty_reality(),
        "outgoing_contracts": [],
    }
    valid, errors = validate_entity(ent)
    assert valid is True
    assert errors == []


def test_validate_entity_missing_id():
    ent = {
        "children": [],
        "dependencies": [],
        "intent": {},
        "reality": {},
    }
    valid, errors = validate_entity(ent)
    assert valid is False
    assert any("id" in e for e in errors)


def test_validate_entity_null_children_invalid():
    ent = {
        "id": "x",
        "children": None,
        "dependencies": [],
        "intent": {},
        "reality": {},
    }
    valid, errors = validate_entity(ent)
    assert valid is False
    assert any("children" in e or "null" in e for e in errors)


# --- normalize_for_schema ---


def test_normalize_for_schema_coerces_null():
    data = {"version": "1.0", "entities": None, "root_id": None}
    out = normalize_for_schema(data)
    assert out.get("entities") == []
    assert out.get("root_id") == ""


def test_normalize_for_schema_adds_missing_keys():
    data = {}
    out = normalize_for_schema(data)
    assert "version" in out
    assert "entities" in out
    assert "root_id" in out


def test_normalize_for_schema_entity_intent_reality_defaults():
    data = {
        "version": "1.0",
        "entities": [{"id": "e1", "intent": None, "reality": None}],
        "root_id": "",
    }
    out = normalize_for_schema(data)
    assert len(out["entities"]) == 1
    ent = out["entities"][0]
    assert isinstance(ent.get("intent"), dict)
    assert isinstance(ent.get("reality"), dict)
    assert ent.get("children") == []
    assert ent.get("dependencies") == []
    assert isinstance(ent.get("outgoing_contracts"), list)


# --- validate_blueprint_data ---


def test_validate_blueprint_data_valid():
    data = {
        "version": "1.0",
        "root_id": PROJECT_ROOT_ID,
        "entities": [
            {
                "id": PROJECT_ROOT_ID,
                "children": ["comp-a"],
                "dependencies": [],
                "intent": empty_intent(),
                "reality": empty_reality(),
                "outgoing_contracts": [],
            },
            {
                "id": "comp-a",
                "children": [],
                "dependencies": [],
                "intent": empty_intent(),
                "reality": empty_reality(),
                "outgoing_contracts": [{"to": "external-x", "type": "dependency"}],
            },
        ],
    }
    valid, errors = validate_blueprint_data(data)
    assert valid is True, errors
    assert errors == []


def test_validate_blueprint_data_invalid_entity():
    # normalize_for_schema fills missing keys; use invalid type so validation still fails
    data = {
        "version": "1.0",
        "root_id": "",
        "entities": [{"id": "e1", "children": "not-a-list", "dependencies": [], "intent": {}, "reality": {}, "outgoing_contracts": []}],
    }
    valid, errors = validate_blueprint_data(data)
    assert valid is False
    assert len(errors) > 0


def test_validate_blueprint_file_missing():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "nonexistent.json"
        valid, errors = validate_blueprint_file(path)
        assert valid is False
        assert any("not found" in e or "exist" in e for e in errors)


def test_validate_blueprint_file_valid_new_format():
    data = {
        "version": "1.0",
        "root_id": PROJECT_ROOT_ID,
        "entities": [
            {"id": PROJECT_ROOT_ID, "children": [], "dependencies": [], "intent": empty_intent(), "reality": empty_reality(), "outgoing_contracts": []},
        ],
    }
    path = Path(tempfile.mkdtemp()) / "blueprint_design.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    try:
        valid, errors = validate_blueprint_file(path)
        assert valid is True, errors
    finally:
        path.unlink(missing_ok=True)
        path.parent.rmdir()
