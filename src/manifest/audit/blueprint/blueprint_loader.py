"""
Load blueprint JSON; normalize and derive contracts from entities.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional

from manifest.audit.blueprint.manifest_filenames import BLUEPRINT_DESIGN_FILE, BLUEPRINT_CODE_FILE
from manifest.audit.entity_schema import empty_blueprint_root
from manifest.audit.entity_validation import normalize_for_schema
from manifest.audit.entity_schema import PROJECT_ROOT_ID
from manifest.core.logger import get_logger

logger = get_logger(__name__)


def _load_and_normalize(path: Path, is_plan: bool) -> Dict[str, Any]:
    """Load JSON, normalize, attach contracts and components from entities."""
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
    data = normalize_for_schema(data)
    entities = data.get("entities") or []
    contracts = []
    for e in entities:
        eid = e.get("id") or ""
        for oc in e.get("outgoing_contracts") or []:
            if not isinstance(oc, dict):
                continue
            contracts.append({
                "from": eid,
                "to": oc.get("to") or "",
                "type": oc.get("type") or "dependency",
                "file": oc.get("file") or "",
                "symbols": list(oc.get("symbols") or []),
            })
    data["contracts"] = contracts
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

    Provides static methods for loading blueprint_design.json and blueprint_code.json.
    Handles file existence checks, error handling, and optional metadata loading.
    """

    @staticmethod
    def load_blueprint(
        manifest_dir: Path,
        with_metadata: bool = False,
        default_source: str = "llm_design"
    ) -> Dict[str, Any]:
        """Load blueprint_design.json (from design). Returns version, root_id, entities, contracts."""
        manifest_dir = Path(manifest_dir)
        blueprint_file = manifest_dir / BLUEPRINT_DESIGN_FILE
        data = _load_and_normalize(blueprint_file, is_plan=True)
        if with_metadata:
            from manifest.audit.blueprint.blueprint_metadata import ensure_blueprint_metadata
            data = ensure_blueprint_metadata(data, default_source, False)
        return data

    @staticmethod
    def load_code_blueprint(manifest_dir: Path) -> Dict[str, Any]:
        """Load blueprint_code.json (from code). Returns version, root_id, entities, contracts."""
        manifest_dir = Path(manifest_dir)
        code_blueprint_file = manifest_dir / BLUEPRINT_CODE_FILE
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
        Save blueprint_design.json with optional backup.
        Uses save_blueprint_with_metadata for validation and entity-format persistence.
        """
        from manifest.audit.blueprint.blueprint_metadata import save_blueprint_with_metadata

        manifest_dir = Path(manifest_dir)
        blueprint_file = manifest_dir / BLUEPRINT_DESIGN_FILE

        if backup and blueprint_file.exists():
            backup_file = manifest_dir / (BLUEPRINT_DESIGN_FILE + ".backup")
            import shutil
            shutil.copy2(blueprint_file, backup_file)
            logger.debug("Created backup: %s", backup_file)

        ok = save_blueprint_with_metadata(
            blueprint_data, blueprint_file, "llm_design", False, "manual"
        )
        if ok:
            from manifest.core.design_history import record_design_save
            record_design_save(manifest_dir, "blueprint", BLUEPRINT_DESIGN_FILE)
            logger.info("Blueprint saved to %s", blueprint_file)
        return ok
