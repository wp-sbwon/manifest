"""
Load design and code blueprints, validate, build view schema, write blueprint_view.json.
"""
from pathlib import Path
from typing import Dict, Any, List, Set, Optional

from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
from manifest.audit.blueprint.view_schema import (
    build_view_schema,
    to_single_value,
    unwrap_list_field,
    write_view_schema,
)
from manifest.audit.entity_schema import PROJECT_ROOT_ID
from manifest.audit.entity_validation import validate_blueprint_data


def entities_and_comp_status_from_view_schema(view_schema: Dict[str, Any]) -> tuple:
    """Derive diagram entities and comp_status from view_schema. Returns (entities, comp_status)."""
    entities_out: List[Dict[str, Any]] = []
    comp_status: Dict[str, str] = {}
    for ve in view_schema.get("entities") or []:
        eid = ve.get("id") or ""
        val = ve.get("validation") or {}
        comp_status[eid] = val.get("status") or "planned"
        single = {}
        for key in ("narrative", "blueprint", "protocol", "profile", "governance", "symbol", "traits", "topology_actual", "preview"):
            single[key] = to_single_value(ve.get(key) or {}, use_actual=False)
        entities_out.append({
            "id": eid,
            "children": unwrap_list_field(ve, "children", use_actual=False),
            "dependencies": unwrap_list_field(ve, "dependencies", use_actual=False),
            "outgoing_contracts": unwrap_list_field(ve, "outgoing_contracts", use_actual=False),
            **single,
        })
    return entities_out, comp_status


def _load_design_and_code(
    manifest_dir: Path,
    design_blueprint: Optional[Dict[str, Any]],
    code_blueprint: Optional[Dict[str, Any]],
) -> tuple:
    manifest_dir = Path(manifest_dir)
    if design_blueprint is None:
        design_blueprint = BlueprintLoader.load_blueprint(
            manifest_dir, with_metadata=True, default_source="llm_design"
        )
    if code_blueprint is None:
        code_blueprint = BlueprintLoader.load_code_blueprint(manifest_dir)
    return design_blueprint, code_blueprint


def _validate_and_collect_errors(design: Dict[str, Any], code: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    valid_d, err_d = validate_blueprint_data(design)
    if not valid_d and err_d:
        errors.extend([f"design: {e}" for e in err_d])
    valid_c, err_c = validate_blueprint_data(code)
    if not valid_c and err_c:
        errors.extend([f"code: {e}" for e in err_c])
    return errors


def _comp_status_from_view(view_schema: Dict[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for ve in view_schema.get("entities") or []:
        eid = ve.get("id")
        if eid:
            out[eid] = (ve.get("validation") or {}).get("status") or "planned"
    return out


def _validation_by_id_from_view(view_schema: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for ve in view_schema.get("entities") or []:
        eid = ve.get("id")
        if eid:
            v = ve.get("validation") or {}
            out[eid] = {"status": v.get("status", "planned"), "deviations": list(v.get("deviations") or [])}
    return out


def get_entities_for_view(
    manifest_dir: Path,
    design_blueprint: Optional[Dict[str, Any]] = None,
    code_blueprint: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Load design and code, build view schema (comparison and status from view), write blueprint_view.json."""
    manifest_dir = Path(manifest_dir)
    design, code = _load_design_and_code(manifest_dir, design_blueprint, code_blueprint)
    schema_validation_errors = _validate_and_collect_errors(design, code)
    view_schema = build_view_schema(design, code)
    view_write_ok = write_view_schema(manifest_dir, view_schema)
    comp_status = _comp_status_from_view(view_schema)
    validation_by_id = _validation_by_id_from_view(view_schema)
    return {
        "blueprint": design,
        "code_blueprint": code,
        "comp_status": comp_status,
        "validation_by_id": validation_by_id,
        "view_schema": view_schema,
        "schema_validation_errors": schema_validation_errors,
        "view_write_ok": view_write_ok,
    }
