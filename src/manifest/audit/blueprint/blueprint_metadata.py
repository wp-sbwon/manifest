"""
Blueprint Metadata Utilities - Ensures blueprint JSON files have proper metadata.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from manifest.core.logger import get_logger

logger = get_logger(__name__)


def ensure_blueprint_metadata(blueprint: Dict[str, Any], source: str,
                              ground_truth: bool, extraction_method: str = None) -> Dict[str, Any]:
    """
    Ensure blueprint has required metadata fields.

    Args:
        blueprint: Blueprint dictionary
        source: "code_extraction" | "llm_design" | "llm_architecture"
        ground_truth: True if ground truth, False otherwise
        extraction_method: "ast_parsing" | "llm_inference" | "manual"

    Returns:
        Blueprint with metadata ensured
    """
    if "version" not in blueprint:
        blueprint["version"] = "1.0"

    blueprint["source"] = source
    blueprint["from_actual_code"] = ground_truth
    blueprint["ground_truth"] = ground_truth  # backward compatibility

    if "last_updated" not in blueprint:
        blueprint["last_updated"] = datetime.utcnow().isoformat()

    if extraction_method:
        blueprint["extraction_method"] = extraction_method
    elif "extraction_method" not in blueprint:
        if source == "code_extraction":
            blueprint["extraction_method"] = "ast_parsing"
        elif source in ["llm_design", "llm_architecture"]:
            blueprint["extraction_method"] = "llm_inference"
        else:
            blueprint["extraction_method"] = "manual"

    return blueprint


def load_blueprint_with_metadata(blueprint_file: Path, default_source: str = "llm_design",
                                 default_ground_truth: bool = False) -> Dict[str, Any]:
    """
    Load blueprint file and ensure it has metadata.

    Args:
        blueprint_file: Path to blueprint JSON file
        default_source: Default source if not present
        default_ground_truth: Default ground_truth if not present

    Returns:
        Blueprint dictionary with metadata
    """
    if not blueprint_file.exists():
        return {
            "version": "1.0",
            "root_id": "",
            "source": default_source,
            "ground_truth": default_ground_truth,
            "last_updated": datetime.utcnow().isoformat(),
            "extraction_method": "llm_inference" if default_source.startswith("llm") else "ast_parsing",
            "entities": [],
            "contracts": [],
            "components": [],
            "zones": {},
        }

    try:
        with open(blueprint_file, "r", encoding="utf-8") as f:
            blueprint = json.load(f)

        # Ensure metadata
        if blueprint_file.name == "blueprint_code.json":
            blueprint = ensure_blueprint_metadata(blueprint, "code_extraction", True, "ast_parsing")
        else:
            blueprint = ensure_blueprint_metadata(blueprint, default_source, default_ground_truth)

        return blueprint
    except Exception:
        # Return default blueprint with metadata
        return {
            "version": "1.0",
            "root_id": "",
            "source": default_source,
            "ground_truth": default_ground_truth,
            "last_updated": datetime.utcnow().isoformat(),
            "extraction_method": "llm_inference" if default_source.startswith("llm") else "ast_parsing",
            "entities": [],
            "contracts": [],
            "components": [],
            "zones": {},
        }


def save_blueprint_with_metadata(blueprint: Dict[str, Any], blueprint_file: Path,
                                 source: str, ground_truth: bool,
                                 extraction_method: str = None) -> bool:
    """
    Save blueprint file with metadata.

    When saving design blueprint (blueprint.json), validates and optionally
    aligns component identity (id/name) against blueprint_code.json so
    top-down and bottom-up docs are comparable for deviation calculation.

    Args:
        blueprint: Blueprint dictionary
        blueprint_file: Path to save blueprint
        source: Source type
        ground_truth: Whether it's ground truth
        extraction_method: Extraction method

    Returns:
        True if successful, False otherwise
    """
    try:
        # Migrate legacy (components) to new format (entities) before save
        from manifest.audit.entity_validation import is_legacy_format
        from manifest.audit.blueprint_migrate import migrate_blueprint_data
        from manifest.audit.entity_validation import validate_blueprint_data

        if is_legacy_format(blueprint):
            blueprint = migrate_blueprint_data(blueprint, is_plan=(blueprint_file.name == "blueprint.json"))

        blueprint = ensure_blueprint_metadata(blueprint, source, ground_truth, extraction_method)
        blueprint["last_updated"] = datetime.utcnow().isoformat()

        # Align design blueprint identity with code blueprint when saving design
        if blueprint_file.name == "blueprint.json" and source in (
            "llm_design", "llm_architecture", "spec_first_management", "automatic_update"
        ):
            from manifest.audit.blueprint.design_identity import validate_and_align_design_identity
            manifest_dir = blueprint_file.parent
            blueprint, identity_warnings = validate_and_align_design_identity(
                manifest_dir, blueprint, auto_align_name=True
            )
            for w in identity_warnings:
                logger.debug("Design identity: %s", w)

        valid, errors = validate_blueprint_data(blueprint)
        if not valid and errors:
            logger.error("Blueprint validation failed before save: %s", errors)
            return False

        # Persist only new-format keys; strip compat-only keys (components, zones)
        out = {k: v for k, v in blueprint.items() if k not in ("components", "zones")}
        # Normalize contracts to use "from"/"to" (JSON schema) not from_id/to_id
        contracts = out.get("contracts") or []
        normalized_contracts = []
        for c in contracts:
            if not isinstance(c, dict):
                continue
            nc = dict(c)
            if "from" not in nc and "from_id" in nc:
                nc["from"] = nc.get("from_id") or ""
            if "to" not in nc and "to_id" in nc:
                nc["to"] = nc.get("to_id") or ""
            normalized_contracts.append(nc)
        out["contracts"] = normalized_contracts

        blueprint_file.parent.mkdir(parents=True, exist_ok=True)
        with open(blueprint_file, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False
