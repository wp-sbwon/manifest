"""Tests for design-to-extraction matching (merge_design_and_extraction)."""
from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_entity
from manifest.audit.code.code_blueprint_builder import merge_design_and_extraction


def _design_ent(eid: str, role: str = "", children=None):
    ent = dict(empty_entity(eid))
    ent["id"] = eid
    ent["children"] = children or []
    ent["narrative"] = {"role": role, "mission": ""}
    return ent


def _extracted(eid: str, name: str = "", symbol: str = ""):
    ent = dict(empty_entity(eid))
    ent["id"] = eid
    ent["narrative"] = {"role": name, "mission": ""}
    ent["symbol"] = symbol
    ent["dependencies"] = []
    return ent


def test_exact_id_match():
    design = {"entities": [_design_ent("cli"), _design_ent(PROJECT_ROOT_ID)], "root_id": PROJECT_ROOT_ID}
    extracted = {"entities": [_extracted("cli", "CLI", "cli.parser")], "root_id": PROJECT_ROOT_ID}
    out = merge_design_and_extraction(design, extracted)
    cli_ent = next(e for e in out["entities"] if e["id"] == "cli")
    assert cli_ent["symbol"] == "cli.parser"


def test_module_path_suffix_match():
    design = {"entities": [_design_ent("cli"), _design_ent(PROJECT_ROOT_ID)], "root_id": PROJECT_ROOT_ID}
    extracted = {
        "entities": [_extracted("comp-src.manifest.cli.parser-ParseArgs", "ParseArgs", "cli.parser")],
        "root_id": PROJECT_ROOT_ID,
    }
    out = merge_design_and_extraction(design, extracted)
    cli_ent = next(e for e in out["entities"] if e["id"] == "cli")
    assert "cli" in (cli_ent.get("symbol") or "") or "parser" in (cli_ent.get("symbol") or "")


def test_normalized_partial_match():
    design = {"entities": [_design_ent("arithmetic_engine"), _design_ent(PROJECT_ROOT_ID)], "root_id": PROJECT_ROOT_ID}
    extracted = {
        "entities": [_extracted("comp-engine.ArithmeticEngine", "ArithmeticEngine", "engine.calculator")],
        "root_id": PROJECT_ROOT_ID,
    }
    out = merge_design_and_extraction(design, extracted)
    eng_ent = next(e for e in out["entities"] if e["id"] == "arithmetic_engine")
    assert eng_ent["symbol"] or eng_ent.get("preview") or "ArithmeticEngine" in str(eng_ent)


def test_token_overlap():
    design = {"entities": [_design_ent("add"), _design_ent(PROJECT_ROOT_ID)], "root_id": PROJECT_ROOT_ID}
    extracted = {
        "entities": [_extracted("comp-engine.calculator-add", "add", "add")],
        "root_id": PROJECT_ROOT_ID,
    }
    out = merge_design_and_extraction(design, extracted)
    add_ent = next(e for e in out["entities"] if e["id"] == "add")
    assert add_ent["symbol"] == "add" or add_ent.get("preview")


def test_design_only_entity_omitted_from_code_blueprint():
    """Code blueprint is code-first: design entities with no extraction match are not included."""
    design = {"entities": [_design_ent("auth"), _design_ent(PROJECT_ROOT_ID)], "root_id": PROJECT_ROOT_ID}
    extracted = {
        "entities": [_extracted("comp-src.authentication.service-AuthenticationService", "AuthenticationService", "service.main")],
        "root_id": PROJECT_ROOT_ID,
    }
    out = merge_design_and_extraction(design, extracted)
    code_ids = {e["id"] for e in out["entities"]}
    assert "auth" not in code_ids
    assert PROJECT_ROOT_ID in code_ids


def test_planned_entity_mul_omitted_when_not_in_extraction():
    """Design has add, sub, mul; extraction has add and sub only. Code blueprint must not contain mul."""
    design = {
        "entities": [
            _design_ent(PROJECT_ROOT_ID, "", ["add", "sub", "mul"]),
            _design_ent("add"),
            _design_ent("sub"),
            _design_ent("mul"),
        ],
        "root_id": PROJECT_ROOT_ID,
    }
    extracted = {
        "entities": [
            _extracted("comp-engine.calculator-add", "add", "engine.calculator"),
            _extracted("comp-engine.calculator-sub", "sub", "engine.calculator"),
        ],
        "root_id": PROJECT_ROOT_ID,
    }
    out = merge_design_and_extraction(design, extracted)
    code_ids = {e["id"] for e in out["entities"]}
    assert "mul" not in code_ids
    assert "add" in code_ids
    assert "sub" in code_ids
