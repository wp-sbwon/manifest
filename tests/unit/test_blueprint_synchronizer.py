"""Unit tests for BlueprintSynchronizer."""
import tempfile
from pathlib import Path

import pytest

from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_entity, empty_intent, empty_reality
from manifest.audit.blueprint.blueprint_synchronizer import BlueprintSynchronizer, ConflictReport
from manifest.audit.blueprint.status_enums import ConflictWorkflowStatus


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


@pytest.mark.unit
def test_conflict_report_from_dict_roundtrip() -> None:
    """ConflictReport.from_dict reconstructs from to_dict output."""
    design = {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [_entity(PROJECT_ROOT_ID)]}
    code = {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [_entity(PROJECT_ROOT_ID)]}
    report = ConflictReport(
        task_id="t1",
        conflicts=[],
        top_down_blueprint=design,
        bottom_up_blueprint=code,
        timestamp="2025-01-01T00:00:00",
        status=ConflictWorkflowStatus.PLANNER_REVIEW.value,
    )
    d = report.to_dict()
    restored = ConflictReport.from_dict(d)
    assert restored.task_id == report.task_id
    assert restored.status == report.status


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
    sync = BlueprintSynchronizer()
    info = sync.calculate_implementation_status(design, code)
    statuses = info["node_statuses"]
    assert statuses.get("a") == "healthy"
    assert statuses.get("b") == "planned"


@pytest.mark.unit
def test_calculate_implementation_status_parent_completion_deviation_counts_full() -> None:
    root = _entity(PROJECT_ROOT_ID, children=["mod"])
    mod_d = _entity("mod", children=["a", "b"], role="Mod", symbol="mod/")
    a_d = _entity("a", role="A", symbol="a.py")
    b_d = _entity("b", role="B", symbol="b.py")
    design = {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [root, mod_d, a_d, b_d]}
    mod_c = _entity("mod", children=["a", "b"], role="Mod", symbol="mod/")
    a_c = _entity("a", role="A_Different", symbol="a.py")
    b_c = _entity("b", role="B", symbol="b.py")
    code = {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [_entity(PROJECT_ROOT_ID, children=["mod"]), mod_c, a_c, b_c]}
    sync = BlueprintSynchronizer()
    info = sync.calculate_implementation_status(design, code)
    assert info["node_statuses"].get("a") == "deviation"
    assert info["node_statuses"].get("b") == "healthy"
    completions = info["parent_completions"]
    assert completions.get("mod") == 100.0


@pytest.mark.unit
def test_update_conflict_status_rejects_invalid_transition() -> None:
    """update_conflict_status rejects illegal transitions (e.g. resolved -> pending)."""
    design = {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [_entity(PROJECT_ROOT_ID)]}
    code = {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [_entity(PROJECT_ROOT_ID)]}
    report = ConflictReport(
        task_id="t1",
        conflicts=[],
        top_down_blueprint=design,
        bottom_up_blueprint=code,
        timestamp="2025-01-01T00:00:00",
        status=ConflictWorkflowStatus.RESOLVED.value,
    )
    with tempfile.TemporaryDirectory() as tmp:
        sync = BlueprintSynchronizer(manifest_dir=Path(tmp))
        ok = sync.update_conflict_status(report, ConflictWorkflowStatus.PENDING.value)
        assert ok is False
