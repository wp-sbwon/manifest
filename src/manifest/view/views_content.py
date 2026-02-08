"""
Stateless view content builders for Manifest View.

Pure functions that take manifest_dir, blueprint, or other data and return
strings or Rich renderables. Used by app.py for Diagram, Files, Mission,
Inspector, and sidebar content. Keeps app.py focused on lifecycle and state.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Set, Union

from rich.table import Table
from rich.console import RenderableType

from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
from manifest.audit.entity_schema import (
    PROJECT_ROOT_ID,
    entity_display_name,
    contracts_from_entities,
    top_layer_entities,
    root_intent,
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


def render_blueprint_diagram(
    blueprint: Dict[str, Any],
    title: str = "Design",
    comp_status: Optional[Dict[str, str]] = None,
) -> str:
    """One line of entity nodes with arrows between."""
    lines: List[str] = []
    entities_display = entities_for_display(blueprint.get("entities", []))
    contracts = contracts_from_entities(blueprint.get("entities", []))
    if not entities_display and not contracts:
        return ""
    id_to_name: Dict[str, str] = {}
    name_len = 24
    for e in entities_display:
        eid = e.get("id")
        name = (e.get("name") or eid or "?")[:name_len]
        if eid:
            id_to_name[eid] = name
    entity_list = order_entities_by_flow(entities_display, contracts) if contracts else entities_display[:12]
    if not entity_list:
        lines.append(title)
        lines.append("  (no nodes)")
        return "\n".join(lines)
    arrow = " ──► "
    node_parts: List[str] = []
    for e in entity_list:
        cid = e.get("id")
        name = id_to_name.get(cid, (e.get("name") or cid or "?")[:name_len])
        w = max(len(name), 2)
        st = (comp_status or {}).get(cid or "", "?")
        tag = status_color_tag(st)
        node_parts.append(f"[{tag}]{single_line_node(name, w)}[/]")
    lines.append(title)
    lines.append("  " + arrow.join(node_parts))
    return "\n".join(lines).strip()


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


def render_features_summary_from_blueprint(
    blueprint: Dict[str, Any],
    comp_names: Optional[Dict[str, str]] = None,
) -> str:
    """Features summary from blueprint (top-layer entities). Blueprint-only; no intent.json features."""
    lines: List[str] = []
    intent = root_intent(blueprint)
    sprint = (intent.get("sprint") or "").strip()
    lines.append(f"Sprint: {sprint[:50] if sprint else '(none)'}")
    features = top_layer_entities(blueprint)
    comp_names = comp_names or {}
    if not features:
        lines.append("Features: (none)")
        return "\n".join(lines)
    lines.append("Features")
    for i, e in enumerate(features[:20], 1):
        name = (entity_display_name(e) or e.get("name") or e.get("id") or "?")[:35]
        child_ids = list(e.get("children") or [])
        if child_ids and comp_names:
            names = [comp_names.get(cid, cid)[:12] for cid in child_ids[:5]]
            comp_str = ", ".join(names)
            if len(child_ids) > 5:
                comp_str += f" +{len(child_ids) - 5}"
            lines.append(f"  {i}. {name} → {comp_str}")
        else:
            lines.append(f"  {i}. {name}")
    if len(features) > 20:
        lines.append(f"  ... and {len(features) - 20} more")
    return "\n".join(lines)


def render_intent_summary(
    intent: Dict[str, Any],
    comp_names: Optional[Dict[str, str]] = None,
) -> str:
    """Sprint and features from intent.json shape (legacy). Prefer render_features_summary_from_blueprint."""
    lines: List[str] = []
    sprint = (intent.get("sprint") or "").strip()
    lines.append(f"Sprint: {sprint[:50] if sprint else '(none)'}")
    features = intent.get("features", []) or []
    comp_names = comp_names or {}
    if not features:
        lines.append("Features: (none)")
        return "\n".join(lines)
    lines.append("Features")
    for i, f in enumerate(features[:20], 1):
        if isinstance(f, dict):
            name = (f.get("name") or f.get("id") or "?")[:35]
            comp_ids = f.get("entity_ids", []) or []
            if comp_ids and comp_names:
                names = [comp_names.get(cid, cid)[:12] for cid in comp_ids[:5]]
                comp_str = ", ".join(names)
                if len(comp_ids) > 5:
                    comp_str += f" +{len(comp_ids) - 5}"
                lines.append(f"  {i}. {name} → {comp_str}")
            else:
                lines.append(f"  {i}. {name}")
        else:
            lines.append(f"  {i}. {str(f)[:40]}")
    if len(features) > 20:
        lines.append(f"  ... and {len(features) - 20} more")
    return "\n".join(lines)


def load_setup_md(manifest_dir: Path) -> str:
    """Load .manifest/setup.md or say how to add it."""
    for name in ("setup.md", "logic.md", "how_it_works.md"):
        path = manifest_dir / name
        if path.exists():
            try:
                return path.read_text(encoding="utf-8").strip() or "(empty)"
            except Exception as e:
                logger.debug("load_setup_md read failed for %s: %s", path, e)
                return "(read failed)"
    return "(Add .manifest/setup.md to describe setup and logic, e.g. OpenCode/Podman requirements.)"


def render_modules_and_methods(manifest_dir: Path, max_rows: int = 40) -> Union[str, RenderableType]:
    """Table of modules and methods from blueprint_code."""
    from manifest.audit.blueprint.manifest_filenames import BLUEPRINT_CODE_FILE
    path = manifest_dir / BLUEPRINT_CODE_FILE
    if not path.exists():
        return "(no blueprint_code — run app or sync refresh)"
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.debug("render_modules_and_methods load failed: %s", e)
        return "(failed to load blueprint_code)"
    components = entities_for_display(data.get("entities", []))
    if not components:
        return "(no entities in blueprint_code)"
    tbl = Table(show_header=True, header_style="bold cyan", box=None)
    tbl.add_column("Module", style="dim", max_width=36)
    tbl.add_column("Name", max_width=28)
    tbl.add_column("Type", width=8)
    tbl.add_column("Methods", max_width=32)
    for comp in components[:max_rows]:
        if not isinstance(comp, dict):
            continue
        mod = (comp.get("module_path") or comp.get("id", "").replace("comp-", "").rsplit("-", 1)[0])[:36]
        name = (comp.get("name") or "?")[:28]
        typ = (comp.get("type") or "?")[:8]
        methods = comp.get("methods") or []
        meth_str = ", ".join(methods[:4]) if methods else "—"
        if len(methods) > 4:
            meth_str += f" +{len(methods) - 4}"
        tbl.add_row(mod, name, typ, meth_str[:32])
    if len(components) > max_rows:
        tbl.add_row("...", f"+{len(components) - max_rows} more", "", "")
    return tbl


def render_deviation_summary(
    comp_status: Dict[str, str],
    conflict_count: int = 0,
) -> str:
    """Status: Healthy, Partial, Deviation, Planned."""
    healthy_n = sum(1 for s in comp_status.values() if s == "healthy")
    planned_n = sum(1 for s in comp_status.values() if s == "planned")
    partial_n = sum(1 for s in comp_status.values() if s == "partial")
    deviation_n = sum(1 for s in comp_status.values() if s == "deviation")
    lines = [
        "Status",
        f"  {status_label_markup('healthy', f'Healthy: {healthy_n}')}",
        f"  {status_label_markup('planned', f'Planned: {planned_n}')}",
        f"  {status_label_markup('partial', f'Partial: {partial_n}')}",
        f"  {status_label_markup('deviation', f'Deviation: {deviation_n}')}",
    ]
    if conflict_count > 0:
        lines.append(f"  Mismatches: {conflict_count}")
    return "\n".join(lines)


def render_design_history_short(manifest_dir: Path, max_entries: int = 10) -> str:
    """Short design history list."""
    try:
        from manifest.core.design_history import get_design_history
        entries = get_design_history(manifest_dir)
        if not entries:
            return "Design history: (none)"
        lines = [f"Design history ({len(entries)} entries)"]
        for entry in entries[:max_entries]:
            doc = entry.get("doc", "?")
            path = entry.get("path", "?")
            ts = (entry.get("timestamp") or "?")[:10]
            lines.append(f"  [{doc}] {path} | {ts}")
        if len(entries) > max_entries:
            lines.append(f"  ... and {len(entries) - max_entries} more")
        return "\n".join(lines)
    except Exception as e:
        logger.debug("render_design_history_short failed: %s", e)
        return "Design history: (unavailable)"


def render_prd_summary(prd: Optional[Dict[str, Any]]) -> str:
    """PRD: title + sections or requirements. Empty shows (none)."""
    if not prd:
        return "(no prd.json)"
    lines: List[str] = []
    title = prd.get("title") or prd.get("name") or "Product Requirements"
    lines.append(title[:60])
    sections = prd.get("sections", [])
    if isinstance(sections, list) and sections:
        for i, sec in enumerate(sections[:12], 1):
            name = item_display_name(sec, 50) if isinstance(sec, dict) else str(sec)[:50]
            lines.append(f"  {i}. {name}")
        if len(sections) > 12:
            lines.append(f"  ... and {len(sections) - 12} more")
    else:
        reqs = prd.get("requirements", [])
        if isinstance(reqs, list) and reqs:
            for i, r in enumerate(reqs[:12], 1):
                lines.append(f"  {i}. {item_display_name(r, 50)}")
            if len(reqs) > 12:
                lines.append(f"  ... and {len(reqs) - 12} more")
        else:
            lines.append("  (no sections or requirements)")
    return "\n".join(lines)
