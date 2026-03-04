"""Integration: CodeExtractor on real Python project — verify entities, contracts, fields."""
import pytest

from manifest.audit.code.code_extractor import CodeExtractor
from manifest.audit.entity_schema import PROJECT_ROOT_ID

from tests.mock_project_builder import create_mock_project


@pytest.mark.integration
def test_extract_returns_valid_blueprint_shape(tmp_path):
    """Extraction produces a blueprint with version, root_id, entities list."""
    project_root, _ = create_mock_project(tmp_path)

    extractor = CodeExtractor(project_root)
    result = extractor.extract_project_structure(project_root)

    assert result["version"] == "1.0"
    assert result["root_id"] == PROJECT_ROOT_ID
    assert isinstance(result["entities"], list)
    assert len(result["entities"]) >= 2  # at least root + some components


@pytest.mark.integration
def test_extract_finds_all_source_components(tmp_path):
    """Extraction discovers Parser class, add/sub/main/format_result functions."""
    project_root, _ = create_mock_project(tmp_path)

    extractor = CodeExtractor(project_root)
    result = extractor.extract_project_structure(project_root)

    entity_names = {e.get("id", "").split("-")[-1] for e in result["entities"] if e.get("id") != PROJECT_ROOT_ID}

    assert "Parser" in entity_names, f"Missing Parser class in {entity_names}"
    assert "add" in entity_names, f"Missing add function in {entity_names}"
    assert "sub" in entity_names, f"Missing sub function in {entity_names}"
    assert "main" in entity_names, f"Missing main function in {entity_names}"
    assert "format_result" in entity_names, f"Missing format_result function in {entity_names}"


@pytest.mark.integration
def test_extract_parser_class_has_methods(tmp_path):
    """Parser class entity includes parse method."""
    project_root, _ = create_mock_project(tmp_path)

    extractor = CodeExtractor(project_root)
    result = extractor.extract_project_structure(project_root)

    parser_ent = next(
        (e for e in result["entities"] if "Parser" in (e.get("id") or "")),
        None,
    )
    assert parser_ent is not None

    # Component was a class with methods — check via the extractor's internal state
    parser_comp = extractor.components.get(parser_ent["id"])
    assert parser_comp is not None
    assert parser_comp.type == "class"
    assert "parse" in parser_comp.methods
    assert "__init__" in parser_comp.methods


@pytest.mark.integration
def test_extract_entities_have_symbol_pointing_to_file(tmp_path):
    """Each entity's symbol contains the source file path."""
    project_root, _ = create_mock_project(tmp_path)

    extractor = CodeExtractor(project_root)
    result = extractor.extract_project_structure(project_root)

    for ent in result["entities"]:
        if ent.get("id") == PROJECT_ROOT_ID:
            continue
        symbol = ent.get("symbol") or ""
        assert symbol.endswith(".py"), f"Entity {ent['id']} symbol '{symbol}' should end with .py"


@pytest.mark.integration
def test_extract_entities_have_protocol(tmp_path):
    """Entities with typed args have protocol.input populated from AST."""
    project_root, _ = create_mock_project(tmp_path)

    extractor = CodeExtractor(project_root)
    result = extractor.extract_project_structure(project_root)

    # add(a: float, b: float) -> float should have protocol
    add_ent = next(
        (e for e in result["entities"] if e.get("id", "").endswith("-add")),
        None,
    )
    assert add_ent is not None
    proto = add_ent.get("protocol") or {}
    inputs = proto.get("input") or []
    assert len(inputs) >= 2, f"add() should have 2 input params, got {inputs}"
    param_names = {p.get("name") for p in inputs}
    assert "a" in param_names
    assert "b" in param_names

    outputs = proto.get("output") or []
    assert len(outputs) >= 1, f"add() should have return type, got {outputs}"


@pytest.mark.integration
def test_extract_detects_complexity(tmp_path):
    """Pure functions like add() get O(1) complexity trait."""
    project_root, _ = create_mock_project(tmp_path)

    extractor = CodeExtractor(project_root)
    result = extractor.extract_project_structure(project_root)

    add_ent = next(
        (e for e in result["entities"] if e.get("id", "").endswith("-add")),
        None,
    )
    assert add_ent is not None
    traits = add_ent.get("traits") or []
    complexity_traits = [t for t in traits if t.startswith("complexity:")]
    assert len(complexity_traits) >= 1, f"Expected complexity trait, got {traits}"
    assert "complexity:O(1)" in complexity_traits


@pytest.mark.integration
def test_extract_detects_side_effects(tmp_path):
    """main() calls print() — should detect stdout side effect."""
    project_root, _ = create_mock_project(tmp_path)

    extractor = CodeExtractor(project_root)
    result = extractor.extract_project_structure(project_root)

    main_ent = next(
        (e for e in result["entities"] if e.get("id", "").endswith("-main")),
        None,
    )
    assert main_ent is not None
    traits = main_ent.get("traits") or []
    assert "stdout" in traits, f"main() calls print() but traits={traits}"


@pytest.mark.integration
def test_extract_root_has_all_children(tmp_path):
    """Root entity's children list contains all extracted component IDs."""
    project_root, _ = create_mock_project(tmp_path)

    extractor = CodeExtractor(project_root)
    result = extractor.extract_project_structure(project_root)

    root = next(e for e in result["entities"] if e.get("id") == PROJECT_ROOT_ID)
    non_root_ids = {e["id"] for e in result["entities"] if e.get("id") != PROJECT_ROOT_ID}
    assert set(root.get("children") or []) == non_root_ids


@pytest.mark.integration
def test_extract_produces_contracts(tmp_path):
    """Extraction finds import-based contracts (main imports from cli, engine)."""
    project_root, _ = create_mock_project(tmp_path)

    extractor = CodeExtractor(project_root)
    extractor.extract_project_structure(project_root)

    assert len(extractor.contracts) > 0, "Should find at least one contract/relationship"
    contract_types = {c.type for c in extractor.contracts}
    assert "dependency" in contract_types or "call" in contract_types
