"""Tests for design-to-extraction merge (exact ID only)."""
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
    """When extracted id equals design id, merge takes mechanical from extraction."""
    design = {"entities": [_design_ent("cli"), _design_ent(PROJECT_ROOT_ID)], "root_id": PROJECT_ROOT_ID}
    extracted = {"entities": [_extracted("cli", "CLI", "cli.parser")], "root_id": PROJECT_ROOT_ID}
    out = merge_design_and_extraction(design, extracted)
    cli_ent = next(e for e in out["entities"] if e["id"] == "cli")
    assert cli_ent["symbol"] == "cli.parser"


def test_no_match_design_entity_remains_planned():
    """When extracted id differs from design id, design entity stays with no extraction data."""
    design = {"entities": [_design_ent("cli"), _design_ent(PROJECT_ROOT_ID)], "root_id": PROJECT_ROOT_ID}
    extracted = {
        "entities": [_extracted("comp-src.manifest.cli.parser-ParseArgs", "ParseArgs", "cli.parser")],
        "root_id": PROJECT_ROOT_ID,
    }
    out = merge_design_and_extraction(design, extracted)
    code_ids = {e["id"] for e in out["entities"]}
    assert "cli" in code_ids
    assert "comp-src.manifest.cli.parser-ParseArgs" in code_ids
    cli_ent = next(e for e in out["entities"] if e["id"] == "cli")
    assert (cli_ent.get("symbol") or "") == ""


def test_extracted_without_design_id_appears_as_orphan():
    """Extracted entities whose id is not in design are included as orphans."""
    design = {"entities": [_design_ent("add"), _design_ent(PROJECT_ROOT_ID)], "root_id": PROJECT_ROOT_ID}
    extracted = {
        "entities": [_extracted("comp-engine.calculator-add", "add", "engine.calculator")],
        "root_id": PROJECT_ROOT_ID,
    }
    out = merge_design_and_extraction(design, extracted)
    code_ids = {e["id"] for e in out["entities"]}
    assert "add" in code_ids
    assert "comp-engine.calculator-add" in code_ids
    orphan = next(e for e in out["entities"] if e["id"] == "comp-engine.calculator-add")
    assert orphan["symbol"] == "engine.calculator"


def test_design_only_entity_included_as_planned():
    """Design entities with no extraction match are included (planned)."""
    design = {"entities": [_design_ent("auth"), _design_ent(PROJECT_ROOT_ID)], "root_id": PROJECT_ROOT_ID}
    extracted = {
        "entities": [_extracted("comp-src.authentication.service-AuthenticationService", "AuthenticationService", "service.main")],
        "root_id": PROJECT_ROOT_ID,
    }
    out = merge_design_and_extraction(design, extracted)
    code_ids = {e["id"] for e in out["entities"]}
    assert "auth" in code_ids
    assert "comp-src.authentication.service-AuthenticationService" in code_ids
    assert PROJECT_ROOT_ID in code_ids


def test_planned_entity_included_when_not_in_extraction():
    """Design entities (e.g. mul) with no extraction match are included as planned."""
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
    assert "mul" in code_ids
    assert "add" in code_ids
    assert "sub" in code_ids
    assert "comp-engine.calculator-add" in code_ids
    assert "comp-engine.calculator-sub" in code_ids
