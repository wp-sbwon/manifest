"""Integration: CodeWatcher and code_blueprint_builder — full extraction pipeline to blueprint_code.json."""
import json
import time

import pytest

from manifest.audit.code.code_blueprint_builder import build_code_blueprint
from manifest.audit.code.code_extractor import CodeExtractor
from manifest.audit.entity_schema import PROJECT_ROOT_ID
from manifest.audit.entity_validation import validate_blueprint_data
from manifest.audit.monitoring.code_watcher import CodeWatcher
from manifest.io.blueprint_io import load_blueprint

from tests.mock_project_builder import build_design_blueprint, create_mock_project


# --- code_blueprint_builder ---


@pytest.mark.integration
def test_build_code_blueprint_merges_design_and_extraction(tmp_path):
    """build_code_blueprint: design narrative preserved, extraction symbol/protocol overlaid."""
    project_root, manifest_dir = create_mock_project(tmp_path)

    design = build_design_blueprint()
    extractor = CodeExtractor(project_root)
    extracted = extractor.extract_project_structure(project_root)

    code_bp = build_code_blueprint(project_root, manifest_dir, design, extracted)

    assert code_bp["root_id"] == PROJECT_ROOT_ID
    entity_ids = {e["id"] for e in code_bp["entities"]}
    # Design entities should appear
    assert "cli" in entity_ids
    assert PROJECT_ROOT_ID in entity_ids

    # CLI entity should have design's narrative but extraction's symbol
    cli_ent = next(e for e in code_bp["entities"] if e["id"] == "cli")
    narrative = cli_ent.get("narrative") or {}
    assert narrative.get("mission"), "Design narrative should be preserved"
    symbol = cli_ent.get("symbol") or ""
    assert symbol, "Extraction symbol should be overlaid"


@pytest.mark.integration
def test_build_code_blueprint_passes_validation(tmp_path):
    """Merged blueprint passes schema validation."""
    project_root, manifest_dir = create_mock_project(tmp_path)

    design = build_design_blueprint()
    extractor = CodeExtractor(project_root)
    extracted = extractor.extract_project_structure(project_root)

    code_bp = build_code_blueprint(project_root, manifest_dir, design, extracted)

    valid, errors = validate_blueprint_data(code_bp)
    assert valid, f"Validation failed: {errors}"


@pytest.mark.integration
def test_build_code_blueprint_includes_orphan_entities(tmp_path):
    """Extracted entities not in design appear as orphans."""
    project_root, manifest_dir = create_mock_project(tmp_path)

    design = build_design_blueprint()
    extractor = CodeExtractor(project_root)
    extracted = extractor.extract_project_structure(project_root)

    code_bp = build_code_blueprint(project_root, manifest_dir, design, extracted)

    entity_ids = {e["id"] for e in code_bp["entities"]}
    design_ids = {e["id"] for e in design["entities"]}
    orphans = entity_ids - design_ids
    # main.py's main() function won't match any design entity by symbol → orphan
    assert len(orphans) >= 1, f"Expected at least 1 orphan entity, got {orphans}"


# --- CodeWatcher ---


@pytest.mark.integration
def test_code_watcher_force_extract_creates_blueprint_code(tmp_path):
    """force_extract() writes blueprint_code.json with valid content."""
    project_root, manifest_dir = create_mock_project(tmp_path)

    watcher = CodeWatcher(project_root=project_root, manifest_dir=manifest_dir)
    result = watcher.force_extract()

    assert result is True
    blueprint_code_path = manifest_dir / "blueprint_code.json"
    assert blueprint_code_path.exists(), "blueprint_code.json should be created"

    code_bp = json.loads(blueprint_code_path.read_text(encoding="utf-8"))
    assert code_bp["root_id"] == PROJECT_ROOT_ID
    assert len(code_bp["entities"]) >= 2


@pytest.mark.integration
def test_code_watcher_force_extract_output_passes_validation(tmp_path):
    """blueprint_code.json from force_extract passes schema validation."""
    project_root, manifest_dir = create_mock_project(tmp_path)

    watcher = CodeWatcher(project_root=project_root, manifest_dir=manifest_dir)
    watcher.force_extract()

    code_bp = json.loads((manifest_dir / "blueprint_code.json").read_text(encoding="utf-8"))
    valid, errors = validate_blueprint_data(code_bp)
    assert valid, f"Validation failed: {errors}"


@pytest.mark.integration
def test_code_watcher_watch_skips_when_unchanged(tmp_path):
    """watch_and_extract() returns False on second call without code changes."""
    project_root, manifest_dir = create_mock_project(tmp_path)

    watcher = CodeWatcher(project_root=project_root, manifest_dir=manifest_dir)
    first = watcher.watch_and_extract()
    assert first is True

    second = watcher.watch_and_extract()
    assert second is False, "Should skip extraction when code hasn't changed"


@pytest.mark.integration
def test_code_watcher_watch_detects_code_change(tmp_path):
    """watch_and_extract() returns True after a source file is modified."""
    project_root, manifest_dir = create_mock_project(tmp_path)

    watcher = CodeWatcher(project_root=project_root, manifest_dir=manifest_dir)
    watcher.watch_and_extract()

    # Touch a source file to change mtime
    time.sleep(0.05)
    calc_py = project_root / "engine" / "calculator.py"
    calc_py.write_text(calc_py.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")

    result = watcher.watch_and_extract()
    assert result is True, "Should re-extract after code change"


@pytest.mark.integration
def test_code_watcher_returns_false_without_design(tmp_path):
    """watch_and_extract() returns False if blueprint_design.json is missing."""
    project_root, manifest_dir = create_mock_project(tmp_path)
    (manifest_dir / "blueprint_design.json").unlink()

    watcher = CodeWatcher(project_root=project_root, manifest_dir=manifest_dir)
    result = watcher.watch_and_extract()

    assert result is False
