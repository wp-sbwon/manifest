"""
Design history for PRD and blueprint.

Records a versioned history when design docs (prd.json, blueprint_design.json)
are saved so the View can display it alongside Git history.
"""
import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from manifest.core.logger import get_logger

logger = get_logger(__name__)

DESIGN_HISTORY_FILE = "design_history.json"
MAX_ENTRIES = 200


def _default_history() -> Dict[str, Any]:
    return {"entries": [], "version": "1.0"}


def get_design_history(manifest_dir: Path) -> List[Dict[str, Any]]:
    """Return design history entries (newest first) for the View.

    Args:
        manifest_dir: Path to the .manifest directory.

    Returns:
        List of entries, each with keys: doc, path, timestamp. Empty list if no history.
    """
    path = Path(manifest_dir) / DESIGN_HISTORY_FILE
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        entries = data.get("entries", [])
        return list(reversed(entries[-MAX_ENTRIES:]))
    except Exception as e:
        logger.debug("Could not load design history: %s", e)
        return []


def record_design_save(manifest_dir: Path, doc: str, path_relative: str) -> None:
    """Append an entry to design history when a design doc is saved.

    Args:
        manifest_dir: Path to the .manifest directory.
        doc: Document name (e.g. "prd", "blueprint").
        path_relative: Relative path of the file (e.g. "prd.json").
    """
    manifest_dir = Path(manifest_dir)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    history_path = manifest_dir / DESIGN_HISTORY_FILE
    data = _default_history()
    if history_path.exists():
        try:
            with open(history_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.debug("Could not load design history file: %s", e)
    entries = data.get("entries", [])
    entries.append({
        "doc": doc,
        "path": path_relative,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })
    if len(entries) > MAX_ENTRIES:
        entries = entries[-MAX_ENTRIES:]
    data["entries"] = entries
    try:
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning("Could not write design history: %s", e)
