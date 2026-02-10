"""
Integrated view schema: plan vs actual per field, validation attached.
"""
import json
from pathlib import Path
from typing import Any, Dict, List

from manifest.audit.blueprint.manifest_filenames import BLUEPRINT_VIEW_FILE
from manifest.audit.entity_schema import PROJECT_ROOT_ID
from manifest.core.logger import get_logger

logger = get_logger(__name__)


def _pair(plan_val: Any, actual_val: Any) -> Dict[str, Any]:
    return {"plan": plan_val if plan_val is not None else "", "actual": actual_val if actual_val is not None else ""}


def _pair_nested(plan_d: Dict[str, Any], actual_d: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k in keys:
        out[k] = _pair(plan_d.get(k) if isinstance(plan_d, dict) else None, actual_d.get(k) if isinstance(actual_d, dict) else None)
    return out


def build_view_schema(
    design: Dict[str, Any],
    code: Dict[str, Any],
    comp_status: Dict[str, str],
    conflicts: List[Any],
) -> Dict[str, Any]:
    """Build view schema: plan/actual pairs and validation per entity."""
    design_entities = {e.get("id"): e for e in (design.get("entities") or []) if e.get("id")}
    code_entities = {e.get("id"): e for e in (code.get("entities") or []) if e.get("id")}
    all_ids = set(design_entities) | set(code_entities)
    root_id = design.get("root_id") or code.get("root_id") or PROJECT_ROOT_ID

    view_entities: List[Dict[str, Any]] = []
    for eid in sorted(all_ids, key=lambda x: (0 if x == root_id else 1, x)):
        de = design_entities.get(eid) or {}
        ce = code_entities.get(eid) or {}
        intent_d = de.get("intent") or {}
        intent_c = ce.get("intent") or {}
        reality_d = de.get("reality") or {}
        reality_c = ce.get("reality") or {}

        narrative_d = intent_d.get("narrative") or {}
        narrative_c = intent_c.get("narrative") or {}
        view_intent = {
            "narrative": {
                "role": _pair(narrative_d.get("role"), narrative_c.get("role")),
                "mission": _pair(narrative_d.get("mission"), narrative_c.get("mission")),
            },
            "blueprint": {
                "type": _pair(intent_d.get("blueprint", {}).get("type"), intent_c.get("blueprint", {}).get("type")),
                "topology": _pair(intent_d.get("blueprint", {}).get("topology"), intent_c.get("blueprint", {}).get("topology")),
            },
            "protocol": {
                "input": _pair(intent_d.get("protocol", {}).get("input"), intent_c.get("protocol", {}).get("input")),
                "output": _pair(intent_d.get("protocol", {}).get("output"), intent_c.get("protocol", {}).get("output")),
            },
            "profile": _pair_nested(
                intent_d.get("profile") or {},
                intent_c.get("profile") or {},
                ["language", "platform", "io_model", "state_model"],
            ),
            "governance": {
                "rules": _pair(intent_d.get("governance", {}).get("rules"), intent_c.get("governance", {}).get("rules")),
                "assertions": _pair(intent_d.get("governance", {}).get("assertions"), intent_c.get("governance", {}).get("assertions")),
            },
        }
        view_reality = {
            "symbol": _pair(reality_d.get("symbol"), reality_c.get("symbol")),
            "protocol": {
                "input": _pair(reality_d.get("protocol", {}).get("input"), reality_c.get("protocol", {}).get("input")),
                "output": _pair(reality_d.get("protocol", {}).get("output"), reality_c.get("protocol", {}).get("output")),
            },
            "profile": _pair_nested(
                reality_d.get("profile") or {},
                reality_c.get("profile") or {},
                ["language", "platform", "io_model", "state_model"],
            ),
            "dependencies": _pair(reality_d.get("dependencies"), reality_c.get("dependencies")),
            "traits": _pair(reality_d.get("traits"), reality_c.get("traits")),
            "topology_actual": _pair(reality_d.get("topology_actual"), reality_c.get("topology_actual")),
            "preview": _pair(reality_d.get("preview"), reality_c.get("preview")),
        }
        deviations = [
            c.message for c in conflicts
            if getattr(c, "node_id", None) == eid
            or (getattr(c, "top_down_node") or {}).get("id") == eid
            or (getattr(c, "bottom_up_node") or {}).get("id") == eid
        ]
        status = comp_status.get(eid, "planned") if eid != root_id else "planned"
        children = de.get("children") if de.get("children") is not None else ce.get("children")
        outgoing_contracts = de.get("outgoing_contracts") if de.get("outgoing_contracts") is not None else ce.get("outgoing_contracts")
        view_entities.append({
            "id": eid,
            "children": children if isinstance(children, list) else [],
            "outgoing_contracts": outgoing_contracts if isinstance(outgoing_contracts, list) else [],
            "intent": view_intent,
            "reality": view_reality,
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


def load_view_schema(manifest_dir: Path) -> Dict[str, Any]:
    """Load blueprint_view.json or return empty structure."""
    path = Path(manifest_dir) / BLUEPRINT_VIEW_FILE
    if not path.exists():
        return {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Failed to load view schema: %s", e)
        return {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": []}
