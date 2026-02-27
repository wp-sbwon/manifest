"""Unit tests for blueprint_status.calculate_implementation_status."""
import pytest

from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_entity
from manifest.audit.blueprint.blueprint_status import calculate_implementation_status


def _entity(eid: str, children: list = None, role: str = "", symbol: str = "", protocol_input: list = None) -> dict:
    e = dict(empty_entity(eid))
    e["children"] = children or []
    e["narrative"] = {"role": role, "mission": ""}
    e["symbol"] = symbol
    if protocol_input is not None:
        e["protocol"] = {"input": protocol_input, "output": (e.get("protocol") or {}).get("output", [])}
    return e


@pytest.mark.unit
def test_calculate_implementation_status_planned_healthy_deviation_extra() -> None:
    """calculate_implementation_status returns planned/healthy/deviation/extra per entity."""
    root = _entity(PROJECT_ROOT_ID, children=["a", "b"])
    a_d = _entity("a", role="A", symbol="a.py")
    b_d = _entity("b", role="B", symbol="b.py")
    design = {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [root, a_d, b_d]}
    a_c = _entity("a", role="A", symbol="a.py")
    design_only = _entity(PROJECT_ROOT_ID)
    code = {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [design_only, a_c]}
    info = calculate_implementation_status(design, code)
    statuses = info["node_statuses"]
    assert statuses.get("a") == "healthy"
    assert statuses.get("b") == "planned"


@pytest.mark.unit
def test_calculate_implementation_status_parent_completion_deviation_counts_full() -> None:
    root = _entity(PROJECT_ROOT_ID, children=["mod"])
    mod_d = _entity("mod", children=["a", "b"], role="Mod", symbol="mod/")
    a_d = _entity("a", role="A", symbol="a.py", protocol_input=[{"name": "x", "type": "str"}])
    b_d = _entity("b", role="B", symbol="b.py")
    design = {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [root, mod_d, a_d, b_d]}
    mod_c = _entity("mod", children=["a", "b"], role="Mod", symbol="mod/")
    a_c = _entity("a", role="A", symbol="a.py", protocol_input=[{"name": "y", "type": "str"}])
    b_c = _entity("b", role="B", symbol="b.py")
    code = {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [_entity(PROJECT_ROOT_ID, children=["mod"]), mod_c, a_c, b_c]}
    info = calculate_implementation_status(design, code)
    assert info["node_statuses"].get("a") == "deviation"
    assert info["node_statuses"].get("b") == "healthy"
    completions = info["parent_completions"]
    # mod has two children: a (deviation), b (healthy). Deviations do not count as completion.
    assert completions.get("mod") == 50.0
