#!/usr/bin/env python3
"""
Create mock project data for the calculator app under tmp/: blueprint_design.json
and blueprint_code.json using the manifest entity schema. The design describes
intent (CLI, Arithmetic Engine, Output); the code blueprint reflects the actual
code in tmp/ (main.py, cli/, engine/, output/) so the View can show drift.

Usage:
  PYTHONPATH=src python scripts/create_mock_project_data.py [manifest_dir]
  Default manifest_dir: tmp/.manifest (when run from manifest repo root).
"""
import json
import sys
from pathlib import Path

# Use real schema from the codebase
def _ensure_src():
    repo = Path(__file__).resolve().parent.parent
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))


_ensure_src()

from manifest.audit.entity_schema import (
    PROJECT_ROOT_ID,
    empty_entity,
    empty_intent,
    empty_reality,
    empty_outgoing_contracts,
)
from manifest.audit.entity_validation import normalize_for_schema
from manifest.audit.blueprint.manifest_filenames import (
    BLUEPRINT_DESIGN_FILE,
    BLUEPRINT_CODE_FILE,
)


def _make_root_entity() -> dict:
    """Root entity: Calculator app (orchestrates CLI, engine, output)."""
    intent = empty_intent()
    intent["narrative"] = {
        "role": "Calculator",
        "mission": "CLI calculator: parse args → compute → format → print.",
    }
    intent["blueprint"] = {"type": "FLOW", "topology": {}}
    intent["protocol"] = {"input": ["argv"], "output": ["stdout"]}
    intent["profile"] = {
        "language": "python",
        "platform": "cli",
        "io_model": "request_response",
        "state_model": "stateless",
    }
    intent["governance"] = {"rules": [], "assertions": []}

    reality = empty_reality()
    reality["symbol"] = "main"
    reality["profile"] = {"language": "python", "platform": "cli", "io_model": "", "state_model": ""}
    reality["dependencies"] = []
    reality["traits"] = ["orchestrator"]
    reality["preview"] = "main.py: parse → engine → format_result → print."

    return {
        "id": PROJECT_ROOT_ID,
        "children": ["cli", "arithmetic_engine", "output"],
        "dependencies": [],
        "intent": intent,
        "reality": reality,
        "outgoing_contracts": [],
    }


def _make_entity(
    eid: str,
    role: str,
    mission: str,
    symbol: str,
    children: list = None,
    contracts: list = None,
) -> dict:
    """One entity with intent/reality for Inspector display."""
    intent = empty_intent()
    intent["narrative"] = {"role": role, "mission": mission}
    intent["blueprint"] = {"type": "FLOW", "topology": {}}
    intent["protocol"] = {"input": ["args"], "output": ["result"]}
    intent["profile"] = {"language": "python", "platform": "cli", "io_model": "request_response", "state_model": "stateless"}
    intent["governance"] = {"rules": [], "assertions": []}

    reality = empty_reality()
    reality["symbol"] = symbol
    reality["profile"] = {"language": "python", "platform": "cli", "io_model": "", "state_model": ""}
    reality["dependencies"] = []
    reality["traits"] = []
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
    """Design blueprint (intent): Calculator root + CLI, Arithmetic Engine, Output."""
    root = _make_root_entity()
    cli = _make_entity(
        "cli",
        "CLI",
        "Parse terminal input into op and two numbers.",
        "cli.parser",
        children=[],
    )
    engine = _make_entity(
        "arithmetic_engine",
        "Arithmetic Engine",
        "Pure arithmetic: add, sub, mul (side-effect free).",
        "engine.calculator",
        children=[],
    )
    output = _make_entity(
        "output",
        "Output",
        "Format numeric result for console.",
        "output.formatter",
        children=[],
    )
    data = {
        "version": "1.0",
        "root_id": PROJECT_ROOT_ID,
        "entities": [root, cli, engine, output],
    }
    return normalize_for_schema(data)


def build_code_blueprint() -> dict:
    """Code blueprint: same structure as design, reality from actual tmp/ code."""
    design = build_design_blueprint()
    # Code view: same ids/structure, reality reflects actual code
    design["source"] = "code_extraction"
    design["ground_truth"] = True
    design["from_actual_code"] = True
    design["extraction_method"] = "mock_from_tmp"
    # Ensure root reality matches actual entrypoint
    for e in design.get("entities") or []:
        if e.get("id") == PROJECT_ROOT_ID:
            e.setdefault("reality", {})["symbol"] = "main"
            e.setdefault("reality", {})["preview"] = "main.py: parse → engine → format_result → print."
            break
    return design


def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    if len(sys.argv) >= 2:
        manifest_dir = Path(sys.argv[1]).resolve()
    else:
        manifest_dir = repo / "tmp" / ".manifest"
    manifest_dir.mkdir(parents=True, exist_ok=True)

    design = build_design_blueprint()
    design_path = manifest_dir / BLUEPRINT_DESIGN_FILE
    with open(design_path, "w", encoding="utf-8") as f:
        json.dump(design, f, indent=2, ensure_ascii=False)
    print(f"Wrote {design_path}")

    code = build_code_blueprint()
    code_path = manifest_dir / BLUEPRINT_CODE_FILE
    with open(code_path, "w", encoding="utf-8") as f:
        json.dump(code, f, indent=2, ensure_ascii=False)
    print(f"Wrote {code_path}")

    print("Mock calculator project data ready. Run the view with this manifest dir to see Inspector/diagram.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
