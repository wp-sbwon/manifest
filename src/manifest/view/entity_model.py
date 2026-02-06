"""
Load design and code blueprints, compare, attach validation; write integrated view schema.
"""
from pathlib import Path
from typing import Dict, Any, List, Set

from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
from manifest.audit.blueprint.blueprint_synchronizer import BlueprintSynchronizer
from manifest.audit.blueprint.blueprint_comparator import BlueprintComparator
from manifest.audit.blueprint.view_schema import build_view_schema, write_view_schema
from manifest.audit.entity_schema import PROJECT_ROOT_ID


def get_entities_for_view(manifest_dir: Path) -> Dict[str, Any]:
    """
    Load design and code, compare, attach validation. Returns dict with blueprint,
    code_blueprint, comp_status, validation_by_id, architecture, conflicts, view_schema.
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

    view_schema = build_view_schema(blueprint, code_blueprint, comp_status, conflicts)
    write_view_schema(manifest_dir, view_schema)

    validation_by_id: Dict[str, Dict[str, Any]] = {}
    entity_ids: Set[str] = set()
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
        "view_schema": view_schema,
    }
