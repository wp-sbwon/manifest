"""Integration: run bin/run_test_implementer.py and bin/run_test_auditor.py as real subprocesses.

Tests verify:
- error behaviour for bad inputs (no opencode needed — fails at context building)
- real agent invocation: actual OpenCode agent runs, modifies files, returns output
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_entity
from manifest.audit.blueprint.manifest_filenames import BLUEPRINT_VIEW_FILE
from manifest.io.blueprint_io import save_blueprint

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BIN_IMPLEMENTER = REPO_ROOT / "bin" / "run_test_implementer.py"
BIN_AUDITOR = REPO_ROOT / "bin" / "run_test_auditor.py"
OPENCODE_JSON = REPO_ROOT / "opencode.json"

STUB_TEST_SOURCE = '''\
"""Generated test stubs for entity cli."""
import pytest

@pytest.mark.manifest_assertion("cli", 0)
def test_cli_assertion_0():
    """CLI parses argv into op, a, b."""
    raise NotImplementedError

@pytest.mark.manifest_assertion("cli", 1)
def test_cli_assertion_1():
    """CLI returns formatted result."""
    raise NotImplementedError
'''

IMPLEMENTED_TEST_SOURCE = '''\
"""Tests for entity cli."""
import pytest

@pytest.mark.manifest_assertion("cli", 0)
def test_cli_assertion_0():
    """CLI parses argv into op, a, b."""
    assert ["add", "1", "2"] == "add 1 2".split()
'''


def _make_project(tmp_path, *, test_source=STUB_TEST_SOURCE, write_view=True):
    """Build a project tree with blueprint, test file, and optional view schema."""
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir()

    root = {**empty_entity(PROJECT_ROOT_ID), "id": PROJECT_ROOT_ID, "children": ["cli"]}
    cli_entity = {
        **empty_entity("cli"),
        "id": "cli",
        "children": [],
        "governance": {"assertions": [
            "CLI parses argv into op, a, b.",
            "CLI returns formatted result.",
        ]},
        "protocol": {"input": {"argv": "list"}, "output": {"result": "str"}},
        "narrative": {"role": "CLI interface", "mission": "Parse user input"},
        "symbol": "cli_main",
        "profile": {"language": "python"},
    }
    blueprint = {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [root, cli_entity]}
    save_blueprint(manifest_dir, blueprint)

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_cli.py").write_text(test_source, encoding="utf-8")

    if write_view:
        view_schema = {
            "version": "1.0",
            "root_id": PROJECT_ROOT_ID,
            "entities": [
                {"id": "cli", "validation": {"status": "deviation", "deviations": ["protocol.input"]}},
            ],
        }
        (manifest_dir / BLUEPRINT_VIEW_FILE).write_text(json.dumps(view_schema), encoding="utf-8")

    return tmp_path, manifest_dir


def _run_script(script: Path, args: list, env_extra: dict = None, cwd: Path = None, timeout: int = 30):
    """Run a bin/ script as a subprocess, return CompletedProcess.

    For agent tests, set timeout > inner opencode timeout (default 180s)
    to allow the agent to complete before the outer process kills it.
    """
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(script)] + args,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(cwd or REPO_ROOT),
        env=env,
    )


def _require_opencode() -> None:
    """Skip if opencode binary or config is physically unavailable."""
    if not shutil.which("opencode"):
        pytest.skip("opencode not on PATH")
    if not OPENCODE_JSON.exists():
        pytest.skip("opencode.json not at repo root")


# ── Error path tests (no opencode needed — fail at context building) ──


@pytest.mark.integration
def test_implementer_missing_entity_exits_nonzero(tmp_path):
    """Nonexistent entity → exit 1 with error on stderr."""
    _, manifest_dir = _make_project(tmp_path)

    result = _run_script(
        BIN_IMPLEMENTER,
        ["--manifest-dir", str(manifest_dir), "--entity", "nonexistent"],
    )

    assert result.returncode == 1
    assert "not found" in result.stderr.lower()


@pytest.mark.integration
def test_implementer_missing_manifest_dir_exits_nonzero(tmp_path):
    """Bad --manifest-dir → exit 1."""
    result = _run_script(
        BIN_IMPLEMENTER,
        ["--manifest-dir", str(tmp_path / "nope"), "--entity", "cli"],
    )

    assert result.returncode == 1
    assert "not found" in result.stderr.lower()


@pytest.mark.integration
def test_implementer_no_stubs_exits_nonzero(tmp_path):
    """All tests implemented → exit 1 (no stubs to fill)."""
    _, manifest_dir = _make_project(tmp_path, test_source=IMPLEMENTED_TEST_SOURCE)

    result = _run_script(
        BIN_IMPLEMENTER,
        ["--manifest-dir", str(manifest_dir), "--entity", "cli"],
    )

    assert result.returncode == 1
    assert "no test stubs" in result.stderr.lower()


@pytest.mark.integration
def test_auditor_missing_entity_exits_nonzero(tmp_path):
    """Nonexistent entity → exit 1."""
    _, manifest_dir = _make_project(tmp_path)

    result = _run_script(
        BIN_AUDITOR,
        ["--manifest-dir", str(manifest_dir), "--entity", "nonexistent"],
    )

    assert result.returncode == 1
    assert "not found" in result.stderr.lower()


@pytest.mark.integration
def test_auditor_missing_manifest_dir_exits_nonzero(tmp_path):
    """Bad --manifest-dir → exit 1."""
    result = _run_script(
        BIN_AUDITOR,
        ["--manifest-dir", str(tmp_path / "nope"), "--entity", "cli"],
    )

    assert result.returncode == 1
    assert "not found" in result.stderr.lower()


# ── Real agent tests (require opencode on PATH) ──


@pytest.mark.integration
def test_implementer_real_agent_fills_stubs(tmp_path):
    """test-implementer fills stub logic and reduces remaining_stubs."""
    _require_opencode()

    project_root, manifest_dir = _make_project(tmp_path)
    shutil.copy2(OPENCODE_JSON, project_root / "opencode.json")

    result = _run_script(
        BIN_IMPLEMENTER,
        ["--manifest-dir", str(manifest_dir), "--entity", "cli"],
        cwd=project_root,
        timeout=300,
    )

    assert result.returncode == 0, f"stderr: {result.stderr}"
    output = json.loads(result.stdout)
    assert isinstance(output["implemented"], int)
    assert isinstance(output["remaining_stubs"], int)
    assert output["implemented"] >= 1, (
        f"Real agent should fill at least 1 stub, got {output}"
    )
    assert output["remaining_stubs"] < 2, (
        f"Started with 2 stubs, expected fewer remaining: {output}"
    )


@pytest.mark.integration
def test_implementer_real_agent_test_file_modified(tmp_path):
    """test-implementer actually modifies the test file, replacing NotImplementedError stubs."""
    _require_opencode()

    project_root, manifest_dir = _make_project(tmp_path)
    shutil.copy2(OPENCODE_JSON, project_root / "opencode.json")
    test_file = project_root / "tests" / "test_cli.py"
    original_content = test_file.read_text(encoding="utf-8")

    result = _run_script(
        BIN_IMPLEMENTER,
        ["--manifest-dir", str(manifest_dir), "--entity", "cli"],
        cwd=project_root,
        timeout=300,
    )

    assert result.returncode == 0, f"stderr: {result.stderr}"
    modified_content = test_file.read_text(encoding="utf-8")
    assert modified_content != original_content, "Agent should have modified the test file"
    assert "@pytest.mark.manifest_assertion" in modified_content
    assert modified_content.count("raise NotImplementedError") < original_content.count(
        "raise NotImplementedError"
    ), "Agent should have replaced at least one NotImplementedError"


@pytest.mark.integration
def test_auditor_real_agent_returns_verdict(tmp_path):
    """test-auditor returns JSON audit report with verdict pass/warn/fail."""
    _require_opencode()

    project_root, manifest_dir = _make_project(tmp_path, test_source=IMPLEMENTED_TEST_SOURCE)
    shutil.copy2(OPENCODE_JSON, project_root / "opencode.json")

    result = _run_script(
        BIN_AUDITOR,
        ["--manifest-dir", str(manifest_dir), "--entity", "cli"],
        cwd=project_root,
        timeout=300,
    )

    assert result.returncode == 0, f"stderr: {result.stderr}"
    output = json.loads(result.stdout)
    assert output["entity_id"] == "cli"
    assert output["verdict"] in ("pass", "warn", "fail"), (
        f"verdict must be pass/warn/fail, got: {output['verdict']}"
    )
    assert isinstance(output.get("gaps"), list)
    assert isinstance(output.get("recommendations"), list)


@pytest.mark.integration
def test_auditor_real_agent_detects_gaps_on_stubs(tmp_path):
    """test-auditor flags gaps when tests are still stubs."""
    _require_opencode()

    project_root, manifest_dir = _make_project(tmp_path, test_source=STUB_TEST_SOURCE)
    shutil.copy2(OPENCODE_JSON, project_root / "opencode.json")

    result = _run_script(
        BIN_AUDITOR,
        ["--manifest-dir", str(manifest_dir), "--entity", "cli"],
        cwd=project_root,
        timeout=300,
    )

    assert result.returncode == 0, f"stderr: {result.stderr}"
    output = json.loads(result.stdout)
    assert output["entity_id"] == "cli"
    assert output["verdict"] in ("warn", "fail"), (
        f"Auditor should detect stub tests as problematic, got verdict: {output['verdict']}"
    )
    has_issues = len(output.get("gaps", [])) > 0 or len(output.get("coverage_issues", [])) > 0
    assert has_issues, f"Auditor should flag stub tests: {output}"
