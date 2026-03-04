"""
Build a minimal mock calculator project for integration tests.

Mirrors tmp/calculator/ structure: main.py, cli/parser.py, engine/calculator.py,
output/formatter.py, tests/test_cli.py. Creates blueprint_design.json.
All in a tmp_path so it's self-contained (no gitignored tmp/ dependency).
"""
import json
from pathlib import Path

from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_entity
from manifest.audit.entity_validation import normalize_for_schema
from manifest.io.blueprint_io import save_blueprint


MAIN_PY = '''\
"""CLI calculator: parse -> engine -> print."""
import sys
from cli.parser import Parser
from engine.calculator import add, sub


def main():
    parser = Parser(sys.argv)
    op, a, b = parser.parse()
    if op == "add":
        result = add(a, b)
    elif op == "sub":
        result = sub(a, b)
    else:
        raise NotImplementedError("mul is planned")
    print(str(result))


if __name__ == "__main__":
    main()
'''

CLI_PARSER_PY = '''\
"""CLI parser: raw argv -> (op, a, b)."""


class Parser:
    """Parse terminal input into op and two numbers."""

    def __init__(self, argv=None):
        self.argv = argv or []

    def parse(self):
        """Return (op, a, b) or raise ValueError."""
        if len(self.argv) < 4:
            raise ValueError("Usage: calc add|sub|mul <a> <b>")
        op = (self.argv[1] or "").strip().lower()
        if op not in ("add", "sub", "mul"):
            raise ValueError("op must be add, sub, or mul")
        a = float(self.argv[2])
        b = float(self.argv[3])
        return op, a, b
'''

ENGINE_CALCULATOR_PY = '''\
"""Arithmetic engine: add, sub (pure, side-effect free)."""


def add(a: float, b: float) -> float:
    """Return a + b."""
    return a + b


def sub(a: float, b: float) -> float:
    """Return a - b."""
    return a - b
'''

OUTPUT_FORMATTER_PY = '''\
"""Format numeric result for console."""


def format_result(value: float) -> str:
    """Format value for stdout."""
    return str(value)
'''

TEST_CLI_PY = '''\
"""Test stubs for entity cli."""
import pytest

@pytest.mark.manifest_assertion("cli", 0)
def test_cli_assertion_0():
    """CLI parses argv into op, a, b."""
    raise NotImplementedError
'''


def _make_entity(eid, role, mission, symbol, **kwargs):
    ent = dict(empty_entity(eid))
    ent["id"] = eid
    ent["children"] = kwargs.get("children", [])
    ent["narrative"] = {"role": role, "mission": mission}
    ent["blueprint"] = {"type": "FLOW", "topology": {}}
    ent["profile"] = {"language": ["python"], "platform": "cli", "io_model": "", "state_model": ""}
    ent["governance"] = {"rules": kwargs.get("rules", []), "assertions": kwargs.get("assertions", [])}
    ent["protocol"] = {"input": kwargs.get("protocol_input", []), "output": kwargs.get("protocol_output", [])}
    ent["symbol"] = symbol
    ent["outgoing_contracts"] = kwargs.get("contracts", [])
    return ent


def build_design_blueprint():
    """Build the design blueprint matching the mock project code."""
    root = _make_entity(
        PROJECT_ROOT_ID, "Calculator", "CLI calculator: parse -> compute -> print.",
        "main",
        children=["cli", "arithmetic_engine", "output"],
    )
    cli = _make_entity(
        "cli", "CLI", "Parse terminal input into op and two numbers.",
        "cli.parser",
        assertions=["CLI parses argv into op, a, b."],
        protocol_input=[{"name": "argv", "type": "list"}],
        protocol_output=[{"name": "op", "type": "str"}, {"name": "a", "type": "float"}, {"name": "b", "type": "float"}],
    )
    engine = _make_entity(
        "arithmetic_engine", "Arithmetic Engine",
        "Pure arithmetic: add, sub (side-effect free).",
        "engine.calculator",
        children=["add", "sub"],
    )
    add_ent = _make_entity("add", "Add", "Return a + b.", "engine.calculator", rules=["Pure function."])
    sub_ent = _make_entity("sub", "Sub", "Return a - b.", "engine.calculator", rules=["Pure function."])
    output = _make_entity("output", "Output", "Format numeric result for console.", "output.formatter")

    return normalize_for_schema({
        "version": "1.0",
        "root_id": PROJECT_ROOT_ID,
        "entities": [root, cli, engine, add_ent, sub_ent, output],
    })


def create_mock_project(tmp_path: Path):
    """
    Create a self-contained mock calculator project under tmp_path.

    Returns (project_root, manifest_dir).
    """
    project_root = tmp_path / "calculator"
    project_root.mkdir()
    manifest_dir = project_root / ".manifest"
    manifest_dir.mkdir()

    # Source files
    (project_root / "main.py").write_text(MAIN_PY, encoding="utf-8")

    (project_root / "cli").mkdir()
    (project_root / "cli" / "__init__.py").write_text("", encoding="utf-8")
    (project_root / "cli" / "parser.py").write_text(CLI_PARSER_PY, encoding="utf-8")

    (project_root / "engine").mkdir()
    (project_root / "engine" / "__init__.py").write_text("", encoding="utf-8")
    (project_root / "engine" / "calculator.py").write_text(ENGINE_CALCULATOR_PY, encoding="utf-8")

    (project_root / "output").mkdir()
    (project_root / "output" / "__init__.py").write_text("", encoding="utf-8")
    (project_root / "output" / "formatter.py").write_text(OUTPUT_FORMATTER_PY, encoding="utf-8")

    # Tests
    (project_root / "tests").mkdir()
    (project_root / "tests" / "__init__.py").write_text("", encoding="utf-8")
    (project_root / "tests" / "test_cli.py").write_text(TEST_CLI_PY, encoding="utf-8")

    # Blueprint design
    design = build_design_blueprint()
    save_blueprint(manifest_dir, design)

    return project_root, manifest_dir
