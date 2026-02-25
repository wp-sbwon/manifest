"""PRD and blueprint I/O: write_prd, write_architecture, create_blueprint_from_prd."""
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, Union

from manifest.io.blueprint_io import save_blueprint
from manifest.io.prd_io import load_prd, save_prd
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
    """Save PRD to prd.json (fixed format: title, mission, sections). Returns { "ok": bool, "error": str? }."""
    manifest_dir = Path(manifest_dir)
    if isinstance(content, str):
        content = {"title": "", "mission": content.strip(), "sections": []}
    if not isinstance(content, dict):
        return {"ok": False, "error": "Content must be a string or dict with title, mission, sections"}
    if save_prd(manifest_dir, content):
        return {"ok": True}
    return {"ok": False, "error": "Failed to write prd.json"}


def create_blueprint_from_prd(manifest_dir: Path, project_root: Optional[Path] = None) -> Dict[str, Any]:
    """Build blueprint_design.json from prd.json and start layer-by-layer expansion.

    Loads PRD, builds root entity, saves blueprint_design.json, spawns layer writer for layer 0.
    Returns { "ok": bool, "error": str?, "message": str? }.
    """
    from manifest.core.logger import get_logger
    logger = get_logger(__name__)

    manifest_dir = Path(manifest_dir)
    project_root = Path(project_root) if project_root is not None else manifest_dir.parent

    prd = load_prd(manifest_dir)
    mission = (prd.get("mission") or "").strip() or "No mission"
    title = (prd.get("title") or "").strip() or "Project"

    root = empty_blueprint_root()
    root["root_id"] = PROJECT_ROOT_ID
    root["entities"] = [
        {
            **empty_entity(PROJECT_ROOT_ID),
            "intent": {
                "narrative": {"role": "project", "mission": mission},
                "blueprint": {"type": "FLOW", "topology": {}},
                "protocol": {"input": [], "output": []},
                "profile": {"language": "", "platform": "", "io_model": "", "state_model": ""},
                "governance": {"rules": [], "assertions": []},
            },
        }
    ]
    if not save_blueprint(manifest_dir, root):
        return {"ok": False, "error": "Failed to write blueprint_design.json"}

    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    script = repo_root / "bin" / "run_doc_layer_writer.py"
    if not script.exists():
        return {"ok": True, "message": "Blueprint created; run bin/run_doc_layer_writer.py for layer 0 to expand"}

    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    try:
        subprocess.Popen(
            [
                "python",
                str(script),
                "--manifest-dir", str(manifest_dir),
                "--parent", PROJECT_ROOT_ID,
                "--layer", "0",
            ],
            cwd=str(project_root),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        logger.warning("Failed to spawn layer writer: %s", e)
    return {"ok": True, "message": "Blueprint created; layer-by-layer expansion started"}
