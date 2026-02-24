"""Load top-down (design) and bottom-up (code) blueprints."""
from pathlib import Path
from typing import Dict, Any


def _load_blueprint_doc(manifest_dir: Path, top_down: bool) -> Dict[str, Any]:
    """Load design (top_down=True) or code (top_down=False) blueprint."""
    from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
    if top_down:
        return BlueprintLoader.load_blueprint(manifest_dir)
    return BlueprintLoader.load_code_blueprint(manifest_dir)


def load_top_down(manifest_dir: Path, doc_type: str) -> Dict[str, Any]:
    """Load top-down (design) blueprint when doc_type is 'blueprint'."""
    if doc_type == "blueprint":
        return _load_blueprint_doc(manifest_dir, top_down=True)
    return {}


def load_bottom_up(manifest_dir: Path, doc_type: str) -> Dict[str, Any]:
    """Load bottom-up (code) blueprint when doc_type is 'blueprint'."""
    if doc_type == "blueprint":
        return _load_blueprint_doc(manifest_dir, top_down=False)
    return {}
