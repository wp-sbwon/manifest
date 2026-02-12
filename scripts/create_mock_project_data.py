#!/usr/bin/env python3
"""
Create mock project data under tmp/.manifest using schema + io only.

Writes blueprint_design.json and blueprint_code.json so the View shows
Diagram and Health. No PRD, tasks, or state.

Usage:
  PYTHONPATH=src python scripts/create_mock_project_data.py [manifest_dir]
  Default manifest_dir: tmp/.manifest (from repo root).
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from manifest.schema.entity_schema import (
    PROJECT_ROOT_ID,
    empty_entity,
    empty_intent,
    empty_reality,
)
from manifest.schema.entity_validation import normalize_for_schema
from manifest.io.blueprint_io import save_blueprint, save_code_blueprint


def _make_root() -> dict:
    intent = empty_intent()
    intent["narrative"] = {"role": "Calculator", "mission": "CLI calculator: parse args → compute → format → print."}
    reality = empty_reality()
    reality["symbol"] = "main"
    reality["preview"] = "main.py: parse → engine → format_result → print."
    return {
        "id": PROJECT_ROOT_ID,
        "children": ["cli", "arithmetic_engine", "output"],
        "dependencies": [],
        "intent": intent,
        "reality": reality,
        "outgoing_contracts": [
            {"to": "cli", "type": "flow", "file": "main.py", "symbols": ["parse_args"]},
            {"to": "arithmetic_engine", "type": "flow", "file": "main.py", "symbols": ["compute"]},
            {"to": "output", "type": "flow", "file": "main.py", "symbols": ["format_result"]},
        ],
    }


def _make_entity(eid: str, role: str, mission: str, symbol: str, children: list = None, contracts: list = None) -> dict:
    intent = empty_intent()
    intent["narrative"] = {"role": role, "mission": mission}
    reality = empty_reality()
    reality["symbol"] = symbol
    reality["preview"] = f"Module: {symbol}"
    return {
        "id": eid,
        "children": children or [],
        "dependencies": [],
        "intent": intent,
        "reality": reality,
        "outgoing_contracts": contracts or [],
    }


def build_design_blueprint() -> dict:
    root = _make_root()
    cli = _make_entity("cli", "CLI", "Parse terminal input into op and two numbers.", "cli.parser", contracts=[{"to": "arithmetic_engine", "type": "flow", "file": "cli/parser.py", "symbols": ["parse_args"]}])
    add_ent = _make_entity("add", "Add", "Return a + b.", "calc.operations.add")
    sub_ent = _make_entity("sub", "Sub", "Return a - b.", "calc.operations.sub")
    mul_ent = _make_entity("mul", "Mul", "Return a * b.", "calc.operations.mul")
    engine = _make_entity(
        "arithmetic_engine",
        "Arithmetic Engine",
        "Pure arithmetic: add, sub, mul.",
        "engine.calculator",
        children=["add", "sub", "mul"],
        contracts=[
            {"to": "add", "type": "dependency", "file": "engine/calculator.py", "symbols": ["add"]},
            {"to": "sub", "type": "dependency", "file": "engine/calculator.py", "symbols": ["sub"]},
            {"to": "mul", "type": "dependency", "file": "engine/calculator.py", "symbols": ["mul"]},
            {"to": "output", "type": "flow", "file": "main.py", "symbols": ["format_result"]},
        ],
    )
    output = _make_entity("output", "Output", "Format numeric result for console.", "output.formatter")
    data = {
        "version": "1.0",
        "root_id": PROJECT_ROOT_ID,
        "entities": [root, cli, engine, add_ent, sub_ent, mul_ent, output],
    }
    return normalize_for_schema(data)


def build_code_blueprint() -> dict:
    design = build_design_blueprint()
    implemented_ids = {PROJECT_ROOT_ID, "cli", "arithmetic_engine", "add", "sub"}
    entities = [e for e in design.get("entities") or [] if (e.get("id") or "") in implemented_ids]
    return normalize_for_schema({"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": entities})


def main() -> int:
    manifest_dir = Path(sys.argv[1]).resolve() if len(sys.argv) >= 2 else REPO / "tmp" / ".manifest"
    manifest_dir.mkdir(parents=True, exist_ok=True)

    design = build_design_blueprint()
    if save_blueprint(manifest_dir, design):
        print(f"Wrote {manifest_dir / 'blueprint_design.json'}")
    else:
        print("Failed to write blueprint_design.json", file=sys.stderr)
        return 1

    code = build_code_blueprint()
    if save_code_blueprint(manifest_dir, code):
        print(f"Wrote {manifest_dir / 'blueprint_code.json'}")
    else:
        print("Failed to write blueprint_code.json", file=sys.stderr)
        return 1

    print("Mock project data ready. Run View with this manifest dir to see Diagram and Health.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
