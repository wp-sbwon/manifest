"""write_prd and write_architecture; validate and save blueprint."""
import json
from pathlib import Path
from typing import Any, Dict, Union

from manifest.io.blueprint_io import save_blueprint
from manifest.audit.entity_validation import normalize_for_schema, validate_blueprint_data
from manifest.audit.entity_schema import empty_blueprint_root, PROJECT_ROOT_ID, empty_entity


def write_architecture(manifest_dir: Path, payload: Union[Dict[str, Any], str]) -> Dict[str, Any]:
    """Validate blueprint payload and save to blueprint_design.json. Returns { "ok": bool, "error": str? }."""
    manifest_dir = Path(manifest_dir)
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as e:
            return {"ok": False, "error": f"Invalid JSON: {e}"}
    if not isinstance(payload, dict):
        return {"ok": False, "error": "Payload must be a blueprint object or JSON string"}
    data = normalize_for_schema(payload)
    valid, errors = validate_blueprint_data(data)
    if not valid and errors:
        return {"ok": False, "error": "; ".join(errors)}
    if save_blueprint(manifest_dir, data):
        return {"ok": True}
    return {"ok": False, "error": "Failed to write file"}


def write_prd(manifest_dir: Path, content: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Create blueprint from mission text and save. Returns { "ok": bool, "error": str? }."""
    manifest_dir = Path(manifest_dir)
    mission = ""
    if isinstance(content, dict):
        mission = (content.get("mission") or content.get("content") or "").strip()
    elif isinstance(content, str):
        mission = content.strip()
    root = empty_blueprint_root()
    root["root_id"] = PROJECT_ROOT_ID
    root["entities"] = [
        {
            **empty_entity(PROJECT_ROOT_ID),
            "intent": {
                "narrative": {"role": "project", "mission": mission or "No mission"},
                "blueprint": {"type": "FLOW", "topology": {}},
                "protocol": {"input": [], "output": []},
                "profile": {"language": "", "platform": "", "io_model": "", "state_model": ""},
                "governance": {"rules": [], "assertions": []},
            },
        }
    ]
    return write_architecture(manifest_dir, root)
