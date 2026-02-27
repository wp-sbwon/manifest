"""Tests for build_code_blueprint: merge_design_and_extraction with design-id mapping."""
from pathlib import Path

import pytest

from manifest.audit.code.code_blueprint_builder import build_code_blueprint, merge_design_and_extraction
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
def test_build_code_blueprint_returns_merged_blueprint(tmp_path: Path) -> None:
    """build_code_blueprint returns merge of design and extraction (exact ID)."""
    design = _minimal_design()
    extracted = _minimal_extraction()
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    out = build_code_blueprint(tmp_path, manifest_dir, design, extracted)
    assert out["root_id"] == PROJECT_ROOT_ID
    assert "entities" in out
    assert len(out["entities"]) >= 1
    assert out["entities"][0]["id"] == PROJECT_ROOT_ID


@pytest.mark.unit
def test_merge_design_and_extraction_exact_id_only() -> None:
    """merge_design_and_extraction uses exact ID; narrative/governance from design, mechanical from extraction."""
    root = dict(empty_entity(PROJECT_ROOT_ID))
    root["children"] = ["cli"]
    root["narrative"] = {"role": "App", "mission": "CLI app."}
    design = {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [root]}
    cli_design = dict(empty_entity("cli"))
    cli_design["children"] = []
    cli_design["narrative"] = {"role": "CLI", "mission": "Parse args."}
    cli_design["symbol"] = "cli.parser"
    design["entities"].append(cli_design)

    root_ext = dict(empty_entity(PROJECT_ROOT_ID))
    root_ext["children"] = ["cli"]
    cli_ext = dict(empty_entity("cli"))
    cli_ext["children"] = []
    cli_ext["symbol"] = "cli/parser.py"
    cli_ext["protocol"] = {"input": [{"name": "argv", "type": "list"}], "output": []}
    extracted = {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [root_ext, cli_ext]}

    result = merge_design_and_extraction(design, extracted)
    assert result["root_id"] == PROJECT_ROOT_ID
    by_id = {e["id"]: e for e in result["entities"]}
    assert "cli" in by_id
    assert by_id["cli"]["narrative"] == {"role": "CLI", "mission": "Parse args."}
    assert by_id["cli"]["symbol"] == "cli/parser.py"
