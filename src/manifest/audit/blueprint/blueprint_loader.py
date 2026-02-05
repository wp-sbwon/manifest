"""
Centralized blueprint loading utility.

Loads blueprint.json and blueprint_code.json in the new entity format
(version, root_id, entities, contracts). Normalizes on load; if legacy
format (components) is detected, runs migration in place.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional

from manifest.audit.entity_schema import empty_blueprint_root
from manifest.audit.entity_validation import is_legacy_format, normalize_for_schema
from manifest.audit.entity_schema import PROJECT_ROOT_ID
from manifest.audit.blueprint_migrate import migrate_file
from manifest.core.logger import get_logger

logger = get_logger(__name__)


def _load_and_normalize(path: Path, is_plan: bool) -> Dict[str, Any]:
    """Load JSON, migrate if legacy, normalize, return new-format dict."""
    if not path.exists():
        out = empty_blueprint_root()
        out["components"] = []
        return out
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error("Error loading %s: %s", path, e, exc_info=True)
        return empty_blueprint_root()
    if is_legacy_format(data):
        logger.info("Legacy format detected in %s; running migration", path)
        if migrate_file(path, is_plan=is_plan):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            logger.warning(
                "Migration did not run or failed; returning empty. Run: python -m manifest.audit.blueprint_migrate --manifest-dir %s",
                path.parent,
            )
            out = empty_blueprint_root()
            out["components"] = []
            return out
    data = normalize_for_schema(data)
    # Backward compat: components = non-root entities with name/file for comparator
    entities = data.get("entities") or []
    components = []
    for e in entities:
        if (e.get("id") or "") == PROJECT_ROOT_ID:
            continue
        c = dict(e)
        if "name" not in c or not c["name"]:
            c["name"] = (
                (c.get("intent") or {}).get("narrative") or {}
            ).get("role") or c.get("id") or ""
        if "file" not in c or not c["file"]:
            c["file"] = ((c.get("reality") or {}).get("symbol") or "")
        components.append(c)
    data["components"] = components
    data["zones"] = data.get("zones") or {}
    return data


class BlueprintLoader:
    """Centralized utility for loading blueprint files.

    Provides static methods for loading blueprint.json and blueprint_code.json
    files. Handles file existence checks, error handling, and optional metadata
    loading. Returns default empty structures if files don't exist or loading fails.
    """

    @staticmethod
    def load_blueprint(
        manifest_dir: Path,
        with_metadata: bool = False,
        default_source: str = "llm_design"
    ) -> Dict[str, Any]:
        """Load blueprint.json (plan). Returns new format: version, root_id, entities, contracts."""
        manifest_dir = Path(manifest_dir)
        blueprint_file = manifest_dir / "blueprint.json"
        data = _load_and_normalize(blueprint_file, is_plan=True)
        if with_metadata:
            from manifest.audit.blueprint.blueprint_metadata import ensure_blueprint_metadata
            data = ensure_blueprint_metadata(data, default_source, False)
        return data

    @staticmethod
    def load_code_blueprint(manifest_dir: Path) -> Dict[str, Any]:
        """Load blueprint_code.json (actual). Returns new format: version, root_id, entities, contracts."""
        manifest_dir = Path(manifest_dir)
        code_blueprint_file = manifest_dir / "blueprint_code.json"
        data = _load_and_normalize(code_blueprint_file, is_plan=False)
        from manifest.audit.blueprint.blueprint_metadata import ensure_blueprint_metadata
        data = ensure_blueprint_metadata(data, "code_extraction", True, "ast_parsing")
        return data

    @staticmethod
    def save_blueprint(
        manifest_dir: Path,
        blueprint_data: Dict[str, Any],
        backup: bool = True
    ) -> bool:
        """
        Save blueprint.json with optional backup.
        Uses save_blueprint_with_metadata for validation and new-format persistence.
        """
        from manifest.audit.blueprint.blueprint_metadata import save_blueprint_with_metadata

        manifest_dir = Path(manifest_dir)
        blueprint_file = manifest_dir / "blueprint.json"

        if backup and blueprint_file.exists():
            backup_file = manifest_dir / "blueprint.json.backup"
            import shutil
            shutil.copy2(blueprint_file, backup_file)
            logger.debug("Created backup: %s", backup_file)

        ok = save_blueprint_with_metadata(
            blueprint_data, blueprint_file, "llm_design", False, "manual"
        )
        if ok:
            from manifest.core.design_history import record_design_save
            record_design_save(manifest_dir, "blueprint", "blueprint.json")
            logger.info("Blueprint saved to %s", blueprint_file)
        return ok
