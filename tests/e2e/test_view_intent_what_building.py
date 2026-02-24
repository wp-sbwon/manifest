"""E2E intent: user can see what they are building (structure and plan vs actual)."""
from pathlib import Path

import pytest

from manifest.view.entity_model import get_entities_for_view
from manifest.audit.entity_schema import PROJECT_ROOT_ID


@pytest.mark.e2e
def test_view_data_exposes_structure_and_plan_actual(tmp_path: Path) -> None:
    """View data contains entities with intent/reality so user can see what is being built and plan vs code."""
    from manifest.audit.entity_schema import empty_entity, empty_intent, empty_reality
    from manifest.audit.entity_validation import normalize_for_schema
    import json
    from manifest.audit.blueprint.manifest_filenames import BLUEPRINT_DESIGN_FILE, BLUEPRINT_CODE_FILE

    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    root = dict(empty_entity(PROJECT_ROOT_ID))
    root["children"] = ["m1"]
    root["intent"] = dict(empty_intent())
    root["intent"]["narrative"] = {"role": "System", "mission": "Build X."}
    root["reality"] = dict(empty_reality())
    m1 = dict(empty_entity("m1"))
    m1["children"] = []
    m1["intent"] = dict(empty_intent())
    m1["intent"]["narrative"] = {"role": "Module1", "mission": "Do Y."}
    m1["reality"] = dict(empty_reality())
    m1["reality"]["symbol"] = "m1.py"
    design = normalize_for_schema({"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [root, m1]})
    code = normalize_for_schema({"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [root, m1]})
    with open(manifest_dir / BLUEPRINT_DESIGN_FILE, "w", encoding="utf-8") as f:
        json.dump(design, f, indent=2)
    with open(manifest_dir / BLUEPRINT_CODE_FILE, "w", encoding="utf-8") as f:
        json.dump(code, f, indent=2)

    data = get_entities_for_view(manifest_dir)
    view_schema = data.get("view_schema") or {}
    entities = view_schema.get("entities") or []

    assert len(entities) >= 2, "User must see at least root and one component (what is being built)"
    by_id = {e["id"]: e for e in entities}
    assert PROJECT_ROOT_ID in by_id
    assert "m1" in by_id
    for e in entities:
        assert "intent" in e, "Each entity must expose intent (plan)"
        assert "reality" in e, "Each entity must expose reality (actual)"
        intent = e.get("intent") or {}
        assert "narrative" in intent
        narrative = intent.get("narrative") or {}
        role_val = narrative.get("role")
        if isinstance(role_val, dict):
            assert "plan" in role_val and "actual" in role_val, "View must expose plan/actual for comparison"
        else:
            assert role_val is not None or e.get("id") == PROJECT_ROOT_ID
