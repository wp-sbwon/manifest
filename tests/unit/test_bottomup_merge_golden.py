"""Golden test: merge_design_and_extraction produces deterministic output for known design + extraction."""
import pytest

from manifest.audit.code.code_blueprint_builder import (
    _extraction_with_design_ids,
    build_code_blueprint,
    merge_design_and_extraction,
)
from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_entity
from manifest.audit.entity_validation import normalize_for_schema


def _design_for_golden():
    """Minimal design: root, a (symbol a.module)."""
    root = dict(empty_entity(PROJECT_ROOT_ID))
    root["children"] = ["a"]
    root["narrative"] = {"role": "Root", "mission": "Golden test."}
    a = dict(empty_entity("a"))
    a["children"] = []
    a["narrative"] = {"role": "A", "mission": "Entity A."}
    a["symbol"] = "a.module"
    a["governance"] = {"rules": [], "assertions": ["A does something."]}
    return normalize_for_schema({"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [root, a]})


def _extraction_for_golden():
    """Extraction: root + entity with symbol a/module.py (normalizes to a.module)."""
    root = dict(empty_entity(PROJECT_ROOT_ID))
    root["children"] = ["comp-a-module"]
    comp = dict(empty_entity("comp-a-module"))
    comp["children"] = []
    comp["symbol"] = "a/module.py"
    comp["protocol"] = {"input": [{"name": "x", "type": "str"}], "output": []}
    comp["dependencies"] = []
    return {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [root, comp]}


def _expected_merge_golden():
    """Expected merge: design ids; a gets narrative from design, symbol from extraction."""
    root = dict(empty_entity(PROJECT_ROOT_ID))
    root["children"] = ["a"]
    root["narrative"] = {"role": "Root", "mission": "Golden test."}
    a = dict(empty_entity("a"))
    a["children"] = []
    a["narrative"] = {"role": "A", "mission": "Entity A."}
    a["symbol"] = "a/module.py"
    a["governance"] = {"rules": [], "assertions": ["A does something."]}
    a["protocol"] = {"input": [{"name": "x", "type": "str"}], "output": []}
    return normalize_for_schema({"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [root, a]})


@pytest.mark.unit
def test_merge_output_matches_golden():
    """Merge with symbol-matching design + extraction must match expected structure (golden)."""
    design = _design_for_golden()
    extracted = _extraction_for_golden()
    extracted_mapped = _extraction_with_design_ids(design, extracted)
    result = merge_design_and_extraction(design, extracted_mapped)
    expected = _expected_merge_golden()
    assert result["root_id"] == expected["root_id"]
    assert result["version"] == expected["version"]
    by_id_result = {e["id"]: e for e in result["entities"]}
    by_id_expected = {e["id"]: e for e in expected["entities"]}
    assert set(by_id_result) == set(by_id_expected)
    for eid in by_id_expected:
        r = by_id_result[eid]
        e = by_id_expected[eid]
        assert r["narrative"] == e["narrative"], f"narrative mismatch for {eid}"
        assert r["governance"] == e["governance"], f"governance mismatch for {eid}"
        assert r["symbol"] == e["symbol"], f"symbol mismatch for {eid}"
        assert r["protocol"] == e["protocol"], f"protocol mismatch for {eid}"


@pytest.mark.unit
def test_build_code_blueprint_matches_merge_golden(tmp_path):
    """build_code_blueprint (symbol mapping + merge) reproduces golden merge result."""
    design = _design_for_golden()
    extracted = _extraction_for_golden()
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    result = build_code_blueprint(tmp_path, manifest_dir, design, extracted)
    expected = _expected_merge_golden()
    by_id_result = {e["id"]: e for e in result["entities"]}
    by_id_expected = {e["id"]: e for e in expected["entities"]}
    assert set(by_id_result) >= set(by_id_expected)
    for eid in ("PROJECT_ROOT", "a"):
        assert eid in by_id_result
        assert by_id_result[eid]["narrative"] == by_id_expected[eid]["narrative"]
        assert by_id_result[eid]["symbol"] == by_id_expected[eid]["symbol"]
