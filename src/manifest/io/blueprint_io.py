"""Load and save blueprint JSON using schema."""
import json
from pathlib import Path
from typing import Dict, Any

from manifest.audit.entity_validation import normalize_for_schema, validate_blueprint_data
from manifest.audit.entity_schema import empty_blueprint_root
from manifest.audit.blueprint.manifest_filenames import BLUEPRINT_DESIGN_FILE, BLUEPRINT_CODE_FILE
from manifest.io.json_io import read_json_or_default


def _save_blueprint_to_path(manifest_dir: Path, data: Dict[str, Any], filename: str) -> bool:
    """Validate, then write normalized blueprint JSON to manifest_dir / filename."""
    manifest_dir = Path(manifest_dir)
    data = normalize_for_schema(data)
    valid, errors = validate_blueprint_data(data)
    if not valid and errors:
        return False
    manifest_dir.mkdir(parents=True, exist_ok=True)
    path = manifest_dir / filename
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def save_blueprint(manifest_dir: Path, data: Dict[str, Any]) -> bool:
    """Validate and save blueprint_design.json."""
    return _save_blueprint_to_path(manifest_dir, data, BLUEPRINT_DESIGN_FILE)


def save_code_blueprint(manifest_dir: Path, data: Dict[str, Any]) -> bool:
    """Validate and save blueprint_code.json."""
    return _save_blueprint_to_path(manifest_dir, data, BLUEPRINT_CODE_FILE)


def load_blueprint(manifest_dir: Path) -> Dict[str, Any]:
    """Load blueprint_design.json; empty root if missing."""
    path = Path(manifest_dir) / BLUEPRINT_DESIGN_FILE
    return read_json_or_default(path, empty_blueprint_root(), normalize=normalize_for_schema)


def load_code_blueprint(manifest_dir: Path) -> Dict[str, Any]:
    """Load blueprint_code.json; empty root if missing."""
    path = Path(manifest_dir) / BLUEPRINT_CODE_FILE
    return read_json_or_default(path, empty_blueprint_root(), normalize=normalize_for_schema)
