"""
Stateless view content builders. Pure functions returning strings or Rich renderables.
"""
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Set, Union

from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
from manifest.audit.blueprint.status_enums import ImplementationStatus
from manifest.audit.blueprint.view_schema import (
    _parent_aggregate_status_from_children,
    _root_status_from_children,
)
from manifest.audit.entity_schema import (
    PROJECT_ROOT_ID,
    entity_display_name,
    contracts_from_entities,
    top_layer_entities,
)
from manifest.core.logger import get_logger

logger = get_logger(__name__)

ACCENT_BLUE = "bright_blue"


def entities_for_display(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Flat dicts with id, name, file, type, methods."""
    out: List[Dict[str, Any]] = []
    for e in entities or []:
        if (e.get("id") or "") == PROJECT_ROOT_ID:
            continue
        name = entity_display_name(e) or "?"
        file_path = e.get("symbol") or e.get("file", "")
        parts = (file_path or "").replace("\\", "/").split("/")
        module_path = "/".join(parts[:-1]) if len(parts) > 1 else (parts[0] if parts else "")
        out.append({
            "id": e.get("id"),
            "name": name,
            "file": file_path,
            "module_path": module_path,
            "type": e.get("type", "?"),
            "methods": e.get("methods", []),
            "attributes": e.get("attributes", []),
            "line": e.get("line"),
            "algorithm": e.get("algorithm"),
            "design_pattern": e.get("design_pattern"),
            "complexity": e.get("complexity"),
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


def parent_aggregate_status_from_children(
    blueprint: Dict[str, Any],
    entity_status: Dict[str, str],
) -> Dict[str, str]:
    """Aggregate status per parent entity id (root's children) from its children's statuses."""
    return _parent_aggregate_status_from_children(blueprint, entity_status)


def root_status_from_children(blueprint: Dict[str, Any], entity_status: Dict[str, str]) -> str:
    """Root status from its direct children (same aggregation as parent_aggregate)."""
    return _root_status_from_children(blueprint, entity_status)


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
    if status in (ImplementationStatus.HEALTHY.value, "implemented"):
        return "Healthy"
    if status in (ImplementationStatus.PLANNED.value, "design_only"):
        return "Planned"
    if status == ImplementationStatus.PARTIAL.value:
        return "Partial"
    if status in (ImplementationStatus.DEVIATION.value, "drift"):
        return "Deviation"
    if status == ImplementationStatus.EXTRA.value:
        return "extra"
    return status


def status_color_tag(status: str) -> str:
    if status in (ImplementationStatus.HEALTHY.value, "implemented"):
        return "green"
    if status in (ImplementationStatus.PLANNED.value, "design_only"):
        return "grey70"
    if status == ImplementationStatus.PARTIAL.value:
        return "yellow"
    if status in (ImplementationStatus.DEVIATION.value, "drift"):
        return "red"
    if status == ImplementationStatus.EXTRA.value:
        return "cyan"
    return "white"


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
