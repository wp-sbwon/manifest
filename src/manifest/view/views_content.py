"""
Stateless view content builders for Manifest View.

Pure functions that take manifest_dir, blueprint, or other data and return
strings or Rich renderables. Used by app.py for Diagram, Files,
Inspector, and sidebar content. Keeps app.py focused on lifecycle and state.
"""
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Set, Union

from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
from manifest.audit.entity_schema import (
    PROJECT_ROOT_ID,
    entity_display_name,
    contracts_from_entities,
    top_layer_entities,
)
from manifest.core.logger import get_logger

logger = get_logger(__name__)

# Re-export for app.py
ACCENT_BLUE = "bright_blue"


def entities_for_display(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Flat dicts with id, name, file, type, methods for display."""
    out: List[Dict[str, Any]] = []
    for e in entities or []:
        if (e.get("id") or "") == PROJECT_ROOT_ID:
            continue
        r = e.get("reality") or {}
        name = entity_display_name(e) or "?"
        file_path = r.get("symbol", e.get("file", ""))
        parts = (file_path or "").replace("\\", "/").split("/")
        module_path = "/".join(parts[:-1]) if len(parts) > 1 else (parts[0] if parts else "")
        out.append({
            "id": e.get("id"),
            "name": name,
            "file": file_path,
            "module_path": module_path,
            "type": r.get("type", e.get("type", "?")),
            "methods": r.get("methods", e.get("methods", [])),
            "attributes": r.get("attributes", e.get("attributes", [])),
            "line": r.get("line", e.get("line")),
            "algorithm": r.get("algorithm", e.get("algorithm")),
            "design_pattern": r.get("design_pattern", e.get("design_pattern")),
            "complexity": r.get("complexity", e.get("complexity")),
            "notes": e.get("notes"),
        })
    return out


def blueprint_component_names(manifest_dir: Path) -> Dict[str, str]:
    """Display name per node id from blueprint."""
    try:
        top_down = BlueprintLoader.load_blueprint(
            manifest_dir, with_metadata=False, default_source="llm_design"
        )
        out: Dict[str, str] = {}
        for c in entities_for_display(top_down.get("entities", [])):
            cid = c.get("id")
            name = (c.get("name") or cid or "?")[:30]
            if cid:
                out[cid] = name
        return out
    except Exception as e:
        logger.debug("blueprint_component_names failed: %s", e)
        return {}


def blueprint_parent_names_by_component(blueprint: Dict[str, Any]) -> Dict[str, List[str]]:
    """Map component id to parent entity display names that list it as a child."""
    comp_to_parents: Dict[str, List[str]] = {}
    for e in top_layer_entities(blueprint):
        name = entity_display_name(e) or e.get("name") or e.get("id") or "?"
        for cid in e.get("children") or []:
            comp_to_parents.setdefault(cid, []).append(name)
    return comp_to_parents


def parent_aggregate_status_from_children(
    blueprint: Dict[str, Any],
    entity_status: Dict[str, str],
) -> Dict[str, str]:
    """Aggregate status per parent entity id (root's children) from its children's statuses."""
    out: Dict[str, str] = {}
    for e in top_layer_entities(blueprint):
        parent_id = e.get("id")
        child_ids = list(e.get("children") or [])
        if not parent_id:
            continue
        if not child_ids:
            continue
        statuses = [entity_status.get(eid, "planned") for eid in child_ids]
        if any(s == "deviation" for s in statuses):
            out[parent_id] = "deviation"
        elif all(s == "healthy" for s in statuses):
            out[parent_id] = "healthy"
        elif all(s == "planned" for s in statuses):
            out[parent_id] = "planned"
        else:
            out[parent_id] = "partial"
    return out


def root_status_from_children(blueprint: Dict[str, Any], entity_status: Dict[str, str]) -> str:
    """Root status from its direct children (same aggregation as parent_aggregate)."""
    child_entities = top_layer_entities(blueprint)
    child_ids = [e.get("id") for e in child_entities if e.get("id")]
    if not child_ids:
        return "planned"
    statuses = [entity_status.get(eid, "planned") for eid in child_ids]
    if any(s == "deviation" for s in statuses):
        return "deviation"
    if all(s == "healthy" for s in statuses):
        return "healthy"
    if all(s == "planned" for s in statuses):
        return "planned"
    return "partial"


def box(name: str, width: int) -> Tuple[str, str, str]:
    """Three lines for a box (top/mid/bot)."""
    w = max(width, 2)
    content = name[:w].ljust(w)[:w]
    top = "┌" + "─" * w + "┐"
    mid = "│" + content + "│"
    bot = "└" + "─" * w + "┘"
    return top, mid, bot


def single_line_node(name: str, width: int) -> str:
    """One line: [ name ] for single-arrow flow."""
    w = max(width, 2)
    content = name[:w].ljust(w)[:w]
    return "[" + content + "]"


def status_label(status: str) -> str:
    """Turn status into a display label (Healthy, Planned, etc.)."""
    if status in ("implemented", "healthy"):
        return "Healthy"
    if status in ("design_only", "planned"):
        return "Planned"
    if status == "partial":
        return "Partial"
    if status in ("drift", "deviation"):
        return "Deviation"
    if status == "extra":
        return "extra"
    return status


def status_color_tag(status: str) -> str:
    """Return Rich color tag for status."""
    if status in ("implemented", "healthy"):
        return "green"
    if status in ("design_only", "planned"):
        return "grey70"
    if status == "partial":
        return "yellow"
    if status in ("drift", "deviation"):
        return "red"
    if status == "extra":
        return "cyan"
    return "white"


def progress_bar(pct: float, width: int = 6) -> str:
    """ASCII bar, e.g. [==  ] for 40%."""
    fill = max(0, min(100, int(pct))) * width // 100
    return "[" + "=" * fill + " " * (width - fill) + "]"


def status_label_markup(status: str, text: Optional[str] = None) -> str:
    plain = text if text is not None else status_label(status)
    tag = status_color_tag(status)
    return f"[{tag}]{plain}[/]"


def order_entities_by_flow(
    entities: List[Dict[str, Any]],
    contracts: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Order entities by contract flow; append the rest."""
    id_to_ent: Dict[str, Dict[str, Any]] = {}
    for e in entities:
        eid = e.get("id")
        if eid:
            id_to_ent[eid] = e
    ordered: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for contract in contracts:
        from_id = contract.get("from")
        to_id = contract.get("to")
        for eid in (from_id, to_id):
            if eid and eid not in seen and eid in id_to_ent:
                ordered.append(id_to_ent[eid])
                seen.add(eid)
    for e in entities:
        eid = e.get("id")
        if eid and eid not in seen:
            ordered.append(e)
    return ordered[:12]


def component_type_color(comp: Dict[str, Any], name: str) -> str:
    """Color for an entity. One accent for all."""
    return ACCENT_BLUE


def item_display_name(item: Any, max_len: int = 60) -> str:
    """Turn goal/requirement (dict or string) into one display string."""
    if item is None:
        return ""
    if isinstance(item, dict):
        return (item.get("name") or item.get("id") or str(item))[:max_len]
    return str(item)[:max_len]
