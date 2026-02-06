"""
Doc set: same formatted docs from top-down and bottom-up.

Both processes produce the same set of docs; the synchronizer compares them mechanically.
- Blueprint: top-down = blueprint_design.json, bottom-up = blueprint_code.json (mechanical extraction).
- Intent: top-down = intent.json, bottom-up = intent_code.json (bottom-up via LLM from code).
- Architecture: top-down = architecture.json, bottom-up = architecture_code.json (bottom-up via LLM from code).
"""
import json
from pathlib import Path
from typing import Dict, Any, List

from manifest.core.logger import get_logger

logger = get_logger(__name__)

# Doc types that both top-down and bottom-up produce (same schema)
DOC_SET = ["blueprint", "intent", "architecture"]

# Bottom-up filenames (same schema as top-down; compared mechanically)
BOTTOM_UP_FILES = {
    "blueprint": "blueprint_code.json",
    "intent": "intent_code.json",
    "architecture": "architecture_code.json",
}

# Top-down filenames
TOP_DOWN_FILES = {
    "blueprint": "blueprint_design.json",
    "intent": "intent.json",
    "architecture": "architecture.json",
}


def load_top_down(manifest_dir: Path, doc_type: str) -> Dict[str, Any]:
    """Load top-down doc for a given doc type. Returns empty default if missing."""
    if doc_type == "blueprint":
        from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
        return BlueprintLoader.load_blueprint(manifest_dir)
    if doc_type == "intent":
        path = manifest_dir / TOP_DOWN_FILES["intent"]
        if not path.exists():
            return {"version": "1.0", "sprint": "", "features": []}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Failed to load intent.json: %s", e)
            return {"version": "1.0", "sprint": "", "features": []}
    if doc_type == "architecture":
        from manifest.audit.metadata.architecture_metadata import load_architecture_with_metadata
        return load_architecture_with_metadata(manifest_dir / TOP_DOWN_FILES["architecture"])
    return {}


def load_bottom_up(manifest_dir: Path, doc_type: str) -> Dict[str, Any]:
    """Load bottom-up doc for a given doc type. Returns empty default if missing."""
    filename = BOTTOM_UP_FILES.get(doc_type)
    if not filename:
        return {}
    path = manifest_dir / filename
    if doc_type == "blueprint":
        from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
        return BlueprintLoader.load_code_blueprint(manifest_dir)
    if doc_type == "intent":
        if not path.exists():
            return {"version": "1.0", "sprint": "", "features": []}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Failed to load intent_code.json: %s", e)
            return {"version": "1.0", "sprint": "", "features": []}
    if doc_type == "architecture":
        if not path.exists():
            return {"version": "1.0", "features": [], "requirements": [], "goals": []}
        try:
            from manifest.audit.metadata.architecture_metadata import load_architecture_with_metadata
            return load_architecture_with_metadata(path)
        except Exception as e:
            logger.warning("Failed to load architecture_code.json: %s", e)
            return {"version": "1.0", "features": [], "requirements": [], "goals": []}
    return {}
