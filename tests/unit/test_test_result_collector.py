"""Unit tests for test_result_collector.collect_test_results()."""
from pathlib import Path

import pytest

from manifest.audit.code.test_result_collector import collect_test_results


def _write_test_file(tests_dir: Path, filename: str, content: str) -> None:
    tests_dir.mkdir(parents=True, exist_ok=True)
    (tests_dir / filename).write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Basic detection
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_collect_stub_detected(tmp_path: Path) -> None:
    _write_test_file(tmp_path / "tests", "test_a.py", (
        'import pytest\n'
        '@pytest.mark.manifest_assertion("foo", 0)\n'
        'def test_foo():\n'
        '    raise NotImplementedError\n'
    ))
    res = collect_test_results(tmp_path)
    assert res["foo"][0]["status"] == "stub"


@pytest.mark.unit
def test_collect_implemented_detected(tmp_path: Path) -> None:
    _write_test_file(tmp_path / "tests", "test_a.py", (
        'import pytest\n'
        '@pytest.mark.manifest_assertion("bar", 0)\n'
        'def test_bar():\n'
        '    assert 1 + 1 == 2\n'
    ))
    res = collect_test_results(tmp_path)
    assert res["bar"][0]["status"] == "implemented"


@pytest.mark.unit
def test_collect_docstring_captured(tmp_path: Path) -> None:
    _write_test_file(tmp_path / "tests", "test_a.py", (
        'import pytest\n'
        '@pytest.mark.manifest_assertion("baz", 0)\n'
        'def test_baz():\n'
        '    """Check baz works."""\n'
        '    assert True\n'
    ))
    res = collect_test_results(tmp_path)
    assert res["baz"][0]["assertion"] == "Check baz works."


# ---------------------------------------------------------------------------
# Multiple entries
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_collect_multiple_assertions_same_entity(tmp_path: Path) -> None:
    _write_test_file(tmp_path / "tests", "test_a.py", (
        'import pytest\n'
        '@pytest.mark.manifest_assertion("ent", 0)\n'
        'def test_ent_0():\n'
        '    raise NotImplementedError\n'
        '@pytest.mark.manifest_assertion("ent", 1)\n'
        'def test_ent_1():\n'
        '    assert True\n'
    ))
    res = collect_test_results(tmp_path)
    assert len(res["ent"]) == 2


@pytest.mark.unit
def test_collect_multiple_entities(tmp_path: Path) -> None:
    _write_test_file(tmp_path / "tests", "test_a.py", (
        'import pytest\n'
        '@pytest.mark.manifest_assertion("alpha", 0)\n'
        'def test_alpha():\n'
        '    raise NotImplementedError\n'
        '@pytest.mark.manifest_assertion("beta", 0)\n'
        'def test_beta():\n'
        '    assert True\n'
    ))
    res = collect_test_results(tmp_path)
    assert "alpha" in res and "beta" in res
    assert res["alpha"][0]["status"] == "stub"
    assert res["beta"][0]["status"] == "implemented"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_collect_no_tests_dir_returns_empty(tmp_path: Path) -> None:
    assert collect_test_results(tmp_path) == {}


@pytest.mark.unit
def test_collect_no_marker_returns_empty(tmp_path: Path) -> None:
    _write_test_file(tmp_path / "tests", "test_a.py", (
        'def test_plain():\n'
        '    assert True\n'
    ))
    assert collect_test_results(tmp_path) == {}


@pytest.mark.unit
def test_collect_syntax_error_skipped(tmp_path: Path) -> None:
    _write_test_file(tmp_path / "tests", "test_bad.py", "def broken(\n")
    _write_test_file(tmp_path / "tests", "test_good.py", (
        'import pytest\n'
        '@pytest.mark.manifest_assertion("ok", 0)\n'
        'def test_ok():\n'
        '    assert True\n'
    ))
    res = collect_test_results(tmp_path)
    assert "ok" in res


@pytest.mark.unit
def test_collect_nested_tests_dir(tmp_path: Path) -> None:
    sub = tmp_path / "tests" / "sub"
    _write_test_file(sub, "test_deep.py", (
        'import pytest\n'
        '@pytest.mark.manifest_assertion("deep", 0)\n'
        'def test_deep():\n'
        '    assert True\n'
    ))
    res = collect_test_results(tmp_path)
    assert "deep" in res


@pytest.mark.unit
def test_collect_stub_with_docstring(tmp_path: Path) -> None:
    _write_test_file(tmp_path / "tests", "test_a.py", (
        'import pytest\n'
        '@pytest.mark.manifest_assertion("ds", 0)\n'
        'def test_ds():\n'
        '    """My docstring."""\n'
        '    raise NotImplementedError\n'
    ))
    res = collect_test_results(tmp_path)
    assert res["ds"][0]["status"] == "stub"
    assert res["ds"][0]["assertion"] == "My docstring."


@pytest.mark.unit
def test_collect_wrong_arg_count_skipped(tmp_path: Path) -> None:
    _write_test_file(tmp_path / "tests", "test_a.py", (
        'import pytest\n'
        '@pytest.mark.manifest_assertion("only_one")\n'
        'def test_one():\n'
        '    assert True\n'
    ))
    assert collect_test_results(tmp_path) == {}


@pytest.mark.unit
def test_collect_non_test_file_ignored(tmp_path: Path) -> None:
    _write_test_file(tmp_path / "tests", "helper.py", (
        'import pytest\n'
        '@pytest.mark.manifest_assertion("nope", 0)\n'
        'def test_nope():\n'
        '    assert True\n'
    ))
    assert collect_test_results(tmp_path) == {}


@pytest.mark.unit
def test_collect_fixture_calculator() -> None:
    """Real calculator fixture: 6 test files, 3 implemented + 3 stubs."""
    fixture = Path(__file__).resolve().parent.parent / "fixtures" / "calculator"
    res = collect_test_results(fixture)
    # 6 entities: add, arithmetic_engine, cli, mul, output, sub
    assert len(res) == 6
    implemented = {eid for eid, entries in res.items() if all(e["status"] == "implemented" for e in entries)}
    stubs = {eid for eid, entries in res.items() if all(e["status"] == "stub" for e in entries)}
    assert implemented == {"add", "sub", "output"}
    assert stubs == {"arithmetic_engine", "cli", "mul"}
