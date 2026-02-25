"""Integration: design + code blueprints -> get_entities_for_view -> view schema and status."""
import json

import pytest

from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_entity
from manifest.audit.blueprint.manifest_filenames import BLUEPRINT_DESIGN_FILE, BLUEPRINT_CODE_FILE, BLUEPRINT_VIEW_FILE
from manifest.view.entity_model import get_entities_for_view

from tests.blueprint_helpers import minimal_blueprint


@pytest.mark.integration
def test_get_entities_for_view_produces_comp_status_and_view_schema(manifest_dir) -> None:
    """Pipeline: write design + code blueprints, call get_entities_for_view; comp_status and view_schema populated."""
    design = minimal_blueprint(["a"])
    code = minimal_blueprint(["a"])
    (design["entities"][0])["symbol"] = "main.py"
    code["entities"][1]["symbol"] = "a.py"
    with open(manifest_dir / BLUEPRINT_DESIGN_FILE, "w", encoding="utf-8") as f:
        json.dump(design, f, indent=2)
    with open(manifest_dir / BLUEPRINT_CODE_FILE, "w", encoding="utf-8") as f:
        json.dump(code, f, indent=2)
    data = get_entities_for_view(manifest_dir)
    assert "comp_status" in data
    assert "view_schema" in data
    comp_status = data["comp_status"] or {}
    assert PROJECT_ROOT_ID in comp_status
    assert "a" in comp_status
    view_schema = data["view_schema"] or {}
    assert view_schema.get("root_id") == PROJECT_ROOT_ID
    assert len(view_schema.get("entities") or []) >= 2


@pytest.mark.integration
def test_get_entities_for_view_writes_blueprint_view_json(manifest_dir) -> None:
    """get_entities_for_view writes blueprint_view.json to manifest dir."""
    design = minimal_blueprint([])
    code = minimal_blueprint([])
    with open(manifest_dir / BLUEPRINT_DESIGN_FILE, "w", encoding="utf-8") as f:
        json.dump(design, f, indent=2)
    with open(manifest_dir / BLUEPRINT_CODE_FILE, "w", encoding="utf-8") as f:
        json.dump(code, f, indent=2)
    get_entities_for_view(manifest_dir)
    view_file = manifest_dir / BLUEPRINT_VIEW_FILE
    assert view_file.exists()
    with open(view_file, "r", encoding="utf-8") as f:
        view_data = json.load(f)
    assert "entities" in view_data
    assert view_data.get("root_id") == PROJECT_ROOT_ID
