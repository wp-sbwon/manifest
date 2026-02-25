"""Unit tests for view_schema (build_view_schema, write/load)."""
from pathlib import Path

import pytest

from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_entity
from manifest.audit.blueprint.view_schema import (
    build_view_schema,
    write_view_schema,
    load_view_schema,
    to_single_value,
)


def _minimal_design() -> dict:
    root = dict(empty_entity(PROJECT_ROOT_ID))
    root["children"] = ["cli"]
    root["narrative"] = {"role": "App", "mission": "CLI app."}
    child = dict(empty_entity("cli"))
    child["children"] = []
    child["narrative"] = {"role": "CLI", "mission": "Parse args."}
    return {
        "version": "1.0",
        "root_id": PROJECT_ROOT_ID,
        "entities": [root, child],
    }


def _minimal_code() -> dict:
    root = dict(empty_entity(PROJECT_ROOT_ID))
    root["children"] = ["cli"]
    root["symbol"] = "main.py"
    child = dict(empty_entity("cli"))
    child["children"] = []
    child["symbol"] = "cli/parser.py"
    return {
        "version": "1.0",
        "root_id": PROJECT_ROOT_ID,
        "entities": [root, child],
    }


@pytest.mark.unit
def test_build_view_schema_same_ids_produces_plan_actual_pairs() -> None:
    """View schema entities have same keys as blueprints; values are plan/actual/deviates."""
    design = _minimal_design()
    code = _minimal_code()
    view = build_view_schema(design, code)
    assert view.get("root_id") == PROJECT_ROOT_ID
    entities = view.get("entities") or []
    assert len(entities) == 2
    for ve in entities:
        assert "id" in ve
        assert "narrative" in ve
        assert "symbol" in ve
        assert "validation" in ve
        assert "status" in (ve.get("validation") or {})
        role = (ve.get("narrative") or {}).get("role")
        if isinstance(role, dict):
            assert "plan" in role
            assert "actual" in role
            assert "deviates" in role


@pytest.mark.unit
def test_build_view_schema_status_in_validation() -> None:
    """Status is derived from view comparison (planned/healthy/deviation/extra)."""
    design = _minimal_design()
    code = _minimal_code()
    view = build_view_schema(design, code)
    by_id = {e["id"]: e for e in view.get("entities") or []}
    assert (by_id.get("cli") or {}).get("validation", {}).get("status") in ("healthy", "deviation", "planned", "extra")


@pytest.mark.unit
def test_write_and_load_view_schema_roundtrip(tmp_path: Path) -> None:
    """write_view_schema then load_view_schema returns same structure."""
    view = {
        "version": "1.0",
        "root_id": PROJECT_ROOT_ID,
        "entities": [
            {
                "id": PROJECT_ROOT_ID,
                "children": {"plan": [], "actual": [], "deviates": False},
                "narrative": {},
                "symbol": {"plan": "", "actual": "", "deviates": False},
                "validation": {"status": "healthy", "deviations": []},
            },
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


@pytest.mark.unit
def test_to_single_value() -> None:
    """to_single_value extracts plan or actual from view pairs."""
    assert to_single_value({"plan": "a", "actual": "b", "deviates": True}, use_actual=False) == "a"
    assert to_single_value({"plan": "a", "actual": "b", "deviates": True}, use_actual=True) == "b"
