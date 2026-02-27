"""Golden test: view status (planned / healthy / deviation / orphan) from design vs code."""
import json
from pathlib import Path

import pytest

from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_entity
from manifest.view.entity_model import get_entities_for_view


def _entity(eid: str, children=None, symbol: str = "", protocol_input=None):
    e = dict(empty_entity(eid))
    e["id"] = eid
    e["children"] = children or []
    e["symbol"] = symbol
    if protocol_input is not None:
        e["protocol"] = {"input": protocol_input, "output": []}
    return e


@pytest.mark.unit
def test_view_status_planned_healthy_deviation_orphan_golden(tmp_path):
    """Given design (root, a, b, c) and code (root, a with diff protocol, b, orphan): status golden."""
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    root_d = _entity(PROJECT_ROOT_ID, ["a", "b", "c"])
    a_d = _entity("a", symbol="a.py", protocol_input=[{"name": "x", "type": "str"}])
    b_d = _entity("b", symbol="b.py")
    c_d = _entity("c", symbol="c.py")
    design = {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [root_d, a_d, b_d, c_d]}

    root_c = _entity(PROJECT_ROOT_ID, ["a", "b", "orphan"])
    a_c = _entity("a", symbol="a.py", protocol_input=[{"name": "y", "type": "str"}])
    b_c = _entity("b", symbol="b.py")
    orphan_c = _entity("comp-orphan", symbol="orphan.py")
    code = {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [root_c, a_c, b_c, orphan_c]}

    (manifest_dir / "blueprint_design.json").write_text(json.dumps(design, indent=2), encoding="utf-8")
    (manifest_dir / "blueprint_code.json").write_text(json.dumps(code, indent=2), encoding="utf-8")

    data = get_entities_for_view(manifest_dir)
    comp_status = data.get("comp_status") or {}
    assert comp_status.get("a") == "deviation", "a: protocol differs (plan x vs actual y)"
    assert comp_status.get("b") == "healthy", "b: matches"
    assert comp_status.get("c") == "planned", "c: in design only"
    assert comp_status.get("comp-orphan") == "extra", "comp-orphan: in code only (orphan)"


@pytest.mark.unit
def test_view_status_all_healthy_golden(tmp_path):
    """Design and code identical: all entities healthy."""
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    root = _entity(PROJECT_ROOT_ID, ["m1"])
    m1 = _entity("m1", symbol="m1.py")
    blue = {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [root, m1]}
    (manifest_dir / "blueprint_design.json").write_text(json.dumps(blue, indent=2), encoding="utf-8")
    (manifest_dir / "blueprint_code.json").write_text(json.dumps(blue, indent=2), encoding="utf-8")
    data = get_entities_for_view(manifest_dir)
    assert (data.get("comp_status") or {}).get("m1") == "healthy"
