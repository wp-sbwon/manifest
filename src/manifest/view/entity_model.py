"""
Load design and code blueprints, validate, compare, and write integrated view schema.
"""
from pathlib import Path
from typing import Dict, Any, List, Set, Optional

from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
from manifest.audit.blueprint.blueprint_synchronizer import BlueprintSynchronizer
from manifest.audit.blueprint.blueprint_comparator import BlueprintComparator
from manifest.audit.blueprint.view_schema import (
    build_view_schema,
    entity_has_any_deviates,
    to_single_value,
    unwrap_list_field,
    write_view_schema,
)
from manifest.audit.entity_schema import PROJECT_ROOT_ID
from manifest.audit.entity_validation import validate_blueprint_data
from manifest.view.views_content import parent_aggregate_status_from_children, root_status_from_children


def entities_and_comp_status_from_view_schema(view_schema: Dict[str, Any]) -> tuple:
    """Derive diagram entities and comp_status from view_schema. Returns (entities, comp_status)."""
    entities_out: List[Dict[str, Any]] = []
    comp_status: Dict[str, str] = {}
    for ve in view_schema.get("entities") or []:
        eid = ve.get("id") or ""
        val = ve.get("validation") or {}
        comp_status[eid] = val.get("status") or "planned"
        intent_single = to_single_value(ve.get("intent") or {}, use_actual=False)
        reality_single = to_single_value(ve.get("reality") or {}, use_actual=True)
        if not isinstance(intent_single, dict):
            intent_single = {}
        if not isinstance(reality_single, dict):
            reality_single = {}
        entities_out.append({
            "id": eid,
            "children": unwrap_list_field(ve, "children", use_actual=False),
            "dependencies": unwrap_list_field(ve, "dependencies", use_actual=False),
            "outgoing_contracts": unwrap_list_field(ve, "outgoing_contracts", use_actual=False),
            "intent": intent_single,
            "reality": reality_single,
        })
    return entities_out, comp_status


def _load_design_and_code(
    manifest_dir: Path,
    design_blueprint: Optional[Dict[str, Any]],
    code_blueprint: Optional[Dict[str, Any]],
) -> tuple:
    """Load design and code blueprints from disk if not provided. Returns (design, code)."""
    manifest_dir = Path(manifest_dir)
    if design_blueprint is None:
        design_blueprint = BlueprintLoader.load_blueprint(
            manifest_dir, with_metadata=True, default_source="llm_design"
        )
    if code_blueprint is None:
        code_blueprint = BlueprintLoader.load_code_blueprint(manifest_dir)
    return design_blueprint, code_blueprint


def _validate_and_collect_errors(design: Dict[str, Any], code: Dict[str, Any]) -> List[str]:
    """Validate both blueprints; return list of prefixed error messages."""
    errors: List[str] = []
    valid_d, err_d = validate_blueprint_data(design)
    if not valid_d and err_d:
        errors.extend([f"design: {e}" for e in err_d])
    valid_c, err_c = validate_blueprint_data(code)
    if not valid_c and err_c:
        errors.extend([f"code: {e}" for e in err_c])
    return errors


def _compute_comp_status(design: Dict[str, Any], code: Dict[str, Any]) -> Dict[str, str]:
    """Sync design/code and aggregate status; return comp_status."""
    sync = BlueprintSynchronizer()
    status_info = sync.calculate_implementation_status(design, code)
    comp_status: Dict[str, str] = dict(status_info.get("node_statuses", {}) or {})
    agg = parent_aggregate_status_from_children(design, comp_status)
    for pid, s in agg.items():
        if comp_status.get(pid) != "deviation":
            comp_status[pid] = s
    comp_status[PROJECT_ROOT_ID] = root_status_from_children(design, comp_status)
    return comp_status


def _compare_blueprints(design: Dict[str, Any], code: Dict[str, Any]) -> List[Any]:
    """Compare design and code blueprints; return list of conflicts."""
    return BlueprintComparator().compare_blueprints(design, code)


def _build_view_schema_with_overrides(
    design: Dict[str, Any],
    code: Dict[str, Any],
    comp_status: Dict[str, str],
    conflicts: List[Any],
) -> Dict[str, Any]:
    """Build view schema and set status to deviation where entity has field-level deviates."""
    view_schema = build_view_schema(design, code, comp_status, conflicts)
    for ve in view_schema.get("entities") or []:
        eid = ve.get("id")
        if not eid or not entity_has_any_deviates(ve):
            continue
        current = comp_status.get(eid, "planned")
        if current in ("healthy", "partial"):
            comp_status[eid] = "deviation"
            v = ve.get("validation") or {}
            v["status"] = "deviation"
            ve["validation"] = v
    return view_schema


def _build_validation_by_id(
    design: Dict[str, Any],
    code: Dict[str, Any],
    comp_status: Dict[str, str],
    conflicts: List[Any],
) -> Dict[str, Dict[str, Any]]:
    """Build validation_by_id from comp_status and conflicts."""
    entity_ids: Set[str] = set()
    for ent in (design.get("entities") or []) + (code.get("entities") or []):
        eid = ent.get("id")
        if eid:
            entity_ids.add(eid)
    out: Dict[str, Dict[str, Any]] = {}
    for eid in entity_ids:
        status = comp_status.get(eid, "planned")
        deviations = [
            c.message for c in conflicts
            if getattr(c, "node_id", None) == eid
            or (getattr(c, "top_down_node") or {}).get("id") == eid
            or (getattr(c, "bottom_up_node") or {}).get("id") == eid
        ]
        out[eid] = {"status": status, "deviations": deviations}
    return out


def get_entities_for_view(
    manifest_dir: Path,
    design_blueprint: Optional[Dict[str, Any]] = None,
    code_blueprint: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Load design and code blueprints, validate, compare, write blueprint_view.json. Returns view dict."""
    manifest_dir = Path(manifest_dir)
    design, code = _load_design_and_code(manifest_dir, design_blueprint, code_blueprint)
    schema_validation_errors = _validate_and_collect_errors(design, code)
    comp_status = _compute_comp_status(design, code)
    conflicts = _compare_blueprints(design, code)
    view_schema = _build_view_schema_with_overrides(design, code, comp_status, conflicts)
    write_view_schema(manifest_dir, view_schema)
    validation_by_id = _build_validation_by_id(design, code, comp_status, conflicts)
    return {
        "blueprint": design,
        "code_blueprint": code,
        "comp_status": comp_status,
        "validation_by_id": validation_by_id,
        "conflicts": conflicts,
        "view_schema": view_schema,
        "schema_validation_errors": schema_validation_errors,
    }
