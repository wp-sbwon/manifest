"""
Stateless view content builders for Manifest View.

Pure functions that take manifest_dir, blueprint, or other data and return
strings or Rich renderables. Used by app.py for Diagram, Files, Mission,
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
from manifest.core.task_constants import status_display_label

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


def blueprint_features_by_component(blueprint: Dict[str, Any]) -> Dict[str, List[str]]:
    """Map component id to feature names that use it. Top-layer entities = features, children = entity_ids."""
    comp_to_features: Dict[str, List[str]] = {}
    for e in top_layer_entities(blueprint):
        name = entity_display_name(e) or e.get("name") or e.get("id") or "?"
        for cid in e.get("children") or []:
            comp_to_features.setdefault(cid, []).append(name)
    return comp_to_features


def feature_status_from_entities(
    blueprint: Dict[str, Any],
    entity_status: Dict[str, str],
) -> Dict[str, str]:
    """Status per feature id (healthy, planned, partial, deviation). Top-layer entities = features."""
    out: Dict[str, str] = {}
    for e in top_layer_entities(blueprint):
        fid = e.get("id")
        ent_ids = list(e.get("children") or [])
        if not fid:
            continue
        if not ent_ids:
            out[fid] = "planned"
            continue
        statuses = [entity_status.get(eid, "planned") for eid in ent_ids]
        if any(s == "deviation" for s in statuses):
            out[fid] = "deviation"
        elif all(s == "healthy" for s in statuses):
            out[fid] = "healthy"
        elif all(s == "planned" for s in statuses):
            out[fid] = "planned"
        else:
            out[fid] = "partial"
    return out


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


def task_status_color_tag(status: str) -> str:
    """Color for task lifecycle status."""
    s = (status or "").strip().lower()
    if s == "pending":
        return "#b8860b"
    if s == "in_progress":
        return "#58a6ff"
    if s == "paused":
        return "orange1"
    if s == "blocked":
        return "red"
    if s == "completed":
        return "green"
    if s == "cancelled":
        return "grey50"
    return "#8b949e"


def task_status_markup(status: str) -> str:
    """Task status label with color in brackets."""
    raw = status or "?"
    label = status_display_label(raw)
    tag = task_status_color_tag(raw)
    return f" [dim]│[/] [{tag}]{label}[/] [dim]│[/] "


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
    """Color by type: blue=module, cyan=method, magenta=gateway."""
    nm = (name or "").upper()
    typ = (comp.get("type") or "").lower()
    if any(x in nm for x in ("PARSER", "FORMATTER", "CLI", "INPUT", "OUTPUT", "GATEWAY")):
        return "magenta"
    if typ == "function" or "method" in nm:
        return "cyan"
    return ACCENT_BLUE


def item_display_name(item: Any, max_len: int = 60) -> str:
    """Turn goal/requirement (dict or string) into one display string."""
    if item is None:
        return ""
    if isinstance(item, dict):
        return (item.get("name") or item.get("id") or str(item))[:max_len]
    return str(item)[:max_len]
