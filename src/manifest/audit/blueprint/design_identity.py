"""
Design–code blueprint identity alignment.

Design and code entities must share the same id/name for deviation calculation.
"""
from pathlib import Path
from typing import Dict, Any, List, Tuple

from manifest.audit.entity_schema import PROJECT_ROOT_ID
from manifest.core.logger import get_logger

logger = get_logger(__name__)


def _get_nodes_list(blueprint: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return list of node dicts (non-root)."""
    entities = blueprint.get("entities") or []
    return [e for e in entities if (e.get("id") or "") != PROJECT_ROOT_ID]


def validate_and_align_design_identity(
    manifest_dir: Path,
    design_blueprint: Dict[str, Any],
    auto_align_name: bool = True,
) -> Tuple[Dict[str, Any], List[str]]:
    """Validate design identity against code blueprint; optionally align names."""
    warnings: List[str] = []
    from manifest.audit.blueprint.manifest_filenames import BLUEPRINT_CODE_FILE
    code_file = manifest_dir / BLUEPRINT_CODE_FILE
    if not code_file.exists():
        return design_blueprint, warnings

    try:
        import json
        with open(code_file, "r", encoding="utf-8") as f:
            code_blueprint = json.load(f)
    except Exception as e:
        logger.debug("Could not load code blueprint for identity check: %s", e)
        return design_blueprint, warnings

    code_by_id: Dict[str, Dict[str, Any]] = {
        c["id"]: c for c in _get_nodes_list(code_blueprint) if c.get("id")
    }
    design_nodes = _get_nodes_list(design_blueprint)
    for comp in design_nodes:
        comp_id = comp.get("id")
        if not comp_id or comp_id not in code_by_id:
            continue
        code_comp = code_by_id[comp_id]
        code_name = code_comp.get("name") or ((code_comp.get("intent") or {}).get("narrative") or {}).get("role")
        design_name = comp.get("name") or ((comp.get("intent") or {}).get("narrative") or {}).get("role")
        if not code_name:
            continue
        if design_name != code_name:
            if auto_align_name:
                old_name = design_name or "(missing)"
                comp["name"] = code_name
                if "intent" in comp and isinstance(comp["intent"], dict) and "narrative" in comp["intent"]:
                    comp["intent"]["narrative"] = dict(comp["intent"]["narrative"])
                    comp["intent"]["narrative"]["role"] = code_name
                msg = f"Aligned design component id={comp_id} name '{old_name}' -> '{code_name}' (code blueprint)"
                warnings.append(msg)
                logger.info(msg)
            else:
                warnings.append(
                    f"Design component id={comp_id} name '{design_name}' differs from code '{code_name}'; "
                    "align for accurate deviation."
                )

    return design_blueprint, warnings
