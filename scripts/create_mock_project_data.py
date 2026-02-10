#!/usr/bin/env python3
"""
Create comprehensive mock project data for the calculator app under tmp/, matching
what a real manifest project would have: blueprints (design + code), PRD, tasks,
state, and full root/entity intent so the View shows Mission, Diagram, Inspector,
and Health correctly.

Status mix (planned vs done): The code blueprint includes only a subset of entities
(cli, arithmetic_engine, add, sub). Entities omitted from the code blueprint (output, mul)
show as "planned" in the diagram and header. This demonstrates the design-vs-code
comparison without needing real extraction from tmp/.

In a real project, blueprint_code.json should be produced by the bottom-up pipeline
(run_bottom_up_docs.py / CodeExtractor) from the actual codebase so it is an exact
reflection of the code. This script is for dev/demo only; it does not run code extraction.

Usage:
  PYTHONPATH=src python scripts/create_mock_project_data.py [manifest_dir]
  Default manifest_dir: tmp/.manifest (when run from manifest repo root).
"""
import json
import sys
from pathlib import Path
from datetime import datetime

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


def _ts() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _make_root_entity() -> dict:
    """Root entity: full intent (goals, interface, global_rules, diagram_title) like a real project."""
    intent = empty_intent()
    intent["narrative"] = {
        "role": "Calculator",
        "mission": "CLI calculator: parse args → compute → format → print.",
    }
    intent["goals"] = [
        {"id": "goal-1", "name": "CLI entry", "description": "User can run calculator from terminal with op and two numbers.", "status": "Done"},
        {"id": "goal-2", "name": "Arithmetic", "description": "Support add, subtract, multiply.", "status": "Done"},
        {"id": "goal-3", "name": "Tests", "description": "Unit tests for operations and CLI.", "status": "Planned"},
    ]
    intent["interface"] = "main(argv) → stdout; CLI parses op and numbers; engine computes; output formats."
    intent["global_rules"] = ["Stateless flow.", "No I/O in arithmetic engine."]
    intent["architecture_style"] = "request_response"
    intent["diagram_title"] = "Calculator Flow"
    intent["blueprint"] = {"type": "FLOW", "topology": {}}
    intent["protocol"] = {
        "input": [{"name": "argv", "type": "string"}],
        "output": [{"name": "stdout", "type": "string"}],
    }
    intent["profile"] = {
        "language": "python",
        "platform": "cli",
        "io_model": "request_response",
        "state_model": "stateless",
    }
    intent["governance"] = {"rules": ["Stateless.", "Pure arithmetic only in engine."], "assertions": []}

    reality = empty_reality()
    reality["symbol"] = "main"
    reality["protocol"] = {"input": [], "output": [{"name": "signature", "type": "string"}]}
    reality["profile"] = {"language": "python", "platform": "cli", "io_model": "", "state_model": ""}
    reality["dependencies"] = ["cli.parser", "engine.calculator", "output.formatter"]
    reality["traits"] = ["orchestrator"]
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


def _make_entity(
    eid: str,
    role: str,
    mission: str,
    symbol: str,
    children: list = None,
    contracts: list = None,
    protocol_input: list = None,
    protocol_output: list = None,
    governance_rules: list = None,
    reality_deps: list = None,
    reality_traits: list = None,
) -> dict:
    """One entity with full intent and reality for Inspector and diagram."""
    intent = empty_intent()
    intent["narrative"] = {"role": role, "mission": mission}
    intent["blueprint"] = {"type": "FLOW", "topology": {}}
    intent["protocol"] = {
        "input": protocol_input if protocol_input is not None else [{"name": "args", "type": "any"}],
        "output": protocol_output if protocol_output is not None else [{"name": "result", "type": "any"}],
    }
    intent["profile"] = {
        "language": "python",
        "platform": "cli",
        "io_model": "request_response",
        "state_model": "stateless",
    }
    intent["governance"] = {
        "rules": governance_rules or [],
        "assertions": [],
    }

    reality = empty_reality()
    reality["symbol"] = symbol
    reality["protocol"] = {"input": [], "output": [{"name": "signature", "type": "string"}]}
    reality["profile"] = {"language": "python", "platform": "cli", "io_model": "", "state_model": ""}
    reality["dependencies"] = reality_deps if reality_deps is not None else []
    reality["traits"] = reality_traits if reality_traits is not None else []
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
    """Design blueprint: root + L1 (cli, arithmetic_engine, output) + L2 (add, sub, mul) with full intent and contracts."""
    root = _make_root_entity()

    cli = _make_entity(
        "cli",
        "CLI",
        "Parse terminal input into op and two numbers.",
        "cli.parser",
        children=[],
        contracts=[{"to": "arithmetic_engine", "type": "flow", "file": "cli/parser.py", "symbols": ["parse_args"]}],
        protocol_input=[{"name": "argv", "type": "list"}],
        protocol_output=[{"name": "op", "type": "str"}, {"name": "a", "type": "float"}, {"name": "b", "type": "float"}],
        reality_deps=["argparse"],
        reality_traits=["parser"],
    )

    add_ent = _make_entity(
        "add",
        "Add",
        "Return a + b.",
        "calc.operations.add",
        children=[],
        contracts=[],
        protocol_input=[{"name": "a", "type": "float"}, {"name": "b", "type": "float"}],
        protocol_output=[{"name": "result", "type": "float"}],
        governance_rules=["Pure function."],
        reality_traits=["pure", "O(1)"],
    )
    sub_ent = _make_entity(
        "sub",
        "Sub",
        "Return a - b.",
        "calc.operations.sub",
        children=[],
        contracts=[],
        protocol_input=[{"name": "a", "type": "float"}, {"name": "b", "type": "float"}],
        protocol_output=[{"name": "result", "type": "float"}],
        governance_rules=["Pure function."],
        reality_traits=["pure", "O(1)"],
    )
    mul_ent = _make_entity(
        "mul",
        "Mul",
        "Return a * b.",
        "calc.operations.mul",
        children=[],
        contracts=[],
        protocol_input=[{"name": "a", "type": "float"}, {"name": "b", "type": "float"}],
        protocol_output=[{"name": "result", "type": "float"}],
        governance_rules=["Pure function."],
        reality_traits=["pure", "O(1)"],
    )

    engine = _make_entity(
        "arithmetic_engine",
        "Arithmetic Engine",
        "Pure arithmetic: add, sub, mul (side-effect free).",
        "engine.calculator",
        children=["add", "sub", "mul"],
        contracts=[
            {"to": "add", "type": "dependency", "file": "engine/calculator.py", "symbols": ["add"]},
            {"to": "sub", "type": "dependency", "file": "engine/calculator.py", "symbols": ["sub"]},
            {"to": "mul", "type": "dependency", "file": "engine/calculator.py", "symbols": ["mul"]},
            {"to": "output", "type": "flow", "file": "main.py", "symbols": ["format_result"]},
        ],
        protocol_input=[{"name": "op", "type": "str"}, {"name": "a", "type": "float"}, {"name": "b", "type": "float"}],
        protocol_output=[{"name": "result", "type": "float"}],
        governance_rules=["No side effects.", "Pure functions only."],
        reality_deps=["calc.operations.add", "calc.operations.sub", "calc.operations.mul"],
        reality_traits=["orchestrator", "pure"],
    )

    output = _make_entity(
        "output",
        "Output",
        "Format numeric result for console.",
        "output.formatter",
        children=[],
        contracts=[],
        protocol_input=[{"name": "value", "type": "float"}],
        protocol_output=[{"name": "formatted", "type": "string"}],
        reality_deps=[],
        reality_traits=["formatter"],
    )

    data = {
        "version": "1.0",
        "root_id": PROJECT_ROOT_ID,
        "entities": [root, cli, engine, add_ent, sub_ent, mul_ent, output],
    }
    return normalize_for_schema(data)


# Entity ids present in the code blueprint (implemented). Omitted ids show as "planned" in the view.
_CODE_IMPLEMENTED_IDS = frozenset({
    PROJECT_ROOT_ID,
    "cli",
    "arithmetic_engine",
    "add",
    "sub",
})
# Omitted on purpose so diagram shows a mix: "output" (L1 planned), "mul" (L2 planned).


def build_code_blueprint() -> dict:
    """Code blueprint: only implemented entities; omitted ones show as planned in the view.
    Matches tmp/ layout: main.py, cli/, engine/, calc/operations (add, sub), output/.
    Design has output + mul; we include output in code but omit mul so diagram shows mix of planned/done."""
    design = build_design_blueprint()
    implemented = [e for e in design.get("entities") or [] if (e.get("id") or "") in _CODE_IMPLEMENTED_IDS]
    code = {
        "version": design.get("version", "1.0"),
        "root_id": design.get("root_id", PROJECT_ROOT_ID),
        "entities": implemented,
        "source": "code_extraction",
        "ground_truth": True,
        "from_actual_code": True,
        "extraction_method": "mock_from_tmp",
    }
    for e in code.get("entities") or []:
        if e.get("id") == PROJECT_ROOT_ID:
            e.setdefault("reality", {})["symbol"] = "main"
            e.setdefault("reality", {})["preview"] = "main.py: parse → engine → format_result → print."
            break
    return code


def build_prd() -> dict:
    """PRD for Mission/planning context."""
    return {
        "title": "Calc CLI MVP",
        "sections": [
            {"id": "sec-1", "name": "User can run calculator from terminal"},
            {"id": "sec-2", "name": "Support add, subtract, multiply"},
            {"id": "sec-3", "name": "Unit tests for operations and CLI"},
        ],
    }


def build_tasks() -> dict:
    """Tasks and sprints for sidebar and planning."""
    return {
        "tasks": [
            {
                "id": "task_001",
                "name": "Implement add/sub/mul operations",
                "status": "completed",
                "stage": "done",
                "assigned_agent": None,
                "sprint_id": "sprint-1",
                "mission_id": "mission-1",
                "blueprint_component_ids": ["arithmetic_engine", "add", "sub", "mul"],
                "created_at": _ts(),
                "updated_at": _ts(),
                "progress": {"percentage": 100, "last_update": _ts()},
            },
            {
                "id": "task_002",
                "name": "Add CLI entry (argparse)",
                "status": "completed",
                "stage": "done",
                "assigned_agent": None,
                "sprint_id": "sprint-1",
                "mission_id": "mission-1",
                "blueprint_component_ids": ["cli"],
                "created_at": _ts(),
                "updated_at": _ts(),
                "progress": {"percentage": 100, "last_update": _ts()},
            },
            {
                "id": "task_003",
                "name": "Add unit tests for operations",
                "status": "pending",
                "stage": "planning",
                "assigned_agent": None,
                "sprint_id": "sprint-1",
                "mission_id": "mission-1",
                "blueprint_component_ids": [],
                "created_at": _ts(),
                "updated_at": _ts(),
                "progress": {"percentage": 0, "last_update": _ts()},
            },
        ],
        "sprints": [
            {"id": "sprint-1", "name": "Calc MVP", "goal": "CLI calculator with add/sub/mul", "created_at": _ts()},
        ],
    }


def build_state(manifest_dir: Path) -> dict:
    """State for health metrics and task checklist."""
    return {
        "version": "1.0",
        "mission_tree": {"id": "mission-1", "name": "Calc CLI", "description": "Minimal CLI calculator for dev/demo"},
        "task_checklist": [
            {"id": "task_001", "name": "Implement add/sub/mul operations", "status": "completed", "progress": {"percentage": 100}},
            {"id": "task_002", "name": "Add CLI entry (argparse)", "status": "completed", "progress": {"percentage": 100}},
            {"id": "task_003", "name": "Add unit tests for operations", "status": "pending", "progress": {"percentage": 0}},
        ],
        "active_task_ids": [],
        "chat_history": {},
        "last_action": "create_mock_project_data",
        "timestamp": _ts(),
        "health_metrics": {
            "code_quality": "Excellent",
            "test_coverage": 24,
            "binary_size": "—",
        },
    }


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

    prd_path = manifest_dir / "prd.json"
    with open(prd_path, "w", encoding="utf-8") as f:
        json.dump(build_prd(), f, indent=2, ensure_ascii=False)
    print(f"Wrote {prd_path}")

    tasks_path = manifest_dir / "tasks.json"
    with open(tasks_path, "w", encoding="utf-8") as f:
        json.dump(build_tasks(), f, indent=2, ensure_ascii=False)
    print(f"Wrote {tasks_path}")

    state_path = manifest_dir / "state.json"
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(build_state(manifest_dir), f, indent=2, ensure_ascii=False)
    print(f"Wrote {state_path}")

    print("Mock calculator project data ready. Run the view with this manifest dir to see Inspector/diagram/Mission/Tasks/Health.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
