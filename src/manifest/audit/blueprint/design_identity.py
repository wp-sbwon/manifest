"""
Design–Code Blueprint Identity Alignment.

Canonical identity rule: For accurate deviation calculation, each component in
blueprint.json (design) must use the same `id` and `name` as in blueprint_code.json
(code). The comparator matches components by `name`; human-friendly descriptions
belong in `description`, not in `name`.

This module validates and optionally auto-corrects design blueprint components
against the code blueprint when saving design, so top-down and bottom-up docs
"come to the same point" for comparison.
"""
from pathlib import Path
from typing import Dict, Any, List, Tuple

from manifest.core.logger import get_logger

logger = get_logger(__name__)


def validate_and_align_design_identity(
    manifest_dir: Path,
    design_blueprint: Dict[str, Any],
    auto_align_name: bool = True,
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Validate design blueprint component identity against code blueprint and optionally align.

    For each design component whose `id` exists in the code blueprint, ensures `name`
    matches. If not and auto_align_name is True, sets design component `name` to the
    code component's `name` so deviation comparison works correctly.

    Args:
        manifest_dir: Path to .manifest (containing blueprint_code.json).
        design_blueprint: The design blueprint dict (may be mutated if auto_align_name).
        auto_align_name: If True, correct design component names to match code by id.

    Returns:
        (design_blueprint, list of warning messages). design_blueprint is the same
        dict (possibly with names updated); warnings describe any alignments made.
    """
    warnings: List[str] = []
    code_file = manifest_dir / "blueprint_code.json"
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
        c["id"]: c for c in code_blueprint.get("components", []) if c.get("id")
    }
    design_components = design_blueprint.get("components") or []
    for comp in design_components:
        comp_id = comp.get("id")
        if not comp_id or comp_id not in code_by_id:
            continue
        code_comp = code_by_id[comp_id]
        code_name = code_comp.get("name")
        design_name = comp.get("name")
        if not code_name:
            continue
        if design_name != code_name:
            if auto_align_name:
                old_name = design_name or "(missing)"
                comp["name"] = code_name
                msg = f"Aligned design component id={comp_id} name '{old_name}' -> '{code_name}' (code blueprint)"
                warnings.append(msg)
                logger.info(msg)
            else:
                warnings.append(
                    f"Design component id={comp_id} name '{design_name}' differs from code '{code_name}'; "
                    "align for accurate deviation."
                )

    return design_blueprint, warnings
