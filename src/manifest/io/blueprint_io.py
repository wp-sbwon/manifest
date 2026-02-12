"""Load and save blueprint JSON using schema. No metadata or history."""
import json
from pathlib import Path
from typing import Dict, Any

from manifest.schema.entity_validation import normalize_for_schema, validate_blueprint_data
from manifest.schema.entity_schema import empty_blueprint_root
from manifest.schema.manifest_filenames import BLUEPRINT_DESIGN_FILE, BLUEPRINT_CODE_FILE


def save_code_blueprint(manifest_dir: Path, data: Dict[str, Any]) -> bool:
    """Validate and save blueprint_code.json. Returns True if saved."""
    manifest_dir = Path(manifest_dir)
    data = normalize_for_schema(data)
    valid, errors = validate_blueprint_data(data)
    if not valid and errors:
        return False
    manifest_dir.mkdir(parents=True, exist_ok=True)
    path = manifest_dir / BLUEPRINT_CODE_FILE
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def load_blueprint(manifest_dir: Path) -> Dict[str, Any]:
    """Load blueprint_design.json. Returns version, root_id, entities. Empty root if missing."""
    manifest_dir = Path(manifest_dir)
    path = manifest_dir / BLUEPRINT_DESIGN_FILE
    if not path.exists():
        return dict(empty_blueprint_root())
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return dict(empty_blueprint_root())
    return normalize_for_schema(data)


def load_code_blueprint(manifest_dir: Path) -> Dict[str, Any]:
    """Load blueprint_code.json. Returns version, root_id, entities. Empty root if missing."""
    manifest_dir = Path(manifest_dir)
    path = manifest_dir / BLUEPRINT_CODE_FILE
    if not path.exists():
        return dict(empty_blueprint_root())
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return dict(empty_blueprint_root())
    return normalize_for_schema(data)


def save_blueprint(manifest_dir: Path, data: Dict[str, Any]) -> bool:
    """Validate and save blueprint_design.json. Returns True if saved."""
    manifest_dir = Path(manifest_dir)
    data = normalize_for_schema(data)
    valid, errors = validate_blueprint_data(data)
    if not valid and errors:
        return False
    manifest_dir.mkdir(parents=True, exist_ok=True)
    path = manifest_dir / BLUEPRINT_DESIGN_FILE
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False
