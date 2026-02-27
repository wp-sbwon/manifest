"""Integration: layer-writer agent output must match golden (when MANIFEST_TEST_AGENTS=1)."""
import json
import os
import shutil
from pathlib import Path

import pytest

from manifest.audit.entity_schema import PROJECT_ROOT_ID
from manifest.io.blueprint_io import save_blueprint
from manifest.io.prd_io import save_prd
from tests.blueprint_helpers import minimal_blueprint

REPO = Path(__file__).resolve().parent.parent.parent
GOLDEN = REPO / "tests" / "golden" / "layer_writer_golden.json"
OPENCODE_JSON = REPO / "opencode.json"


@pytest.mark.integration
def test_layer_writer_output_matches_golden(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """With MANIFEST_TEST_AGENTS=1, layer-writer output matches golden (empty parent -> empty children)."""
    if os.environ.get("MANIFEST_TEST_AGENTS") != "1":
        pytest.skip("Set MANIFEST_TEST_AGENTS=1 to run layer-writer golden test.")
    if not shutil.which("opencode"):
        pytest.skip("opencode not on PATH")
    if not OPENCODE_JSON.exists():
        pytest.skip("opencode.json not at repo root")
    if not GOLDEN.exists():
        pytest.skip("Golden file missing: tests/golden/layer_writer_golden.json")

    shutil.copy2(OPENCODE_JSON, tmp_path / "opencode.json")
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    design = minimal_blueprint([])
    save_blueprint(manifest_dir, design)
    save_prd(manifest_dir, {"title": "T", "mission": "Minimal.", "sections": []})
    context = {
        "layer_index": 0,
        "max_depth": 2,
        "parent_entity": design["entities"][0],
        "prd_excerpt": {"title": "T", "mission": "Minimal.", "sections": []},
        "blueprint_excerpt": {
            "path_from_root": [PROJECT_ROOT_ID],
            "parent_id": PROJECT_ROOT_ID,
            "sibling_ids": [],
            "root_id": PROJECT_ROOT_ID,
        },
    }
    timeout = min(int(os.environ.get("MANIFEST_LAYER_TIMEOUT", "90")), 90)
    monkeypatch.setenv("MANIFEST_LAYER_TIMEOUT", str(timeout))

    from manifest.opencode.layer_writer import write_blueprint_layer
    result = write_blueprint_layer(context, tmp_path, manifest_dir)

    with open(GOLDEN, "r", encoding="utf-8") as f:
        golden = json.load(f)
    assert "children" in result, "layer-writer must return children"
    assert result["children"] == golden["children"], (
        "Layer-writer must reproduce golden. "
        "Expected %s; got %s. Update tests/golden/layer_writer_golden.json if the agent contract changed."
    ) % (golden["children"], result["children"])
