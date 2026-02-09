#!/usr/bin/env python3
"""
Create mock project data (blueprint_design.json, blueprint_code.json) using the actual
manifest entity schema. Use so the View app shows non-blank Inspector and diagram.

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
    """Root entity (System Core) with intent and reality filled for display."""
    intent = empty_intent()
    intent["narrative"] = {"role": "System Core", "mission": "Orchestrate the app and backend services."}
    intent["blueprint"] = {"type": "FLOW", "topology": {}}
    intent["protocol"] = {"input": ["config", "env"], "output": ["lifecycle"]}
    intent["profile"] = {"language": "python", "platform": "cli", "io_model": "request_response", "state_model": "stateless"}
    intent["governance"] = {"rules": ["Single source of truth for blueprint"], "assertions": ["Root owns top-level features"]}

    reality = empty_reality()
    reality["symbol"] = "manifest"
    reality["profile"] = {"language": "python", "platform": "cli", "io_model": "", "state_model": ""}
    reality["dependencies"] = []
    reality["traits"] = ["orchestrator"]
    reality["preview"] = "Manifest CLI and view."

    return {
        "id": PROJECT_ROOT_ID,
        "children": ["feature_api", "feature_core"],
        "dependencies": [],
        "intent": intent,
        "reality": reality,
        "outgoing_contracts": [],
    }


def _make_entity(eid: str, role: str, mission: str, symbol: str, children: list = None) -> dict:
    """One entity with intent/reality for Inspector display."""
    intent = empty_intent()
    intent["narrative"] = {"role": role, "mission": mission}
    intent["blueprint"] = {"type": "FLOW", "topology": {}}
    intent["protocol"] = {"input": ["request"], "output": ["response"]}
    intent["profile"] = {"language": "python", "platform": "server", "io_model": "request_response", "state_model": "stateless"}
    intent["governance"] = {"rules": [], "assertions": []}

    reality = empty_reality()
    reality["symbol"] = symbol
    reality["profile"] = {"language": "python", "platform": "server", "io_model": "", "state_model": ""}
    reality["dependencies"] = []
    reality["traits"] = []
    reality["preview"] = f"Module: {symbol}"

    return {
        "id": eid,
        "children": children or [],
        "dependencies": [],
        "intent": intent,
        "reality": reality,
        "outgoing_contracts": [],
    }


def build_design_blueprint() -> dict:
    """Design blueprint (llm_design) with root + two features."""
    root = _make_root_entity()
    api = _make_entity("feature_api", "API Layer", "Expose REST and internal APIs.", "src.app.api")
    core = _make_entity("feature_core", "Core Logic", "Business logic and domain.", "src.app.core")
    data = {
        "version": "1.0",
        "root_id": PROJECT_ROOT_ID,
        "entities": [root, api, core],
    }
    return normalize_for_schema(data)


def build_code_blueprint() -> dict:
    """Code blueprint (code_extraction) same shape for view comparison."""
    design = build_design_blueprint()
    # Add metadata that ensure_blueprint_metadata adds when loading
    design["source"] = "code_extraction"
    design["ground_truth"] = True
    design["from_actual_code"] = True
    design["extraction_method"] = "ast_parsing"
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

    print("Mock project data ready. Run the view with this manifest dir to see Inspector/diagram data.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
