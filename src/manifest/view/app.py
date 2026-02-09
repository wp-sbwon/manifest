"""Manifest View: Diagram, Files, Timeline, Mission. D=Differences, Tab=next, S=refresh."""
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Set, Union
from enum import Enum

# Use color when we have a TTY (same terminal as OpenCode can show color).
if sys.stdout.isatty():
    os.environ.pop("NO_COLOR", None)
    os.environ.setdefault("TEXTUAL_COLOR_SYSTEM", "truecolor")

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
from manifest.core.git_manager import GitManager
from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
from manifest.audit.blueprint.blueprint_synchronizer import BlueprintSynchronizer
from manifest.audit.blueprint.blueprint_comparator import BlueprintComparator
from manifest.core.logger import get_logger
from manifest.view.file_watcher import ViewFileWatcher
from manifest.audit.monitoring.deviation_monitor import DeviationMonitor
from manifest.view.entity_model import get_entities_for_view
from manifest.core.paths import default_manifest_dir
from manifest.core.constants import STATE_FILE, TASKS_FILE
from manifest.view.diagram import (
    load_diagram_config,
    build_diagram_spec,
    render_diagram,
)
from manifest.audit.entity_schema import (
    PROJECT_ROOT_ID,
    entity_display_name,
    goals_from_blueprint,
    non_root_entities,
    contracts_from_entities,
    get_root_entity,
    top_layer_entities,
    root_intent,
    mission_from_blueprint,
)
from manifest.view.views_content import (
    ACCENT_BLUE,
    blueprint_component_names as _blueprint_component_names,
    component_type_color as _component_type_color,
    entities_for_display as _entities_for_display,
    feature_status_from_entities as _feature_status_from_entities,
    item_display_name as _item_display_name,
    order_entities_by_flow as _order_entities_by_flow,
    progress_bar as _progress_bar,
    single_line_node as _single_line_node,
    status_color_tag as _status_color_tag,
    status_label as _status_label,
    status_label_markup as _status_label_markup,
    task_status_color_tag as _task_status_color_tag,
    task_status_markup as _task_status_markup,
)

logger = get_logger(__name__)


class ViewType(Enum):
    """View: Diagram, Files, Timeline, Mission. History = Timeline."""
    DIAGRAM = "diagram"
    FILES = "files"
    TIMELINE = "timeline"
    HISTORY = "history"  # alias: same content as TIMELINE (Design + Git timeline)
    MISSION_CONTROL = "mission_control"
    INSPECTOR = "inspector"


class InspectorMode(Enum):
    """Right panel: Design or Differences (D). Detail = selected node."""
    DESIGN = "design"
    DIFFERENCES = "differences"
    VISUAL = "visual"
    DATA = "data"
    DEVIATION = "deviation"
    DETAIL = "detail"


def _app_version() -> str:
    """Single source: pyproject.toml [project].version via package metadata."""
    try:
        import importlib.metadata
        return importlib.metadata.version("manifest")
    except Exception:
        return "0.0"


APP_VERSION = _app_version()


class ManifestViewApp(App[None]):
    TITLE = "Manifest View"
    SUB_TITLE = ""
    CSS = """
    /* Do not set color on Screen: widget color overrides content markup colors and forces grey everywhere. */
    Screen { background: #0d1117; }
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
        Binding("p", "select_prev_node", "Prev"),
        Binding("n", "select_next_node", "Next"),
        Binding("enter", "drill_down", "Drill"),
        Binding("backspace", "drill_up", "Back"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, manifest_dir: Optional[Path] = None, **kwargs: Any):
        super().__init__(**kwargs)
        self.manifest_dir = default_manifest_dir(manifest_dir)
        self.current_view = ViewType.DIAGRAM
        self.inspector_mode = InspectorMode.DESIGN
        self._right_panel_differences = False  # D toggles Design vs Differences
        self._last_completed_task_ids: set = set()
        self._selected_node_index: int = 1  # 1-based; 1 = root
        self._diagram_component_list: List[Dict[str, Any]] = []
        self._diagram_blueprint: Optional[Dict[str, Any]] = None
        self._diagram_comp_status: Dict[str, str] = {}
        self._view_data: Dict[str, Any] = {}
        self._diagram_root_id: str = "PROJECT_ROOT"
        self._diagram_root_stack: List[str] = []
        self._diagram_layered_spec: Optional[Dict[str, Any]] = None
        self._diagram_selectable_nodes: List[Tuple[str, str, Dict[str, Any]]] = []
        self._state_manager: Optional[StateManager] = None
        self._task_manager: Optional[TaskManager] = None
        self._blueprint_sync: Optional[BlueprintSynchronizer] = None
        self._git_manager: Optional[GitManager] = None
        self._blueprint_comparator: Optional[BlueprintComparator] = None
        self._cached_design_blueprint: Optional[Dict[str, Any]] = None
        self._cached_code_blueprint: Optional[Dict[str, Any]] = None

    def _get_cached_design_blueprint(self) -> Dict[str, Any]:
        """Design blueprint for current refresh cycle; empty dict if not yet loaded."""
        return self._cached_design_blueprint if self._cached_design_blueprint is not None else {}

    def _get_cached_code_blueprint(self) -> Dict[str, Any]:
        """Code blueprint for current refresh cycle; empty dict if not yet loaded."""
        return self._cached_code_blueprint if self._cached_code_blueprint is not None else {}

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

    def _ensure_diagram_components(self) -> None:
        """Populate diagram from get_entities_for_view; layered spec and selectable nodes."""
        try:
            view_data = get_entities_for_view(
                self.manifest_dir,
                self._cached_design_blueprint,
                self._cached_code_blueprint,
            )
            blueprint = view_data["blueprint"]
            code_blueprint = view_data["code_blueprint"]
            comp_status = view_data["comp_status"]
            diagram_blueprint = code_blueprint if (code_blueprint.get("entities")) else blueprint
            entities = diagram_blueprint.get("entities") or []
            root_id = diagram_blueprint.get("root_id") or "PROJECT_ROOT"
            self._diagram_blueprint = diagram_blueprint
            self._diagram_comp_status = comp_status
            self._view_data = view_data

            if entities and root_id:
                spec = build_diagram_spec(
                    entities,
                    comp_status,
                    root_id=self._diagram_root_id,
                    title=None,
                    filter_app_only=True,
                )
                self._diagram_layered_spec = spec
                selectable: List[Tuple[str, str, Dict[str, Any]]] = []
                if self._diagram_root_id != root_id and self._diagram_root_stack:
                    parent_id = self._diagram_root_stack[-1]
                    selectable.append((
                        "up",
                        parent_id,
                        {"id": parent_id, "name": "↑ Up", "description": "Back to parent."},
                    ))
                else:
                    root_desc = mission_from_blueprint(self._get_cached_design_blueprint(), "Project root.")
                    selectable.append((
                        "root",
                        "PROJECT_ROOT",
                        {"id": "PROJECT_ROOT", "name": "System Core", "description": root_desc},
                    ))
                for node in spec.get("nodes") or []:
                    data = node.get("_data")
                    nid = node.get("id") or ""
                    if data and nid:
                        selectable.append(("node", nid, data))
                    for t in node.get("row") or []:
                        td = t.get("_data")
                        tid = t.get("id") or ""
                        if td and tid:
                            selectable.append(("node", tid, td))
                self._diagram_selectable_nodes = selectable
                self._diagram_component_list = [d for _, _, d in selectable if _ != "root" and _ != "up"]
            else:
                self._diagram_layered_spec = None
                self._diagram_component_list = []
                root_desc = mission_from_blueprint(self._get_cached_design_blueprint(), "Project root.")
                self._diagram_selectable_nodes = [
                    (
                        "root",
                        "PROJECT_ROOT",
                        {"id": "PROJECT_ROOT", "name": "System Core", "description": root_desc},
                    ),
                ]

            n_nodes = len(self._diagram_selectable_nodes)
            self._selected_node_index = max(1, min(self._selected_node_index, n_nodes))
        except Exception as e:
            logger.debug("Ensure diagram components failed: %s", e)
            self._diagram_component_list = []
            self._diagram_blueprint = None
            self._diagram_comp_status = {}
            self._view_data = {}
            self._diagram_layered_spec = None
            self._diagram_selectable_nodes = []

    def _get_selectable_nodes(self) -> List[Tuple[str, str, Dict[str, Any]]]:
        """List of nodes: root/up, then entities (matches diagram order when layered)."""
        if self._diagram_selectable_nodes:
            return self._diagram_selectable_nodes
        root_fallback: Tuple[str, str, Dict[str, Any]] = (
            "root",
            "PROJECT_ROOT",
            {"id": "PROJECT_ROOT", "name": "System Core", "description": "Project root."},
        )
        nodes: List[Tuple[str, str, Dict[str, Any]]] = []
        try:
            root_desc = mission_from_blueprint(self._get_cached_design_blueprint(), "Project root.")
            nodes.append((
                "root",
                "PROJECT_ROOT",
                {"id": "PROJECT_ROOT", "name": "System Core", "description": root_desc},
            ))
            for comp in self._diagram_component_list:
                if isinstance(comp, dict) and comp.get("id"):
                    nodes.append(("node", comp["id"], comp))
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
        top_down = self._get_cached_design_blueprint()
        bottom_up = self._get_cached_code_blueprint()
        if not top_down and not bottom_up:
            try:
                top_down = BlueprintLoader.load_blueprint(
                    self.manifest_dir, with_metadata=True, default_source="llm_design"
                )
                bottom_up = BlueprintLoader.load_code_blueprint(self.manifest_dir)
            except Exception as e:
                logger.debug("_selected_node_is_deviating load failed: %s", e)
                return False
        status_info = self._get_blueprint_sync().calculate_implementation_status(
            top_down, bottom_up
        )
        comp_status = status_info.get("node_statuses", {})
        if kind == "feature":
            feat_status = _feature_status_from_entities(top_down, comp_status)
            return feat_status.get(nid) == "deviation"
        return comp_status.get(nid) == "deviation"

    def action_select_prev_node(self) -> None:
        """Select previous node (Up). Index is 1-based (1 = root)."""
        if self._selected_node_index > 1:
            self._selected_node_index -= 1
            self.refresh_view()

    def action_select_next_node(self) -> None:
        """Select next node (Down). Index is 1-based; max = len(nodes)."""
        nodes = self._get_selectable_nodes()
        if self._selected_node_index < len(nodes):
            self._selected_node_index += 1
            self.refresh_view()

    def action_drill_down(self) -> None:
        """Set diagram root to selected entity; show Layer 2–3. Only when entity is selected."""
        nodes = self._get_selectable_nodes()
        if not nodes:
            return
        idx = max(0, min(self._selected_node_index - 1, len(nodes) - 1))
        kind, nid, _ = nodes[idx]
        if kind != "node":
            return
        self._diagram_root_stack.append(self._diagram_root_id)
        self._diagram_root_id = nid
        self._selected_node_index = 1
        self._ensure_diagram_components()
        self.refresh_view()

    def action_drill_up(self) -> None:
        """Restore diagram root to parent."""
        if not self._diagram_root_stack:
            return
        self._diagram_root_id = self._diagram_root_stack.pop()
        self._selected_node_index = 1
        self._ensure_diagram_components()
        self.refresh_view()

    def _render_detail_content(self) -> str:
        """Detail for selected node (feature or component)."""
        nodes = self._get_selectable_nodes()
        if not nodes:
            return "No features or components. Use n/p in Diagram view to change selection."
        if self._selected_node_index <= 0 or self._selected_node_index > len(nodes):
            n_feat = sum(1 for k, _, _ in nodes if k == "feature")
            return f"Select a feature or component with [n] Next / [p] Prev."
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
            ent_ids = data.get("children", []) or []
            lines.append(f"  children: {', '.join(ent_ids) if ent_ids else '(none)'}")
            return "\n".join(lines)
        comp = dict(data)
        from manifest.audit.blueprint.manifest_filenames import BLUEPRINT_CODE_FILE
        path = self.manifest_dir / BLUEPRINT_CODE_FILE
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    code_data = json.load(f)
                for c in code_data.get("entities", []) or []:
                    if isinstance(c, dict) and c.get("id") == nid:
                        r = c.get("reality") or {}
                        comp.update(c)
                        comp["file"] = r.get("symbol", comp.get("file"))
                        comp["methods"] = r.get("methods", comp.get("methods"))
                        comp["type"] = r.get("type", comp.get("type"))
                        break
            except Exception as e:
                logger.debug("Could not merge blueprint_code for node %s: %s", nid, e)
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
        """Diagram: layered spec (L1 + L2 rows) or empty. Return markup string so Static renders color."""
        try:
            if not self._diagram_blueprint:
                return "  (no blueprint — run app or sync refresh)"
            config = load_diagram_config(self.manifest_dir)
            if self._diagram_layered_spec and self._diagram_layered_spec.get("nodes") is not None:
                spec = dict(self._diagram_layered_spec)
                spec["title"] = spec.get("title") or config.get("title") or "ARCHITECTURE FLOW"
                return render_diagram(spec, config)
            spec = {
                "title": config.get("title") or "ARCHITECTURE FLOW",
                "nodes": [],
            }
            return render_diagram(spec, config)
        except Exception as e:
            logger.debug("Diagram view load failed: %s", e)
            return f"(load failed: {e})"

    def _load_files_view(self) -> Union[str, RenderableType]:
        """Source tree: root/ with dirs and files, dot by status."""
        try:
            bottom_up = self._get_cached_code_blueprint()
            top_down = self._get_cached_design_blueprint()
            status_info = self._get_blueprint_sync().calculate_implementation_status(
                top_down, bottom_up
            )
            comp_status = status_info.get("node_statuses", {})
            components = _entities_for_display(bottom_up.get("entities", []))
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
                except Exception as e:
                    logger.debug("Timeline: could not get git commits: %s", e)
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

    def _load_inspector_view(self) -> str:
        """Inspect: Deviation, Visual, Data, Detail."""
        lines = []
        try:
            if self.inspector_mode == InspectorMode.DEVIATION:
                top_down = self._get_cached_design_blueprint()
                bottom_up = self._get_cached_code_blueprint()
                comparator = self._get_blueprint_comparator()
                conflicts = comparator.compare_blueprints(top_down, bottom_up)
                lines.append(f"Deviation (mismatches): {len(conflicts)}")
                for conflict in conflicts[:20]:
                    severity = conflict.severity.value
                    msg = conflict.message[:70]
                    comp_id = conflict.node_id or "?"
                    lines.append(f"  [{severity}] {comp_id}: {msg}")
                if len(conflicts) > 20:
                    lines.append(f"  ... and {len(conflicts) - 20} more")
            elif self.inspector_mode == InspectorMode.VISUAL:
                top_down = self._get_cached_design_blueprint()
                bottom_up = self._get_cached_code_blueprint()
                status_info = self._get_blueprint_sync().calculate_implementation_status(
                    top_down, bottom_up
                )
                comp_status = status_info.get("node_statuses", {})
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
            blueprint = self._get_cached_design_blueprint()
            goals = goals_from_blueprint(blueprint)
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
                lines.append("[dim](no objectives — add goals in blueprint root intent)[/]")
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
            raw = self._load_diagram_view()
            if isinstance(raw, str):
                return Text.from_markup(raw)
            return raw
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
            # Each item shows status label and progress bar
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
            top_down = self._get_cached_design_blueprint()
            bottom_up = self._get_cached_code_blueprint()
            status_info = self._get_blueprint_sync().calculate_implementation_status(
                top_down, bottom_up
            )
            comp_status = status_info.get("node_statuses", {})
            total = len(comp_status) or 1
            deviation_count = sum(1 for s in comp_status.values() if s in ("deviation", "partial"))
            pct = int(100 * deviation_count / total)
            dev_color = "yellow" if pct > 0 else "green"
            metrics = {}
            state_file = self.manifest_dir / STATE_FILE
            if state_file.exists():
                try:
                    with open(state_file, "r", encoding="utf-8") as f:
                        state = json.load(f)
                    metrics = state.get("health_metrics") or {}
                except Exception as e:
                    logger.debug("Could not load state.json health_metrics: %s", e)
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
            ViewType.INSPECTOR: "Inspector",
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

    def _get_diagram_label_for_node(self, kind: str, nid: str, data: Dict[str, Any]) -> str:
        """Label for right panel: match diagram (feature name for single-comp feature, else node name)."""
        if kind == "root":
            return "System Core"
        if kind == "up":
            return "↑ Up"
        if kind == "node":
            role = ((data.get("intent") or {}).get("narrative") or {}).get("role") or ""
            if role:
                return role.strip()
            symbol = (data.get("reality") or {}).get("symbol") or ""
            if symbol:
                return symbol.strip()
            return (data.get("name") or nid or "?").strip()
        blueprint = self._get_cached_design_blueprint()
        for e in top_layer_entities(blueprint):
            comp_ids = list(e.get("children") or [])
            if nid not in comp_ids:
                continue
            if len(comp_ids) == 1:
                return (entity_display_name(e) or e.get("name") or e.get("id") or "?").strip()
            return (data.get("name") or nid or "?").strip()
        return (data.get("name") or nid or "?").strip()

    def _get_entities_by_id(self, nid: str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Resolve node by id from design and code blueprints."""
        top = self._get_cached_design_blueprint()
        bottom = self._get_cached_code_blueprint()
        design_ent = next((e for e in (top.get("entities") or []) if isinstance(e, dict) and (e.get("id") or "") == nid), None)
        code_ent = next((e for e in (bottom.get("entities") or []) if isinstance(e, dict) and (e.get("id") or "") == nid), None)
        return design_ent, code_ent

    def _get_entity_for_inspector(self, nid: str, fallback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Merged entity for inspector: intent from design, reality from code."""
        design_ent, code_ent = self._get_entities_by_id(nid)
        if not design_ent and not code_ent:
            return fallback or {"id": nid, "intent": {}, "reality": {}, "children": [], "dependencies": [], "outgoing_contracts": []}
        intent = (design_ent or {}).get("intent") or {}
        reality = (code_ent or design_ent or {}).get("reality") or {}
        children = (design_ent or code_ent or {}).get("children") or []
        deps = (design_ent or code_ent or {}).get("dependencies") or []
        contracts = (design_ent or code_ent or {}).get("outgoing_contracts") or []
        return {
            "id": nid,
            "intent": intent,
            "reality": reality,
            "children": children,
            "dependencies": deps,
            "outgoing_contracts": contracts,
        }

    def _get_info_hub_content(self) -> str:
        """Inspector: node from blueprints."""
        nodes = self._get_selectable_nodes()
        idx = max(0, min(self._selected_node_index - 1, len(nodes) - 1))
        if not nodes:
            return "(No nodes. Run app or refresh.)"
        kind, nid, data = nodes[idx]
        display_name = self._get_diagram_label_for_node(kind, nid, data)
        deviating = self._selected_node_is_deviating()
        entity_label = "System Core" if kind == "root" else display_name
        header = f"[bold cyan]Inspector::[/] [bold #f0c674]{entity_label}[/]"
        if deviating:
            header += "  [red bold][D] DIFF[/]"
        header += "\n\n"

        if self._right_panel_differences:
            return self._get_info_hub_diff_view(header, nid, data, deviating)

        if kind == "up":
            return header + "\n\n  [dim]Press Backspace to go back.[/]"
        if kind == "root":
            root_entity = self._get_root_entity_for_inspector()
            validation = self._view_data.get("validation_by_id") or {}
            validation = validation.get(PROJECT_ROOT_ID) or {}
            return self._get_info_hub_node(header, PROJECT_ROOT_ID, root_entity, validation, deviating)
        if kind == "feature":
            return header + self._render_detail_content()
        entity = data if (data.get("intent") is not None and data.get("reality") is not None) else self._get_entity_for_inspector(nid, data)
        validation = (self._view_data.get("validation_by_id") or {}).get(nid) or {}
        return self._get_info_hub_node(header, nid, entity, validation, deviating)

    def _inspection_section(self, title: str, body: str) -> str:
        """One inspection section: title, rule, then content (indented). Sub-headers use #58a6ff (same as OpenCode/sidebar-title)."""
        rule = "[#58a6ff]" + "─" * 36 + "[/]"
        indented = "\n  ".join(body.split("\n"))
        return f"[bold #58a6ff]{title}[/]\n{rule}\n  {indented}\n"

    def _get_root_entity_for_inspector(self) -> Dict[str, Any]:
        """Root (System Core) as entity: same shape as other entities. From blueprint root or synthetic from root_intent."""
        design = self._get_cached_design_blueprint()
        code = self._get_cached_code_blueprint()
        root_design = get_root_entity(design) if design else None
        root_code = get_root_entity(code) if code else None
        if root_design:
            out = dict(root_design)
            out.setdefault("id", PROJECT_ROOT_ID)
            out.setdefault("intent", root_intent(design or {}))
            out.setdefault("reality", {})
            out.setdefault("children", [])
            out.setdefault("dependencies", [])
            out.setdefault("outgoing_contracts", [])
            if root_code and root_code.get("reality") is not None:
                out["reality"] = root_code.get("reality") or {}
            return out
        intent = root_intent(design or {})
        child_ids = [e.get("id") for e in top_layer_entities(design or {}) if e.get("id")]
        return {
            "id": PROJECT_ROOT_ID,
            "intent": intent,
            "reality": (root_code.get("reality") or {}) if root_code else {},
            "children": child_ids,
            "dependencies": [],
            "outgoing_contracts": [],
        }

    def _get_info_hub_node(self, header: str, nid: str, data: Dict[str, Any], validation: Dict[str, Any], deviating: bool) -> str:
        """Inspector for any entity (including root): Identity, Intent, Reality, Outgoing contracts, Validation."""
        def _fmt(val: Any, max_len: int = 200) -> str:
            if val is None or val == "":
                return "—"
            s = str(val).strip()
            return (s[:max_len] + "…") if len(s) > max_len else s

        def _cap(s: str) -> str:
            """Capitalize label: 'io_model' -> 'Io model', 'input' -> 'Input'."""
            if not s:
                return s
            return " ".join(w.capitalize() for w in s.replace("_", " ").strip().split())

        intent = data.get("intent") or {}
        reality = data.get("reality") or {}
        narrative = intent.get("narrative") or {}
        role = _fmt(narrative.get("role"), 80)
        mission = _fmt(narrative.get("mission"), 240)
        blueprint = intent.get("blueprint") or {}
        bp_type = _fmt(blueprint.get("type"), 20)
        protocol_i = intent.get("protocol") or {}
        profile_i = intent.get("profile") or {}
        gov = intent.get("governance") or {}
        symbol = _fmt(reality.get("symbol"), 120)
        profile_r = reality.get("profile") or {}
        deps = data.get("dependencies") or []
        reality_deps = reality.get("dependencies") or []
        traits = reality.get("traits") or []
        preview = _fmt(reality.get("preview"), 160)
        children_ids = data.get("children") or []
        contracts = data.get("outgoing_contracts") or []
        status = _fmt(validation.get("status"), 20)
        deviations = validation.get("deviations") or []

        identity_body = "\n".join([
            f"[white]{_cap('id')}[/]: {nid}",
            f"[white]{_cap('children')}[/]: {', '.join(children_ids) or '—'}",
            f"[white]{_cap('dependencies')}[/]: {', '.join(deps[:12]) or '—'}",
        ])
        intent_body = "\n".join([
            f"{_cap('role')}: {role}",
            f"{_cap('mission')}: {mission}",
            f"{_cap('blueprint')}",
            f"  — {_cap('type')}: {bp_type}",
            f"{_cap('protocol')}",
            f"  — {_cap('input')}: {_fmt(protocol_i.get('input'))}",
            f"  — {_cap('output')}: {_fmt(protocol_i.get('output'))}",
            f"{_cap('profile')}",
            f"  — {_cap('language')}: {profile_i.get('language') or '—'}",
            f"  — {_cap('platform')}: {profile_i.get('platform') or '—'}",
            f"  — {_cap('io_model')}: {profile_i.get('io_model') or '—'}",
            f"  — {_cap('state_model')}: {profile_i.get('state_model') or '—'}",
            f"{_cap('governance')}",
            f"  — {_cap('rules')}: {_fmt(gov.get('rules'))}",
            f"  — {_cap('assertions')}: {_fmt(gov.get('assertions'))}",
        ])
        reality_body = "\n".join([
            f"{_cap('symbol')}: {symbol}",
            f"{_cap('profile')}",
            f"  — {_cap('language')}: {profile_r.get('language') or '—'}",
            f"  — {_cap('platform')}: {profile_r.get('platform') or '—'}",
            f"{_cap('dependencies')}: {', '.join(reality_deps[:12]) or '—'}",
            f"{_cap('traits')}: {', '.join(traits[:10]) or '—'}",
            f"{_cap('preview')}: {preview}",
        ])
        contract_lines = [f"→ {c.get('to') or '—'} [{c.get('type') or 'dependency'}] {c.get('file') or ''} {', '.join((c.get('symbols') or [])[:4])}" for c in (contracts or [])[:10]]
        contracts_body = "\n".join(contract_lines) if contract_lines else "—"
        validation_body = f"{_cap('status')}: {status}"
        if deviations:
            validation_body += "\n" + "\n".join(f"{_cap('deviation')}: {_fmt(d, 120)}" for d in deviations[:6])

        parts = [
            header,
            self._inspection_section("Identity", identity_body),
            self._inspection_section("Intent", intent_body),
            self._inspection_section("Reality", reality_body),
            self._inspection_section("Outgoing contracts", contracts_body),
            self._inspection_section("Validation", validation_body),
        ]
        if deviating:
            parts.append(self._inspection_section("Deviation Alert", "[red]Plan and code mismatch. [D] DIFF to compare.[/]"))
        return "\n".join(parts)

    def _get_info_hub_diff_view(self, header: str, nid: str, data: Dict[str, Any], deviating: bool) -> str:
        """Differences view: Plan (design intent/reality) | Code (code intent/reality) from entities."""
        design_ent, code_ent = self._get_entities_by_id(nid)
        plan = design_ent or data
        actual = code_ent or data
        plan_intent = plan.get("intent") or {}
        plan_narr = plan_intent.get("narrative") or {}
        plan_reality = plan.get("reality") or {}
        actual_intent = actual.get("intent") or {}
        actual_narr = actual_intent.get("narrative") or {}
        actual_reality = actual.get("reality") or {}
        def _s(v: Any, w: int = 28) -> str:
            return (str(v) if v is not None and v != "" else "—")[:w].replace("\n", " ")
        rows = [
            ("role", _s(plan_narr.get("role")), _s(actual_narr.get("role"))),
            ("mission", _s(plan_narr.get("mission")), _s(actual_narr.get("mission"))),
            ("symbol", _s(plan_reality.get("symbol")), _s(actual_reality.get("symbol"))),
            ("blueprint.type", _s(plan_intent.get("blueprint", {}).get("type")), _s(actual_intent.get("blueprint", {}).get("type"))),
        ]
        lines = [header, "[white]  Planned          |  Code[/]", "[white]  " + "-" * 30 + "+" + "-" * 30 + "[/]"]
        for label, d_val, a_val in rows:
            match = (d_val or "—") == (a_val or "—")
            d_str = (d_val or "—")[:30].replace("\n", " ")
            a_str = (a_val or "—")[:30].replace("\n", " ")
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
                    yield Static("", id="main-content", markup=True)
            with Container(id="info-hub"):
                with VerticalScroll(id="info-hub-scroll"):
                    yield Static("[bold cyan]Inspector:: (loading)[/]\n[dim]────────────────────────────────────────[/]\n  (loading)", id="info-hub-content", classes="sidebar-section")
                yield Static("[dim][E] Edit Design  [S] Re-Sync Data[/]", id="info-hub-footer")
        yield Footer()
        with Container(id="app-version-strip"):
            with Horizontal():
                yield Static("", id="footer-spacer")
                yield Static(f"Manifest app {APP_VERSION}", id="footer-version")

    def on_mount(self) -> None:
        self.refresh_view()
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
            p.name in (TASKS_FILE, STATE_FILE) for p in changed_paths
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
        """Update blueprint_code if code changed."""
        try:
            self._deviation_monitor.check_and_update()
        except Exception as e:
            logger.debug("Deviation check failed: %s", e)

    def _get_header_strip_content(self) -> Union[str, RenderableType]:
        """Header: Manifest View, Planning/Differences, STATUS (implementation status), TIME."""
        planning_active = not self._right_panel_differences
        diff_active = self._right_panel_differences
        now = datetime.now().strftime("%H:%M:%S")
        planning = "[bold white][ Planning ][/]" if planning_active else "[dim][ Planning ][/]"
        diff = "[bold red underline][ Differences ][/]" if diff_active else "[dim][ Differences ][/]"
        # Overall implementation status from diagram component statuses (healthy/partial/deviation/planned)
        comp_status = self._diagram_comp_status or {}
        if comp_status:
            deviation_n = sum(1 for s in comp_status.values() if s == "deviation")
            partial_n = sum(1 for s in comp_status.values() if s == "partial")
            healthy_n = sum(1 for s in comp_status.values() if s == "healthy")
            planned_n = sum(1 for s in comp_status.values() if s == "planned")
            if deviation_n > 0:
                status_label, status_tag = "Deviation", "red"
            elif partial_n > 0:
                status_label, status_tag = "Partial", "yellow"
            elif healthy_n == len(comp_status) and len(comp_status) > 0:
                status_label, status_tag = "Healthy", "green"
            elif planned_n == len(comp_status):
                status_label, status_tag = "Planned", "grey70"
            else:
                status_label, status_tag = "Partial", "yellow"
            status_markup = f"[{status_tag}]{status_label}[/]"
        else:
            status_markup = "[dim]—[/]"
        return (
            f"[bold {ACCENT_BLUE}]Manifest View[/]  {planning}  {diff}     "
            f"STATUS: {status_markup}  TIME: [dim]{now}[/]"
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
            except Exception as e:
                logger.debug("Info hub refresh failed: %s", e)
        except Exception as e:
            logger.debug("Sidebar refresh failed: %s", e)

    def refresh_view(self) -> None:
        """Refresh all. Load design + code blueprints once per refresh and reuse in this cycle."""
        try:
            self._cached_design_blueprint = BlueprintLoader.load_blueprint(
                self.manifest_dir, with_metadata=True, default_source="llm_design"
            )
            self._cached_code_blueprint = BlueprintLoader.load_code_blueprint(self.manifest_dir)
        except Exception as e:
            logger.debug("refresh_view cache load failed: %s", e)
            self._cached_design_blueprint = {}
            self._cached_code_blueprint = {}
        self._ensure_diagram_components()
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
            "Inspector": ViewType.INSPECTOR,
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
