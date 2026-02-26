"""
View schema: same keys as design/code blueprints; values are plan/actual/deviates; status from comparison.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from manifest.audit.blueprint.manifest_filenames import BLUEPRINT_VIEW_FILE
from manifest.audit.blueprint.status_enums import ImplementationStatus
from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_entity, top_layer_entities
from manifest.core.logger import get_logger
from manifest.io.json_io import read_json_or_default

logger = get_logger(__name__)


def _nested_get(d: Dict[str, Any], path: Tuple[str, ...]) -> Any:
    for k in path:
        d = (d or {}).get(k)
        if d is None:
            return None
    return d


def _nested_set(d: Dict[str, Any], path: Tuple[str, ...], value: Any) -> None:
    for k in path[:-1]:
        if k not in d:
            d[k] = {}
        d = d[k]
    d[path[-1]] = value


def _language_to_list(val: Any) -> list:
    """Normalize profile.language to list of strings (string or list accepted)."""
    if val is None or val == "":
        return []
    if isinstance(val, list):
        return [x for x in val if x]
    return [val] if val else []


def _pair_nested(
    design_d: Dict[str, Any],
    code_d: Dict[str, Any],
    empty_d: Dict[str, Any],
    key_paths: List[Tuple[str, ...]],
) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for path in key_paths:
        d_val = _nested_get(design_d, path) if design_d else None
        c_val = _nested_get(code_d, path) if code_d else None
        empty_val = _nested_get(empty_d, path) if empty_d else None
        plan_val = d_val if d_val is not None else empty_val
        actual_val = c_val if c_val is not None else empty_val
        if path == ("profile", "language"):
            plan_val = _language_to_list(plan_val)
            actual_val = _language_to_list(actual_val)
        _nested_set(out, path, _pair_deviates(plan_val, actual_val))
    return out


def _values_equal(a: Any, b: Any) -> bool:
    if a is b:
        return True
    if type(a) != type(b):
        return False
    if a is None or b is None:
        return a == b
    if isinstance(a, (str, int, float, bool)):
        return a == b
    if isinstance(a, list):
        return len(a) == len(b) and all(_values_equal(x, y) for x, y in zip(a, b))
    if isinstance(a, dict):
        keys = set(a) | set(b)
        return all(_values_equal(a.get(k), b.get(k)) for k in keys)
    return a == b


def _pair_deviates(plan_val: Any, actual_val: Any) -> Dict[str, Any]:
    p = plan_val if plan_val is not None else ""
    a = actual_val if actual_val is not None else ""
    if isinstance(p, dict) and isinstance(a, dict) and not p and not a:
        p, a = {}, {}
    return {"plan": p, "actual": a, "deviates": not _values_equal(p, a)}


# Comparable paths for unified entity (top-level and nested)
_ENTITY_COMPARE_PATHS: List[Tuple[str, ...]] = [
    ("narrative", "role"),
    ("narrative", "mission"),
    ("blueprint", "type"),
    ("blueprint", "topology"),
    ("protocol", "input"),
    ("protocol", "output"),
    ("profile", "language"),
    ("profile", "platform"),
    ("profile", "io_model"),
    ("profile", "state_model"),
    ("governance", "rules"),
    ("governance", "assertions"),
    ("symbol",),
    ("dependencies",),
    ("traits",),
    ("topology_actual",),
    ("preview",),
]


def _entity_view_fields(design_ent: Dict[str, Any], code_ent: Dict[str, Any]) -> Dict[str, Any]:
    """Build plan/actual/deviates for all comparable fields of one entity."""
    empty = empty_entity("")
    return _pair_nested(design_ent or empty, code_ent or empty, empty, _ENTITY_COMPARE_PATHS)


def _collect_deviations(obj: Any, prefix: str = "") -> List[str]:
    """Collect paths where deviates is True in a view entity subtree."""
    out: List[str] = []
    if isinstance(obj, dict):
        if obj.get("deviates") is True:
            out.append(prefix or "value")
        for k, v in obj.items():
            if k in ("plan", "actual", "deviates"):
                continue
            sub = prefix + ("." + k if prefix else k)
            out.extend(_collect_deviations(v, sub))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            out.extend(_collect_deviations(item, f"{prefix}[{i}]"))
    return out


def _status_from_view_entity(
    eid: str,
    view_ent: Dict[str, Any],
    design_entities: Dict[str, Dict[str, Any]],
    code_entities: Dict[str, Dict[str, Any]],
) -> str:
    in_design = eid in design_entities
    in_code = eid in code_entities
    if not in_design and in_code:
        return "extra"
    if in_design and not in_code:
        return "planned"
    if entity_has_any_deviates(view_ent):
        return "deviation"
    return "healthy"


def build_view_schema(design: Dict[str, Any], code: Dict[str, Any]) -> Dict[str, Any]:
    """Build view schema from design and code. Same keys as blueprints; values are plan/actual/deviates; status derived from comparison."""
    design_entities = {e.get("id"): e for e in (design.get("entities") or []) if e.get("id")}
    code_entities = {e.get("id"): e for e in (code.get("entities") or []) if e.get("id")}
    all_ids = set(design_entities) | set(code_entities)
    root_id = design.get("root_id") or code.get("root_id") or PROJECT_ROOT_ID

    view_entities: List[Dict[str, Any]] = []
    for eid in sorted(all_ids, key=lambda x: (0 if x == root_id else 1, x)):
        de = design_entities.get(eid) or {}
        ce = code_entities.get(eid) or {}
        children_pd = _pair_deviates(de.get("children"), ce.get("children"))
        contracts_pd = _pair_deviates(de.get("outgoing_contracts"), ce.get("outgoing_contracts"))
        compared = _entity_view_fields(de, ce)
        status = _status_from_view_entity(eid, {"children": children_pd, "outgoing_contracts": contracts_pd, **compared}, design_entities, code_entities)
        deviations = _collect_deviations(compared) + _collect_deviations(children_pd) + _collect_deviations(contracts_pd)
        view_entities.append({
            "id": eid,
            "children": children_pd,
            "dependencies": compared.get("dependencies", _pair_deviates(None, None)),
            "narrative": compared.get("narrative", {}),
            "blueprint": compared.get("blueprint", {}),
            "protocol": compared.get("protocol", {}),
            "profile": compared.get("profile", {}),
            "governance": compared.get("governance", {}),
            "symbol": compared.get("symbol", _pair_deviates(None, None)),
            "traits": compared.get("traits", _pair_deviates(None, None)),
            "topology_actual": compared.get("topology_actual", _pair_deviates(None, None)),
            "preview": compared.get("preview", _pair_deviates(None, None)),
            "outgoing_contracts": contracts_pd,
            "validation": {"status": status, "deviations": deviations},
        })

    comp_status = _derive_comp_status_from_view(view_entities, design, root_id)
    for ve in view_entities:
        eid = ve.get("id")
        if eid:
            ve["validation"] = {"status": comp_status.get(eid, ve["validation"]["status"]), "deviations": ve["validation"]["deviations"]}

    return {
        "version": design.get("version") or code.get("version") or "1.0",
        "root_id": root_id,
        "entities": view_entities,
    }


def _parent_aggregate_status_from_children(
    blueprint: Dict[str, Any],
    entity_status: Dict[str, str],
) -> Dict[str, str]:
    """Aggregate status per parent entity id from its children's statuses."""
    out: Dict[str, str] = {}
    for e in top_layer_entities(blueprint):
        parent_id = e.get("id")
        child_ids = list(e.get("children") or [])
        if not parent_id or not child_ids:
            continue
        statuses = [entity_status.get(eid, ImplementationStatus.PLANNED.value) for eid in child_ids]
        if any(s == ImplementationStatus.DEVIATION.value for s in statuses):
            out[parent_id] = ImplementationStatus.DEVIATION.value
        elif all(s == ImplementationStatus.HEALTHY.value for s in statuses):
            out[parent_id] = ImplementationStatus.HEALTHY.value
        elif all(s == ImplementationStatus.PLANNED.value for s in statuses):
            out[parent_id] = ImplementationStatus.PLANNED.value
        else:
            out[parent_id] = ImplementationStatus.PARTIAL.value
    return out


def _root_status_from_children(blueprint: Dict[str, Any], entity_status: Dict[str, str]) -> str:
    """Root status from its direct children."""
    child_entities = top_layer_entities(blueprint)
    child_ids = [e.get("id") for e in child_entities if e.get("id")]
    if not child_ids:
        return ImplementationStatus.PLANNED.value
    statuses = [entity_status.get(eid, ImplementationStatus.PLANNED.value) for eid in child_ids]
    if any(s == ImplementationStatus.DEVIATION.value for s in statuses):
        return ImplementationStatus.DEVIATION.value
    if all(s == ImplementationStatus.HEALTHY.value for s in statuses):
        return ImplementationStatus.HEALTHY.value
    if all(s == ImplementationStatus.PLANNED.value for s in statuses):
        return ImplementationStatus.PLANNED.value
    return ImplementationStatus.PARTIAL.value


def _derive_comp_status_from_view(
    view_entities: List[Dict[str, Any]],
    design: Dict[str, Any],
    root_id: str,
) -> Dict[str, str]:
    """Derive comp_status from view (planned/healthy/deviation/extra) with parent aggregation."""
    status_by_id: Dict[str, str] = {}
    for ve in view_entities:
        eid = ve.get("id")
        if eid:
            status_by_id[eid] = (ve.get("validation") or {}).get("status") or "planned"
    agg = _parent_aggregate_status_from_children(design, status_by_id)
    for pid, s in agg.items():
        if status_by_id.get(pid) != "deviation":
            status_by_id[pid] = s
    status_by_id[root_id] = _root_status_from_children(design, status_by_id)
    return status_by_id


def write_view_schema(manifest_dir: Path, view_schema: Dict[str, Any]) -> bool:
    path = Path(manifest_dir) / BLUEPRINT_VIEW_FILE
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(view_schema, f, indent=2, ensure_ascii=False)
        logger.debug("Wrote %s", path)
        return True
    except Exception as e:
        logger.warning("Failed to write view schema: %s", e)
        return False


_EMPTY_VIEW_SCHEMA: Dict[str, Any] = {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": []}


def to_single_value(val: Any) -> Any:
    """Convert plan/actual/deviates pairs to a single value (plan)."""
    if isinstance(val, dict) and ("plan" in val or "actual" in val):
        v = val["plan"] if "plan" in val else val.get("actual")
        return to_single_value(v) if isinstance(v, dict) else v
    if isinstance(val, dict):
        return {k: to_single_value(v) for k, v in val.items()}
    if isinstance(val, list):
        return [to_single_value(item) for item in val]
    return val


def entity_has_any_deviates(obj: Any) -> bool:
    """True if any nested pair has deviates=True."""
    if isinstance(obj, dict):
        if obj.get("deviates") is True:
            return True
        for k, v in obj.items():
            if k in ("plan", "actual"):
                continue
            if entity_has_any_deviates(v):
                return True
        return False
    if isinstance(obj, list):
        return any(entity_has_any_deviates(item) for item in obj)
    return False


def unwrap_list_field(ve: Dict[str, Any], key: str) -> List[Any]:
    raw = ve.get(key)
    if isinstance(raw, list):
        return raw
    unwrapped = to_single_value(raw or {})
    return unwrapped if isinstance(unwrapped, list) else []


def load_view_schema(manifest_dir: Path) -> Dict[str, Any]:
    path = Path(manifest_dir) / BLUEPRINT_VIEW_FILE
    # Pass a fresh default so read_json_or_default's shallow copy does not share entities list.
    default = {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": []}
    return read_json_or_default(path, default, logger=logger)
