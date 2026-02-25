"""Tests for merge_design_and_extraction matching heuristics."""
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
        "entities": [_extracted("comp-calc.operations-add", "add", "add")],
        "root_id": PROJECT_ROOT_ID,
    }
    out = merge_design_and_extraction(design, extracted)
    add_ent = next(e for e in out["entities"] if e["id"] == "add")
    assert add_ent["symbol"] == "add" or add_ent.get("preview")


def test_auth_no_false_match_authentication():
    design = {"entities": [_design_ent("auth"), _design_ent(PROJECT_ROOT_ID)], "root_id": PROJECT_ROOT_ID}
    extracted = {
        "entities": [_extracted("comp-src.authentication.service-AuthenticationService", "AuthenticationService", "service.main")],
        "root_id": PROJECT_ROOT_ID,
    }
    out = merge_design_and_extraction(design, extracted)
    auth_ent = next(e for e in out["entities"] if e["id"] == "auth")
    assert not (auth_ent.get("symbol") or auth_ent.get("preview"))
