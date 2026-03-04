"""Tests for manifest.opencode.test_implementer."""
import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_entity
from manifest.io.blueprint_io import save_blueprint
from manifest.opencode.test_implementer import (
    build_test_implementer_context,
    implement_test_stubs,
)

STUB_TEST_SOURCE = '''\
"""Generated test stubs for entity cli."""
import pytest

@pytest.mark.manifest_assertion("cli", 0)
def test_cli_assertion_0():
    """CLI parses argv into op, a, b."""
    raise NotImplementedError
'''

MIXED_TEST_SOURCE = '''\
"""Test file with one stub and one implemented."""
import pytest

@pytest.mark.manifest_assertion("cli", 0)
def test_cli_assertion_0():
    """CLI parses argv into op, a, b."""
    assert True

@pytest.mark.manifest_assertion("cli", 1)
def test_cli_assertion_1():
    """CLI returns formatted result."""
    raise NotImplementedError
'''


@pytest.fixture
def tmp_project(tmp_path):
    """Create a minimal project with blueprint, test file, and stubs."""
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
        "profile": {"language": "python"},
    }
    blueprint = {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [root, cli_entity]}
    save_blueprint(manifest_dir, blueprint)

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_cli.py").write_text(STUB_TEST_SOURCE, encoding="utf-8")

    return tmp_path, manifest_dir


# --- build_test_implementer_context ---


def test_build_context_extracts_design_values(tmp_project):
    """Context design fields match exact values from blueprint entity."""
    project_root, manifest_dir = tmp_project
    ctx = build_test_implementer_context(manifest_dir, "cli", project_root)

    assert ctx["entity_id"] == "cli"
    assert ctx["project_root"] == str(project_root.resolve())
    assert ctx["test_file"].endswith("test_cli.py")

    # Design values must match what we put in the blueprint fixture
    design = ctx["design"]
    assert design["assertions"] == ["CLI parses argv into op, a, b."]
    assert design["protocol"] == {"input": {"argv": "list"}, "output": {"result": "str"}}
    assert design["narrative"] == {"role": "CLI interface", "mission": "Parse user input"}
    assert design["symbol"] == "cli_main"
    assert design["profile"]["language"] == "python"


def test_build_context_stubs_reflect_test_file(tmp_project):
    """Stubs list matches the actual stub functions parsed from the test file."""
    project_root, manifest_dir = tmp_project
    ctx = build_test_implementer_context(manifest_dir, "cli", project_root)

    assert len(ctx["stubs"]) == 1
    stub = ctx["stubs"][0]
    assert stub["index"] == 0
    assert stub["status"] == "stub"
    assert "parses argv" in stub["assertion"]


def test_build_context_mixed_stubs_and_implemented(tmp_project):
    """With mixed file, stubs list includes both stub and implemented entries."""
    project_root, manifest_dir = tmp_project
    (project_root / "tests" / "test_cli.py").write_text(MIXED_TEST_SOURCE, encoding="utf-8")

    ctx = build_test_implementer_context(manifest_dir, "cli", project_root)

    assert len(ctx["stubs"]) == 2
    statuses = {s["index"]: s["status"] for s in ctx["stubs"]}
    assert statuses[0] == "implemented"
    assert statuses[1] == "stub"


def test_build_context_missing_entity_raises(tmp_project):
    """ValueError if entity not in blueprint."""
    _, manifest_dir = tmp_project
    with pytest.raises(ValueError, match="not found"):
        build_test_implementer_context(manifest_dir, "nonexistent")


def test_build_context_no_test_file_raises(tmp_project):
    """ValueError if test file doesn't exist."""
    project_root, manifest_dir = tmp_project
    blueprint = json.loads((manifest_dir / "blueprint_design.json").read_text())
    blueprint["entities"].append({**empty_entity("engine"), "id": "engine", "children": []})
    save_blueprint(manifest_dir, blueprint)

    with pytest.raises(ValueError, match="Test file not found"):
        build_test_implementer_context(manifest_dir, "engine", project_root)


def test_build_context_no_stubs_raises(tmp_project):
    """ValueError if all tests already implemented (no stubs)."""
    project_root, manifest_dir = tmp_project
    implemented_source = '''\
"""Generated test stubs for entity cli."""
import pytest

@pytest.mark.manifest_assertion("cli", 0)
def test_cli_assertion_0():
    """CLI parses argv into op, a, b."""
    assert True
'''
    (project_root / "tests" / "test_cli.py").write_text(implemented_source, encoding="utf-8")

    with pytest.raises(ValueError, match="No test stubs found"):
        build_test_implementer_context(manifest_dir, "cli", project_root)


def test_build_context_defaults_project_root_from_manifest_dir(tmp_project):
    """When project_root is None, defaults to manifest_dir.parent."""
    project_root, manifest_dir = tmp_project
    ctx = build_test_implementer_context(manifest_dir, "cli")
    assert ctx["project_root"] == str(manifest_dir.parent.resolve())


# --- implement_test_stubs ---


def test_implement_missing_opencode_raises(tmp_project):
    """RuntimeError when opencode is not on PATH."""
    project_root, manifest_dir = tmp_project
    ctx = build_test_implementer_context(manifest_dir, "cli", project_root)

    with patch("shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="opencode not on PATH"):
            implement_test_stubs(ctx, project_root)


def test_implement_subprocess_failure_raises(tmp_project):
    """RuntimeError when subprocess exits non-zero, includes exit code."""
    project_root, manifest_dir = tmp_project
    ctx = build_test_implementer_context(manifest_dir, "cli", project_root)

    mock_result = MagicMock(returncode=1, stdout="some error output", stderr="")
    with patch("shutil.which", return_value="/fake/opencode"):
        with patch("manifest.opencode.test_implementer.subprocess.run", return_value=mock_result):
            with pytest.raises(RuntimeError, match="exit 1"):
                implement_test_stubs(ctx, project_root)


def test_implement_timeout_raises(tmp_project):
    """RuntimeError on subprocess timeout, mentions timeout value."""
    project_root, manifest_dir = tmp_project
    ctx = build_test_implementer_context(manifest_dir, "cli", project_root)

    with patch("shutil.which", return_value="/fake/opencode"):
        with patch(
            "manifest.opencode.test_implementer.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="opencode", timeout=180),
        ):
            with pytest.raises(RuntimeError, match="timed out after 180s"):
                implement_test_stubs(ctx, project_root)


def test_implement_calls_subprocess_with_correct_cmd(tmp_project):
    """Verify full command structure: opencode run <prompt> --agent --dir --format -f."""
    project_root, manifest_dir = tmp_project
    ctx = build_test_implementer_context(manifest_dir, "cli", project_root)

    mock_result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("shutil.which", return_value="/fake/opencode"):
        with patch("manifest.opencode.test_implementer.subprocess.run", return_value=mock_result) as mock_run:
            implement_test_stubs(ctx, project_root)

    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "/fake/opencode"
    assert cmd[1] == "run"
    # prompt is cmd[2]
    assert "--agent" in cmd
    agent_idx = cmd.index("--agent")
    assert cmd[agent_idx + 1] == "test-implementer"
    assert "--format" in cmd
    fmt_idx = cmd.index("--format")
    assert cmd[fmt_idx + 1] == "json"
    assert "--dir" in cmd
    assert "-f" in cmd

    # Also verify subprocess.run kwargs
    kwargs = mock_run.call_args[1]
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert kwargs["timeout"] == 180


def test_implement_all_stubs_filled_returns_correct_counts(tmp_project):
    """Post-verification: all stubs implemented → correct implemented/remaining counts."""
    project_root, manifest_dir = tmp_project
    ctx = build_test_implementer_context(manifest_dir, "cli", project_root)

    mock_result = MagicMock(returncode=0, stdout="", stderr="")
    post_results = {"cli": [{"index": 0, "assertion": "CLI parses argv", "status": "implemented"}]}

    with patch("shutil.which", return_value="/fake/opencode"):
        with patch("manifest.opencode.test_implementer.subprocess.run", return_value=mock_result):
            with patch("manifest.opencode.test_implementer.collect_test_results", return_value=post_results):
                result = implement_test_stubs(ctx, project_root)

    assert result == {"implemented": 1, "remaining_stubs": 0}


def test_implement_partial_fill_returns_correct_counts(tmp_project):
    """Post-verification: only some stubs filled → counts reflect partial progress."""
    project_root, manifest_dir = tmp_project
    (project_root / "tests" / "test_cli.py").write_text(MIXED_TEST_SOURCE, encoding="utf-8")
    ctx = build_test_implementer_context(manifest_dir, "cli", project_root)
    # pre_stubs = 1 (index 1 is stub)

    mock_result = MagicMock(returncode=0, stdout="", stderr="")
    # Simulate: stub at index 1 is still a stub (agent didn't fill it)
    post_results = {"cli": [
        {"index": 0, "assertion": "a0", "status": "implemented"},
        {"index": 1, "assertion": "a1", "status": "stub"},
    ]}

    with patch("shutil.which", return_value="/fake/opencode"):
        with patch("manifest.opencode.test_implementer.subprocess.run", return_value=mock_result):
            with patch("manifest.opencode.test_implementer.collect_test_results", return_value=post_results):
                result = implement_test_stubs(ctx, project_root)

    assert result == {"implemented": 0, "remaining_stubs": 1}


def test_implement_custom_timeout_from_env(tmp_project):
    """MANIFEST_TEST_IMPLEMENTER_TIMEOUT env var overrides default 180s."""
    project_root, manifest_dir = tmp_project
    ctx = build_test_implementer_context(manifest_dir, "cli", project_root)

    mock_result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("shutil.which", return_value="/fake/opencode"):
        with patch("manifest.opencode.test_implementer.subprocess.run", return_value=mock_result) as mock_run:
            with patch.dict("os.environ", {"MANIFEST_TEST_IMPLEMENTER_TIMEOUT": "300"}):
                implement_test_stubs(ctx, project_root)

    assert mock_run.call_args[1]["timeout"] == 300
