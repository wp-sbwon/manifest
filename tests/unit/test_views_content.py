from pathlib import Path

import pytest

from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_entity, empty_intent, empty_reality
from manifest.view.views_content import blueprint_parent_names_by_component


def _entity(eid: str, children=None, role: str = ""):
    e = dict(empty_entity(eid))
    e["children"] = children or []
    e["intent"] = {"narrative": {"role": role, "mission": ""}}
    e["reality"] = dict(empty_reality())
    return e


@pytest.mark.unit
def test_blueprint_parent_names_by_component_nested_hierarchy() -> None:
    root = _entity(PROJECT_ROOT_ID, children=["mod"], role="Root")
    mod = _entity("mod", children=["a", "b"], role="Module")
    a = _entity("a", role="A")
    b = _entity("b", role="B")
    blueprint = {"entities": [root, mod, a, b]}
    result = blueprint_parent_names_by_component(blueprint)
    assert "mod" in result
    assert "Root" in result["mod"]
    assert "a" in result
    assert "Module" in result["a"]
    assert "b" in result
    assert "Module" in result["b"]
