"""
Load design and code blueprints, validate, compare, and write integrated view schema.
"""
from pathlib import Path
from typing import Dict, Any, List, Set, Optional

from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
from manifest.audit.blueprint.blueprint_synchronizer import BlueprintSynchronizer
from manifest.audit.blueprint.blueprint_comparator import BlueprintComparator
from manifest.audit.blueprint.view_schema import build_view_schema, write_view_schema
from manifest.audit.entity_schema import PROJECT_ROOT_ID
from manifest.audit.entity_validation import validate_blueprint_data


def _unwrap_plan_actual(obj: Any) -> Any:
    """Return plan or actual from a pair dict; otherwise return obj."""
    if isinstance(obj, dict) and ("plan" in obj or "actual" in obj):
        return obj.get("plan") if obj.get("plan") is not None else obj.get("actual")
    return obj


def _to_single_value(val: Any, use_actual: bool = False) -> Any:
    """Convert plan/actual pairs to a single value; use_actual chooses which side."""
    if isinstance(val, dict) and ("plan" in val or "actual" in val):
        v = val.get("actual" if use_actual else "plan") or val.get("plan") or val.get("actual")
        return _to_single_value(v, use_actual) if isinstance(v, dict) else v
    if isinstance(val, dict):
        return {k: _to_single_value(v, use_actual) for k, v in val.items()}
    if isinstance(val, list):
        return [_to_single_value(item, use_actual) for item in val]
    return val


def entities_and_comp_status_from_view_schema(view_schema: Dict[str, Any]) -> tuple:
    """Derive diagram entities and comp_status from view_schema. Returns (entities, comp_status)."""
    entities_out: List[Dict[str, Any]] = []
    comp_status: Dict[str, str] = {}
    for ve in view_schema.get("entities") or []:
        eid = ve.get("id") or ""
        val = ve.get("validation") or {}
        comp_status[eid] = val.get("status") or "planned"
        intent_single = _to_single_value(ve.get("intent") or {}, use_actual=False)
        reality_single = _to_single_value(ve.get("reality") or {}, use_actual=True)
        if not isinstance(intent_single, dict):
            intent_single = {}
        if not isinstance(reality_single, dict):
            reality_single = {}
        entities_out.append({
            "id": eid,
            "children": ve.get("children") or [],
            "outgoing_contracts": ve.get("outgoing_contracts") or [],
            "intent": intent_single,
            "reality": reality_single,
        })
    return entities_out, comp_status


def get_entities_for_view(
    manifest_dir: Path,
    design_blueprint: Optional[Dict[str, Any]] = None,
    code_blueprint: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Load design and code blueprints, validate, compare, write blueprint_view.json. Returns view dict."""
    manifest_dir = Path(manifest_dir)
    if design_blueprint is None:
        design_blueprint = BlueprintLoader.load_blueprint(
            manifest_dir, with_metadata=True, default_source="llm_design"
        )
    if code_blueprint is None:
        code_blueprint = BlueprintLoader.load_code_blueprint(manifest_dir)
    blueprint = design_blueprint

    schema_validation_errors: List[str] = []
    valid_d, err_d = validate_blueprint_data(blueprint)
    if not valid_d and err_d:
        schema_validation_errors.extend([f"design: {e}" for e in err_d])
    valid_c, err_c = validate_blueprint_data(code_blueprint)
    if not valid_c and err_c:
        schema_validation_errors.extend([f"code: {e}" for e in err_c])

    sync = BlueprintSynchronizer()
    status_info = sync.calculate_implementation_status(blueprint, code_blueprint)
    comp_status: Dict[str, str] = status_info.get("node_statuses", {}) or {}

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
            if getattr(c, "node_id", None) == eid
            or (getattr(c, "top_down_node") or {}).get("id") == eid
            or (getattr(c, "bottom_up_node") or {}).get("id") == eid
        ]
        validation_by_id[eid] = {"status": status, "deviations": deviations}

    return {
        "blueprint": blueprint,
        "code_blueprint": code_blueprint,
        "comp_status": comp_status,
        "validation_by_id": validation_by_id,
        "conflicts": conflicts,
        "view_schema": view_schema,
        "schema_validation_errors": schema_validation_errors,
    }
