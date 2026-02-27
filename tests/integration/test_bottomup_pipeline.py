"""Integration: full bottom-up pipeline (extract + merge) on calculator fixture produces valid blueprint_code."""
from pathlib import Path

import pytest

from manifest.audit.code.code_blueprint_builder import build_code_blueprint
from manifest.audit.code.code_extractor import CodeExtractor
from manifest.audit.entity_schema import PROJECT_ROOT_ID
from manifest.audit.entity_validation import normalize_for_schema, validate_blueprint_data

REPO = Path(__file__).resolve().parent.parent.parent
CALCULATOR = REPO / "tests" / "fixtures" / "calculator"


def _minimal_calculator_design():
    from manifest.audit.entity_schema import empty_entity
    root = dict(empty_entity(PROJECT_ROOT_ID))
    root["children"] = ["cli", "arithmetic_engine", "output"]
    cli = dict(empty_entity("cli"))
    cli["children"] = []
    cli["symbol"] = "cli.parser"
    engine = dict(empty_entity("arithmetic_engine"))
    engine["children"] = ["add", "sub", "mul"]
    engine["symbol"] = "engine.calculator"
    add_ = dict(empty_entity("add"))
    add_["children"] = []
    add_["symbol"] = "engine.calculator"
    sub_ = dict(empty_entity("sub"))
    sub_["children"] = []
    sub_["symbol"] = "engine.calculator"
    mul_ = dict(empty_entity("mul"))
    mul_["children"] = []
    mul_["symbol"] = "engine.calculator"
    out = dict(empty_entity("output"))
    out["children"] = []
    out["symbol"] = "output.formatter"
    entities = [root, cli, engine, add_, sub_, mul_, out]
    return normalize_for_schema({"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": entities})


@pytest.mark.integration
def test_bottomup_pipeline_calculator_produces_valid_blueprint(tmp_path):
    """Extract from calculator fixture + merge with design produces valid blueprint_code; design ids preserved or orphans added."""
    if not CALCULATOR.is_dir():
        pytest.skip("Fixture missing: tests/fixtures/calculator")
    project_root = tmp_path / "proj"
    import shutil
    shutil.copytree(CALCULATOR, project_root)
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    design = _minimal_calculator_design()
    extractor = CodeExtractor(project_root)
    extracted = extractor.extract_project_structure(project_root)
    code = build_code_blueprint(project_root, manifest_dir, design, extracted)
    valid, errors = validate_blueprint_data(code)
    assert valid, f"blueprint_code must pass validation: {errors}"
    assert code["root_id"] == PROJECT_ROOT_ID
    design_ids = {e["id"] for e in design["entities"] if e.get("id")}
    result_ids = {e["id"] for e in code["entities"] if e.get("id")}
    assert design_ids <= result_ids, "All design entity ids must appear in result (plus possible orphans)"
    by_id = {e["id"]: e for e in code["entities"]}
    assert PROJECT_ROOT_ID in by_id
    assert "cli" in by_id or "arithmetic_engine" in by_id or "output" in by_id
