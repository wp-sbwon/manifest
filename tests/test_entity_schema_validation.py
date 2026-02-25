"""Tests for entity schema and validation (unified entity shape)."""
import json
import tempfile
from pathlib import Path

import pytest

from manifest.audit.entity_schema import (
    PROJECT_ROOT_ID,
    empty_entity,
    empty_blueprint_root,
)
from manifest.audit.entity_validation import (
    normalize_for_schema,
    validate_entity,
    validate_blueprint_data,
    validate_blueprint_file,
)


def test_project_root_id_constant():
    assert PROJECT_ROOT_ID == "PROJECT_ROOT"


def test_empty_entity_has_required_keys():
    ent = empty_entity("")
    assert ent.get("id") == ""
    assert "children" in ent and ent["children"] == []
    assert "dependencies" in ent and ent["dependencies"] == []
    assert "narrative" in ent and isinstance(ent["narrative"], dict)
    assert "blueprint" in ent and isinstance(ent["blueprint"], dict)
    assert "protocol" in ent and isinstance(ent["protocol"], dict)
    assert "profile" in ent and isinstance(ent["profile"], dict)
    assert "governance" in ent and isinstance(ent["governance"], dict)
    assert "symbol" in ent and isinstance(ent["symbol"], str)
    assert "traits" in ent and isinstance(ent["traits"], list)
    assert "topology_actual" in ent and isinstance(ent["topology_actual"], dict)
    assert "preview" in ent and isinstance(ent["preview"], str)
    assert "outgoing_contracts" in ent and ent["outgoing_contracts"] == []
    assert None not in (ent.get("narrative") or {}).values()


def test_empty_blueprint_root_has_required_keys():
    root = empty_blueprint_root()
    assert "version" in root
    assert "entities" in root and root["entities"] == []
    assert "root_id" in root
    assert "contracts" not in root
    assert None not in [root.get("version"), root.get("entities")]


def test_validate_entity_valid():
    ent = dict(empty_entity("comp-1"))
    ent["id"] = "comp-1"
    valid, errors = validate_entity(ent)
    assert valid is True
    assert errors == []


def test_validate_entity_missing_id():
    ent = dict(empty_entity(""))
    ent.pop("id", None)
    valid, errors = validate_entity(ent)
    assert valid is False
    assert any("id" in e for e in errors)


def test_validate_entity_null_children_invalid():
    ent = dict(empty_entity("x"))
    ent["children"] = None
    valid, errors = validate_entity(ent)
    assert valid is False
    assert any("children" in e or "null" in e for e in errors)


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


def test_normalize_for_schema_entity_defaults():
    data = {
        "version": "1.0",
        "entities": [{"id": "e1"}],
        "root_id": "",
    }
    out = normalize_for_schema(data)
    assert len(out["entities"]) == 1
    ent = out["entities"][0]
    assert isinstance(ent.get("narrative"), dict)
    assert isinstance(ent.get("blueprint"), dict)
    assert ent.get("children") == []
    assert ent.get("dependencies") == []
    assert isinstance(ent.get("outgoing_contracts"), list)


def test_validate_blueprint_data_valid():
    data = {
        "version": "1.0",
        "root_id": PROJECT_ROOT_ID,
        "entities": [
            dict(empty_entity(PROJECT_ROOT_ID)),
            {**dict(empty_entity("comp-a")), "outgoing_contracts": [{"to": "external-x", "type": "dependency", "file": "", "symbols": []}]},
        ],
    }
    data["entities"][0]["children"] = ["comp-a"]
    valid, errors = validate_blueprint_data(data)
    assert valid is True, errors
    assert errors == []


def test_validate_blueprint_data_referential_integrity():
    data = {
        "version": "1.0",
        "root_id": PROJECT_ROOT_ID,
        "entities": [
            {**dict(empty_entity(PROJECT_ROOT_ID)), "children": ["ghost"]},
            {**dict(empty_entity("comp-a")), "dependencies": ["missing-dep"]},
        ],
    }
    valid, errors = validate_blueprint_data(data)
    assert valid is False
    assert any("ghost" in e or "non-existent" in e for e in errors)
    assert any("missing-dep" in e or "non-existent" in e for e in errors)


def test_validate_blueprint_data_outgoing_contracts_referential_integrity():
    data = {
        "version": "1.0",
        "root_id": PROJECT_ROOT_ID,
        "entities": [
            dict(empty_entity(PROJECT_ROOT_ID)),
            {**dict(empty_entity("comp-a")), "outgoing_contracts": [{"to": "nonexistent-target", "type": "dependency", "file": "", "symbols": []}]},
        ],
    }
    valid, errors = validate_blueprint_data(data)
    assert valid is False
    assert any("nonexistent-target" in e and "outgoing_contracts" in e for e in errors)


def test_validate_blueprint_data_invalid_entity():
    data = {
        "version": "1.0",
        "root_id": "",
        "entities": [{"id": "e1", "children": "not-a-list", "dependencies": [], "narrative": {}, "blueprint": {}, "protocol": {}, "profile": {}, "governance": {}, "symbol": "", "traits": [], "topology_actual": {}, "preview": "", "outgoing_contracts": []}],
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
        "entities": [dict(empty_entity(PROJECT_ROOT_ID))],
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
