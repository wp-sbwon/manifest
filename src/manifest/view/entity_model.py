"""
Integration module for view: load blueprint + blueprint_code, run compare/sync, attach validation per entity.

View consumes get_entities_for_view() as the single source for diagram and inspector data.
"""
from pathlib import Path
from typing import Dict, Any, List, Tuple

from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
from manifest.audit.blueprint.blueprint_synchronizer import BlueprintSynchronizer
from manifest.audit.blueprint.blueprint_comparator import BlueprintComparator
from manifest.audit.entity_schema import PROJECT_ROOT_ID


def get_entities_for_view(manifest_dir: Path) -> Dict[str, Any]:
    """
    Load design and code blueprints, run comparison, attach validation per entity.

    Returns a single dict for the view:
      - blueprint: design blueprint (with components compat from loader)
      - code_blueprint: code blueprint (with components compat)
      - comp_status: component_id -> status (healthy | planned | deviation | partial)
      - validation_by_id: entity_id -> { "status": str, "deviations": [str] }
      - architecture: loaded architecture.json (for features/diagram title)
      - conflicts: list of BlueprintConflict (from comparator)

    No validation key is stored in blueprint/code files; it is computed here.
    """
    manifest_dir = Path(manifest_dir)
    blueprint = BlueprintLoader.load_blueprint(
        manifest_dir, with_metadata=True, default_source="llm_design"
    )
    code_blueprint = BlueprintLoader.load_code_blueprint(manifest_dir)

    arch_file = manifest_dir / "architecture.json"
    if arch_file.exists():
        from manifest.audit.metadata.architecture_metadata import load_architecture_with_metadata
        architecture = load_architecture_with_metadata(arch_file)
    else:
        architecture = {}

    sync = BlueprintSynchronizer()
    status_info = sync.calculate_implementation_status(blueprint, code_blueprint, architecture)
    comp_status: Dict[str, str] = status_info.get("component_statuses", {}) or {}

    comparator = BlueprintComparator()
    conflicts: List[Any] = comparator.compare_blueprints(blueprint, code_blueprint)

    # Build validation per entity: status from comp_status, deviations from conflicts
    validation_by_id: Dict[str, Dict[str, Any]] = {}
    entity_ids: set = set()
    for ent in (blueprint.get("entities") or []) + (code_blueprint.get("entities") or []):
        eid = ent.get("id")
        if eid:
            entity_ids.add(eid)
    for eid in entity_ids:
        if (eid or "") == PROJECT_ROOT_ID:
            continue
        status = comp_status.get(eid, "planned")
        deviations = [
            c.message for c in conflicts
            if getattr(c, "component_id", None) == eid
            or (getattr(c, "top_down_component") or {}).get("id") == eid
            or (getattr(c, "bottom_up_component") or {}).get("id") == eid
        ]
        validation_by_id[eid] = {"status": status, "deviations": deviations}

    return {
        "blueprint": blueprint,
        "code_blueprint": code_blueprint,
        "comp_status": comp_status,
        "validation_by_id": validation_by_id,
        "architecture": architecture,
        "conflicts": conflicts,
    }
