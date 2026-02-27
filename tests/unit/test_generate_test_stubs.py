"""Tests for bin/generate_test_stubs: stub layout and manifest_assertion decorator."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_entity
from manifest.audit.entity_validation import normalize_for_schema

REPO = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO / "bin" / "generate_test_stubs.py"


@pytest.mark.unit
def test_generate_stubs_creates_file_per_entity_with_assertion_decorator(tmp_path):
    """generate_stubs produces test_<id>.py with @pytest.mark.manifest_assertion and assertion in docstring."""
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    root = dict(empty_entity(PROJECT_ROOT_ID))
    root["children"] = ["m1"]
    m1 = dict(empty_entity("m1"))
    m1["children"] = []
    m1["governance"] = {"rules": [], "assertions": ["M1 must validate input."]}
    design = normalize_for_schema({"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [root, m1]})
    (manifest_dir / "blueprint_design.json").write_text(json.dumps(design, indent=2), encoding="utf-8")
    tests_dir = tmp_path / "tests"
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--manifest-dir", str(manifest_dir), "--tests-dir", str(tests_dir)],
        cwd=str(REPO),
        env={**os.environ, "PYTHONPATH": str(REPO / "src")},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert r.returncode == 0, r.stderr
    stub_file = tests_dir / "test_m1.py"
    assert stub_file.exists()
    content = stub_file.read_text(encoding="utf-8")
    assert '@pytest.mark.manifest_assertion("m1", 0)' in content
    assert "M1 must validate input." in content
    assert "def test_m1_assertion_0" in content
    assert "raise NotImplementedError" in content


@pytest.mark.unit
def test_generate_stubs_entity_without_assertions_gets_one_stub(tmp_path):
    """Entity with empty assertions list still gets one test_<id>_assertion_0 stub."""
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    root = dict(empty_entity(PROJECT_ROOT_ID))
    root["children"] = ["x"]
    x = dict(empty_entity("x"))
    x["children"] = []
    x["governance"] = {"rules": [], "assertions": []}
    design = normalize_for_schema({"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [root, x]})
    (manifest_dir / "blueprint_design.json").write_text(json.dumps(design, indent=2), encoding="utf-8")
    tests_dir = tmp_path / "tests"
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--manifest-dir", str(manifest_dir), "--tests-dir", str(tests_dir)],
        cwd=str(REPO),
        env={**os.environ, "PYTHONPATH": str(REPO / "src")},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert r.returncode == 0
    content = (tests_dir / "test_x.py").read_text(encoding="utf-8")
    assert "test_x_assertion_0" in content
    assert "manifest_assertion" in content
