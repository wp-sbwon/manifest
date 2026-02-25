"""Tests that view status and deviation alerts stay consistent (no healthy + alerts)."""
from pathlib import Path

import pytest

from manifest.audit.entity_schema import PROJECT_ROOT_ID
from manifest.audit.blueprint.view_schema import entity_has_any_deviates
from manifest.view.entity_model import get_entities_for_view


def test_root_status_not_planned_and_no_healthy_with_deviations(tmp_path: Path) -> None:
    """Root must not be 'planned'; no entity may be healthy and have field-level deviations."""
    # Use repo tmp/calculator/.manifest if present (after create_mock_project_data.py); else skip.
    repo = Path(__file__).resolve().parent.parent
    manifest_dir = repo / "tmp" / "calculator" / ".manifest"
    if not (manifest_dir / "blueprint_design.json").exists():
        pytest.skip("Run: PYTHONPATH=src python scripts/create_mock_project_data.py tmp/calculator/.manifest")

    data = get_entities_for_view(manifest_dir)
    comp_status = data.get("comp_status") or {}
    view_schema = data.get("view_schema") or {}

    assert comp_status.get(PROJECT_ROOT_ID) != "planned", (
        "System Core (root) status must not be 'planned'."
    )

    for ve in view_schema.get("entities") or []:
        eid = ve.get("id") or ""
        status = (ve.get("validation") or {}).get("status") or "planned"
        has_deviates = entity_has_any_deviates(ve)
        assert not (status == "healthy" and has_deviates), (
            f"Entity {eid} is healthy but has field-level deviations (red alerts)."
        )


def test_system_core_and_cli_no_spurious_alerts(tmp_path: Path) -> None:
    """When System Core or CLI are healthy, they must have no deviation alerts."""
    repo = Path(__file__).resolve().parent.parent
    manifest_dir = repo / "tmp" / "calculator" / ".manifest"
    if not (manifest_dir / "blueprint_design.json").exists():
        pytest.skip("Run: PYTHONPATH=src python scripts/create_mock_project_data.py tmp/calculator/.manifest")

    data = get_entities_for_view(manifest_dir)
    view_schema = data.get("view_schema") or {}
    entities = {e.get("id"): e for e in view_schema.get("entities") or [] if e.get("id")}

    for eid in (PROJECT_ROOT_ID, "cli"):
        ve = entities.get(eid)
        if not ve:
            continue
        status = (ve.get("validation") or {}).get("status") or "planned"
        if status != "healthy":
            continue
        assert not entity_has_any_deviates(ve), (
            f"{eid} is marked healthy but has deviation alerts (e.g. profile, platform)."
        )
