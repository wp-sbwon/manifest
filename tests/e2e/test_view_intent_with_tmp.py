"""E2E intent: with tmp mock project, view shows what is built and how much is done consistently."""
from pathlib import Path

import pytest

from manifest.audit.blueprint.view_schema import entity_has_any_deviates
from manifest.view.entity_model import get_entities_for_view
from manifest.audit.entity_schema import PROJECT_ROOT_ID


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TMP_MANIFEST = REPO_ROOT / "tmp" / "calculator" / ".manifest"


@pytest.mark.e2e
def test_tmp_view_shows_what_is_built() -> None:
    """With tmp/calculator/.manifest, view exposes multiple entities so user sees what is being built."""
    if not TMP_MANIFEST.exists() or not (TMP_MANIFEST / "blueprint_design.json").exists():
        pytest.skip("Run: PYTHONPATH=src python scripts/create_mock_project_data.py tmp/calculator/.manifest")
    data = get_entities_for_view(TMP_MANIFEST)
    view_schema = data.get("view_schema") or {}
    entities = view_schema.get("entities") or []
    assert len(entities) > 1, "User must see more than root (what is being built)"
    ids = {e.get("id") for e in entities if e.get("id")}
    assert PROJECT_ROOT_ID in ids
    assert "cli" in ids or "arithmetic_engine" in ids or "add" in ids, "User must see concrete components"


@pytest.mark.e2e
def test_tmp_view_shows_how_much_done_no_contradiction() -> None:
    """With tmp/calculator/.manifest, status and deviations are consistent (no healthy + field-level deviations)."""
    if not TMP_MANIFEST.exists() or not (TMP_MANIFEST / "blueprint_design.json").exists():
        pytest.skip("Run: PYTHONPATH=src python scripts/create_mock_project_data.py tmp/calculator/.manifest")
    data = get_entities_for_view(TMP_MANIFEST)
    view_schema = data.get("view_schema") or {}
    for ve in view_schema.get("entities") or []:
        status = (ve.get("validation") or {}).get("status", "planned")
        has_deviates = entity_has_any_deviates(ve)
        assert not (status == "healthy" and has_deviates), (
            "User must not see entity as healthy while it has deviation alerts (how much is done must be consistent)."
        )


@pytest.mark.e2e
def test_tmp_root_status_reflects_implementation() -> None:
    """With tmp/calculator/.manifest, root status is not 'planned' when code exists (user sees progress)."""
    if not TMP_MANIFEST.exists() or not (TMP_MANIFEST / "blueprint_design.json").exists():
        pytest.skip("Run: PYTHONPATH=src python scripts/create_mock_project_data.py tmp/calculator/.manifest")
    data = get_entities_for_view(TMP_MANIFEST)
    comp_status = data.get("comp_status") or {}
    root_status = comp_status.get(PROJECT_ROOT_ID)
    assert root_status != "planned", (
        "When code blueprint has entities, root must not be 'planned' so user sees that something is done."
    )
