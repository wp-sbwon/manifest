"""Integration: mock project data (tmp/calculator/.manifest) works with view pipeline."""
import json
from pathlib import Path

import pytest

from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_entity
from manifest.view.entity_model import get_entities_for_view


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TMP_MANIFEST = REPO_ROOT / "tmp" / "calculator" / ".manifest"


def _calculator_design_with_mul():
    """Design: root, cli, arithmetic_engine, add, sub, mul, output (mul is planned in design)."""
    entities = []
    for eid, children in [
        (PROJECT_ROOT_ID, ["cli", "arithmetic_engine", "output"]),
        ("cli", []),
        ("arithmetic_engine", ["add", "sub", "mul"]),
        ("add", []),
        ("sub", []),
        ("mul", []),
        ("output", []),
    ]:
        e = dict(empty_entity(eid))
        e["id"] = eid
        e["children"] = children
        e["narrative"] = {"role": eid, "mission": ""}
        entities.append(e)
    return {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": entities}


def _calculator_code_without_mul():
    """Code blueprint: same as design but no mul (code-only)."""
    entities = []
    for eid, children in [
        (PROJECT_ROOT_ID, ["cli", "arithmetic_engine", "output"]),
        ("cli", []),
        ("arithmetic_engine", ["add", "sub"]),
        ("add", []),
        ("sub", []),
        ("output", []),
    ]:
        e = dict(empty_entity(eid))
        e["id"] = eid
        e["children"] = children
        e["symbol"] = "engine.calculator" if eid in ("add", "sub") else ("output.formatter" if eid == "output" else "cli.parser")
        e["narrative"] = {"role": eid, "mission": ""}
        entities.append(e)
    return {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": entities}


@pytest.mark.integration
def test_calculator_shape_code_without_mul_gives_planned_for_mul(tmp_path: Path) -> None:
    """When blueprint_code omits mul (code-only), view gives mul=planned and implemented entities non-planned."""
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    design = _calculator_design_with_mul()
    code = _calculator_code_without_mul()
    (manifest_dir / "blueprint_design.json").write_text(json.dumps(design, indent=2), encoding="utf-8")
    (manifest_dir / "blueprint_code.json").write_text(json.dumps(code, indent=2), encoding="utf-8")
    data = get_entities_for_view(manifest_dir)
    comp_status = data.get("comp_status") or {}
    assert comp_status.get("mul") == "planned"
    assert comp_status.get("add") in ("healthy", "deviation", "partial")
    assert comp_status.get("sub") in ("healthy", "deviation", "partial")
    assert comp_status.get("output") in ("healthy", "deviation", "partial")
    code_ids = [e["id"] for e in code.get("entities", [])]
    assert "mul" not in code_ids


@pytest.mark.integration
def test_tmp_manifest_produces_valid_view_data() -> None:
    """With tmp/calculator/.manifest populated by create_mock_project_data, get_entities_for_view returns valid comp_status and view_schema."""
    if not TMP_MANIFEST.exists() or not (TMP_MANIFEST / "blueprint_design.json").exists():
        pytest.skip("Run: PYTHONPATH=src python scripts/create_mock_project_data.py")
    data = get_entities_for_view(TMP_MANIFEST)
    assert data.get("comp_status") is not None
    assert data.get("view_schema") is not None
    comp_status = data["comp_status"]
    assert PROJECT_ROOT_ID in comp_status
    view_schema = data["view_schema"]
    assert view_schema.get("root_id") == PROJECT_ROOT_ID
    entities = view_schema.get("entities") or []
    assert len(entities) >= 2
    for ve in entities:
        assert ve.get("validation") is not None
        assert "status" in (ve.get("validation") or {})
