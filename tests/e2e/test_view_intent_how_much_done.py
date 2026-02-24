"""E2E intent: user can see how much is done (status and progress)."""
from pathlib import Path

import pytest

from manifest.view.entity_model import get_entities_for_view
from manifest.audit.entity_schema import PROJECT_ROOT_ID


@pytest.mark.e2e
def test_view_data_exposes_status_per_entity(tmp_path: Path) -> None:
    """View data exposes comp_status so user can see how much is done per entity."""
    from manifest.audit.entity_schema import empty_entity, empty_intent, empty_reality
    from manifest.audit.entity_validation import normalize_for_schema
    import json
    from manifest.audit.blueprint.manifest_filenames import BLUEPRINT_DESIGN_FILE, BLUEPRINT_CODE_FILE

    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    root = dict(empty_entity(PROJECT_ROOT_ID))
    root["children"] = ["a", "b"]
    root["intent"] = dict(empty_intent())
    root["reality"] = dict(empty_reality())
    a = dict(empty_entity("a"))
    a["children"] = []
    a["intent"] = dict(empty_intent())
    a["reality"] = dict(empty_reality())
    a["reality"]["symbol"] = "a.py"
    b = dict(empty_entity("b"))
    b["children"] = []
    b["intent"] = dict(empty_intent())
    b["reality"] = dict(empty_reality())
    design = normalize_for_schema({"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [root, a, b]})
    code = normalize_for_schema({"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [root, a]})
    code["entities"][0]["children"] = ["a"]
    with open(manifest_dir / BLUEPRINT_DESIGN_FILE, "w", encoding="utf-8") as f:
        json.dump(design, f, indent=2)
    with open(manifest_dir / BLUEPRINT_CODE_FILE, "w", encoding="utf-8") as f:
        json.dump(code, f, indent=2)

    data = get_entities_for_view(manifest_dir)
    comp_status = data.get("comp_status") or {}

    assert PROJECT_ROOT_ID in comp_status, "User must see root status (how much is done overall)"
    assert "a" in comp_status
    assert "b" in comp_status
    allowed = {"planned", "healthy", "partial", "deviation"}
    for eid, status in comp_status.items():
        assert status in allowed, f"Status for {eid} must be one of {allowed}"
    assert comp_status.get("a") in ("healthy", "partial", "deviation"), "Implemented entity must not be planned only"
    assert comp_status.get("b") == "planned", "Design-only entity must show as planned"
