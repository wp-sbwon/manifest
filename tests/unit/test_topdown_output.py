"""Unit: top-down process output matches schema and is fully populated."""
from pathlib import Path

import pytest

from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_entity
from manifest.audit.entity_validation import normalize_for_schema, validate_blueprint_data
from manifest.io.blueprint_io import load_blueprint, save_blueprint
from manifest.io.prd_io import save_prd
from manifest.opencode.architect import create_blueprint_from_prd
from manifest.opencode.layer_writer import merge_children_into_blueprint
from tests.blueprint_helpers import minimal_blueprint


def _entity_required_keys() -> set:
    return {"id", "children", "dependencies", "narrative", "blueprint", "protocol", "profile", "governance", "symbol", "traits", "topology_actual", "preview", "outgoing_contracts"}


def _assert_entity_fully_populated(ent: dict, path: str = "entity") -> None:
    """Assert entity has all required keys and no nulls at top level."""
    for key in _entity_required_keys():
        assert key in ent, f"{path}: missing key '{key}'"
        assert ent[key] is not None, f"{path}: '{key}' must not be null"


def _assert_blueprint_schema_and_fully_populated(blueprint: dict) -> None:
    valid, errors = validate_blueprint_data(blueprint)
    assert valid, f"Blueprint must pass validation: {errors}"
    for i, ent in enumerate(blueprint.get("entities") or []):
        _assert_entity_fully_populated(ent, f"entities[{i}]")


@pytest.mark.unit
def test_create_blueprint_from_prd_output_matches_schema_and_fully_populated(
    tmp_path: Path,
) -> None:
    """create_blueprint_from_prd writes blueprint_design.json that validates and is fully populated."""
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    save_prd(manifest_dir, {"title": "T", "mission": "Build a calculator.", "sections": []})
    out = create_blueprint_from_prd(manifest_dir, project_root=tmp_path)
    assert out.get("ok") is True, out.get("error", "create_blueprint_from_prd failed")
    blueprint = load_blueprint(manifest_dir)
    assert blueprint is not None
    assert "version" in blueprint and "root_id" in blueprint and "entities" in blueprint
    _assert_blueprint_schema_and_fully_populated(blueprint)
    root = next((e for e in (blueprint.get("entities") or []) if (e.get("id") or "") == PROJECT_ROOT_ID), None)
    assert root is not None
    assert (root.get("narrative") or {}).get("mission") == "Build a calculator."


@pytest.mark.unit
def test_merge_children_into_blueprint_produces_valid_fully_populated(manifest_dir: Path) -> None:
    """Merging layer-writer children into blueprint yields valid, fully populated blueprint."""
    design = minimal_blueprint(["mod_a"])
    save_blueprint(manifest_dir, design)
    child_a = {**empty_entity("mod_a"), "narrative": {"role": "module", "mission": "API"}}
    child_b = {**empty_entity("mod_b"), "narrative": {"role": "module", "mission": "CLI"}}
    children = [
        normalize_for_schema(child_a),
        normalize_for_schema(child_b),
    ]
    ok = merge_children_into_blueprint(manifest_dir, PROJECT_ROOT_ID, children)
    assert ok
    blueprint = load_blueprint(manifest_dir)
    assert blueprint is not None
    _assert_blueprint_schema_and_fully_populated(blueprint)
    ids = {e.get("id") for e in (blueprint.get("entities") or []) if e.get("id")}
    assert PROJECT_ROOT_ID in ids and "mod_a" in ids and "mod_b" in ids
    root = next((e for e in (blueprint.get("entities") or []) if (e.get("id") or "") == PROJECT_ROOT_ID), None)
    assert set(root.get("children") or []) >= {"mod_a", "mod_b"}
