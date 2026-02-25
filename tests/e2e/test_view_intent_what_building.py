"""E2E: user can see what they are building (structure and plan vs actual)."""
import json
from pathlib import Path

import pytest

from manifest.audit.blueprint.manifest_filenames import BLUEPRINT_DESIGN_FILE, BLUEPRINT_CODE_FILE
from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_entity
from manifest.audit.entity_validation import normalize_for_schema
from manifest.view.entity_model import get_entities_for_view


@pytest.mark.e2e
def test_view_data_exposes_structure_and_plan_actual(tmp_path: Path) -> None:
    """View data contains entities with same keys as blueprints plus validation (plan/actual from comparison)."""
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    root = dict(empty_entity(PROJECT_ROOT_ID))
    root["children"] = ["m1"]
    root["narrative"] = {"role": "System", "mission": "Build X."}
    m1 = dict(empty_entity("m1"))
    m1["children"] = []
    m1["narrative"] = {"role": "Module1", "mission": "Do Y."}
    m1["symbol"] = "m1.py"
    design = normalize_for_schema({"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [root, m1]})
    code = normalize_for_schema({"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [root, m1]})
    with open(manifest_dir / BLUEPRINT_DESIGN_FILE, "w", encoding="utf-8") as f:
        json.dump(design, f, indent=2)
    with open(manifest_dir / BLUEPRINT_CODE_FILE, "w", encoding="utf-8") as f:
        json.dump(code, f, indent=2)

    data = get_entities_for_view(manifest_dir)
    view_schema = data.get("view_schema") or {}
    entities = view_schema.get("entities") or []

    assert len(entities) >= 2
    by_id = {e["id"]: e for e in entities}
    assert PROJECT_ROOT_ID in by_id
    assert "m1" in by_id
    for e in entities:
        assert "narrative" in e
        assert "validation" in e
        narrative = e.get("narrative") or {}
        role_val = narrative.get("role")
        if isinstance(role_val, dict):
            assert "plan" in role_val and "actual" in role_val
        else:
            assert role_val is not None or e.get("id") == PROJECT_ROOT_ID
