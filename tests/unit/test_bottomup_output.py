"""Unit: bottom-up pipeline output (blueprint_code) matches golden.

Runs extract then build_code_blueprint (agent reads outline + code + design).
Asserts structure and code-derived fields match the golden.
Requires MANIFEST_TEST_AGENTS=1 (calls opencode); skipped in default CI."""
import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict

import pytest

from manifest.audit.code.code_blueprint_builder import build_code_blueprint
from manifest.audit.code.code_extractor import CodeExtractor
from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_entity
from manifest.audit.entity_validation import normalize_for_schema, validate_blueprint_data

# Keys we compare: structure + code-derived from agent output. Omit narrative/preview/governance text.
_STRUCTURE_KEYS = ("id", "children", "symbol", "dependencies", "outgoing_contracts", "protocol", "profile", "traits")


def _bottom_up_design_with_depth() -> dict:
    """Design for fixture project: root → runner → [greeter, formatter]; runner has outgoing_contracts."""
    root = dict(empty_entity(PROJECT_ROOT_ID))
    root["children"] = ["runner"]
    runner = dict(empty_entity("runner"))
    runner["children"] = ["greeter", "formatter"]
    runner["outgoing_contracts"] = [
        {"to": "greeter", "type": "call", "file": "", "symbols": ["greet"]},
        {"to": "formatter", "type": "call", "file": "", "symbols": ["format"]},
    ]
    greeter = dict(empty_entity("greeter"))
    greeter["children"] = []
    formatter = dict(empty_entity("formatter"))
    formatter["children"] = []
    entities = [root, runner, greeter, formatter]
    return normalize_for_schema({"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": entities})


# Fixture project lives under tests/fixtures; we copy to a path without "tests" so CodeExtractor finds .py files.
BOTTOM_UP_FIXTURE_SOURCE = Path(__file__).resolve().parent.parent / "fixtures" / "bottom_up_project"
BOTTOM_UP_EXPECTED_JSON = Path(__file__).resolve().parent.parent / "fixtures" / "bottom_up_expected.json"
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OPENCODE_JSON = REPO_ROOT / "opencode.json"


def _normalize_paths_in_value(obj: Any, project_root: Path, placeholder: str = "<PROJECT_ROOT>") -> Any:
    """Replace project_root (as string) with placeholder for comparable golden match."""
    if isinstance(obj, dict):
        return {k: _normalize_paths_in_value(v, project_root, placeholder) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize_paths_in_value(i, project_root, placeholder) for i in obj]
    if isinstance(obj, str):
        root_str = str(project_root.resolve())
        if root_str in obj:
            return obj.replace(root_str, placeholder)
        return obj
    return obj


def _blueprint_structure_subset(blueprint: Dict[str, Any]) -> Dict[str, Any]:
    """Extract structure and code-derived fields for comparison; omit model-generated text."""
    out: Dict[str, Any] = {
        "version": blueprint.get("version"),
        "root_id": blueprint.get("root_id"),
        "entities": [],
    }
    for e in blueprint.get("entities") or []:
        ent = {k: e[k] for k in _STRUCTURE_KEYS if k in e}
        out["entities"].append(ent)
    return out


@pytest.mark.unit
def test_bottomup_final_output_matches_golden(tmp_path: Path) -> None:
    """Full bottom-up pipeline (extract → agent) produces blueprint_code that matches golden."""
    if os.environ.get("MANIFEST_TEST_AGENTS") != "1":
        pytest.skip("Set MANIFEST_TEST_AGENTS=1 to run bottom-up agent tests.")
    if not BOTTOM_UP_FIXTURE_SOURCE.exists():
        pytest.skip("Fixture missing: tests/fixtures/bottom_up_project")
    if not BOTTOM_UP_EXPECTED_JSON.exists():
        pytest.skip("Golden file missing: tests/fixtures/bottom_up_expected.json")

    if not OPENCODE_JSON.exists():
        pytest.fail("opencode.json required at repo root for bottom-up pipeline test (copy to project so opencode finds agents).")
    project_root = tmp_path / "proj"
    manifest_dir = tmp_path / ".manifest"
    shutil.copytree(BOTTOM_UP_FIXTURE_SOURCE, project_root)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(OPENCODE_JSON, project_root / "opencode.json")

    design = _bottom_up_design_with_depth()
    extractor = CodeExtractor(project_root)
    extracted = extractor.extract_project_structure(project_root)
    blueprint_code = build_code_blueprint(project_root, manifest_dir, design, extracted)

    result_normalized = _normalize_paths_in_value(blueprint_code, project_root)
    result_subset = _blueprint_structure_subset(result_normalized)
    with open(BOTTOM_UP_EXPECTED_JSON, "r", encoding="utf-8") as f:
        golden = json.load(f)
    expected_subset = _blueprint_structure_subset(golden)

    assert result_subset == expected_subset, (
        "Bottom-up pipeline structure and code-derived fields must match golden. "
        "Golden: tests/fixtures/bottom_up_expected.json. Fix the process or update the golden."
    )


@pytest.mark.unit
def test_bottomup_final_output_valid_schema(tmp_path: Path) -> None:
    """Full bottom-up pipeline produces valid blueprint_code (schema, referential integrity)."""
    if os.environ.get("MANIFEST_TEST_AGENTS") != "1":
        pytest.skip("Set MANIFEST_TEST_AGENTS=1 to run bottom-up agent tests.")
    if not BOTTOM_UP_FIXTURE_SOURCE.exists():
        pytest.skip("Fixture missing: tests/fixtures/bottom_up_project")

    if not OPENCODE_JSON.exists():
        pytest.fail("opencode.json required at repo root for bottom-up pipeline test.")
    project_root = tmp_path / "proj"
    manifest_dir = tmp_path / ".manifest"
    shutil.copytree(BOTTOM_UP_FIXTURE_SOURCE, project_root)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(OPENCODE_JSON, project_root / "opencode.json")

    design = _bottom_up_design_with_depth()
    extractor = CodeExtractor(project_root)
    extracted = extractor.extract_project_structure(project_root)
    blueprint_code = build_code_blueprint(project_root, manifest_dir, design, extracted)

    valid, errors = validate_blueprint_data(blueprint_code)
    assert valid, f"blueprint_code must pass validation: {errors}"
    assert blueprint_code.get("root_id") == design.get("root_id")
    design_ids = {e.get("id") for e in (design.get("entities") or []) if e.get("id")}
    result_ids = {e.get("id") for e in (blueprint_code.get("entities") or []) if e.get("id")}
    assert design_ids == result_ids, "Pipeline must preserve design entity ids"
