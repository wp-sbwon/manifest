"""
Doc set: top-down and bottom-up blueprints.

Design = blueprint_design.json, code = blueprint_code.json.
"""
from pathlib import Path
from typing import Dict, Any

DOC_SET = ["blueprint"]


def load_top_down(manifest_dir: Path, doc_type: str) -> Dict[str, Any]:
    """Load top-down doc. Only blueprint is supported."""
    if doc_type == "blueprint":
        from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
        return BlueprintLoader.load_blueprint(manifest_dir)
    return {}


def load_bottom_up(manifest_dir: Path, doc_type: str) -> Dict[str, Any]:
    """Load bottom-up doc. Only blueprint is supported."""
    if doc_type == "blueprint":
        from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
        return BlueprintLoader.load_code_blueprint(manifest_dir)
    return {}
