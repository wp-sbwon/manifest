"""Integration: mock project data (tmp/calculator/.manifest) works with view pipeline."""
from pathlib import Path

import pytest

from manifest.view.entity_model import get_entities_for_view
from manifest.audit.entity_schema import PROJECT_ROOT_ID


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TMP_MANIFEST = REPO_ROOT / "tmp" / "calculator" / ".manifest"


@pytest.mark.integration
def test_tmp_manifest_produces_valid_view_data() -> None:
    """With tmp/calculator/.manifest populated by create_mock_project_data, get_entities_for_view returns valid comp_status and view_schema."""
    if not TMP_MANIFEST.exists() or not (TMP_MANIFEST / "blueprint_design.json").exists():
        pytest.skip("Run: PYTHONPATH=src python scripts/create_mock_project_data.py")
    data = get_entities_for_view(TMP_MANIFEST)
    assert data.get("comp_status") is not None
    assert data.get("view_schema") is not None
    comp_status = data["comp_status"]
    assert PROJECT_ROOT_ID in comp_status
    view_schema = data["view_schema"]
    assert view_schema.get("root_id") == PROJECT_ROOT_ID
    entities = view_schema.get("entities") or []
    assert len(entities) >= 2
    for ve in entities:
        assert ve.get("validation") is not None
        assert "status" in (ve.get("validation") or {})
