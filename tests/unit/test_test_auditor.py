"""Tests for manifest.opencode.test_auditor."""
import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_entity
from manifest.io.blueprint_io import save_blueprint
from manifest.opencode.test_auditor import (
    audit_entity_tests,
    build_test_auditor_context,
)

TEST_SOURCE = '''\
"""Generated test stubs for entity cli."""
import pytest

@pytest.mark.manifest_assertion("cli", 0)
def test_cli_assertion_0():
    """CLI parses argv into op, a, b."""
    assert True
'''


@pytest.fixture
def tmp_project(tmp_path):
    """Create minimal project with blueprint, test file, and view schema."""
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir()

    root = {**empty_entity(PROJECT_ROOT_ID), "id": PROJECT_ROOT_ID, "children": ["cli"]}
    cli_entity = {
        **empty_entity("cli"),
        "id": "cli",
        "children": [],
        "governance": {"assertions": ["CLI parses argv into op, a, b."]},
        "protocol": {"input": {"argv": "list"}, "output": {"result": "str"}},
        "narrative": {"role": "CLI interface", "mission": "Parse user input"},
        "symbol": "cli_main",
    }
    blueprint = {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [root, cli_entity]}
    save_blueprint(manifest_dir, blueprint)

    view_schema = {
        "version": "1.0",
        "root_id": PROJECT_ROOT_ID,
        "entities": [
            {"id": "cli", "validation": {"status": "deviation", "deviations": ["protocol.input"]}},
        ],
    }
    (manifest_dir / "blueprint_view.json").write_text(json.dumps(view_schema), encoding="utf-8")

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_cli.py").write_text(TEST_SOURCE, encoding="utf-8")

    return tmp_path, manifest_dir


def _opencode_stdout(payload_dict):
    """Build opencode JSON-line stdout from a payload dict."""
    return json.dumps({"type": "text", "part": {"text": json.dumps(payload_dict)}}) + "\n"


# --- build_test_auditor_context ---


def test_build_auditor_context_extracts_design_values(tmp_project):
    """Context design fields match exact values from blueprint entity."""
    project_root, manifest_dir = tmp_project
    ctx = build_test_auditor_context(manifest_dir, "cli", project_root)

    assert ctx["entity_id"] == "cli"
    assert ctx["test_file"].endswith("test_cli.py")

    design = ctx["design"]
    assert design["assertions"] == ["CLI parses argv into op, a, b."]
    assert design["protocol"] == {"input": {"argv": "list"}, "output": {"result": "str"}}
    assert design["narrative"] == {"role": "CLI interface", "mission": "Parse user input"}
    assert design["symbol"] == "cli_main"


def test_build_auditor_context_includes_test_file_contents(tmp_project):
    """test_file_contents is the actual source of the test file."""
    project_root, manifest_dir = tmp_project
    ctx = build_test_auditor_context(manifest_dir, "cli", project_root)

    assert ctx["test_file_contents"] == TEST_SOURCE


def test_build_auditor_context_includes_test_results(tmp_project):
    """test_results reflect parsed manifest_assertion markers from test file."""
    project_root, manifest_dir = tmp_project
    ctx = build_test_auditor_context(manifest_dir, "cli", project_root)

    assert len(ctx["test_results"]) == 1
    tr = ctx["test_results"][0]
    assert tr["index"] == 0
    assert tr["status"] == "implemented"
    assert "parses argv" in tr["assertion"]


def test_build_auditor_context_includes_view_deviations(tmp_project):
    """view_deviations loaded from blueprint_view.json."""
    project_root, manifest_dir = tmp_project
    ctx = build_test_auditor_context(manifest_dir, "cli", project_root)

    assert ctx["view_deviations"] == ["protocol.input"]


def test_build_auditor_context_no_view_schema_returns_empty_deviations(tmp_project):
    """Graceful default: no view schema file → empty deviations list."""
    project_root, manifest_dir = tmp_project
    (manifest_dir / "blueprint_view.json").unlink()

    ctx = build_test_auditor_context(manifest_dir, "cli", project_root)
    assert ctx["view_deviations"] == []


def test_build_auditor_context_missing_entity_raises(tmp_project):
    """ValueError if entity not in blueprint."""
    _, manifest_dir = tmp_project
    with pytest.raises(ValueError, match="not found"):
        build_test_auditor_context(manifest_dir, "nonexistent")


def test_build_auditor_context_missing_test_file_raises(tmp_project):
    """ValueError if test file doesn't exist."""
    project_root, manifest_dir = tmp_project
    blueprint = json.loads((manifest_dir / "blueprint_design.json").read_text())
    blueprint["entities"].append({**empty_entity("engine"), "id": "engine", "children": []})
    save_blueprint(manifest_dir, blueprint)

    with pytest.raises(ValueError, match="Test file not found"):
        build_test_auditor_context(manifest_dir, "engine", project_root)


# --- audit_entity_tests ---


def test_audit_parses_full_report_from_stdout(tmp_project):
    """Parsed report contains all fields with correct values from agent output."""
    project_root, manifest_dir = tmp_project
    ctx = build_test_auditor_context(manifest_dir, "cli", project_root)

    report = {
        "gaps": [{"index": 1, "assertion": "missing test", "reason": "not covered"}],
        "coverage_issues": [{"index": 0, "issue": "weak assertion"}],
        "verdict": "warn",
        "recommendations": ["Add edge case tests"],
    }
    mock_result = MagicMock(returncode=0, stdout=_opencode_stdout(report), stderr="")

    with patch("shutil.which", return_value="/fake/opencode"):
        with patch("manifest.opencode.test_auditor.subprocess.run", return_value=mock_result):
            result = audit_entity_tests(ctx, project_root)

    assert result["entity_id"] == "cli"
    assert result["verdict"] == "warn"
    assert result["gaps"] == [{"index": 1, "assertion": "missing test", "reason": "not covered"}]
    assert result["coverage_issues"] == [{"index": 0, "issue": "weak assertion"}]
    assert result["recommendations"] == ["Add edge case tests"]


def test_audit_pass_verdict_with_no_issues(tmp_project):
    """Clean audit: verdict=pass, empty gaps/issues/recommendations."""
    project_root, manifest_dir = tmp_project
    ctx = build_test_auditor_context(manifest_dir, "cli", project_root)

    report = {"gaps": [], "coverage_issues": [], "verdict": "pass", "recommendations": []}
    mock_result = MagicMock(returncode=0, stdout=_opencode_stdout(report), stderr="")

    with patch("shutil.which", return_value="/fake/opencode"):
        with patch("manifest.opencode.test_auditor.subprocess.run", return_value=mock_result):
            result = audit_entity_tests(ctx, project_root)

    assert result["verdict"] == "pass"
    assert result["gaps"] == []
    assert result["coverage_issues"] == []
    assert result["recommendations"] == []


def test_audit_missing_keys_in_output_defaults_to_empty(tmp_project):
    """Agent returns partial JSON (only verdict) → missing keys default to []."""
    project_root, manifest_dir = tmp_project
    ctx = build_test_auditor_context(manifest_dir, "cli", project_root)

    report = {"verdict": "pass"}
    mock_result = MagicMock(returncode=0, stdout=_opencode_stdout(report), stderr="")

    with patch("shutil.which", return_value="/fake/opencode"):
        with patch("manifest.opencode.test_auditor.subprocess.run", return_value=mock_result):
            result = audit_entity_tests(ctx, project_root)

    assert result["verdict"] == "pass"
    assert result["gaps"] == []
    assert result["coverage_issues"] == []
    assert result["recommendations"] == []


def test_audit_bad_json_returns_error_verdict(tmp_project):
    """Malformed output → verdict 'error' with error message."""
    project_root, manifest_dir = tmp_project
    ctx = build_test_auditor_context(manifest_dir, "cli", project_root)

    opencode_stdout = json.dumps({"type": "text", "part": {"text": "not valid json {["}}) + "\n"
    mock_result = MagicMock(returncode=0, stdout=opencode_stdout, stderr="")

    with patch("shutil.which", return_value="/fake/opencode"):
        with patch("manifest.opencode.test_auditor.subprocess.run", return_value=mock_result):
            result = audit_entity_tests(ctx, project_root)

    assert result["entity_id"] == "cli"
    assert result["verdict"] == "error"
    assert "error" in result


def test_audit_empty_stdout_returns_error_verdict(tmp_project):
    """No text output from opencode → verdict 'error'."""
    project_root, manifest_dir = tmp_project
    ctx = build_test_auditor_context(manifest_dir, "cli", project_root)

    mock_result = MagicMock(returncode=0, stdout="", stderr="")

    with patch("shutil.which", return_value="/fake/opencode"):
        with patch("manifest.opencode.test_auditor.subprocess.run", return_value=mock_result):
            result = audit_entity_tests(ctx, project_root)

    assert result["verdict"] == "error"


def test_audit_missing_opencode_raises(tmp_project):
    """RuntimeError when opencode is not on PATH."""
    project_root, manifest_dir = tmp_project
    ctx = build_test_auditor_context(manifest_dir, "cli", project_root)

    with patch("shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="opencode not on PATH"):
            audit_entity_tests(ctx, project_root)


def test_audit_subprocess_failure_raises(tmp_project):
    """RuntimeError when subprocess exits non-zero."""
    project_root, manifest_dir = tmp_project
    ctx = build_test_auditor_context(manifest_dir, "cli", project_root)

    mock_result = MagicMock(returncode=1, stdout="agent error", stderr="")
    with patch("shutil.which", return_value="/fake/opencode"):
        with patch("manifest.opencode.test_auditor.subprocess.run", return_value=mock_result):
            with pytest.raises(RuntimeError, match="exit 1"):
                audit_entity_tests(ctx, project_root)


def test_audit_timeout_raises(tmp_project):
    """RuntimeError on subprocess timeout."""
    project_root, manifest_dir = tmp_project
    ctx = build_test_auditor_context(manifest_dir, "cli", project_root)

    with patch("shutil.which", return_value="/fake/opencode"):
        with patch(
            "manifest.opencode.test_auditor.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="opencode", timeout=120),
        ):
            with pytest.raises(RuntimeError, match="timed out after 120s"):
                audit_entity_tests(ctx, project_root)


def test_audit_calls_subprocess_with_correct_cmd(tmp_project):
    """Verify full command: opencode run <prompt> --agent test-auditor --dir --format json -f."""
    project_root, manifest_dir = tmp_project
    ctx = build_test_auditor_context(manifest_dir, "cli", project_root)

    report = {"gaps": [], "verdict": "pass", "coverage_issues": [], "recommendations": []}
    mock_result = MagicMock(returncode=0, stdout=_opencode_stdout(report), stderr="")

    with patch("shutil.which", return_value="/fake/opencode"):
        with patch("manifest.opencode.test_auditor.subprocess.run", return_value=mock_result) as mock_run:
            audit_entity_tests(ctx, project_root)

    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "/fake/opencode"
    assert cmd[1] == "run"
    agent_idx = cmd.index("--agent")
    assert cmd[agent_idx + 1] == "test-auditor"
    fmt_idx = cmd.index("--format")
    assert cmd[fmt_idx + 1] == "json"
    assert "--dir" in cmd
    assert "-f" in cmd

    kwargs = mock_run.call_args[1]
    assert kwargs["capture_output"] is True
    assert kwargs["timeout"] == 120


def test_audit_custom_timeout_from_env(tmp_project):
    """MANIFEST_TEST_AUDITOR_TIMEOUT env var overrides default 120s."""
    project_root, manifest_dir = tmp_project
    ctx = build_test_auditor_context(manifest_dir, "cli", project_root)

    report = {"gaps": [], "verdict": "pass"}
    mock_result = MagicMock(returncode=0, stdout=_opencode_stdout(report), stderr="")

    with patch("shutil.which", return_value="/fake/opencode"):
        with patch("manifest.opencode.test_auditor.subprocess.run", return_value=mock_result) as mock_run:
            with patch.dict("os.environ", {"MANIFEST_TEST_AUDITOR_TIMEOUT": "60"}):
                audit_entity_tests(ctx, project_root)

    assert mock_run.call_args[1]["timeout"] == 60
