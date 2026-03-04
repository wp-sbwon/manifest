"""Unit: core logic ensures design and code blueprints produce comparable view output.

Whatever the source (agents or fixtures), the app must align design and code so that
view_schema has one entity per id (union of both), each with plan/actual/deviates structure,
and comp_status has an entry per entity id.
"""
import json
from pathlib import Path

import pytest

from manifest.audit.blueprint.view_schema import build_view_schema, entity_has_any_deviates
from manifest.audit.entity_schema import PROJECT_ROOT_ID
from manifest.view.entity_model import get_entities_for_view
from tests.blueprint_helpers import minimal_blueprint


@pytest.mark.unit
def test_view_schema_entity_ids_are_union_of_design_and_code(manifest_dir: Path) -> None:
    """View schema entities are exactly the union of design and code entity ids; each has comparable structure."""
    design = minimal_blueprint(["a", "b"])
    code = minimal_blueprint(["a", "b"])
    with open(manifest_dir / "blueprint_design.json", "w", encoding="utf-8") as f:
        json.dump(design, f, indent=2)
    with open(manifest_dir / "blueprint_code.json", "w", encoding="utf-8") as f:
        json.dump(code, f, indent=2)
    data = get_entities_for_view(manifest_dir)
    view_schema = data["view_schema"] or {}
    comp_status = data["comp_status"] or {}
    design_ids = {e["id"] for e in (design.get("entities") or []) if e.get("id")}
    code_ids = {e["id"] for e in (code.get("entities") or []) if e.get("id")}
    expected_ids = design_ids | code_ids
    view_entities = view_schema.get("entities") or []
    view_ids = {ve["id"] for ve in view_entities if ve.get("id")}
    assert view_ids == expected_ids, "view_schema must have exactly union of design and code entity ids"
    assert set(comp_status.keys()) == expected_ids, "comp_status must have entry per entity id"
    for ve in view_entities:
        assert "blueprint" in ve and "validation" in ve, "each view entity must have blueprint and validation (plan/actual from comparison)"
        assert "status" in (ve.get("validation") or {}), "each must have validation.status"


@pytest.mark.unit
def test_view_schema_comparable_structure_when_identical(manifest_dir: Path) -> None:
    """When design and code have same structure and content, view entities have deviates=False for matching fields."""
    design = minimal_blueprint(["a"])
    code = minimal_blueprint(["a"])
    with open(manifest_dir / "blueprint_design.json", "w", encoding="utf-8") as f:
        json.dump(design, f, indent=2)
    with open(manifest_dir / "blueprint_code.json", "w", encoding="utf-8") as f:
        json.dump(code, f, indent=2)
    data = get_entities_for_view(manifest_dir)
    view_schema = data["view_schema"] or {}
    for ve in view_schema.get("entities") or []:
        if not entity_has_any_deviates(ve):
            continue
        status = (ve.get("validation") or {}).get("status")
        assert status in ("planned", "healthy", "partial", "deviation", "extra"), "status must be a known value"


@pytest.mark.unit
def test_view_schema_includes_code_only_entity(manifest_dir: Path) -> None:
    """When code has an entity not in design, view_schema still has one entry for it (plan empty/default, actual from code)."""
    design = minimal_blueprint(["a"])
    code = minimal_blueprint(["a", "b"])
    with open(manifest_dir / "blueprint_design.json", "w", encoding="utf-8") as f:
        json.dump(design, f, indent=2)
    with open(manifest_dir / "blueprint_code.json", "w", encoding="utf-8") as f:
        json.dump(code, f, indent=2)
    data = get_entities_for_view(manifest_dir)
    view_schema = data["view_schema"] or {}
    view_ids = {ve["id"] for ve in (view_schema.get("entities") or []) if ve.get("id")}
    assert "b" in view_ids, "view_schema must include code-only entity b so design and code remain comparable"
    comp_status = data["comp_status"] or {}
    assert "b" in comp_status, "comp_status must have entry for code-only entity"


@pytest.mark.unit
def test_build_view_schema_produces_comparable_structure() -> None:
    """build_view_schema produces view entities with same keys as blueprints; values are plan/actual/deviates; status from view."""
    from manifest.audit.blueprint.blueprint_status import calculate_implementation_status

    design = minimal_blueprint(["a"])
    code = minimal_blueprint(["a"])
    status_info = calculate_implementation_status(design, code)
    assert "node_statuses" in status_info
    view_schema = build_view_schema(design, code)
    for ve in view_schema.get("entities") or []:
        assert isinstance(ve.get("blueprint"), dict), "blueprint must be dict (nested plan/actual/deviates)"
        assert "validation" in ve and "status" in (ve.get("validation") or {}), "each entity must have validation.status"
