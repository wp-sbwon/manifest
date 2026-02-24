"""Unit tests for BlueprintComparator."""
import pytest

from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_entity, empty_intent, empty_reality
from manifest.audit.blueprint.blueprint_comparator import BlueprintComparator, BlueprintConflict, ConflictType


def _entity(eid: str, children: list = None, role: str = "", symbol: str = "") -> dict:
    e = dict(empty_entity(eid))
    e["children"] = children or []
    e["intent"] = dict(empty_intent())
    e["intent"]["narrative"] = {"role": role, "mission": ""}
    e["reality"] = dict(empty_reality())
    e["reality"]["symbol"] = symbol
    return e


@pytest.mark.unit
def test_compare_blueprints_empty_no_conflicts() -> None:
    """Two empty root-only blueprints yield no conflicts."""
    design = {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [_entity(PROJECT_ROOT_ID)]}
    code = {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [_entity(PROJECT_ROOT_ID)]}
    comparator = BlueprintComparator()
    conflicts = comparator.compare_blueprints(design, code)
    assert conflicts == []


@pytest.mark.unit
def test_compare_blueprints_design_only_entity_missing_in_code() -> None:
    """Design has entity not in code -> MISSING_ENTITY conflict."""
    root_d = _entity(PROJECT_ROOT_ID, children=["cli"])
    cli_d = _entity("cli", role="CLI", symbol="cli.py")
    design = {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [root_d, cli_d]}
    code = {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [_entity(PROJECT_ROOT_ID)]}
    comparator = BlueprintComparator()
    conflicts = comparator.compare_blueprints(design, code)
    missing = [c for c in conflicts if c.type == ConflictType.MISSING_ENTITY]
    assert len(missing) >= 1
    assert any("cli" in (c.message or "").lower() or c.node_id == "cli" for c in missing)


@pytest.mark.unit
def test_compare_blueprints_code_only_entity_extra_in_code() -> None:
    """Code has entity not in design -> EXTRA_ENTITY conflict."""
    root_d = _entity(PROJECT_ROOT_ID)
    design = {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [root_d]}
    root_c = _entity(PROJECT_ROOT_ID, children=["extra"])
    extra_c = _entity("extra", symbol="extra.py")
    code = {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [root_c, extra_c]}
    comparator = BlueprintComparator()
    conflicts = comparator.compare_blueprints(design, code)
    extra = [c for c in conflicts if c.type == ConflictType.EXTRA_ENTITY]
    assert len(extra) >= 1
    assert any(c.node_id == "extra" for c in extra)
