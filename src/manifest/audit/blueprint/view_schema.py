"""
View schema: same keys as blueprint/blueprint_code; values are pair + deviation status.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from manifest.audit.blueprint.manifest_filenames import BLUEPRINT_VIEW_FILE
from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_intent, empty_reality
from manifest.core.logger import get_logger
from manifest.io.json_io import read_json_or_default

logger = get_logger(__name__)


def _nested_get(d: Dict[str, Any], path: Tuple[str, ...]) -> Any:
    """Get value at path (tuple of keys); return None if missing."""
    for k in path:
        d = (d or {}).get(k)
        if d is None:
            return None
    return d


def _nested_set(d: Dict[str, Any], path: Tuple[str, ...], value: Any) -> None:
    """Set value at path; create nested dicts as needed."""
    for k in path[:-1]:
        if k not in d:
            d[k] = {}
        d = d[k]
    d[path[-1]] = value


def _pair_nested(
    design_d: Dict[str, Any],
    code_d: Dict[str, Any],
    empty_d: Dict[str, Any],
    key_paths: List[Tuple[str, ...]],
) -> Dict[str, Any]:
    """Build nested dict: each leaf is _pair_deviates(design_val, code_val) for the path."""
    out: Dict[str, Any] = {}
    for path in key_paths:
        d_val = _nested_get(design_d, path) if design_d else None
        c_val = _nested_get(code_d, path) if code_d else None
        empty_val = _nested_get(empty_d, path) if empty_d else None
        plan_val = d_val if d_val is not None else empty_val
        actual_val = c_val if c_val is not None else empty_val
        _nested_set(out, path, _pair_deviates(plan_val, actual_val))
    return out


def _values_equal(a: Any, b: Any) -> bool:
    """Deep equality for plan vs actual (JSON-like values)."""
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
    """Single value as in blueprint, but stored as plan/actual + deviates."""
    p = plan_val if plan_val is not None else ""
    a = actual_val if actual_val is not None else ""
    if isinstance(p, dict) and isinstance(a, dict) and not p and not a:
        p, a = {}, {}
    return {"plan": p, "actual": a, "deviates": not _values_equal(p, a)}


_INTENT_KEY_PATHS: List[Tuple[str, ...]] = [
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
]

_REALITY_KEY_PATHS: List[Tuple[str, ...]] = [
    ("symbol",),
    ("protocol", "input"),
    ("protocol", "output"),
    ("profile", "language"),
    ("profile", "platform"),
    ("profile", "io_model"),
    ("profile", "state_model"),
    ("dependencies",),
    ("traits",),
    ("topology_actual",),
    ("preview",),
]


def _intent_view(design: Dict[str, Any], code: Dict[str, Any]) -> Dict[str, Any]:
    """Intent with same keys as blueprint intent; each leaf is pair+deviates."""
    return _pair_nested(
        design.get("intent") or {},
        code.get("intent") or {},
        empty_intent(),
        _INTENT_KEY_PATHS,
    )


def _reality_view(design: Dict[str, Any], code: Dict[str, Any]) -> Dict[str, Any]:
    """Reality with same keys as blueprint reality; each leaf is pair+deviates."""
    return _pair_nested(
        design.get("reality") or {},
        code.get("reality") or {},
        empty_reality(),
        _REALITY_KEY_PATHS,
    )


def build_view_schema(
    design: Dict[str, Any],
    code: Dict[str, Any],
    comp_status: Dict[str, str],
    conflicts: List[Any],
) -> Dict[str, Any]:
    """Build view schema: same keys as blueprint/blueprint_code; values are plan/actual + deviates."""
    design_entities = {e.get("id"): e for e in (design.get("entities") or []) if e.get("id")}
    code_entities = {e.get("id"): e for e in (code.get("entities") or []) if e.get("id")}
    all_ids = set(design_entities) | set(code_entities)
    root_id = design.get("root_id") or code.get("root_id") or PROJECT_ROOT_ID

    view_entities: List[Dict[str, Any]] = []
    for eid in sorted(all_ids, key=lambda x: (0 if x == root_id else 1, x)):
        de = design_entities.get(eid) or {}
        ce = code_entities.get(eid) or {}
        children_pd = _pair_deviates(de.get("children"), ce.get("children"))
        deps_pd = _pair_deviates(de.get("dependencies"), ce.get("dependencies"))
        contracts_pd = _pair_deviates(de.get("outgoing_contracts"), ce.get("outgoing_contracts"))
        deviations = [
            c.message for c in conflicts
            if getattr(c, "node_id", None) == eid
            or (getattr(c, "top_down_node") or {}).get("id") == eid
            or (getattr(c, "bottom_up_node") or {}).get("id") == eid
        ]
        status = comp_status.get(eid, "planned")
        view_entities.append({
            "id": eid,
            "children": children_pd,
            "dependencies": deps_pd,
            "intent": _intent_view(de, ce),
            "reality": _reality_view(de, ce),
            "outgoing_contracts": contracts_pd,
            "validation": {"status": status, "deviations": deviations},
        })

    return {
        "version": design.get("version") or code.get("version") or "1.0",
        "root_id": root_id,
        "entities": view_entities,
    }


def write_view_schema(manifest_dir: Path, view_schema: Dict[str, Any]) -> bool:
    """Write integrated view schema to blueprint_view.json."""
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


def to_single_value(val: Any, use_actual: bool = False) -> Any:
    """Convert plan/actual/deviates pairs to a single value; use_actual chooses which side."""
    if isinstance(val, dict) and ("plan" in val or "actual" in val):
        v = val.get("actual" if use_actual else "plan") or val.get("plan") or val.get("actual")
        return to_single_value(v, use_actual) if isinstance(v, dict) else v
    if isinstance(val, dict):
        return {k: to_single_value(v, use_actual) for k, v in val.items()}
    if isinstance(val, list):
        return [to_single_value(item, use_actual) for item in val]
    return val


def entity_has_any_deviates(obj: Any) -> bool:
    """True if any nested pair has deviates=True (view entity or subtree)."""
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


def unwrap_list_field(ve: Dict[str, Any], key: str, use_actual: bool = False) -> List[Any]:
    """Unwrap a view entity field that may be {plan, actual, deviates} to a list."""
    raw = ve.get(key)
    if isinstance(raw, list):
        return raw
    unwrapped = to_single_value(raw or {}, use_actual)
    return unwrapped if isinstance(unwrapped, list) else []


def load_view_schema(manifest_dir: Path) -> Dict[str, Any]:
    """Load blueprint_view.json or return empty structure."""
    path = Path(manifest_dir) / BLUEPRINT_VIEW_FILE
    return read_json_or_default(path, _EMPTY_VIEW_SCHEMA, logger=logger)
