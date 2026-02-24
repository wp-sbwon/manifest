"""Unit tests for BlueprintSynchronizer."""
import tempfile
from pathlib import Path

import pytest

from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_entity, empty_intent, empty_reality
from manifest.audit.blueprint.blueprint_synchronizer import BlueprintSynchronizer


def _entity(eid: str, children: list = None, role: str = "", symbol: str = "") -> dict:
    e = dict(empty_entity(eid))
    e["children"] = children or []
    e["intent"] = dict(empty_intent())
    e["intent"]["narrative"] = {"role": role, "mission": ""}
    e["reality"] = dict(empty_reality())
    e["reality"]["symbol"] = symbol
    return e


@pytest.mark.unit
def test_compare_all_docs_accepts_preloaded_blueprints() -> None:
    """compare_all_docs uses pre-loaded blueprints when provided to avoid duplicate disk reads."""
    design = {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [_entity(PROJECT_ROOT_ID)]}
    code = {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [_entity(PROJECT_ROOT_ID)]}
    sync = BlueprintSynchronizer()
    result = sync.compare_all_docs(design_blueprint=design, code_blueprint=code)
    assert "blueprint" in result
    assert "implementation_progress" in result["blueprint"]
    assert "deviation_conflicts" in result["blueprint"]
