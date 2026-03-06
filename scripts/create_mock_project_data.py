#!/usr/bin/env python3
"""
Create blueprint_design.json and blueprint_code.json (unified entity schema).

Usage: PYTHONPATH=src python scripts/create_mock_project_data.py [manifest_dir_or_project_name]
  manifest_dir_or_project_name: path to .manifest dir, or project name for tmp/<name>/.manifest.
Default: tmp/calculator/.manifest. Project root = manifest_dir.parent.
"""
import os
import subprocess
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
    ent["profile"] = {"language": ["python"], "platform": "cli", "io_model": "request_response", "state_model": "stateless"}
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
    assertions: Optional[List[str]] = None,
    protocol_input: Optional[List[Dict[str, Any]]] = None,
    protocol_output: Optional[List[Dict[str, Any]]] = None,
    traits: Optional[List[str]] = None,
) -> Dict[str, Any]:
    ent = dict(empty_entity(eid))
    ent["id"] = eid
    ent["children"] = children or []
    ent["narrative"] = {"role": role, "mission": mission}
    ent["blueprint"] = {"type": "FLOW", "topology": {}}
    ent["profile"] = {"language": ["python"], "platform": "cli", "io_model": "", "state_model": ""}
    ent["governance"] = {"rules": rules or [], "assertions": assertions or []}
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
        assertions=["CLI parses argv into op, a, b."],
    )
    add_ent = _make_entity(
        "add",
        "Add",
        "Return a + b.",
        "engine.calculator",
        preview="engine/calculator.py: add(a, b) → float",
        rules=["Pure function."],
        assertions=["Return a + b."],
        protocol_input=[{"name": "a", "type": "float"}, {"name": "b", "type": "float"}],
        protocol_output=[{"name": "result", "type": "float"}],
        traits=["pure", "O(1)"],
    )
    sub_ent = _make_entity(
        "sub",
        "Sub",
        "Return a - b.",
        "engine.calculator",
        preview="engine/calculator.py: sub(a, b) → float",
        rules=["Pure function."],
        assertions=["Return a - b."],
        protocol_input=[{"name": "a", "type": "float"}, {"name": "b", "type": "float"}],
        protocol_output=[{"name": "result", "type": "float"}],
        traits=["pure", "O(1)"],
    )
    mul_ent = _make_entity(
        "mul",
        "Mul",
        "Return a * b.",
        "engine.calculator",
        preview="Planned.",
        rules=["Pure function."],
        assertions=["Return a * b."],
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
        assertions=["Dispatch op to correct arithmetic function."],
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
        assertions=["Format numeric result for console."],
    )
    return normalize_for_schema({
        "version": "1.0",
        "root_id": PROJECT_ROOT_ID,
        "entities": [root, cli, engine, add_ent, sub_ent, mul_ent, output],
    })


def _build_code_blueprint_from_design_and_extraction(
    project_root: Path, manifest_dir: Path, design_blueprint: Dict[str, Any]
) -> Dict[str, Any]:
    """Run extraction, then build blueprint_code via deterministic merge (exact ID)."""
    from manifest.audit.code.code_blueprint_builder import build_code_blueprint
    from manifest.audit.code.code_extractor import CodeExtractor

    extractor = CodeExtractor(project_root)
    extracted = extractor.extract_project_structure(project_root)
    code = build_code_blueprint(project_root, manifest_dir, design_blueprint, extracted)
    code["source"] = "code_extraction"
    code["ground_truth"] = True
    code["extraction_method"] = "ast_parsing"
    code = normalize_for_schema(code)
    entities = code.get("entities") or []
    orphan = dict(empty_entity("comp-extra-stub"))
    orphan["id"] = "comp-extra-stub"
    orphan["symbol"] = "extra/stub.py"
    orphan["children"] = []
    orphan["dependencies"] = []
    orphan["outgoing_contracts"] = []
    entities.append(orphan)
    root_ent = next((e for e in entities if (e.get("id") or "") == PROJECT_ROOT_ID), None)
    if root_ent is not None:
        root_ent["children"] = list(root_ent.get("children") or []) + ["comp-extra-stub"]
    for e in entities:
        if (e.get("id") or "") == "cli":
            proto = e.get("protocol") or {}
            e["protocol"] = {"input": [{"name": "argv_list", "type": "list"}], "output": proto.get("output", [])}
            break
    code["entities"] = entities
    return code


def main() -> int:
    if len(sys.argv) >= 2:
        arg = sys.argv[1].strip()
        if "/" in arg or "\\" in arg:
            manifest_dir = Path(arg).resolve()
            project_root = manifest_dir.parent
        else:
            manifest_dir = (REPO / "tmp" / arg / ".manifest").resolve()
            project_root = REPO / "tests" / "fixtures" / arg if (REPO / "tests" / "fixtures" / arg).is_dir() else manifest_dir.parent
    else:
        manifest_dir = REPO / "tmp" / "calculator" / ".manifest"
        project_root = REPO / "tests" / "fixtures" / "calculator"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    if not project_root.is_dir():
        project_root = manifest_dir.parent

    design = build_design_blueprint()
    if not save_blueprint(manifest_dir, design):
        print("Failed to write blueprint_design.json", file=sys.stderr)
        return 1
    print(f"Wrote {manifest_dir / 'blueprint_design.json'}")

    code = _build_code_blueprint_from_design_and_extraction(project_root, manifest_dir, design)
    if not save_code_blueprint(manifest_dir, code):
        print("Failed to write blueprint_code.json", file=sys.stderr)
        return 1
    print(f"Wrote {manifest_dir / 'blueprint_code.json'}")

    try:
        from manifest.view.entity_model import get_entities_for_view
        get_entities_for_view(manifest_dir, write_view=True)
        print(f"Wrote {manifest_dir / 'blueprint_view.json'}")
    except Exception as e:
        print(f"Warning: failed to write blueprint_view.json: {e}", file=sys.stderr)

    if "calculator" in str(manifest_dir):
        _write_calculator_state(manifest_dir)

    tests_dir = project_root / "tests"
    try:
        r = subprocess.run(
            [sys.executable, str(REPO / "bin" / "generate_test_stubs.py"), "--manifest-dir", str(manifest_dir), "--tests-dir", str(tests_dir)],
            cwd=str(REPO),
            env={**os.environ, "PYTHONPATH": str(REPO / "src")},
            capture_output=True,
            text=True,
            timeout=30,
        )
        if r.returncode == 0:
            print(f"Wrote test stubs under {tests_dir}")
        elif r.stderr:
            print(f"Warning: generate_test_stubs: {r.stderr.strip()}", file=sys.stderr)
    except Exception as e:
        print(f"Warning: failed to generate test stubs: {e}", file=sys.stderr)

    # Copy test files to manifest_dir.parent/tests/ so the view's test_result_collector finds them.
    import shutil
    runtime_tests_dir = manifest_dir.parent / "tests"
    if runtime_tests_dir.resolve() != tests_dir.resolve():
        runtime_tests_dir.mkdir(parents=True, exist_ok=True)
        for tf in tests_dir.glob("*.py"):
            shutil.copy2(tf, runtime_tests_dir / tf.name)
        init_file = runtime_tests_dir / "__init__.py"
        if not init_file.exists():
            init_file.write_text("", encoding="utf-8")

    # Copy source files from fixture to runtime dir for consistency.
    fixture_root = REPO / "tests" / "fixtures" / "calculator"
    runtime_root = manifest_dir.parent
    for subdir in ("cli", "engine", "output"):
        src_dir = fixture_root / subdir
        dst_dir = runtime_root / subdir
        if src_dir.is_dir():
            if dst_dir.exists():
                shutil.rmtree(dst_dir)
            shutil.copytree(src_dir, dst_dir)
    main_src = fixture_root / "main.py"
    if main_src.exists():
        shutil.copy2(main_src, runtime_root / "main.py")

    # Remove stale root-level blueprint_view.json if it exists (real one is in .manifest/).
    stale_view = runtime_root / "blueprint_view.json"
    if stale_view.exists():
        stale_view.unlink()

    print("Mock project data ready. Run View with this manifest dir to see Diagram and Health.")
    return 0


def _write_calculator_state(manifest_dir: Path) -> None:
    import json
    from datetime import datetime, timezone
    state = {
        "version": "1.0",
        "health_metrics": None,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    state_file = manifest_dir / "state.json"
    try:
        state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        print(f"Wrote {state_file}")
    except Exception as e:
        print(f"Warning: failed to write state.json: {e}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
