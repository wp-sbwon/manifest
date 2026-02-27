"""Tests for build_code_blueprint: agent is invoked with design + extraction; failures propagate."""
from pathlib import Path
from unittest.mock import patch

import pytest

from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_entity


def _minimal_design():
    root = dict(empty_entity(PROJECT_ROOT_ID))
    root["children"] = []
    return {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [root]}


def _minimal_extraction():
    root = dict(empty_entity(PROJECT_ROOT_ID))
    root["children"] = []
    return {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [root]}


@pytest.mark.unit
def test_build_code_blueprint_calls_enricher_with_design_and_extraction(tmp_path: Path) -> None:
    """build_code_blueprint invokes the agent with design, extraction, project_root, manifest_dir."""
    from manifest.audit.code.code_blueprint_builder import build_code_blueprint

    design = _minimal_design()
    extracted = _minimal_extraction()
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    root_ent = dict(empty_entity(PROJECT_ROOT_ID))
    root_ent["id"] = PROJECT_ROOT_ID
    root_ent["children"] = []
    result_blueprint = {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [root_ent]}

    with patch("manifest.opencode.code_blueprint_enricher.enrich_code_blueprint", return_value=result_blueprint) as mock_enrich:
        out = build_code_blueprint(tmp_path, manifest_dir, design, extracted)
    mock_enrich.assert_called_once()
    args = mock_enrich.call_args[0]
    assert args[0] == design
    assert args[1] == extracted
    assert args[2] == tmp_path
    assert args[3] == manifest_dir
    assert out["root_id"] == PROJECT_ROOT_ID
    assert "entities" in out


@pytest.mark.unit
def test_build_code_blueprint_propagates_enricher_failure(tmp_path: Path) -> None:
    """When the agent (enricher) raises, build_code_blueprint propagates; no fallback."""
    from manifest.audit.code.code_blueprint_builder import build_code_blueprint

    design = _minimal_design()
    extracted = _minimal_extraction()
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir(parents=True, exist_ok=True)

    with patch("manifest.opencode.code_blueprint_enricher.enrich_code_blueprint", side_effect=RuntimeError("opencode not on PATH")):
        with pytest.raises(RuntimeError, match="opencode not on PATH"):
            build_code_blueprint(tmp_path, manifest_dir, design, extracted)
