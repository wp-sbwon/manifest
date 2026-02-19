#!/usr/bin/env python3
"""
Create blueprint_design.json (fully populated) and blueprint_code.json (from extraction + design-id mapping).

Usage: PYTHONPATH=src python scripts/create_mock_project_data.py [manifest_dir]
Default manifest_dir: tmp/.manifest (from repo root). Project root = manifest_dir.parent.
"""
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from manifest.audit.entity_schema import (
    PROJECT_ROOT_ID,
    empty_entity,
    empty_intent,
    empty_reality,
)
from manifest.audit.entity_validation import normalize_for_schema
from manifest.io.blueprint_io import save_blueprint, save_code_blueprint


def _intent(
    role: str,
    mission: str,
    language: str = "python",
    platform: str = "cli",
    io_model: str = "request_response",
    state_model: str = "stateless",
    rules: Optional[List[str]] = None,
    assertions: Optional[List[str]] = None,
    protocol_input: Optional[List[Dict[str, Any]]] = None,
    protocol_output: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    i = empty_intent()
    i["narrative"] = {"role": role, "mission": mission}
    i["blueprint"] = {"type": "FLOW", "topology": {}}
    i["profile"] = {"language": language, "platform": platform, "io_model": io_model, "state_model": state_model}
    i["governance"] = {"rules": rules or [], "assertions": assertions or []}
    i["protocol"] = {"input": protocol_input or [], "output": protocol_output or []}
    return i


def _reality(
    symbol: str,
    preview: str = "",
    language: str = "python",
    platform: str = "cli",
    dependencies: Optional[List[str]] = None,
    traits: Optional[List[str]] = None,
    protocol_input: Optional[List[Dict[str, Any]]] = None,
    protocol_output: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    r = empty_reality()
    r["symbol"] = symbol
    r["preview"] = preview
    r["profile"] = {"language": language, "platform": platform, "io_model": "", "state_model": ""}
    r["dependencies"] = dependencies or []
    r["traits"] = traits or []
    if protocol_input is not None:
        r["protocol"] = dict(r.get("protocol") or {})
        r["protocol"]["input"] = protocol_input
    if protocol_output is not None:
        r["protocol"] = dict(r.get("protocol") or {})
        r["protocol"]["output"] = protocol_output
    return r


def _make_root() -> Dict[str, Any]:
    intent = _intent(
        "Calculator",
        "CLI calculator: parse args → compute → format → print.",
        rules=["Stateless flow.", "No I/O in arithmetic engine."],
        protocol_input=[{"name": "argv", "type": "list"}],
        protocol_output=[{"name": "stdout", "type": "string"}],
    )
    reality = _reality(
        "main",
        "main.py: parse → engine → format_result → print.",
        protocol_input=[{"name": "argv", "type": "list"}],
        protocol_output=[{"name": "stdout", "type": "string"}],
    )
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
    preview: str = "",
    children: Optional[List[str]] = None,
    contracts: Optional[List[Dict[str, Any]]] = None,
    rules: Optional[List[str]] = None,
    protocol_input: Optional[List[Dict[str, Any]]] = None,
    protocol_output: Optional[List[Dict[str, Any]]] = None,
    traits: Optional[List[str]] = None,
) -> Dict[str, Any]:
    intent = _intent(role, mission, protocol_input=protocol_input, protocol_output=protocol_output, rules=rules)
    reality = _reality(symbol, preview=preview or f"Module: {symbol}", traits=traits)
    return {
        "id": eid,
        "children": children or [],
        "dependencies": [],
        "intent": intent,
        "reality": reality,
        "outgoing_contracts": contracts or [],
    }


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
    data = {
        "version": "1.0",
        "root_id": PROJECT_ROOT_ID,
        "entities": [root, cli, engine, add_ent, sub_ent, mul_ent, output],
    }
    return normalize_for_schema(data)


def _match_extracted_to_design_id(raw_entities: List[Dict[str, Any]], design_id: str) -> Optional[Dict[str, Any]]:
    """Return first raw entity whose id/name matches the design id (e.g. cli -> comp-cli.parser-Parser)."""
    for ent in raw_entities:
        eid = (ent.get("id") or "").strip()
        name = (ent.get("name") or "").strip()
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


def _code_intent(eid: str) -> Dict[str, Any]:
    """Intent for code blueprint. Match design for healthy entities; output differs (deviation)."""
    i = empty_intent()
    # Align profile with design so no spurious profile/language/platform deviations.
    i["profile"] = {"language": "python", "platform": "cli", "io_model": "request_response", "state_model": "stateless"}
    if eid == PROJECT_ROOT_ID:
        i["narrative"] = {"role": "Calculator", "mission": "CLI calculator: parse args → compute → format → print."}
        i["protocol"] = {"input": [{"name": "argv", "type": "list"}], "output": [{"name": "stdout", "type": "string"}]}
        i["governance"] = {"rules": ["Stateless flow.", "No I/O in arithmetic engine."], "assertions": []}
        return i
    if eid == "cli":
        i["narrative"] = {"role": "CLI", "mission": "Parse terminal input into op and two numbers."}
        i["protocol"] = {"input": [{"name": "argv", "type": "list"}], "output": [{"name": "op", "type": "str"}, {"name": "a", "type": "float"}, {"name": "b", "type": "float"}]}
        return i
    if eid == "arithmetic_engine":
        i["narrative"] = {"role": "Arithmetic Engine", "mission": "Pure arithmetic: add, sub, mul (side-effect free)."}
        i["protocol"] = {"input": [{"name": "op", "type": "str"}, {"name": "a", "type": "float"}, {"name": "b", "type": "float"}], "output": [{"name": "result", "type": "float"}]}
        i["governance"] = {"rules": ["No side effects.", "Pure functions only."], "assertions": []}
        return i
    if eid == "add":
        i["narrative"] = {"role": "Add", "mission": "Return a + b."}
        i["protocol"] = {"input": [{"name": "a", "type": "float"}, {"name": "b", "type": "float"}], "output": [{"name": "result", "type": "float"}]}
        i["governance"] = {"rules": ["Pure function."], "assertions": []}
        return i
    if eid == "sub":
        i["narrative"] = {"role": "Sub", "mission": "Return a - b."}
        i["protocol"] = {"input": [{"name": "a", "type": "float"}, {"name": "b", "type": "float"}], "output": [{"name": "result", "type": "float"}]}
        i["governance"] = {"rules": ["Pure function."], "assertions": []}
        return i
    if eid == "output":
        # Deliberate deviation: code has different role so comparator reports mismatch.
        i["narrative"] = {"role": "CLI formatter", "mission": "format_result(value) stub; not called by main."}
        i["protocol"] = {"input": [{"name": "value", "type": "float"}], "output": [{"name": "formatted", "type": "string"}]}
        return i
    return empty_intent()


def build_code_blueprint_from_extraction(project_root: Path, design_blueprint: Dict[str, Any]) -> Dict[str, Any]:
    """Run CodeExtractor; map to design ids; structure from design, reality from extraction, intent from _code_intent."""
    from manifest.audit.code.code_extractor import CodeExtractor

    extractor = CodeExtractor(project_root)
    raw = extractor.extract_project_structure(project_root)
    raw_entities = raw.get("entities") or []
    design_entities = design_blueprint.get("entities") or []

    implemented_ids = {PROJECT_ROOT_ID, "cli", "arithmetic_engine", "add", "sub", "output"}
    code_entities: List[Dict[str, Any]] = []

    for design_ent in design_entities:
        eid = design_ent.get("id") or ""
        if eid == PROJECT_ROOT_ID:
            root_ent = dict(empty_entity(PROJECT_ROOT_ID))
            root_ent["id"] = PROJECT_ROOT_ID
            root_ent["children"] = [c for c in (design_ent.get("children") or []) if c in implemented_ids]
            root_ent["intent"] = _code_intent(PROJECT_ROOT_ID)
            root_ent["reality"] = _reality(
                "main",
                (design_ent.get("reality") or {}).get("preview") or "main.py: parse → engine → print.",
                protocol_input=[{"name": "argv", "type": "list"}],
                protocol_output=[{"name": "stdout", "type": "string"}],
            )
            root_ent["reality"]["profile"] = (design_ent.get("reality") or design_ent.get("intent") or {}).get("profile") or root_ent["reality"].get("profile") or {}
            root_ent["outgoing_contracts"] = design_ent.get("outgoing_contracts") or []
            code_entities.append(root_ent)
            continue
        if eid not in implemented_ids:
            continue
        matched = _match_extracted_to_design_id(raw_entities, eid)
        if matched:
            reality = dict(matched.get("reality") or empty_reality())
            if not reality.get("symbol"):
                reality["symbol"] = matched.get("file") or (design_ent.get("reality") or {}).get("symbol") or ""
            reality["profile"] = (design_ent.get("reality") or design_ent.get("intent") or {}).get("profile") or reality.get("profile") or {}
            if eid == "output":
                reality["protocol"] = (design_ent.get("intent") or {}).get("protocol") or reality.get("protocol") or {}
            # For non-output, align reality with design so no spurious deviations (healthy).
            if eid != "output":
                design_reality = design_ent.get("reality") or {}
                reality["preview"] = design_reality.get("preview") or reality.get("preview") or ""
                reality["protocol"] = design_reality.get("protocol") or reality.get("protocol") or {}
                reality["traits"] = list(design_reality.get("traits") if design_reality.get("traits") is not None else (reality.get("traits") or []))
                reality["dependencies"] = list(design_reality.get("dependencies") if design_reality.get("dependencies") is not None else (reality.get("dependencies") or []))
                reality["symbol"] = design_reality.get("symbol") or reality.get("symbol") or ""
            code_entities.append({
                "id": eid,
                "children": design_ent.get("children") if eid == "arithmetic_engine" else [],
                "dependencies": reality.get("dependencies", []),
                "intent": _code_intent(eid),
                "reality": reality,
                "outgoing_contracts": (design_ent.get("outgoing_contracts") or []) if eid != "output" else (matched.get("outgoing_contracts") or design_ent.get("outgoing_contracts") or []),
            })
        else:
            reality = _reality((design_ent.get("reality") or {}).get("symbol", ""), preview="No matching extracted component.")
            reality["profile"] = (design_ent.get("reality") or design_ent.get("intent") or {}).get("profile") or reality.get("profile") or {}
            if eid == "output":
                reality["protocol"] = (design_ent.get("intent") or {}).get("protocol") or reality.get("protocol") or {}
            if eid != "output":
                design_reality = design_ent.get("reality") or {}
                reality["preview"] = design_reality.get("preview") or reality.get("preview") or ""
                reality["protocol"] = design_reality.get("protocol") or reality.get("protocol") or {}
                reality["traits"] = list(design_reality.get("traits") if design_reality.get("traits") is not None else [])
                reality["dependencies"] = list(design_reality.get("dependencies") if design_reality.get("dependencies") is not None else [])
                reality["symbol"] = design_reality.get("symbol") or reality.get("symbol") or ""
            code_entities.append({
                "id": eid,
                "children": design_ent.get("children") or [],
                "dependencies": reality.get("dependencies", []),
                "intent": _code_intent(eid),
                "reality": reality,
                "outgoing_contracts": design_ent.get("outgoing_contracts") or [],
            })

    result = {
        "version": "1.0",
        "root_id": PROJECT_ROOT_ID,
        "entities": code_entities,
        "source": "code_extraction",
        "from_actual_code": True,
        "ground_truth": True,
        "extraction_method": "ast_parsing",
    }
    return normalize_for_schema(result)


def main() -> int:
    manifest_dir = Path(sys.argv[1]).resolve() if len(sys.argv) >= 2 else REPO / "tmp" / ".manifest"
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
        from manifest.audit.entity_schema import empty_blueprint_root
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
