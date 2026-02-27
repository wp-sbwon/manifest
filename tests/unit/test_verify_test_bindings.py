"""Tests for scripts/verify_test_bindings: pass when all test_* have decorator, fail when one is missing."""
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO / "scripts" / "verify_test_bindings.py"


@pytest.mark.unit
def test_verify_test_bindings_pass_when_all_have_decorator(tmp_path):
    """Exit 0 when every test_* function in a stub file has @pytest.mark.manifest_assertion."""
    stub_dir = tmp_path / "tests"
    stub_dir.mkdir(parents=True, exist_ok=True)
    (stub_dir / "test_foo.py").write_text(
        'import pytest\n\n@pytest.mark.manifest_assertion("foo", 0)\ndef test_foo_assertion_0():\n    """Assertion."""\n    raise NotImplementedError\n',
        encoding="utf-8",
    )
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--tests-dir", str(stub_dir)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert r.returncode == 0, r.stderr


@pytest.mark.unit
def test_verify_test_bindings_fail_when_test_function_missing_decorator(tmp_path):
    """Exit 1 when a test_* function lacks @pytest.mark.manifest_assertion in a file that contains the string."""
    stub_dir = tmp_path / "tests"
    stub_dir.mkdir(parents=True, exist_ok=True)
    (stub_dir / "test_foo.py").write_text(
        'import pytest\n\n@pytest.mark.manifest_assertion("foo", 0)\ndef test_foo_assertion_0():\n    pass\n\ndef test_foo_other():\n    """No decorator."""\n    pass\n',
        encoding="utf-8",
    )
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--tests-dir", str(stub_dir)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert r.returncode == 1
    assert "missing @pytest.mark.manifest_assertion" in (r.stderr or "")


@pytest.mark.unit
def test_verify_test_bindings_skips_files_without_manifest_assertion_string(tmp_path):
    """Files that do not contain 'manifest_assertion' are not checked (no error for plain test_*.py)."""
    stub_dir = tmp_path / "tests"
    stub_dir.mkdir(parents=True, exist_ok=True)
    (stub_dir / "test_plain.py").write_text(
        "def test_something():\n    assert True\n",
        encoding="utf-8",
    )
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--tests-dir", str(stub_dir)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert r.returncode == 0
