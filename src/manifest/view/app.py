"""Manifest View: Diagram, Files, Timeline, Mission. D=Differences, Tab=next, S=refresh."""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Set, Union
from enum import Enum

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, Container, Horizontal
from textual.widgets import Static, Header, Footer
from textual.binding import Binding

from manifest.core.state_manager import StateManager
from manifest.core.task_manager import TaskManager
from manifest.core.task_constants import status_display_label
from manifest.core.git_manager import GitManager
from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
from manifest.audit.blueprint.blueprint_synchronizer import BlueprintSynchronizer
from manifest.audit.blueprint.blueprint_comparator import BlueprintComparator
from manifest.audit.metadata.architecture_metadata import load_architecture_with_metadata
from manifest.core.logger import get_logger
from manifest.view.file_watcher import ViewFileWatcher
from manifest.audit.monitoring.deviation_monitor import DeviationMonitor

logger = get_logger(__name__)


def _blueprint_component_names(manifest_dir: Path) -> Dict[str, str]:
    """Get display name for each component from blueprint."""
    try:
        top_down = BlueprintLoader.load_blueprint(
            manifest_dir, with_metadata=False, default_source="llm_design"
        )
        out: Dict[str, str] = {}
        for c in top_down.get("components", []):
            cid = c.get("id")
            name = (c.get("name") or cid or "?")[:30]
            if cid:
                out[cid] = name
        return out
    except Exception:
        return {}


def _architecture_features_by_component(architecture: Dict[str, Any]) -> Dict[str, List[str]]:
    """Map component id to feature names that use it."""
    comp_to_features: Dict[str, List[str]] = {}
    for feat in architecture.get("features", []) or []:
        if not isinstance(feat, dict):
            continue
        name = feat.get("name") or feat.get("id") or "?"
        for cid in feat.get("components", []) or []:
            comp_to_features.setdefault(cid, []).append(name)
    return comp_to_features


def _feature_status_from_components(
    architecture: Dict[str, Any],
    comp_status: Dict[str, str],
) -> Dict[str, str]:
    """Get status per feature from its components (healthy, planned, partial, deviation)."""
    out: Dict[str, str] = {}
    for feat in architecture.get("features", []) or []:
        if not isinstance(feat, dict):
            continue
        fid = feat.get("id")
        comp_ids = feat.get("components", []) or []
        if not fid:
            continue
        if not comp_ids:
            out[fid] = "planned"
            continue
        statuses = [comp_status.get(cid, "planned") for cid in comp_ids]
        if any(s == "deviation" for s in statuses):
            out[fid] = "deviation"
        elif all(s == "healthy" for s in statuses):
            out[fid] = "healthy"
        elif all(s == "planned" for s in statuses):
            out[fid] = "planned"
        else:
            out[fid] = "partial"
    return out


def _box(name: str, width: int) -> Tuple[str, str, str]:
    """Three lines for a box (top/mid/bot)."""
    w = max(width, 2)
    content = name[:w].ljust(w)[:w]
    top = "┌" + "─" * w + "┐"
    mid = "│" + content + "│"
    bot = "└" + "─" * w + "┘"
    return top, mid, bot


def _single_line_node(name: str, width: int) -> str:
    """One line: [ name ] for single-arrow flow (no triple arrows)."""
    w = max(width, 2)
    content = name[:w].ljust(w)[:w]
    return "[" + content + "]"


def _status_label(status: str) -> str:
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


def _status_color_tag(status: str) -> str:
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


def _progress_bar(pct: float, width: int = 6) -> str:
    """ASCII bar, e.g. [==  ] for 40%."""
    fill = max(0, min(100, int(pct))) * width // 100
    return "[" + "=" * fill + " " * (width - fill) + "]"


def _status_label_markup(status: str, text: Optional[str] = None) -> str:
    plain = text if text is not None else _status_label(status)
    tag = _status_color_tag(status)
    return f"[{tag}]{plain}[/]"


def _task_status_color_tag(status: str) -> str:
    """Color for task lifecycle (not design vs code)."""
    if status == "pending":
        return "dim"
    if status == "in_progress":
        return "cyan"
    if status == "paused":
        return "orange1"
    if status == "blocked":
        return "red"
    if status == "completed":
        return "green"
    if status == "cancelled":
        return "grey50"
    return "white"


def _task_status_markup(status: str) -> str:
    """Task status label with color, in brackets."""
    label = status_display_label(status)
    tag = _task_status_color_tag(status)
    return f" [dim]│[/] [{tag}]{label}[/] [dim]│[/] "


def _order_components_by_flow(
    components: List[Dict[str, Any]],
    contracts: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Order components by contract flow; add the rest."""
    id_to_comp: Dict[str, Dict[str, Any]] = {}
    for c in components:
        cid = c.get("id")
        if cid:
            id_to_comp[cid] = c
    ordered: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for contract in contracts:
        from_id = contract.get("from")
        to_id = contract.get("to")
        for cid in (from_id, to_id):
            if cid and cid not in seen and cid in id_to_comp:
                ordered.append(id_to_comp[cid])
                seen.add(cid)
    for c in components:
        cid = c.get("id")
        if cid and cid not in seen:
            ordered.append(c)
    return ordered[:12]


def _render_blueprint_diagram(
    blueprint: Dict[str, Any],
    title: str = "Design",
    comp_status: Optional[Dict[str, str]] = None,
) -> str:
    """One line of component nodes with arrows between."""
    lines: List[str] = []
    components = blueprint.get("components", [])
    contracts = blueprint.get("contracts", [])
    if not components and not contracts:
        return ""
    id_to_name: Dict[str, str] = {}
    name_len = 24
    for c in components:
        cid = c.get("id")
        name = (c.get("name") or cid or "?")[:name_len]
        if cid:
            id_to_name[cid] = name
    comp_list = _order_components_by_flow(components, contracts) if contracts else components[:12]
    if not comp_list:
        lines.append(title)
        lines.append("  (no components)")
        return "\n".join(lines)
    arrow = " ──► "
    node_parts: List[str] = []
    for c in comp_list:
        cid = c.get("id")
        name = id_to_name.get(cid, (c.get("name") or cid or "?")[:name_len])
        w = max(len(name), 2)
        st = (comp_status or {}).get(cid or "", "?")
        tag = _status_color_tag(st)
        node_parts.append(f"[{tag}]{_single_line_node(name, w)}[/]")
    lines.append(title)
    lines.append("  " + arrow.join(node_parts))
    return "\n".join(lines).strip()


# Lighter blue for readability (OpenCode-style accent); use in Rich markup.
ACCENT_BLUE = "bright_blue"


def _component_type_color(comp: Dict[str, Any], name: str) -> str:
    """Color by type: blue=module, cyan=method, magenta=gateway."""
    nm = (name or "").upper()
    typ = (comp.get("type") or "").lower()
    if any(x in nm for x in ("PARSER", "FORMATTER", "CLI", "INPUT", "OUTPUT", "GATEWAY")):
        return "magenta"
    if typ == "function" or "method" in nm:
        return "cyan"
    return ACCENT_BLUE


def _order_components_for_diagram(
    components: List[Dict[str, Any]],
    contracts: List[Dict[str, Any]],
    blueprint: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Order components for diagram: prefer zone (server) order when present, else contract flow."""
    zones = blueprint.get("zones") or {}
    server_ids = zones.get("server") or []
    if server_ids:
        id_to_comp = {c.get("id"): c for c in components if c.get("id")}
        ordered = [id_to_comp[cid] for cid in server_ids if cid in id_to_comp]
        seen = {c.get("id") for c in ordered}
        for c in components:
            if c.get("id") and c.get("id") not in seen:
                ordered.append(c)
        return ordered[:14]
    return _order_components_by_flow(components, contracts) if contracts else components[:14]


def _render_architecture_flow_diagram(
    blueprint: Dict[str, Any],
    comp_status: Dict[str, str],
    box_width: int = 28,
) -> str:
    """Vertical flow diagram: title 'ARCHITECTURE FLOW', then one box per component (■ = status).

    Intended view (mock): blueprint.components ordered by blueprint.zones.server when present,
    so flow is e.g. main → add → sub → mul → format_result. Data from blueprint.json + comp_status
    from design vs code comparison. If title or order looked wrong, cause was (1) Rich markup
    parsing '[ARCHITECTURE FLOW]' as a style tag, (2) contract-first order putting format_result
    before sub/mul; zone order fixes the latter.
    """
    lines: List[str] = []
    components = blueprint.get("components", []) or []
    contracts = blueprint.get("contracts", []) or []
    comp_list = _order_components_for_diagram(components, contracts, blueprint)
    if not comp_list:
        return "  (no components)"
    S = "■"
    # Title bar: literal "ARCHITECTURE FLOW" (no Rich tag; [ARCHITECTURE FLOW] would be parsed as style)
    lines.append("[white]  ┌" + "─" * (box_width + 2) + "┐[/]")
    lines.append("[white]  │  ARCHITECTURE FLOW" + " " * max(0, box_width - 21) + "│[/]")
    lines.append("[white]  └" + "─" * (box_width + 2) + "┘[/]")
    for i, c in enumerate(comp_list):
        cid = c.get("id")
        raw_name = (c.get("name") or cid or "?")
        name = raw_name[: box_width - 6].strip()
        st = comp_status.get(cid or "", "planned")
        status_tag = _status_color_tag(st)
        type_tag = _component_type_color(c, raw_name)
        w = max(len(name) + 6, 12)
        w = min(w, box_width + 2)
        top = "  ┌" + "─" * (w - 2) + "┐"
        # Mid: │ ■ name │ with type color for box, status color for ■
        mid = f"  [{type_tag}]│ [/][{status_tag}]{S}[/] [{type_tag}]{name:<{w-6}}│[/]"
        bot = "  └" + "─" * (w - 2) + "┘"
        lines.append(f"  [{type_tag}]{top}[/]")
        lines.append(mid)
        lines.append(f"  [{type_tag}]{bot}[/]")
        if i < len(comp_list) - 1:
            lines.append(" " * (w // 2 + 2) + "│")
            lines.append(" " * (w // 2 + 2) + "▼")
    return "\n".join(lines)


def _render_project_map(
    architecture: Dict[str, Any],
    blueprint: Dict[str, Any],
    comp_names: Dict[str, str],
    comp_status: Dict[str, str],
    feature_status: Dict[str, str],
    manifest_dir: Optional[Path] = None,
) -> str:
    """Diagram: vertical flow from blueprint and status."""
    return _render_architecture_flow_diagram(blueprint, comp_status)


def _render_unified_architecture_code_diagram(
    architecture: Dict[str, Any],
    blueprint: Dict[str, Any],
    comp_names: Dict[str, str],
    comp_status: Dict[str, str],
    feature_status: Dict[str, str],
    manifest_dir: Optional[Path] = None,
) -> str:
    """Diagram: vertical flow with type and status colors."""
    diagram = _render_project_map(
        architecture, blueprint, comp_names, comp_status, feature_status, manifest_dir
    )
    return diagram if diagram else "(no architecture or blueprint)"


def _item_display_name(item: Any, max_len: int = 60) -> str:
    """Turn goal/requirement (dict or string) into one display string."""
    if item is None:
        return ""
    if isinstance(item, dict):
        return (item.get("name") or item.get("id") or str(item))[:max_len]
    return str(item)[:max_len]


def _render_intent_summary(
    intent: Dict[str, Any],
    comp_names: Optional[Dict[str, str]] = None,
) -> str:
    """Sprint and features; show (none) when empty."""
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
            comp_ids = f.get("components", []) or []
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


def _load_setup_md(manifest_dir: Path) -> str:
    """Load .manifest/setup.md or say how to add it."""
    for name in ("setup.md", "logic.md", "how_it_works.md"):
        path = manifest_dir / name
        if path.exists():
            try:
                return path.read_text(encoding="utf-8").strip() or "(empty)"
            except Exception:
                return "(read failed)"
    return "(Add .manifest/setup.md to describe setup and logic, e.g. OpenCode/Podman requirements.)"


def _render_modules_and_methods(manifest_dir: Path, max_rows: int = 40) -> Union[str, RenderableType]:
    """Table of modules and methods from blueprint_code.json."""
    path = manifest_dir / "blueprint_code.json"
    if not path.exists():
        return "(no blueprint_code.json — run app or sync refresh)"
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return "(failed to load blueprint_code.json)"
    components = data.get("components", [])
    zones = data.get("zones", {}) or {}
    # If no components list, derive from zones: "comp-module_path-Name" -> module, name
    if not components and zones:
        seen: Set[str] = set()
        for zone_list in zones.values():
            if not isinstance(zone_list, list):
                continue
            for comp_id in zone_list:
                if not isinstance(comp_id, str) or not comp_id.startswith("comp-"):
                    continue
                rest = comp_id[5:]  # drop "comp-"
                if "-" not in rest:
                    continue
                last_dash = rest.rfind("-")
                module_path = rest[:last_dash]
                name = rest[last_dash + 1:]
                key = (module_path, name)
                if key not in seen:
                    seen.add(key)
                    components.append({
                        "id": comp_id,
                        "module_path": module_path,
                        "name": name,
                        "type": "class",
                        "methods": [],
                    })
    if not components:
        return "(no components in blueprint_code)"
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


def _render_deviation_summary(
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
        f"  {_status_label_markup('healthy', f'Healthy: {healthy_n}')}",
        f"  {_status_label_markup('planned', f'Planned: {planned_n}')}",
        f"  {_status_label_markup('partial', f'Partial: {partial_n}')}",
        f"  {_status_label_markup('deviation', f'Deviation: {deviation_n}')}",
    ]
    if conflict_count > 0:
        lines.append(f"  Mismatches: {conflict_count}")
    return "\n".join(lines)


def _render_design_history_short(manifest_dir: Path, max_entries: int = 10) -> str:
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
    except Exception:
        return "Design history: (unavailable)"


def _render_prd_summary(prd: Optional[Dict[str, Any]]) -> str:
    """PRD: title + sections or requirements. Empty shows (none)."""
    if not prd:
        return "(no prd.json)"
    lines: List[str] = []
    title = prd.get("title") or prd.get("name") or "Product Requirements"
    lines.append(title[:60])
    sections = prd.get("sections", [])
    if isinstance(sections, list) and sections:
        for i, sec in enumerate(sections[:12], 1):
            name = _item_display_name(sec, 50) if isinstance(sec, dict) else str(sec)[:50]
            lines.append(f"  {i}. {name}")
        if len(sections) > 12:
            lines.append(f"  ... and {len(sections) - 12} more")
    else:
        reqs = prd.get("requirements", [])
        if isinstance(reqs, list) and reqs:
            for i, r in enumerate(reqs[:12], 1):
                lines.append(f"  {i}. {_item_display_name(r, 50)}")
            if len(reqs) > 12:
                lines.append(f"  ... and {len(reqs) - 12} more")
        else:
            lines.append("  (no sections or requirements)")
    return "\n".join(lines)


class ViewType(Enum):
    """View: Diagram, Files, Timeline, Mission. History = Timeline."""
    DIAGRAM = "diagram"
    FILES = "files"
    TIMELINE = "timeline"
    HISTORY = "history"  # alias: same content as TIMELINE (Design + Git timeline)
    MISSION_CONTROL = "mission_control"
    ARCHITECT = "architect"
    BLUEPRINT = "blueprint"
    INSPECTOR = "inspector"


class InspectorMode(Enum):
    """Right panel: Design or Differences (D). Detail = selected node."""
    DESIGN = "design"
    DIFFERENCES = "differences"
    VISUAL = "visual"
    DATA = "data"
    DEVIATION = "deviation"
    DETAIL = "detail"


# App version for footer; not bumped until release (effectively 0.0 during development).
APP_VERSION = "0.0"


class ManifestViewApp(App[None]):
    TITLE = "Manifest View"
    SUB_TITLE = ""
    CSS = """
    Screen { background: #0d1117; color: #c9d1d9; }
    #header-strip { height: auto; padding: 0 1; background: #161b22; border: solid #30363d; }
    #body-row { height: 1fr; }
    #sidebar { width: 1fr; min-width: 46; max-width: 52; border-right: solid #30363d; background: #0d1117; }
    #sidebar ScrollableContainer { padding: 0 1; }
    #main { width: 3fr; padding: 0; }
    #main-tab-bar { height: auto; padding: 0 1; background: #161b22; border-bottom: solid #30363d; }
    #main-scroll { padding: 1 2; }
    #info-hub { width: 1fr; min-width: 48; max-width: 62; border-left: solid #30363d; background: #0d1117; }
    #info-hub ScrollableContainer { padding: 0 2; }
    #info-hub-footer { height: 1; padding: 0 1; border-top: solid #30363d; }
    .sidebar-section { margin-bottom: 1; padding: 0 1; border-bottom: solid #30363d; }
    #sidebar-tasks { overflow: hidden; }
    .sidebar-title { color: #58a6ff; text-style: bold; }
    .nav-item { padding: 0 1; margin-right: 1; }
    .nav-item.active { background: #1f6feb; color: white; }
    #app-version-strip { height: 1; padding: 0 1; background: #161b22; border-top: solid #30363d; }
    #app-version-strip Horizontal { width: 100%; }
    #footer-spacer { width: 1fr; }
    """

    BINDINGS = [
        Binding("1", "switch_view('Diagram')", "MAP", key_display="1"),
        Binding("2", "switch_view('Files')", "FILES", key_display="2"),
        Binding("3", "switch_view('Timeline')", "HISTORY", key_display="3"),
        Binding("4", "switch_view('Mission')", "MISSION", key_display="4"),
        Binding("tab", "select_next_node", "CYCLE", key_display="Tab"),
        Binding("shift+tab", "select_prev_node", "Prev", key_display="⇧Tab"),
        Binding("d", "toggle_differences", "Design/Diff", key_display="D"),
        Binding("s", "refresh", "Refresh", key_display="S"),
        Binding("up", "select_prev_node", "Prev", key_display="↑"),
        Binding("down", "select_next_node", "Next", key_display="↓"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, manifest_dir: Optional[Path] = None, **kwargs: Any):
        super().__init__(**kwargs)
        self.manifest_dir = (manifest_dir or (Path.cwd() / ".manifest")).resolve()
        self.current_view = ViewType.DIAGRAM
        self.inspector_mode = InspectorMode.DESIGN
        self._right_panel_differences = False  # D toggles Design vs Differences
        self._last_completed_task_ids: set = set()
        self._selected_node_index: int = 0
        self._state_manager: Optional[StateManager] = None
        self._task_manager: Optional[TaskManager] = None
        self._blueprint_sync: Optional[BlueprintSynchronizer] = None
        self._git_manager: Optional[GitManager] = None
        self._blueprint_comparator: Optional[BlueprintComparator] = None

    def _get_state_manager(self) -> StateManager:
        if self._state_manager is None:
            self._state_manager = StateManager(self.manifest_dir)
        return self._state_manager

    def _get_task_manager(self) -> TaskManager:
        if self._task_manager is None:
            self._task_manager = TaskManager(self._get_state_manager())
        return self._task_manager

    def _get_blueprint_sync(self) -> BlueprintSynchronizer:
        if self._blueprint_sync is None:
            self._blueprint_sync = BlueprintSynchronizer()
        return self._blueprint_sync

    def _get_git_manager(self) -> GitManager:
        if self._git_manager is None:
            self._git_manager = GitManager(
                self.manifest_dir.parent,
                search_parent_directories=False,
            )
        return self._git_manager

    def _get_blueprint_comparator(self) -> BlueprintComparator:
        if self._blueprint_comparator is None:
            self._blueprint_comparator = BlueprintComparator()
        return self._blueprint_comparator

    def _get_tasks_and_sprints_from_manifest(self) -> Tuple[List[Dict[str, Any]], List[Any]]:
        """Tasks and sprints from state."""
        from manifest.core.task_status_observer import observe_tasks_with_status
        state_mgr = self._get_state_manager()
        tasks = state_mgr.get_task_checklist()
        active_task_ids = state_mgr.get_active_task_ids()
        tasks = observe_tasks_with_status(tasks, active_task_ids)
        sprint_ids = state_mgr.list_sprints()
        sprints = [{"id": sid} for sid in sprint_ids]
        return tasks, sprints

    def _get_selectable_nodes(self) -> List[Tuple[str, str, Dict[str, Any]]]:
        """List of nodes: root, then features, then components (1-based index)."""
        root_fallback: Tuple[str, str, Dict[str, Any]] = (
            "root",
            "PROJECT_ROOT",
            {"id": "PROJECT_ROOT", "name": "System Core", "description": "Project root."},
        )
        nodes: List[Tuple[str, str, Dict[str, Any]]] = []
        try:
            arch_file = self.manifest_dir / "architecture.json"
            architecture = load_architecture_with_metadata(arch_file) if arch_file.exists() else {}
            root_desc = (architecture.get("mission") or "").strip() or "Project root."
            nodes.append((
                "root",
                "PROJECT_ROOT",
                {"id": "PROJECT_ROOT", "name": "System Core", "description": root_desc},
            ))
            for feat in architecture.get("features", []) or []:
                if isinstance(feat, dict) and feat.get("id"):
                    nodes.append(("feature", feat["id"], feat))
            top_down = BlueprintLoader.load_blueprint(
                self.manifest_dir,
                with_metadata=True,
                default_source="llm_design",
            )
            for comp in top_down.get("components", []) or []:
                if isinstance(comp, dict) and comp.get("id"):
                    nodes.append(("component", comp["id"], comp))
        except Exception as e:
            logger.debug("Selectable nodes failed: %s", e)
            if not nodes:
                nodes = [root_fallback]
        return nodes

    def _selected_node_is_deviating(self) -> bool:
        """True if selected node is in deviation."""
        nodes = self._get_selectable_nodes()
        if not nodes:
            return False
        idx = max(0, min(self._selected_node_index - 1, len(nodes) - 1))
        kind, nid, data = nodes[idx]
        if kind == "root":
            return False
        if kind == "feature":
            arch_file = self.manifest_dir / "architecture.json"
            architecture = load_architecture_with_metadata(arch_file)
            top_down = BlueprintLoader.load_blueprint(
                self.manifest_dir, with_metadata=True, default_source="llm_design"
            )
            bottom_up = BlueprintLoader.load_code_blueprint(self.manifest_dir)
            status_info = self._get_blueprint_sync().calculate_implementation_status(
                top_down, bottom_up, architecture
            )
            comp_status = status_info.get("component_statuses", {})
            feat_status = _feature_status_from_components(architecture, comp_status)
            return feat_status.get(nid) == "deviation"
        # component
        arch_file = self.manifest_dir / "architecture.json"
        architecture = load_architecture_with_metadata(arch_file)
        top_down = BlueprintLoader.load_blueprint(
            self.manifest_dir, with_metadata=True, default_source="llm_design"
        )
        bottom_up = BlueprintLoader.load_code_blueprint(self.manifest_dir)
        status_info = self._get_blueprint_sync().calculate_implementation_status(
            top_down, bottom_up, architecture
        )
        comp_status = status_info.get("component_statuses", {})
        return comp_status.get(nid) == "deviation"

    def action_select_prev_node(self) -> None:
        """Select previous node (Up)."""
        nodes = self._get_selectable_nodes()
        if self._selected_node_index > 0:
            self._selected_node_index -= 1
            self.refresh_view()

    def action_select_next_node(self) -> None:
        """Select next node (Down)."""
        nodes = self._get_selectable_nodes()
        if self._selected_node_index < len(nodes):
            self._selected_node_index += 1
            self.refresh_view()

    def _render_detail_content(self) -> str:
        """Detail for selected node (feature or component)."""
        nodes = self._get_selectable_nodes()
        if not nodes:
            return "No features or components. Select with ↑/↓ in Diagram view."
        if self._selected_node_index <= 0 or self._selected_node_index > len(nodes):
            n_feat = sum(1 for k, _, _ in nodes if k == "feature")
            return f"Select a feature (1–{n_feat}) or component ({n_feat + 1}–{len(nodes)}) with ↑/↓."
        kind, nid, data = nodes[self._selected_node_index - 1]
        if kind == "feature":
            lines = [
                f"Feature: {data.get('name') or nid}",
                f"  id: {nid}",
                f"  status: {data.get('status', '?')}",
                "  requirements:",
            ]
            for r in data.get("requirements", []) or []:
                name = _item_display_name(r, 60) if isinstance(r, dict) else str(r)
                lines.append(f"    - {name}")
            comp_ids = data.get("components", []) or []
            lines.append(f"  components: {', '.join(comp_ids) if comp_ids else '(none)'}")
            return "\n".join(lines)
        comp = dict(data)
        path = self.manifest_dir / "blueprint_code.json"
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    code_data = json.load(f)
                for c in code_data.get("components", []) or []:
                    if isinstance(c, dict) and c.get("id") == nid:
                        comp.update(c)
                        break
            except Exception:
                pass
        lines = [
            f"Component: {comp.get('name') or nid}",
            f"  id: {nid}",
            f"  file: {comp.get('file', '?')}",
            f"  line: {comp.get('line', '?')}",
            f"  type: {comp.get('type', '?')}",
            f"  methods: {', '.join(comp.get('methods') or []) or '—'}",
        ]
        if comp.get("algorithm"):
            lines.append(f"  algorithm: {comp.get('algorithm')}")
        if comp.get("design_pattern"):
            lines.append(f"  design_pattern: {comp.get('design_pattern')}")
        if comp.get("complexity"):
            lines.append(f"  complexity: {comp.get('complexity')}")
        if comp.get("notes"):
            lines.append(f"  notes: {comp.get('notes')}")
        return "\n".join(lines)

    def _load_diagram_view(self) -> Union[str, RenderableType]:
        """Diagram: flow and status."""
        try:
            arch_file = self.manifest_dir / "architecture.json"
            architecture = load_architecture_with_metadata(arch_file)
            comp_names = _blueprint_component_names(self.manifest_dir)
            top_down = BlueprintLoader.load_blueprint(
                self.manifest_dir,
                with_metadata=True,
                default_source="llm_design",
            )
            bottom_up = BlueprintLoader.load_code_blueprint(self.manifest_dir)
            status_info = self._get_blueprint_sync().calculate_implementation_status(
                top_down, bottom_up, architecture
            )
            comp_status = status_info.get("component_statuses", {})
            feature_status = _feature_status_from_components(architecture, comp_status)
            diagram_txt = _render_unified_architecture_code_diagram(
                architecture, top_down, comp_names, comp_status, feature_status, self.manifest_dir
            )
            return diagram_txt
        except Exception as e:
            logger.debug("Diagram view load failed: %s", e)
            return f"(load failed: {e})"

    def _load_files_view(self) -> Union[str, RenderableType]:
        """Source tree: root/ with dirs and files, dot by status."""
        try:
            bottom_up = BlueprintLoader.load_code_blueprint(self.manifest_dir)
            top_down = BlueprintLoader.load_blueprint(
                self.manifest_dir, with_metadata=True, default_source="llm_design"
            )
            arch_file = self.manifest_dir / "architecture.json"
            architecture = load_architecture_with_metadata(arch_file)
            status_info = self._get_blueprint_sync().calculate_implementation_status(
                top_down, bottom_up, architecture
            )
            comp_status = status_info.get("component_statuses", {})
            components = bottom_up.get("components", []) or []
            # Build tree: dir -> [(file, comp, status), ...]; file -> [(method, status), ...]
            dirs: Dict[str, List[Tuple[str, Dict[str, Any], str]]] = {}
            for c in components:
                if not isinstance(c, dict):
                    continue
                fp = (c.get("file") or "?").replace("\\", "/")
                parts = fp.split("/")
                dir_name = parts[0] if len(parts) > 1 else "."
                if dir_name not in dirs:
                    dirs[dir_name] = []
                dirs[dir_name].append((parts[-1] if parts else "?", c, comp_status.get(c.get("id") or "", "planned")))
            S = "■"
            lines = ["[dim]Source Tree[/]", "", "[white]root/[/]"]
            dir_list = sorted(dirs.items())
            for i, (d, items) in enumerate(dir_list):
                prefix = "└── " if i == len(dir_list) - 1 else "├── "
                tag = "magenta" if d in ("cli", "output") else ACCENT_BLUE
                lines.append(f"[{tag}]{prefix}{S}[/] {d}/")
                for j, (fname, comp, st) in enumerate(items[:12]):
                    st_tag = _status_color_tag(st)
                    sub_prefix = "    " if i == len(dir_list) - 1 else "│   "
                    lines.append(f"[dim]{sub_prefix}└── {fname}[/] ..... [{st_tag}]{S}[/]")
                    for meth in (comp.get("methods") or [])[:4]:
                        m_tag = _status_color_tag(st)
                        lines.append(f"[dim]{sub_prefix}    ├── [/][cyan]{meth}()[/] [{m_tag}]{S}[/]")
            if not dirs:
                for c in components[:20]:
                    if not isinstance(c, dict):
                        continue
                    cid = c.get("id")
                    name = (c.get("name") or cid or "?")[:28]
                    st = comp_status.get(cid or "", "planned")
                    tag = _status_color_tag(st)
                    lines.append(f"  [{tag}]{S}[/] {name}")
            return "\n".join(lines)
        except Exception as e:
            logger.debug("Files view load failed: %s", e)
            return f"(load failed: {e})"

    def _load_timeline_view(self) -> Union[str, RenderableType]:
        """Timeline: DESIGN and CODE events by time."""
        try:
            from manifest.core.design_history import get_design_history
            design_entries = get_design_history(self.manifest_dir) or []
            git_mgr = self._get_git_manager()
            commits = []
            if git_mgr.is_available():
                try:
                    commits = git_mgr.get_latest_commits(limit=20)
                except Exception:
                    pass
            events: List[Tuple[str, str, str, str]] = []
            for e in design_entries[:20]:
                ts = (e.get("timestamp") or "?")[:16].replace("T", " ")
                events.append((ts, "DESIGN", (e.get("doc") or e.get("path") or "?")[:50], ACCENT_BLUE))
            for c in commits:
                ts = (c.get("timestamp") or "?")[:16].replace("T", " ")
                msg = (c.get("message") or "?").replace("\n", " ")[:50]
                events.append((ts, "CODE", msg, "green"))
            events.sort(key=lambda x: x[0], reverse=True)
            lines = ["[dim]Project Changes Timeline[/]", ""]
            for ts, side, msg, color in events[:25]:
                lines.append(f"[dim]{ts}[/]  [{color}]{side}[/]  {msg}")
            if not events:
                lines.append("(no design or code events)")
            return "\n".join(lines)
        except Exception as e:
            logger.debug("Timeline load failed: %s", e)
            return f"(load failed: {e})"

    def _load_history_view(
        self, title_for_fallback: str = "History"
    ) -> Union[str, RenderableType]:
        """Design history and git commits as panels."""
        panels: List[RenderableType] = []
        try:
            from manifest.core.design_history import get_design_history
            design_entries = get_design_history(self.manifest_dir)
            if design_entries:
                tbl = Table(show_header=True, header_style="bold cyan", box=None)
                tbl.add_column("Doc", style="dim", width=10)
                tbl.add_column("Path", max_width=40)
                tbl.add_column("Date", style="dim", width=10)
                for entry in design_entries[:15]:
                    tbl.add_row(
                        entry.get("doc", "?"),
                        entry.get("path", "?"),
                        (entry.get("timestamp") or "?")[:10],
                    )
                if len(design_entries) > 15:
                    tbl.add_row("...", f"+{len(design_entries) - 15} more", "")
                panels.append(Panel(tbl, title=f"Design history ({len(design_entries)} entries)", border_style="cyan"))
            else:
                panels.append(Panel("(none)", title="Design history", border_style="dim"))

            git_mgr = self._get_git_manager()
            if git_mgr.is_available():
                try:
                    branch = git_mgr.get_current_branch()
                except Exception:
                    branch = "unknown"
                try:
                    commits = git_mgr.get_latest_commits(limit=20)
                except Exception:
                    commits = []
                tbl = Table(show_header=True, header_style="bold green", box=None)
                tbl.add_column("Hash", style="dim", width=8)
                tbl.add_column("Author", width=16)
                tbl.add_column("Date", style="dim", width=10)
                tbl.add_column("Message", max_width=50)
                for commit in commits:
                    tbl.add_row(
                        commit.get("short_hash", "?"),
                        (commit.get("author", "?") or "?")[:16],
                        (commit.get("timestamp", "?") or "?")[:10],
                        (commit.get("message", "?") or "?").replace("\n", " ")[:50],
                    )
                body: RenderableType = Group(Text(f"Branch: {branch}"), tbl) if commits else Text(f"Branch: {branch}\n(no commits)")
                panels.append(Panel(
                    body,
                    title=f"Git commits ({len(commits)})",
                    border_style="green",
                ))
            else:
                if not design_entries:
                    panels.append(Panel("(Git not available)", title="Git", border_style="dim"))
            if not panels:
                return Panel("(no design history; Git not available)", title=title_for_fallback, border_style="dim")
            return Group(*panels)
        except Exception as e:
            logger.debug("History view load failed: %s", e)
            return Panel(f"(load failed: {e})", title=title_for_fallback, border_style="red")

    def _load_inspector_view(self) -> str:
        """Inspect: Deviation, Visual, Data, Detail."""
        lines = []
        try:
            if self.inspector_mode == InspectorMode.DEVIATION:
                top_down = BlueprintLoader.load_blueprint(
                    self.manifest_dir,
                    with_metadata=True,
                    default_source="llm_design",
                )
                bottom_up = BlueprintLoader.load_code_blueprint(self.manifest_dir)
                comparator = self._get_blueprint_comparator()
                conflicts = comparator.compare_blueprints(top_down, bottom_up)
                lines.append(f"Deviation (mismatches): {len(conflicts)}")
                for conflict in conflicts[:20]:
                    severity = conflict.severity.value
                    msg = conflict.message[:70]
                    comp_id = conflict.component_id or "?"
                    lines.append(f"  [{severity}] {comp_id}: {msg}")
                if len(conflicts) > 20:
                    lines.append(f"  ... and {len(conflicts) - 20} more")
            elif self.inspector_mode == InspectorMode.VISUAL:
                top_down = BlueprintLoader.load_blueprint(
                    self.manifest_dir,
                    with_metadata=True,
                    default_source="llm_design",
                )
                bottom_up = BlueprintLoader.load_code_blueprint(self.manifest_dir)
                arch_file = self.manifest_dir / "architecture.json"
                architecture = load_architecture_with_metadata(arch_file)
                status_info = self._get_blueprint_sync().calculate_implementation_status(
                    top_down, bottom_up, architecture
                )
                comp_status = status_info.get("component_statuses", {})
                healthy_n = sum(1 for s in comp_status.values() if s == "healthy")
                planned_n = sum(1 for s in comp_status.values() if s == "planned")
                partial_n = sum(1 for s in comp_status.values() if s == "partial")
                deviation_n = sum(1 for s in comp_status.values() if s == "deviation")
                lines.append("Status:")
                lines.append(f"  {_status_label_markup('healthy', f'Healthy: {healthy_n}')}")
                lines.append(f"  {_status_label_markup('planned', f'Planned: {planned_n}')}")
                lines.append(f"  {_status_label_markup('partial', f'Partial: {partial_n}')}")
                lines.append(f"  {_status_label_markup('deviation', f'Deviation: {deviation_n}')}")
            elif self.inspector_mode == InspectorMode.DETAIL:
                return self._render_detail_content()
            else:
                lines.append("(Execution trace when orchestrator/agents run.)")
            lines.append("")
            state_mgr = self._get_state_manager()
            chat_history = state_mgr.get_state().get("chat_history", {})
            shadow_channels = [c for c in chat_history if isinstance(c, str) and c.startswith("shadow-")]
            lines.append("Component / shadow output (what/how modules are doing):")
            if shadow_channels:
                for ch in shadow_channels[:8]:
                    msgs = state_mgr.get_chat_history(ch)
                    lines.append(f"  [{ch}] ({len(msgs)} msgs)")
                    for m in msgs[-2:]:
                        role = m.get("role", "?")
                        content = (m.get("content") or "")[:60].replace("\n", " ")
                        lines.append(f"    {role}: {content}...")
            else:
                lines.append("  (none yet)")
        except Exception as e:
            logger.debug("Inspector view load failed: %s", e)
            lines.append("Inspector: (load failed)")
        return "\n".join(lines) if lines else "Inspector: (no data)"

    def _load_mission_control_view(self) -> Union[str, RenderableType]:
        """Mission: goal cards (id, name, status, body)."""
        try:
            arch_file = self.manifest_dir / "architecture.json"
            architecture = load_architecture_with_metadata(arch_file) if arch_file.exists() else {}
            goals = architecture.get("goals") or []
            cards: List[Tuple[str, str, str, str]] = []
            for i, g in enumerate(goals[:10]):
                if isinstance(g, dict):
                    name = (g.get("name") or g.get("id") or f"Goal {i+1}")[:40]
                    body = (g.get("description") or g.get("name") or "")[:120]
                    status = (g.get("status") or "Planned").strip() or "Planned"
                else:
                    name = str(g)[:40]
                    body = ""
                    status = "Planned"
                cards.append((f"M{i+1}", name, status, body))
            lines = ["[dim]Mission Control: Objectives[/]", ""]
            if not cards:
                lines.append("[dim](no objectives — add goals in architecture.json)[/]")
                return "\n".join(lines)
            for oid, name, status, body in cards:
                s = (status or "").lower()
                st_color = "green" if s in ("done", "completed") else ("yellow" if s in ("in progress", "in_progress") else ("red" if s in ("deviation", "failed") else "dim"))
                lines.append(f"[bold {ACCENT_BLUE}]{oid}: {name}[/]  [{st_color}]{status}[/]")
                lines.append(f"  [dim]│[/] {body}")
                lines.append("")
            return "\n".join(lines).rstrip()
        except Exception as e:
            logger.debug("Mission Control view load failed: %s", e)
            return f"(load failed: {e})"

    def _get_current_view_content(self) -> Union[str, RenderableType]:
        """Content for current view. History = Timeline."""
        if self.current_view == ViewType.DIAGRAM:
            return self._load_diagram_view()
        elif self.current_view == ViewType.FILES:
            return self._load_files_view()
        elif self.current_view in (ViewType.TIMELINE, ViewType.HISTORY):
            return self._load_timeline_view()
        elif self.current_view == ViewType.MISSION_CONTROL:
            return self._load_mission_control_view()
        return Panel("Unknown view", title="View", border_style="red")

    def _get_sidebar_tasks(self) -> str:
        """Sidebar tasks: sprint bar, then each task with icon, name, status, progress."""
        try:
            tasks, sprints = self._get_tasks_and_sprints_from_manifest()
            if not tasks:
                return "[bold cyan]Tasks[/]\n[dim]─────────────────────[/]\n[white](0)[/]"
            # Old TUI style: each task shows status label and progress bar + %
            name_max = 36
            total_pct = 0.0
            for t in tasks:
                prog = t.get("progress") or {}
                pct = prog.get("percentage", 0) if isinstance(prog, dict) else 0
                if (t.get("status") or "").lower() == "completed" and pct == 0:
                    pct = 100
                total_pct += pct
            overall_pct = total_pct / len(tasks) if tasks else 0
            head = f"[white]SPRINT  {int(overall_pct)}%[/]"
            head_bar = f"[white]{_progress_bar(overall_pct, 8)}[/]"
            task_lines = []
            for i, t in enumerate(tasks[:8], 1):
                raw_name = (t.get("name") or t.get("id") or "?").replace("\n", " ").strip()
                name = raw_name[:name_max].strip()
                prog = t.get("progress") or {}
                pct = prog.get("percentage", 0) if isinstance(prog, dict) else 0
                st = (t.get("status") or "").lower()
                if st == "completed" and pct == 0:
                    pct = 100
                if st == "completed":
                    icon = "[green][X][/]"
                elif st == "in_progress":
                    icon = "[cyan][>][/]"
                else:
                    icon = "[dim][ ][/]"
                bar = _progress_bar(pct, 6)
                status_markup = _task_status_markup(t.get("status", "?"))
                task_lines.append(f"  {icon} [white]{i}. {name}[/]")
                task_lines.append(f"        {status_markup}[white]{bar} {pct}%[/]")
                task_lines.append("")
            lines = ["[bold cyan]Tasks[/]", "[dim]─────────────────────[/]", head, head_bar, ""] + task_lines
            if len(tasks) > 8:
                lines.append(f"[white] ... +{len(tasks) - 8}[/]")
            return "\n".join(lines).rstrip()
        except Exception as e:
            logger.debug("Sidebar tasks failed: %s", e)
            return "[bold cyan]Tasks[/]\n[dim]─────────────────────[/]\n  (—)"

    def _get_sidebar_health(self) -> str:
        """Project Health: deviation % from blueprint sync; code quality/coverage/size from state (updated by bottom-up)."""
        try:
            top_down = BlueprintLoader.load_blueprint(
                self.manifest_dir, with_metadata=True, default_source="llm_design"
            )
            bottom_up = BlueprintLoader.load_code_blueprint(self.manifest_dir)
            arch_file = self.manifest_dir / "architecture.json"
            architecture = load_architecture_with_metadata(arch_file)
            status_info = self._get_blueprint_sync().calculate_implementation_status(
                top_down, bottom_up, architecture
            )
            comp_status = status_info.get("component_statuses", {})
            total = len(comp_status) or 1
            deviation_count = sum(1 for s in comp_status.values() if s in ("deviation", "partial"))
            pct = int(100 * deviation_count / total)
            dev_color = "yellow" if pct > 0 else "green"
            metrics = {}
            state_file = self.manifest_dir / "state.json"
            if state_file.exists():
                try:
                    with open(state_file, "r", encoding="utf-8") as f:
                        state = json.load(f)
                    metrics = state.get("health_metrics") or {}
                except Exception:
                    pass
            quality_str = metrics.get("code_quality") or "—"
            q = str(quality_str).lower()
            if q in ("excellent", "good", "ok"):
                quality_tag = "green"
            elif "issues" in q:
                n = re.search(r"(\d+)\s*issues", q)
                quality_tag = "yellow" if (n and int(n.group(1)) <= 20) else "red"
            else:
                quality_tag = "dim"
            cov_val = metrics.get("test_coverage")
            cov_str = f"{cov_val}%" if cov_val is not None else "—"
            size_str = metrics.get("binary_size") or "—"
            return (
                "[bold cyan]Project Health[/]\n"
                "[dim]─────────────────────[/]\n"
                f"  Total Deviation:  [{dev_color}]{pct}%[/]\n"
                f"  Code Quality:     [{quality_tag}]{quality_str}[/]\n"
                f"  Test Coverage:   [{ACCENT_BLUE}]{cov_str}[/]\n"
                f"  Binary Size:     [dim]{size_str}[/]"
            )
        except Exception as e:
            logger.debug("Sidebar health failed: %s", e)
            return "[bold cyan]Project Health[/]\n[dim]─────────────────────[/]\n  (—)"

    def _get_sidebar_viz(self) -> str:
        """Name of current main view."""
        name = {
            ViewType.DIAGRAM: "Diagram",
            ViewType.FILES: "Files",
            ViewType.TIMELINE: "Timeline",
            ViewType.HISTORY: "Timeline",
            ViewType.MISSION_CONTROL: "Mission",
            ViewType.ARCHITECT: "Architect",
            ViewType.BLUEPRINT: "Blueprint",
        }.get(self.current_view, "—")
        return f"View: {name}"

    def _get_shadow_results_for_node(self, nid: str) -> Tuple[str, str]:
        """Last Output and Shadow Trace for node from state (shadow-* channels). Returns (last_output, trace)."""
        try:
            state_mgr = self._get_state_manager()
            chat_history = state_mgr.get_state().get("chat_history", {})
            if not isinstance(chat_history, dict):
                return "—", "—"
            shadow_keys = [k for k in chat_history if isinstance(k, str) and k.startswith("shadow-")]
            # Prefer channel for this component (e.g. shadow-<nid>)
            for key in shadow_keys:
                if nid in key or key == f"shadow-{nid}":
                    msgs = state_mgr.get_chat_history(key) or []
                    if not msgs:
                        return "—", "—"
                    last = msgs[-1]
                    last_out = (last.get("content") or "")[:200].replace("\n", " ")
                    trace = "\n".join((m.get("content") or "")[:120].replace("\n", " ") for m in msgs[-5:])
                    return last_out or "—", trace or "—"
            if shadow_keys:
                msgs = state_mgr.get_chat_history(shadow_keys[0]) or []
                if msgs:
                    last = msgs[-1]
                    last_out = (last.get("content") or "")[:200].replace("\n", " ")
                    trace = "\n".join((m.get("content") or "")[:120].replace("\n", " ") for m in msgs[-5:])
                    return last_out or "—", trace or "—"
        except Exception as e:
            logger.debug("Shadow results failed: %s", e)
        return "—", "—"

    def _get_info_hub_content(self) -> str:
        """Core inspection: 8 fields by category (Planning, Code Reality, Results, Alert). Data from docs; Code Reality from codebase."""
        nodes = self._get_selectable_nodes()
        idx = max(0, min(self._selected_node_index - 1, len(nodes) - 1))
        if not nodes:
            return "(No nodes. Run app or refresh.)"
        kind, nid, data = nodes[idx]
        display_name = (data.get("name") or nid or "?").strip()
        deviating = self._selected_node_is_deviating()
        header = (
            "[bold cyan]System Core Inspection[/]\n"
            "[dim]────────────────────────────────────────[/]\n"
            f"[white]{display_name}[/]  [dim][TAB] NEXT[/]"
        )
        if deviating:
            header += "  [red bold][D] DIFF[/]"
        header += "\n\n"

        if self._right_panel_differences:
            return self._get_info_hub_diff_view(header, kind, nid, data, deviating)

        if kind == "root":
            return self._get_info_hub_root(header, deviating)
        if kind == "feature":
            return header + self._render_detail_content()

        return self._get_info_hub_component(header, nid, data, deviating)

    def _factor_box(self, title: str, body: str) -> str:
        """One inspection factor: title, rule, then content (indented)."""
        rule = "[dim]" + "─" * 36 + "[/]"
        indented = "\n  ".join(body.split("\n"))
        return f"[bold white]{title}[/]\n{rule}\n  {indented}\n"

    def _get_info_hub_root(self, header: str, deviating: bool) -> str:
        """Inspection for PROJECT_ROOT: 8 factor sections from architecture."""
        arch_file = self.manifest_dir / "architecture.json"
        arch = load_architecture_with_metadata(arch_file) if arch_file.exists() else {}
        goal = (arch.get("mission") or "").strip() or "Project root."
        interface_plan = "Binary Execution -> Console Output"
        style = (arch.get("architecture_style") or "").strip() or "—"
        rules = arch.get("global_rules") or []
        last_out, trace = self._get_shadow_results_for_node("PROJECT_ROOT")
        rules_text = "\n  ".join(f"[white]» {str(r)[:72]}[/]" for r in (rules or [])[:6]) or "[white]—[/]"
        code_reality = "[white]Dependencies: —  Side Effects: —  Complexity: —[/]"
        parts = [
            header,
            self._factor_box("Goal Intent", f"[white]{goal[:280] or '—'}[/]"),
            self._factor_box("Interface Contract", f"[white]{interface_plan}[/]"),
            self._factor_box("Logic Style", f"[white]{style}[/]"),
            self._factor_box("Code Reality", code_reality),
            self._factor_box("Last Output", f"[white]{last_out[:160] if last_out != '—' else '—'}[/]"),
            self._factor_box("Shadow Trace Output", f"[white]{trace[:240] if trace != '—' else '—'}[/]"),
            self._factor_box("Essential Rules", rules_text),
        ]
        if deviating:
            parts.append(self._factor_box("Deviation Alert", "[red]Plan and code mismatch. [D] DIFF to compare.[/]"))
        return "\n".join(parts)

    def _get_info_hub_component(self, header: str, nid: str, data: Dict[str, Any], deviating: bool) -> str:
        """Inspection for component: 8 factor sections from design (docs) and Code Reality (blueprint_code)."""
        design_comp: Dict[str, Any] = dict(data)
        top_down = BlueprintLoader.load_blueprint(
            self.manifest_dir, with_metadata=False, default_source="llm_design"
        )
        for c in (top_down.get("components") or []):
            if isinstance(c, dict) and c.get("id") == nid:
                design_comp.update(c)
                break
        actual_comp: Dict[str, Any] = {}
        path = self.manifest_dir / "blueprint_code.json"
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for c in json.load(f).get("components", []) or []:
                        if isinstance(c, dict) and c.get("id") == nid:
                            actual_comp = c
                            break
            except Exception:
                pass
        goal = (design_comp.get("description") or "").strip() or "—"
        interface_plan = (design_comp.get("interface") or "—").strip()
        style = (design_comp.get("logic_style") or "—").strip()
        rules = design_comp.get("project_rules") or []
        deps = ", ".join((actual_comp.get("dependencies") or [])[:8]) or "—"
        side_effects = ", ".join((actual_comp.get("side_effects") or [])[:5]) or "—"
        complexity = (actual_comp.get("complexity") or "—").strip()
        last_out, trace = self._get_shadow_results_for_node(nid)
        rules_text = "\n  ".join(f"[white]» {str(r)[:72]}[/]" for r in (rules or [])[:6]) or "[white]—[/]"
        code_reality = f"[white]Dependencies: {deps[:64]}[/]\n  [white]Side Effects: {side_effects[:64]}[/]\n  [white]Complexity: {complexity[:48]}[/]"
        parts = [
            header,
            self._factor_box("Goal Intent", f"[white]{goal[:280] or '—'}[/]"),
            self._factor_box("Interface Contract", f"[white]{interface_plan[:72]}[/]"),
            self._factor_box("Logic Style", f"[white]{style[:48]}[/]"),
            self._factor_box("Code Reality", code_reality),
            self._factor_box("Last Output", f"[white]{last_out[:160] if last_out != '—' else '—'}[/]"),
            self._factor_box("Shadow Trace Output", f"[white]{trace[:240] if trace != '—' else '—'}[/]"),
            self._factor_box("Essential Rules", rules_text),
        ]
        if deviating:
            parts.append(self._factor_box("Deviation Alert", "[red]Plan and code mismatch. [D] DIFF to compare.[/]"))
        return "\n".join(parts)

    def _get_info_hub_diff_view(self, header: str, kind: str, nid: str, data: Dict[str, Any], deviating: bool) -> str:
        """Differences view: Planned | Code side-by-side."""
        design_comp: Dict[str, Any] = dict(data)
        top_down = BlueprintLoader.load_blueprint(
            self.manifest_dir, with_metadata=False, default_source="llm_design"
        )
        for c in (top_down.get("components") or []):
            if isinstance(c, dict) and c.get("id") == nid:
                design_comp.update(c)
                break
        actual_comp: Dict[str, Any] = {}
        path = self.manifest_dir / "blueprint_code.json"
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for c in json.load(f).get("components", []) or []:
                        if isinstance(c, dict) and c.get("id") == nid:
                            actual_comp = c
                            break
            except Exception:
                pass
        rows = [
            ("Interface", design_comp.get("interface") or "—", actual_comp.get("detected_interface") or "—"),
            ("Goal Intent", (design_comp.get("description") or "—")[:32], "—"),
            ("Dependencies", "—", ", ".join((actual_comp.get("dependencies") or [])[:5])),
            ("Side Effects", "—", ", ".join((actual_comp.get("side_effects") or [])[:5]) or "—"),
            ("Complexity", design_comp.get("logic_style") or "—", actual_comp.get("complexity") or "—"),
        ]
        lines = [header, "[white]  Planned          |  Code[/]", "[white]  " + "-" * 30 + "+" + "-" * 30 + "[/]"]
        for label, d_val, a_val in rows:
            match = (d_val or "—") == (a_val or "—") if label == "Interface" else True
            d_str = str(d_val)[:30].replace("\n", " ")
            a_str = str(a_val)[:30].replace("\n", " ")
            if not match:
                lines.append(f"  [red]{d_str:<30}[/] | [red]{a_str}[/]")
            else:
                lines.append(f"[white]  {d_str:<30} | {a_str}[/]")
        if deviating:
            lines.extend(["", "[bold red]⚠ Deviation Alert[/]  [red]Mismatch detected. See above.[/]"])
        return "\n".join(lines)

    def compose(self) -> ComposeResult:
        with Container(id="header-strip"):
            yield Static("Manifest View", id="header-metrics")
        with Horizontal(id="body-row"):
            with Container(id="sidebar"):
                with VerticalScroll(id="sidebar-scroll"):
                    yield Static("[bold cyan]Project Health[/]\n[dim]─────────────────────[/]\n  (loading)", id="sidebar-health", classes="sidebar-section")
                    yield Static("[bold cyan]Tasks[/]\n[dim]─────────────────────[/]\n  (loading)", id="sidebar-tasks", classes="sidebar-section")
            with Container(id="main"):
                yield Static("", id="main-tab-bar")
                with VerticalScroll(id="main-scroll"):
                    yield Static("", id="main-content")
            with Container(id="info-hub"):
                with VerticalScroll(id="info-hub-scroll"):
                    yield Static("[bold cyan]System Core Inspection[/]\n[dim]────────────────────────────────────────[/]\n  (loading)", id="info-hub-content", classes="sidebar-section")
                yield Static("[dim][E] Edit Design  [S] Re-Sync Data[/]", id="info-hub-footer")
        yield Footer()
        with Container(id="app-version-strip"):
            with Horizontal():
                yield Static("", id="footer-spacer")
                yield Static(f"Manifest app {APP_VERSION}", id="footer-version")

    def on_mount(self) -> None:
        self._refresh_sidebar()
        self._refresh_main_content()
        self._refresh_header_metrics()
        self.set_interval(1, self._refresh_header_metrics)
        self._view_file_watcher = ViewFileWatcher(
            self.manifest_dir,
            on_change=self._on_manifest_change,
        )
        self.set_interval(2, self._check_manifest_changes)
        self._deviation_monitor = DeviationMonitor(
            project_root=self.manifest_dir.parent,
            manifest_dir=self.manifest_dir,
        )
        self._check_deviation()

    def _check_manifest_changes(self) -> None:
        """Check .manifest for changes."""
        try:
            self._view_file_watcher.check()
        except Exception as e:
            logger.debug("Manifest watch check failed: %s", e)

    def _on_manifest_change(self, changed_paths: List[Path]) -> None:
        """On .manifest change: refresh; sync deviation if task done."""
        if not changed_paths:
            return
        task_or_state = any(
            p.name in ("tasks.json", "state.json") for p in changed_paths
        )
        if task_or_state:
            try:
                tasks, _ = self._get_tasks_and_sprints_from_manifest()
                completed = {t.get("id") for t in tasks if t.get("id") and t.get("status") == "completed"}
                if completed - self._last_completed_task_ids:
                    self._check_deviation()
                self._last_completed_task_ids = completed
            except Exception as e:
                logger.debug("Task-done deviation check failed: %s", e)
        self.refresh_view()

    def _check_deviation(self) -> None:
        """Update blueprint_code.json if code changed."""
        try:
            self._deviation_monitor.check_and_update()
        except Exception as e:
            logger.debug("Deviation check failed: %s", e)

    def _get_header_strip_content(self) -> Union[str, RenderableType]:
        """Header: Manifest View, Planning/Differences, STATUS, TIME."""
        planning_active = not self._right_panel_differences
        diff_active = self._right_panel_differences
        now = datetime.now().strftime("%H:%M:%S")
        # Fixed structure: blue title, Planning/Differences (UI state), STATUS label, TIME (live clock)
        planning = "[bold white][ Planning ][/]" if planning_active else "[dim][ Planning ][/]"
        diff = "[bold red underline][ Differences ][/]" if diff_active else "[dim][ Differences ][/]"
        return (
            f"[bold {ACCENT_BLUE}]Manifest View[/]  {planning}  {diff}     "
            f"STATUS: [dim]—[/]  TIME: [dim]{now}[/]"
        )

    def _refresh_header_metrics(self) -> None:
        """Refresh header strip (Planning/Differences, STATUS, TIME)."""
        try:
            strip_w = self.query_one("#header-metrics", Static)
            strip_w.update(self._get_header_strip_content())
        except Exception as e:
            logger.debug("Header refresh failed: %s", e)

    def _get_tab_bar_content(self) -> str:
        """Tab bar: Diagram, Files, Timeline, Mission; current one highlighted."""
        tabs = [
            ("1:DIAGRAM", ViewType.DIAGRAM),
            ("2:FILES", ViewType.FILES),
            ("3:TIMELINE", ViewType.TIMELINE),
            ("4:MISSION", ViewType.MISSION_CONTROL),
        ]
        parts = []
        for label, vt in tabs:
            if self.current_view == vt or (vt == ViewType.TIMELINE and self.current_view == ViewType.HISTORY):
                parts.append(f"[bold {ACCENT_BLUE}]{label}[/]")
            else:
                parts.append(f"[dim]{label}[/]")
        return "  ".join(parts)

    def _refresh_main_content(self) -> None:
        """Refresh tab bar and main content."""
        try:
            tab_w = self.query_one("#main-tab-bar", Static)
            tab_w.update(self._get_tab_bar_content())
            main_w = self.query_one("#main-content", Static)
            main_w.update(self._get_current_view_content())
        except Exception as e:
            logger.debug("Main content refresh failed: %s", e)

    def _refresh_sidebar(self) -> None:
        """Refresh left (Health, Tasks) and right (Inspector) panels."""
        try:
            health_w = self.query_one("#sidebar-health", Static)
            health_w.update(self._get_sidebar_health())
            tasks_w = self.query_one("#sidebar-tasks", Static)
            tasks_w.update(self._get_sidebar_tasks())
            try:
                hub_w = self.query_one("#info-hub-content", Static)
                hub_w.update(self._get_info_hub_content())
            except Exception:
                pass
        except Exception as e:
            logger.debug("Sidebar refresh failed: %s", e)

    def refresh_view(self) -> None:
        """Refresh all."""
        self._refresh_sidebar()
        self._refresh_main_content()
        self._refresh_header_metrics()

    def action_switch_view(self, view_name: str) -> None:
        """Switch main view. History = Timeline."""
        view_map = {
            "Diagram": ViewType.DIAGRAM,
            "Files": ViewType.FILES,
            "Timeline": ViewType.TIMELINE,
            "History": ViewType.HISTORY,
            "Mission": ViewType.MISSION_CONTROL,
            "Architect": ViewType.ARCHITECT,
            "Blueprint": ViewType.BLUEPRINT,
        }
        if view_name in view_map:
            self.current_view = view_map[view_name]
            self.refresh_view()

    def action_toggle_differences(self) -> None:
        """Toggle right panel: Design or Differences (D)."""
        self._right_panel_differences = not self._right_panel_differences
        try:
            hub_w = self.query_one("#info-hub-content", Static)
            hub_w.update(self._get_info_hub_content())
        except Exception as e:
            logger.debug("Info hub refresh failed: %s", e)

    def action_switch_inspector_mode(self, mode_name: str) -> None:
        """Set inspector mode (Visual/Data/Deviation/Detail). Right panel shows inspection."""
        mode_map = {
            "Visual": InspectorMode.VISUAL,
            "Data": InspectorMode.DATA,
            "Deviation": InspectorMode.DEVIATION,
            "Drift": InspectorMode.DEVIATION,  # alias
            "Detail": InspectorMode.DETAIL,
        }
        if mode_name in mode_map:
            self.inspector_mode = mode_map[mode_name]
            self.refresh_view()

    def action_refresh(self) -> None:
        self.refresh_view()

    def action_quit(self) -> None:
        self.exit()


def run_view(manifest_dir: Optional[Path] = None) -> None:
    app = ManifestViewApp(manifest_dir=manifest_dir)
    app.run()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Manifest View (Read-only Visualization)")
    parser.add_argument("--manifest-dir", type=Path, default=None, help="Path to .manifest")
    args = parser.parse_args()
    run_view(manifest_dir=args.manifest_dir)
