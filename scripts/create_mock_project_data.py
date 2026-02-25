#!/usr/bin/env python3
"""
Create blueprint_design.json and blueprint_code.json (unified entity schema).

Usage: PYTHONPATH=src python scripts/create_mock_project_data.py [manifest_dir_or_project_name]
  manifest_dir_or_project_name: path to .manifest dir, or project name for tmp/<name>/.manifest.
Default: tmp/calculator/.manifest. Project root = manifest_dir.parent.
"""
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_entity
from manifest.audit.entity_validation import normalize_for_schema
from manifest.io.blueprint_io import save_blueprint, save_code_blueprint


def _make_root() -> Dict[str, Any]:
    ent = dict(empty_entity(PROJECT_ROOT_ID))
    ent["children"] = ["cli", "arithmetic_engine", "output"]
    ent["narrative"] = {"role": "Calculator", "mission": "CLI calculator: parse args → compute → format → print."}
    ent["blueprint"] = {"type": "FLOW", "topology": {}}
    ent["profile"] = {"language": "python", "platform": "cli", "io_model": "request_response", "state_model": "stateless"}
    ent["governance"] = {"rules": ["Stateless flow.", "No I/O in arithmetic engine."], "assertions": []}
    ent["protocol"] = {"input": [{"name": "argv", "type": "list"}], "output": [{"name": "stdout", "type": "string"}]}
    ent["symbol"] = "main"
    ent["preview"] = "main.py: parse → engine → format_result → print."
    ent["outgoing_contracts"] = [
        {"to": "cli", "type": "flow", "file": "main.py", "symbols": ["parse_args"]},
        {"to": "arithmetic_engine", "type": "flow", "file": "main.py", "symbols": ["compute"]},
        {"to": "output", "type": "flow", "file": "main.py", "symbols": ["format_result"]},
    ]
    return ent


def _make_entity(
    eid: str,
    role: str,
    mission: str,
    symbol: str,
    preview: str = "",
    children: Optional[List[str]] = None,
    contracts: Optional[List[Dict[str, Any]]] = None,
    rules: Optional[List[str]] = None,
    protocol_input: Optional[List[Dict[str, Any]]] = None,
    protocol_output: Optional[List[Dict[str, Any]]] = None,
    traits: Optional[List[str]] = None,
) -> Dict[str, Any]:
    ent = dict(empty_entity(eid))
    ent["id"] = eid
    ent["children"] = children or []
    ent["narrative"] = {"role": role, "mission": mission}
    ent["blueprint"] = {"type": "FLOW", "topology": {}}
    ent["profile"] = {"language": "python", "platform": "cli", "io_model": "", "state_model": ""}
    ent["governance"] = {"rules": rules or [], "assertions": []}
    ent["protocol"] = {"input": protocol_input or [], "output": protocol_output or []}
    ent["symbol"] = symbol
    ent["preview"] = preview or f"Module: {symbol}"
    ent["traits"] = traits or []
    ent["outgoing_contracts"] = contracts or []
    return ent


def build_design_blueprint() -> Dict[str, Any]:
    root = _make_root()
    cli = _make_entity(
        "cli",
        "CLI",
        "Parse terminal input into op and two numbers.",
        "cli.parser",
        preview="cli/parser.py: Parser.parse() → (op, a, b)",
        contracts=[{"to": "arithmetic_engine", "type": "flow", "file": "cli/parser.py", "symbols": ["parse_args"]}],
        protocol_input=[{"name": "argv", "type": "list"}],
        protocol_output=[{"name": "op", "type": "str"}, {"name": "a", "type": "float"}, {"name": "b", "type": "float"}],
    )
    add_ent = _make_entity(
        "add",
        "Add",
        "Return a + b.",
        "calc.operations.add",
        preview="engine/calculator.py: add(a, b) → float",
        rules=["Pure function."],
        protocol_input=[{"name": "a", "type": "float"}, {"name": "b", "type": "float"}],
        protocol_output=[{"name": "result", "type": "float"}],
        traits=["pure", "O(1)"],
    )
    sub_ent = _make_entity(
        "sub",
        "Sub",
        "Return a - b.",
        "calc.operations.sub",
        preview="engine/calculator.py: sub(a, b) → float",
        rules=["Pure function."],
        protocol_input=[{"name": "a", "type": "float"}, {"name": "b", "type": "float"}],
        protocol_output=[{"name": "result", "type": "float"}],
        traits=["pure", "O(1)"],
    )
    mul_ent = _make_entity(
        "mul",
        "Mul",
        "Return a * b.",
        "calc.operations.mul",
        preview="Planned.",
        rules=["Pure function."],
        protocol_input=[{"name": "a", "type": "float"}, {"name": "b", "type": "float"}],
        protocol_output=[{"name": "result", "type": "float"}],
        traits=["pure", "O(1)"],
    )
    engine = _make_entity(
        "arithmetic_engine",
        "Arithmetic Engine",
        "Pure arithmetic: add, sub, mul (side-effect free).",
        "engine.calculator",
        preview="engine/calculator.py: add, sub, mul",
        children=["add", "sub", "mul"],
        contracts=[
            {"to": "add", "type": "dependency", "file": "engine/calculator.py", "symbols": ["add"]},
            {"to": "sub", "type": "dependency", "file": "engine/calculator.py", "symbols": ["sub"]},
            {"to": "mul", "type": "dependency", "file": "engine/calculator.py", "symbols": ["mul"]},
            {"to": "output", "type": "flow", "file": "main.py", "symbols": ["format_result"]},
        ],
        protocol_input=[{"name": "op", "type": "str"}, {"name": "a", "type": "float"}, {"name": "b", "type": "float"}],
        protocol_output=[{"name": "result", "type": "float"}],
        rules=["No side effects.", "Pure functions only."],
    )
    output = _make_entity(
        "output",
        "Output",
        "Format numeric result for console.",
        "output.formatter",
        preview="output/formatter.py: format_result(value) → str",
        protocol_input=[{"name": "value", "type": "float"}],
        protocol_output=[{"name": "formatted", "type": "string"}],
        traits=["formatter"],
    )
    return normalize_for_schema({
        "version": "1.0",
        "root_id": PROJECT_ROOT_ID,
        "entities": [root, cli, engine, add_ent, sub_ent, mul_ent, output],
    })


def _match_extracted_to_design_id(raw_entities: List[Dict[str, Any]], design_id: str) -> Optional[Dict[str, Any]]:
    for ent in raw_entities:
        eid = (ent.get("id") or "").strip()
        name = (ent.get("narrative") or {}).get("role") or (ent.get("symbol") or "").strip()
        if eid == PROJECT_ROOT_ID:
            continue
        eid_lower = eid.lower()
        name_lower = name.lower()
        if design_id == "cli" and ("cli.parser" in eid_lower or "parser" in name_lower):
            return ent
        if design_id == "arithmetic_engine":
            if "engine" in eid_lower and "calculator" in eid_lower and "-add" not in eid and "-sub" not in eid and "-mul" not in eid:
                return ent
            continue
        if design_id == "add" and (eid_lower.endswith("-add") or name_lower == "add"):
            return ent
        if design_id == "sub" and (eid_lower.endswith("-sub") or name_lower == "sub"):
            return ent
        if design_id == "mul" and (eid_lower.endswith("-mul") or name_lower == "mul"):
            return ent
        if design_id == "output" and ("output" in eid_lower or "formatter" in eid_lower or "format_result" in name_lower):
            return ent
    return None


def _code_entity_overrides(eid: str, design_ent: Dict[str, Any]) -> Dict[str, Any]:
    """Overrides for code blueprint; output entity has different narrative (deviation)."""
    overrides: Dict[str, Any] = {}
    if eid == PROJECT_ROOT_ID:
        overrides["narrative"] = {"role": "Calculator", "mission": "CLI calculator: parse args → compute → format → print."}
        overrides["protocol"] = {"input": [{"name": "argv", "type": "list"}], "output": [{"name": "stdout", "type": "string"}]}
        overrides["governance"] = {"rules": ["Stateless flow.", "No I/O in arithmetic engine."], "assertions": []}
        return overrides
    if eid == "output":
        overrides["narrative"] = {"role": "CLI formatter", "mission": "format_result(value) stub; not called by main."}
        overrides["protocol"] = {"input": [{"name": "value", "type": "float"}], "output": [{"name": "formatted", "type": "string"}]}
        return overrides
    design_narrative = design_ent.get("narrative") or {}
    design_protocol = design_ent.get("protocol") or {}
    design_governance = design_ent.get("governance") or {}
    overrides["narrative"] = {"role": design_narrative.get("role", ""), "mission": design_narrative.get("mission", "")}
    overrides["protocol"] = dict(design_protocol)
    overrides["governance"] = dict(design_governance)
    return overrides


def build_code_blueprint_from_extraction(project_root: Path, design_blueprint: Dict[str, Any]) -> Dict[str, Any]:
    """Run CodeExtractor; merge with design ids/structure; unified entity schema."""
    from manifest.audit.code.code_blueprint_builder import merge_design_and_extraction

    from manifest.audit.code.code_extractor import CodeExtractor

    extractor = CodeExtractor(project_root)
    raw = extractor.extract_project_structure(project_root)
    code_draft = merge_design_and_extraction(design_blueprint, raw)
    design_entities = {e.get("id"): e for e in (design_blueprint.get("entities") or []) if e.get("id")}
    implemented_ids = {PROJECT_ROOT_ID, "cli", "arithmetic_engine", "add", "sub", "output"}
    code_entities = list(code_draft.get("entities") or [])
    for ent in code_entities:
        eid = ent.get("id")
        if eid not in implemented_ids:
            continue
        design_ent = design_entities.get(eid) or {}
        overrides = _code_entity_overrides(eid, design_ent)
        for k, v in overrides.items():
            ent[k] = v
        if eid != PROJECT_ROOT_ID and eid == "output":
            continue
        if eid != "output":
            ent["preview"] = (design_ent.get("preview") or ent.get("preview") or "")
            ent["protocol"] = dict(design_ent.get("protocol") or ent.get("protocol") or {})
            ent["traits"] = list(design_ent.get("traits") if (design_ent.get("traits") or []) else (ent.get("traits") or []))
            ent["dependencies"] = list(design_ent.get("dependencies") if (design_ent.get("dependencies") or []) else (ent.get("dependencies") or []))
            ent["symbol"] = (design_ent.get("symbol") or ent.get("symbol") or "")

    return normalize_for_schema({
        "version": "1.0",
        "root_id": PROJECT_ROOT_ID,
        "entities": code_entities,
        "source": "code_extraction",
        "ground_truth": True,
        "extraction_method": "ast_parsing",
    })


def main() -> int:
    if len(sys.argv) >= 2:
        arg = sys.argv[1].strip()
        if "/" in arg or "\\" in arg:
            manifest_dir = Path(arg).resolve()
        else:
            manifest_dir = (REPO / "tmp" / arg / ".manifest").resolve()
    else:
        manifest_dir = REPO / "tmp" / "calculator" / ".manifest"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    project_root = manifest_dir.parent

    design = build_design_blueprint()
    if not save_blueprint(manifest_dir, design):
        print("Failed to write blueprint_design.json", file=sys.stderr)
        return 1
    print(f"Wrote {manifest_dir / 'blueprint_design.json'}")

    try:
        code = build_code_blueprint_from_extraction(project_root, design)
    except Exception as e:
        code = normalize_for_schema({
            "version": "1.0",
            "root_id": PROJECT_ROOT_ID,
            "entities": [dict(empty_entity(PROJECT_ROOT_ID))],
        })
        print(f"Extraction failed ({e}), wrote minimal blueprint_code.json", file=sys.stderr)
    if not save_code_blueprint(manifest_dir, code):
        print("Failed to write blueprint_code.json", file=sys.stderr)
        return 1
    print(f"Wrote {manifest_dir / 'blueprint_code.json'}")

    try:
        from manifest.view.entity_model import get_entities_for_view
        get_entities_for_view(manifest_dir)
        print(f"Wrote {manifest_dir / 'blueprint_view.json'}")
    except Exception as e:
        print(f"Warning: failed to write blueprint_view.json: {e}", file=sys.stderr)

    print("Mock project data ready. Run View with this manifest dir to see Diagram and Health.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
