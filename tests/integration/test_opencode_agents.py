"""Integration: run OpenCode agents (layer-writer, enricher) with default model and assert output shape.

Run when MANIFEST_TEST_AGENTS=1. Requires opencode on PATH and opencode.json at repo root; fails if missing.
"""
import os
import shutil
from pathlib import Path

import pytest

from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_entity
from manifest.audit.entity_validation import normalize_for_schema, validate_blueprint_data
from manifest.io.blueprint_io import save_blueprint
from manifest.io.prd_io import save_prd
from tests.blueprint_helpers import minimal_blueprint

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OPENCODE_JSON = REPO_ROOT / "opencode.json"


def _require_agents_env() -> None:
    """Skip unless MANIFEST_TEST_AGENTS=1; fail if opencode or opencode.json missing."""
    if os.environ.get("MANIFEST_TEST_AGENTS") != "1":
        pytest.skip("Set MANIFEST_TEST_AGENTS=1 to run OpenCode agent tests.")
    if not shutil.which("opencode"):
        pytest.fail("opencode required on PATH when MANIFEST_TEST_AGENTS=1.")
    if not OPENCODE_JSON.exists():
        pytest.fail("opencode.json required at repo root when MANIFEST_TEST_AGENTS=1.")


@pytest.mark.integration
def test_layer_writer_produces_valid_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """With MANIFEST_TEST_AGENTS=1, layer-writer returns a dict with 'children' list; each child has id and valid shape."""
    _require_agents_env()
    shutil.copy2(OPENCODE_JSON, tmp_path / "opencode.json")
    from manifest.opencode.layer_writer import write_blueprint_layer

    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    design = minimal_blueprint([])
    save_blueprint(manifest_dir, design)
    save_prd(manifest_dir, {"title": "T", "mission": "Minimal app.", "sections": []})
    context = {
        "layer_index": 0,
        "max_depth": 2,
        "parent_entity": design["entities"][0],
        "prd_excerpt": {"title": "T", "mission": "Minimal app.", "sections": []},
        "blueprint_excerpt": {
            "path_from_root": [PROJECT_ROOT_ID],
            "parent_id": PROJECT_ROOT_ID,
            "sibling_ids": [],
            "root_id": PROJECT_ROOT_ID,
        },
    }
    timeout = min(int(os.environ.get("MANIFEST_LAYER_TIMEOUT", "90")), 90)
    monkeypatch.setenv("MANIFEST_LAYER_TIMEOUT", str(timeout))
    result = write_blueprint_layer(context, tmp_path, manifest_dir)
    assert "children" in result
    assert isinstance(result["children"], list)
    for c in result["children"]:
        assert isinstance(c, dict), "each child must be a dict"
        assert "id" in c, "each child must have id"
        assert isinstance(c.get("id"), str), "id must be string"


@pytest.mark.integration
def test_enricher_produces_valid_blueprint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """With MANIFEST_TEST_AGENTS=1, enricher returns a valid blueprint with same root_id and entity ids as design."""
    _require_agents_env()
    shutil.copy2(OPENCODE_JSON, tmp_path / "opencode.json")
    from manifest.opencode.code_blueprint_enricher import enrich_code_blueprint

    design = minimal_blueprint(["a"])
    design["entities"][1]["symbol"] = "a.py"
    code_draft = normalize_for_schema(
        {
            "version": "1.0",
            "root_id": PROJECT_ROOT_ID,
            "entities": [
                {**empty_entity(PROJECT_ROOT_ID), "children": ["a"], "symbol": "main"},
                {**empty_entity("a"), "children": [], "symbol": "a.py"},
            ],
        }
    )
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    timeout = min(int(os.environ.get("MANIFEST_ENRICH_TIMEOUT", "120")), 90)
    monkeypatch.setenv("MANIFEST_ENRICH_TIMEOUT", str(timeout))
    result = enrich_code_blueprint(design, code_draft, tmp_path, manifest_dir)
    assert result.get("root_id") == design.get("root_id")
    assert "entities" in result
    design_ids = {e.get("id") for e in (design.get("entities") or []) if e.get("id")}
    result_ids = {e.get("id") for e in (result.get("entities") or []) if e.get("id")}
    assert design_ids == result_ids, "enricher must preserve design entity ids"
    valid, errors = validate_blueprint_data(result)
    assert valid, f"enricher output must pass blueprint validation: {errors}"
