"""Manifest View: Diagram, Files, Timeline. D=Differences, Tab=next, S=refresh."""
import os
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
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, Container, Horizontal
from textual.widgets import Static, Header, Footer
from textual.binding import Binding

from manifest.core.logger import get_logger
from manifest.view.data_access import get_timeline_events
from manifest.view.file_watcher import ViewFileWatcher
from manifest.view.entity_model import (
    get_entities_for_view,
    entities_and_comp_status_from_view_schema,
)
from manifest.core.paths import default_manifest_dir
from manifest.view.diagram import (
    load_diagram_config,
    build_diagram_spec,
    render_diagram,
)
from manifest.audit.entity_schema import (
    PROJECT_ROOT_ID,
    entity_display_name,
    get_root_entity,
    top_layer_entities,
    mission_from_blueprint,
)
from manifest.view.constants import (
    DEFAULT_DIAGRAM_TITLE,
    DEFAULT_PROJECT_LABEL,
    DEFAULT_ROOT_DESC,
    DEFAULT_ROOT_LABEL,
    INSPECTOR_ACCENT,
)
from manifest.view.content import (
    build_files_view_content,
    build_header_strip_content,
    build_info_hub_diff_view,
    build_info_hub_node_content,
    build_tab_bar_content,
    build_timeline_view_content,
    get_sidebar_health_text,
    get_sidebar_viz_text,
)
from manifest.view.views_content import status_label_markup as _status_label_markup

logger = get_logger(__name__)


class ViewType(Enum):
    """View: Diagram, Files, Timeline. History = Timeline."""
    DIAGRAM = "diagram"
    FILES = "files"
    TIMELINE = "timeline"
    HISTORY = "history"  # alias: same content as TIMELINE (Design + Git timeline)
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
    #info-hub { width: 1fr; min-width: 58; max-width: 78; border-left: solid #30363d; background: #0d1117; }
    #info-hub ScrollableContainer { padding: 0 2; }
    #info-hub-footer { height: 1; padding: 0 1; border-top: solid #30363d; }
    .sidebar-section { margin-bottom: 1; padding: 0 1; border-bottom: solid #30363d; }
    .sidebar-title { color: """ + INSPECTOR_ACCENT + """; text-style: bold; }
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
        self._selected_node_index: int = 1  # 1-based; 1 = root
        self._diagram_component_list: List[Dict[str, Any]] = []
        self._diagram_blueprint: Optional[Dict[str, Any]] = None
        self._diagram_comp_status: Dict[str, str] = {}
        self._view_data: Dict[str, Any] = {}
        self._diagram_root_id: str = PROJECT_ROOT_ID
        self._diagram_root_stack: List[str] = []
        self._diagram_layered_spec: Optional[Dict[str, Any]] = None
        self._diagram_selectable_nodes: List[Tuple[str, str, Dict[str, Any]]] = []

    def _get_design_blueprint(self) -> Dict[str, Any]:
        """Design blueprint from view data; empty dict if not yet loaded."""
        return (self._view_data or {}).get("blueprint") or {}

    def _get_code_blueprint(self) -> Dict[str, Any]:
        """Code blueprint from view data; empty dict if not yet loaded."""
        return (self._view_data or {}).get("code_blueprint") or {}

    def _get_design_and_code_for_status(self) -> tuple:
        """Design and code blueprints from current view data."""
        return (self._get_design_blueprint(), self._get_code_blueprint())

    def _get_implementation_status(self) -> tuple:
        """Comp status and status_info from view data."""
        vd = self._view_data
        comp_status = (vd.get("comp_status") or {}).copy()
        status_info = {"node_statuses": comp_status}
        return (comp_status, status_info)

    def _get_deviations_from_view(self) -> List[Dict[str, Any]]:
        """Deviations from view (validation_by_id or view_schema)."""
        out: List[Dict[str, Any]] = []
        vby = (self._view_data or {}).get("validation_by_id") or {}
        for eid, val in vby.items():
            for d in val.get("deviations") or []:
                out.append({"node_id": eid, "message": d})
        return out

    def _ensure_diagram_components(self) -> None:
        """Populate diagram from view data; layered spec and selectable nodes."""
        self._diagram_selectable_nodes = []
        self._diagram_layered_spec = None
        self._diagram_component_list = []
        try:
            view_data = self._view_data or {}
            blueprint = view_data.get("blueprint") or {}
            code_blueprint = view_data.get("code_blueprint") or {}
            comp_status = view_data.get("comp_status") or {}
            view_schema = view_data.get("view_schema") or {}
            # Use comparison output for diagram when available.
            if view_schema.get("entities"):
                entities, comp_status = entities_and_comp_status_from_view_schema(view_schema)
                root_id = view_schema.get("root_id") or PROJECT_ROOT_ID
                diagram_blueprint = {"root_id": root_id, "entities": entities}
            else:
                diagram_blueprint = code_blueprint if (code_blueprint.get("entities")) else blueprint
                entities = diagram_blueprint.get("entities") or []
                root_id = diagram_blueprint.get("root_id") or PROJECT_ROOT_ID
            self._diagram_blueprint = diagram_blueprint
            self._diagram_comp_status = comp_status
            self._view_data = view_data

            if entities and root_id:
                if self._diagram_root_id == PROJECT_ROOT_ID:
                    design = self._get_design_blueprint()
                    root_entity = get_root_entity(design) if design else None
                    diagram_title = entity_display_name(root_entity) if root_entity else DEFAULT_PROJECT_LABEL
                else:
                    root_ent = next(
                        (e for e in entities if (e.get("id") or "") == self._diagram_root_id),
                        None,
                    )
                    diagram_title = (
                        entity_display_name(root_ent) if root_ent else self._diagram_root_id
                    )
                spec = build_diagram_spec(
                    entities,
                    comp_status,
                    root_id=self._diagram_root_id,
                    title=diagram_title,
                    filter_app_only=True,
                )
                self._diagram_layered_spec = spec
                selectable: List[Tuple[str, str, Dict[str, Any]]] = []
                design = self._get_design_blueprint()
                root_entity = get_root_entity(design) if design else None
                root_display_name = entity_display_name(root_entity) if root_entity else DEFAULT_ROOT_LABEL
                root_desc = mission_from_blueprint(design, DEFAULT_ROOT_DESC)
                if self._diagram_root_id != root_id and self._diagram_root_stack:
                    parent_id = self._diagram_root_stack[-1]
                    selectable.append((
                        "up",
                        parent_id,
                        {"id": parent_id, "name": "↑ Up", "description": "Back to parent."},
                    ))
                else:
                    selectable.append((
                        "root",
                        PROJECT_ROOT_ID,
                        {"id": PROJECT_ROOT_ID, "name": root_display_name, "description": root_desc},
                    ))
                # Selectable: root's direct children; n/p cycles within that set.
                for node in spec.get("nodes") or []:
                    data = node.get("_data")
                    nid = node.get("id") or ""
                    if data and nid:
                        selectable.append(("node", nid, data))
                self._diagram_selectable_nodes = selectable
                self._diagram_component_list = [d for _, _, d in selectable if _ != "root" and _ != "up"]
            else:
                self._diagram_layered_spec = None
                self._diagram_component_list = []
                design = self._get_design_blueprint()
                root_entity = get_root_entity(design) if design else None
                root_display_name = entity_display_name(root_entity) if root_entity else DEFAULT_ROOT_LABEL
                root_desc = mission_from_blueprint(design, DEFAULT_ROOT_DESC)
                self._diagram_selectable_nodes = [
                    (
                        "root",
                        PROJECT_ROOT_ID,
                        {"id": PROJECT_ROOT_ID, "name": root_display_name, "description": root_desc},
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
        nodes: List[Tuple[str, str, Dict[str, Any]]] = []
        try:
            design = self._get_design_blueprint()
            root_entity = get_root_entity(design) if design else None
            root_display_name = entity_display_name(root_entity) if root_entity else DEFAULT_ROOT_LABEL
            root_desc = mission_from_blueprint(design, DEFAULT_ROOT_DESC)
            nodes.append((
                "root",
                PROJECT_ROOT_ID,
                {"id": PROJECT_ROOT_ID, "name": root_display_name, "description": root_desc},
            ))
            for comp in self._diagram_component_list:
                if isinstance(comp, dict) and comp.get("id"):
                    nodes.append(("node", comp["id"], comp))
        except Exception as e:
            logger.debug("Selectable nodes failed: %s", e)
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
        comp_status, _ = self._get_implementation_status()
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
        """Set diagram root to selected entity; show its children. Only when entity is selected."""
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
        """Detail for selected node (entity/component)."""
        nodes = self._get_selectable_nodes()
        if not nodes:
            return "No entities. Use n/p in Diagram view to change selection."
        if self._selected_node_index <= 0 or self._selected_node_index > len(nodes):
            return "Select an entity with [n] Next / [p] Prev."
        kind, nid, data = nodes[self._selected_node_index - 1]
        comp = dict(data)
        code_data = self._get_code_blueprint()
        if code_data:
            for c in code_data.get("entities", []) or []:
                if isinstance(c, dict) and c.get("id") == nid:
                    comp.update(c)
                    comp["file"] = c.get("symbol", comp.get("file"))
                    comp["methods"] = c.get("methods", comp.get("methods"))
                    comp["type"] = c.get("type", comp.get("type"))
                    break
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
        """Diagram: root's children as main row; each can have a row of its children. Selected node in magenta."""
        try:
            if not self._diagram_blueprint:
                return "  No blueprint. Run app or sync refresh."
            config = load_diagram_config(self.manifest_dir)
            selected_node_id: Optional[str] = None
            nodes = self._get_selectable_nodes()
            idx = max(0, min(self._selected_node_index - 1, len(nodes) - 1))
            if idx < len(nodes):
                kind, nid, _ = nodes[idx]
                if kind == "node":
                    selected_node_id = nid
            if self._diagram_layered_spec and self._diagram_layered_spec.get("nodes") is not None:
                spec = dict(self._diagram_layered_spec)
                spec["title"] = spec.get("title") or config.get("title") or DEFAULT_DIAGRAM_TITLE
                return render_diagram(spec, config, selected_node_id=selected_node_id)
            spec = {
                "title": config.get("title") or DEFAULT_DIAGRAM_TITLE,
                "nodes": [],
            }
            return render_diagram(spec, config, selected_node_id=selected_node_id)
        except Exception as e:
            logger.debug("Diagram view load failed: %s", e)
            return f"Diagram load failed: {e}"

    def _load_files_view(self) -> Union[str, RenderableType]:
        """Source tree: project root (manifest_dir.parent) with dirs and files, dot by status."""
        try:
            comp_status, _ = self._get_implementation_status()
            bottom_up = self._get_code_blueprint()
            return build_files_view_content(comp_status, bottom_up, self.manifest_dir.parent)
        except Exception as e:
            logger.debug("Files view load failed: %s", e)
            return f"Files load failed: {e}"

    def _load_timeline_view(self) -> Union[str, RenderableType]:
        """Timeline: DESIGN = git history for .manifest design docs; CODE = rest of repo."""
        try:
            events = get_timeline_events(self.manifest_dir)
            return build_timeline_view_content(events)
        except Exception as e:
            logger.debug("Timeline load failed: %s", e)
            return f"Timeline load failed: {e}"

    def _load_inspector_view(self) -> str:
        """Inspect: Deviation, Visual, Data, Detail."""
        lines = []
        try:
            if self.inspector_mode == InspectorMode.DEVIATION:
                deviations = self._get_deviations_from_view()
                lines.append(f"Deviation (mismatches): {len(deviations)}")
                for d in deviations[:20]:
                    comp_id = d.get("node_id") or "?"
                    msg = (d.get("message") or "?")[:70]
                    lines.append(f"  {comp_id}: {msg}")
                if len(deviations) > 20:
                    lines.append(f"  ... and {len(deviations) - 20} more")
            elif self.inspector_mode == InspectorMode.VISUAL:
                comp_status, _ = self._get_implementation_status()
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
                lines.append("Execution trace when orchestrator or agents run.")
        except Exception as e:
            logger.debug("Inspector view load failed: %s", e)
            lines.append("Inspector: load failed.")
        return "\n".join(lines) if lines else "Inspector: no data."

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
        return Panel("Unknown view", title="View", border_style="red")

    def _get_sidebar_health(self) -> str:
        """Project Health: status distribution + assertion proof rate."""
        try:
            comp_status, _ = self._get_implementation_status()
            test_results = (self._view_data or {}).get("test_results") or {}
            return get_sidebar_health_text(comp_status, test_results)
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
            ViewType.INSPECTOR: "Inspector",
        }.get(self.current_view, "—")
        return get_sidebar_viz_text(name)

    def _get_diagram_label_for_node(self, kind: str, nid: str, data: Dict[str, Any]) -> str:
        """Label for right panel: match diagram (entity/node name)."""
        if kind == "root":
            design = self._get_design_blueprint()
            root_entity = get_root_entity(design) if design else None
            return (entity_display_name(root_entity) or "System Core").strip()
        if kind == "up":
            return "↑ Up"
        if kind == "node":
            narrative = data.get("narrative") or {}
            role = (narrative.get("role") or "").strip()
            if role:
                return role
            symbol = (data.get("symbol") or "").strip()
            if symbol:
                return symbol
            return (data.get("name") or nid or "?").strip()
        blueprint = self._get_design_blueprint()
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
        top = self._get_design_blueprint()
        bottom = self._get_code_blueprint()
        design_ent = next((e for e in (top.get("entities") or []) if isinstance(e, dict) and (e.get("id") or "") == nid), None)
        code_ent = next((e for e in (bottom.get("entities") or []) if isinstance(e, dict) and (e.get("id") or "") == nid), None)
        return design_ent, code_ent

    def _get_entity_for_inspector(self, nid: str) -> Dict[str, Any]:
        """Entity for inspector (unified schema); prefer code, fallback design."""
        from manifest.audit.entity_schema import empty_entity
        design_ent, code_ent = self._get_entities_by_id(nid)
        if not design_ent and not code_ent:
            return dict(empty_entity(nid))
        base = design_ent or code_ent or {}
        fill = code_ent or design_ent or {}
        out = dict(empty_entity(nid))
        out["id"] = nid
        for key in ("children", "dependencies", "narrative", "blueprint", "protocol", "profile", "governance", "symbol", "traits", "topology_actual", "preview", "outgoing_contracts"):
            out[key] = fill.get(key, base.get(key, out[key]))
        return out

    def _get_info_hub_content(self) -> Union[str, RenderableType]:
        """Inspector: node from blueprints. Returns str or Rich Group (diff view table)."""
        nodes = self._get_selectable_nodes()
        idx = max(0, min(self._selected_node_index - 1, len(nodes) - 1))
        if not nodes:
            return "No nodes. Run app or refresh."
        kind, nid, data = nodes[idx]
        display_name = self._get_diagram_label_for_node(kind, nid, data)
        deviating = self._selected_node_is_deviating()
        entity_label = "System Core" if kind == "root" else display_name
        header = f"[bold cyan]Inspector::[/] [bold #f0c674]{entity_label}[/]"
        if deviating:
            header += "  [bold][D] DIFF[/]"
        header += "\n\n"

        if self._right_panel_differences:
            design_ent, code_ent = self._get_entities_by_id(nid)
            return build_info_hub_diff_view(header, nid, data, deviating, design_ent, code_ent)

        test_results = (self._view_data or {}).get("test_results") or {}

        if kind == "up":
            return header + "\n\n  [dim]Press Backspace to go back.[/]"
        if kind == "root":
            root_entity = self._get_root_entity_for_inspector()
            view_ent = self._get_view_entity_by_id(PROJECT_ROOT_ID)
            return build_info_hub_node_content(
                header, PROJECT_ROOT_ID, root_entity, deviating, view_ent, self._id_to_display_name_map(),
                test_results=test_results,
            )
        entity = data if (data.get("narrative") is not None or data.get("symbol") is not None) else self._get_entity_for_inspector(nid)
        view_ent = self._get_view_entity_by_id(nid)
        return build_info_hub_node_content(
            header, nid, entity, deviating, view_ent, self._id_to_display_name_map(),
            test_results=test_results,
        )

    def _id_to_display_name_map(self) -> Dict[str, str]:
        """Build map entity id -> display name (same as diagram labels) from current view data."""
        out: Dict[str, str] = {}
        for blueprint_key in ("blueprint", "code_blueprint"):
            bp = (self._view_data or {}).get(blueprint_key) or {}
            for e in bp.get("entities") or []:
                eid = e.get("id")
                if eid:
                    name = entity_display_name(e) or e.get("name") or eid
                    out[eid] = name.strip() or eid
        return out

    def _get_view_entity_by_id(self, nid: str) -> Optional[Dict[str, Any]]:
        """Return view_schema entity for nid (same keys as blueprint; values plan/actual/deviates)."""
        view_schema = (self._view_data or {}).get("view_schema") or {}
        for e in view_schema.get("entities") or []:
            if (e.get("id") or "") == nid:
                return e
        return None

    def _get_root_entity_for_inspector(self) -> Dict[str, Any]:
        """Root (System Core) as entity; same shape as other entities."""
        from manifest.audit.entity_schema import empty_entity
        design = self._get_design_blueprint()
        code = self._get_code_blueprint()
        root_design = get_root_entity(design) if design else None
        root_code = get_root_entity(code) if code else None
        out = dict(empty_entity(PROJECT_ROOT_ID))
        out["id"] = PROJECT_ROOT_ID
        base = root_design or root_code
        if base:
            for key in ("children", "dependencies", "narrative", "blueprint", "protocol", "profile", "governance", "symbol", "traits", "topology_actual", "preview", "outgoing_contracts"):
                out[key] = base.get(key, out[key])
        if root_code:
            for key in ("narrative", "blueprint", "protocol", "profile", "governance", "symbol", "traits", "topology_actual", "preview"):
                if root_code.get(key) is not None:
                    out[key] = root_code.get(key)
        out["children"] = [e.get("id") for e in top_layer_entities(design or {}) if e.get("id")]
        return out

    def compose(self) -> ComposeResult:
        with Container(id="header-strip"):
            yield Static("Manifest View", id="header-metrics")
        with Horizontal(id="body-row"):
            with Container(id="sidebar"):
                with VerticalScroll(id="sidebar-scroll"):
                    yield Static("[bold cyan]Project Health[/]\n[dim]─────────────────────[/]\n  —", id="sidebar-health", classes="sidebar-section")
            with Container(id="main"):
                yield Static("", id="main-tab-bar")
                with VerticalScroll(id="main-scroll"):
                    yield Static("", id="main-content", markup=True)
            with Container(id="info-hub"):
                with VerticalScroll(id="info-hub-scroll"):
                    yield Static("[bold cyan]Inspector::[/]\n[dim]────────────────────────────────────────[/]\n  —", id="info-hub-content", classes="sidebar-section")
                yield Static("[dim][S] Re-Sync Data[/]", id="info-hub-footer")
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
            on_change=lambda paths: self.call_from_thread(self._on_manifest_change, paths),
        )
        self._view_file_watcher.start()

    def on_unmount(self) -> None:
        if hasattr(self, "_view_file_watcher") and self._view_file_watcher is not None:
            self._view_file_watcher.stop()

    def _on_manifest_change(self, changed_paths: List[Path]) -> None:
        if not changed_paths:
            return
        self.refresh_view()

    def _get_header_strip_content(self) -> Union[str, RenderableType]:
        """Header: Manifest View, Planning/Differences, STATUS (implementation status), TIME."""
        return build_header_strip_content(
            self._diagram_comp_status or {},
            self._right_panel_differences,
            datetime.now().strftime("%H:%M:%S"),
        )

    def _refresh_header_metrics(self) -> None:
        """Refresh header strip (Planning/Differences, STATUS, TIME)."""
        try:
            strip_w = self.query_one("#header-metrics", Static)
            strip_w.update(self._get_header_strip_content())
        except Exception as e:
            logger.debug("Header refresh failed: %s", e)

    def _get_tab_bar_content(self) -> str:
        """Tab bar: Diagram, Files, Timeline; current one highlighted."""
        return build_tab_bar_content(self.current_view.value)

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
        """Refresh left (Health) and right (Inspector) panels."""
        try:
            health_w = self.query_one("#sidebar-health", Static)
            health_w.update(self._get_sidebar_health())
            try:
                hub_w = self.query_one("#info-hub-content", Static)
                hub_w.update(self._get_info_hub_content())
            except Exception as e:
                logger.debug("Info hub refresh failed: %s", e)
        except Exception as e:
            logger.debug("Sidebar refresh failed: %s", e)

    def refresh_view(self) -> None:
        """Refresh all. Load view data via entity_model once per cycle; reuse for diagram, sidebar, content."""
        try:
            self._view_data = get_entities_for_view(self.manifest_dir)
        except Exception as e:
            logger.debug("refresh_view load failed: %s", e)
            self._view_data = {}
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
