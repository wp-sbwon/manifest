"""Unit tests for view_schema (build_view_schema, write/load)."""
import json
from pathlib import Path

import pytest

from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_intent, empty_reality, empty_entity
from manifest.audit.blueprint.view_schema import build_view_schema, write_view_schema, load_view_schema


def _minimal_design() -> dict:
    root = dict(empty_entity(PROJECT_ROOT_ID))
    root["children"] = ["cli"]
    root["intent"] = dict(empty_intent())
    root["intent"]["narrative"] = {"role": "App", "mission": "CLI app."}
    root["reality"] = dict(empty_reality())
    child = dict(empty_entity("cli"))
    child["children"] = []
    child["intent"] = dict(empty_intent())
    child["intent"]["narrative"] = {"role": "CLI", "mission": "Parse args."}
    child["reality"] = dict(empty_reality())
    return {
        "version": "1.0",
        "root_id": PROJECT_ROOT_ID,
        "entities": [root, child],
    }


def _minimal_code() -> dict:
    root = dict(empty_entity(PROJECT_ROOT_ID))
    root["children"] = ["cli"]
    root["intent"] = dict(empty_intent())
    root["reality"] = dict(empty_reality())
    root["reality"]["symbol"] = "main.py"
    child = dict(empty_entity("cli"))
    child["children"] = []
    child["intent"] = dict(empty_intent())
    child["reality"] = dict(empty_reality())
    child["reality"]["symbol"] = "cli/parser.py"
    return {
        "version": "1.0",
        "root_id": PROJECT_ROOT_ID,
        "entities": [root, child],
    }


@pytest.mark.unit
def test_build_view_schema_same_ids_produces_plan_actual_pairs() -> None:
    """View schema entities have intent/reality as plan/actual + deviates."""
    design = _minimal_design()
    code = _minimal_code()
    comp_status = {PROJECT_ROOT_ID: "healthy", "cli": "healthy"}
    view = build_view_schema(design, code, comp_status, [])
    assert view.get("root_id") == PROJECT_ROOT_ID
    entities = view.get("entities") or []
    assert len(entities) == 2
    for ve in entities:
        assert "id" in ve
        assert "intent" in ve
        assert "reality" in ve
        assert "validation" in ve
        assert "status" in (ve.get("validation") or {})
        # Intent/reality values are { plan, actual, deviates }
        role = (ve.get("intent") or {}).get("narrative") or {}
        if isinstance(role.get("role"), dict):
            assert "plan" in role["role"]
            assert "actual" in role["role"]
            assert "deviates" in role["role"]


@pytest.mark.unit
def test_build_view_schema_status_in_validation() -> None:
    """comp_status flows into validation.status per entity."""
    design = _minimal_design()
    code = _minimal_code()
    comp_status = {PROJECT_ROOT_ID: "partial", "cli": "planned"}
    view = build_view_schema(design, code, comp_status, [])
    by_id = {e["id"]: e for e in view.get("entities") or []}
    assert (by_id.get(PROJECT_ROOT_ID) or {}).get("validation", {}).get("status") == "partial"
    assert (by_id.get("cli") or {}).get("validation", {}).get("status") == "planned"


@pytest.mark.unit
def test_write_and_load_view_schema_roundtrip(tmp_path: Path) -> None:
    """write_view_schema then load_view_schema returns same structure."""
    view = {
        "version": "1.0",
        "root_id": PROJECT_ROOT_ID,
        "entities": [
            {"id": PROJECT_ROOT_ID, "children": {"plan": [], "actual": [], "deviates": False}, "intent": {}, "reality": {}, "validation": {"status": "healthy", "deviations": []}},
        ],
    }
    ok = write_view_schema(tmp_path, view)
    assert ok
    loaded = load_view_schema(tmp_path)
    assert loaded.get("root_id") == view["root_id"]
    assert len(loaded.get("entities") or []) == 1
    assert (loaded["entities"][0].get("validation") or {}).get("status") == "healthy"


@pytest.mark.unit
def test_load_view_schema_missing_returns_empty_structure(tmp_path: Path) -> None:
    """load_view_schema when file missing returns empty root and entities."""
    data = load_view_schema(tmp_path)
    assert data.get("version") == "1.0"
    assert data.get("root_id") == PROJECT_ROOT_ID
    assert data.get("entities") == []
