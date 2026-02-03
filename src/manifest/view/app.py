"""TUI dashboard: 1=Design, 2=History, 3=Mission; panel i, v/d/f for Inspect."""
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Set
from enum import Enum

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
from manifest.audit.metadata.architecture_metadata import load_architecture_with_metadata
from manifest.core.logger import get_logger
from manifest.view.file_watcher import ViewFileWatcher
from manifest.audit.monitoring.drift_monitor import DriftMonitor

logger = get_logger(__name__)


def _blueprint_component_names(manifest_dir: Path) -> Dict[str, str]:
    """Component id → display name from blueprint."""
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
    """Component id → feature names that reference it."""
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
    """Feature id → status: implemented, design_only, partial, or drift (from linked components)."""
    out: Dict[str, str] = {}
    for feat in architecture.get("features", []) or []:
        if not isinstance(feat, dict):
            continue
        fid = feat.get("id")
        comp_ids = feat.get("components", []) or []
        if not fid:
            continue
        if not comp_ids:
            out[fid] = "design_only"
            continue
        statuses = [comp_status.get(cid, "design_only") for cid in comp_ids]
        if any(s == "drift" for s in statuses):
            out[fid] = "drift"
        elif all(s == "implemented" for s in statuses):
            out[fid] = "implemented"
        elif all(s == "design_only" for s in statuses):
            out[fid] = "design_only"
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


def _status_label(status: str) -> str:
    if status == "implemented":
        return "done"
    if status == "design_only":
        return "design"
    if status == "partial":
        return "partial"
    if status == "drift":
        return "drift"
    if status == "extra":
        return "extra"
    return status


def _status_color_tag(status: str) -> str:
    """Rich color: green=done, yellow=design, orange=partial, red=drift."""
    if status == "implemented":
        return "green"
    if status == "design_only":
        return "yellow"
    if status == "partial":
        return "orange1"
    if status == "drift":
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


def _order_components_by_flow(
    components: List[Dict[str, Any]],
    contracts: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Order by contract from→to; append rest."""
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
    """Boxes connected by arrows (contract order), status under each."""
    lines: List[str] = []
    components = blueprint.get("components", [])
    contracts = blueprint.get("contracts", [])
    if not components and not contracts:
        return ""
    id_to_name: Dict[str, str] = {}
    for c in components:
        cid = c.get("id")
        name = (c.get("name") or cid or "?")[:20]
        if cid:
            id_to_name[cid] = name
    comp_list = _order_components_by_flow(components, contracts) if contracts else components[:12]
    if not comp_list:
        lines.append(title)
        lines.append("  (no components)")
        return "\n".join(lines)
    arrow = " ───► "
    boxes_top = []
    boxes_mid = []
    boxes_bot = []
    for c in comp_list:
        cid = c.get("id")
        name = id_to_name.get(cid, (c.get("name") or cid or "?")[:20])
        w = max(len(name), 2)
        t, m, b = _box(name, w)
        st = (comp_status or {}).get(cid or "", "?")
        tag = _status_color_tag(st)
        boxes_top.append(f"[{tag}]{t}[/]")
        boxes_mid.append(f"[{tag}]{m}[/]")
        boxes_bot.append(f"[{tag}]{b}[/]")
    lines.append(title)
    lines.append("  " + arrow.join(boxes_top))
    lines.append("  " + arrow.join(boxes_mid))
    lines.append("  " + arrow.join(boxes_bot))
    return "\n".join(lines).strip()


def _render_architecture_diagram(
    architecture: Dict[str, Any],
    feature_status: Optional[Dict[str, str]] = None,
) -> str:
    """Feature boxes in a row with arrows; color by status (done/design/partial/drift)."""
    lines: List[str] = []
    features = architecture.get("features", [])
    if not features:
        return ""
    arrow = " ───► "
    boxes_top = []
    boxes_mid = []
    boxes_bot = []
    for feat in features[:12]:
        if not isinstance(feat, dict):
            continue
        fid = feat.get("id")
        name = (feat.get("name") or feat.get("id") or "?")[:20]
        w = max(len(name), 2)
        t, m, b = _box(name, w)
        st = (feature_status or {}).get(fid or "", "design_only")
        tag = _status_color_tag(st)
        boxes_top.append(f"[{tag}]{t}[/]")
        boxes_mid.append(f"[{tag}]{m}[/]")
        boxes_bot.append(f"[{tag}]{b}[/]")
    if not boxes_top:
        return ""
    lines.append("  " + arrow.join(boxes_top))
    lines.append("  " + arrow.join(boxes_mid))
    lines.append("  " + arrow.join(boxes_bot))
    if len(features) > 12:
        lines.append("  ...")
    return "\n".join(lines)


def _render_link_diagram(
    architecture: Dict[str, Any],
    comp_names: Dict[str, str],
    feature_status: Optional[Dict[str, str]] = None,
    comp_status: Optional[Dict[str, str]] = None,
) -> str:
    """Diagram: feature boxes above, component boxes below; color by status."""
    lines: List[str] = []
    features = architecture.get("features", []) or []
    if not features or not comp_names:
        return ""
    sep = "   "
    f_tops, f_mids, f_bots = [], [], []
    c_tops, c_mids, c_bots = [], [], []
    pipe_parts = []
    v_parts = []
    for feat in features[:10]:
        if not isinstance(feat, dict):
            continue
        fid = feat.get("id")
        fname = (feat.get("name") or feat.get("id") or "?")[:14]
        comp_ids = feat.get("components", []) or []
        cid = comp_ids[0] if comp_ids else None
        cname = comp_names.get(cid, cid[:14] if cid else "—")[:14] if cid else "—"
        w = max(len(fname), len(cname), 2)
        ft, fm, fb = _box(fname, w)
        ct, cm, cb = _box(cname, w)
        fst = (feature_status or {}).get(fid or "", "design_only")
        cst = (comp_status or {}).get(cid or "", "design_only") if cid else "design_only"
        ftag = _status_color_tag(fst)
        ctag = _status_color_tag(cst)
        f_tops.append(f"[{ftag}]{ft}[/]")
        f_mids.append(f"[{ftag}]{fm}[/]")
        f_bots.append(f"[{ftag}]{fb}[/]")
        c_tops.append(f"[{ctag}]{ct}[/]")
        c_mids.append(f"[{ctag}]{cm}[/]")
        c_bots.append(f"[{ctag}]{cb}[/]")
        col_w = w + 2
        mid = col_w // 2
        pipe_parts.append(" " * (mid - 1) + "|" + " " * (col_w - mid - 1))
        v_parts.append(" " * (mid - 1) + "v" + " " * (col_w - mid - 1))
    if not f_tops:
        return ""
    lines.append("  " + sep.join(f_tops))
    lines.append("  " + sep.join(f_mids))
    lines.append("  " + sep.join(f_bots))
    lines.append("  " + sep.join(pipe_parts))
    lines.append("  " + sep.join(v_parts))
    lines.append("  " + sep.join(c_tops))
    lines.append("  " + sep.join(c_mids))
    lines.append("  " + sep.join(c_bots))
    return "\n".join(lines)


class ViewType(Enum):
    DESIGN = "design"
    HISTORY = "history"
    MISSION_CONTROL = "mission_control"
    ARCHITECT = "architect"
    BLUEPRINT = "blueprint"
    INSPECTOR = "inspector"


class InspectorMode(Enum):
    """Inspector view mode (drift, visual status, or data)."""
    VISUAL = "visual"
    DATA = "data"
    DRIFT = "drift"


class ManifestViewApp(App[None]):
    TITLE = "Manifest Dashboard"
    SUB_TITLE = "Metrics"
    CSS = """
    Screen { background: #0d1117; color: #c9d1d9; }
    #header-strip { height: auto; padding: 0 1; background: #161b22; border: solid #30363d; }
    #body-row { height: 1fr; }
    #sidebar { width: 1fr; min-width: 22; max-width: 35; border-right: solid #30363d; background: #0d1117; }
    #sidebar ScrollableContainer { padding: 0 1; }
    #main { width: 3fr; padding: 1 2; }
    .sidebar-section { margin-bottom: 1; padding: 0 1; border-bottom: solid #30363d; }
    #sidebar-tasks { overflow: hidden; }
    .sidebar-title { color: #58a6ff; text-style: bold; }
    .nav-item { padding: 0 1; margin-right: 1; }
    .nav-item.active { background: #1f6feb; color: white; }
    #inspect-panel { height: auto; max-height: 40%; border-top: solid #30363d; background: #161b22; padding: 0 1; }
    .inspect-panel-hidden { display: none; }
    """

    BINDINGS = [
        Binding("1", "switch_view('Design')", "Design", key_display="1"),
        Binding("2", "switch_view('History')", "History", key_display="2"),
        Binding("3", "switch_view('Mission')", "Mission", key_display="3"),
        Binding("i", "toggle_inspect_panel", "Inspect", key_display="i"),
        Binding("v", "switch_inspector_mode('Visual')", "Visual", key_display="v"),
        Binding("d", "switch_inspector_mode('Data')", "Data", key_display="d"),
        Binding("f", "switch_inspector_mode('Drift')", "Drift", key_display="f"),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, manifest_dir: Optional[Path] = None, **kwargs: Any):
        super().__init__(**kwargs)
        self.manifest_dir = (manifest_dir or (Path.cwd() / ".manifest")).resolve()
        self.current_view = ViewType.DESIGN
        self.inspector_mode = InspectorMode.DRIFT
        self._inspect_panel_visible = False
        self._last_completed_task_ids: set = set()
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
        """Tasks and sprints from tasks.json or state."""
        tasks_file = self.manifest_dir / "tasks.json"
        if tasks_file.exists():
            try:
                with open(tasks_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                tasks = data.get("tasks", [])
                sprints = data.get("sprints", [])
                return tasks, sprints
            except Exception:
                pass
        state_mgr = self._get_state_manager()
        tasks = state_mgr.get_task_checklist()
        sprint_ids = state_mgr.list_sprints()
        sprints = [{"id": sid} for sid in sprint_ids]
        return tasks, sprints

    def _load_design_view(self) -> str:
        """Diagram view: Features, Structure, Link (all as diagrams)."""
        lines = []
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

            feat_diag = _render_architecture_diagram(architecture, feature_status)
            if feat_diag:
                lines.append("Features")
                lines.append(feat_diag)
                lines.append("")

            struct_diag = _render_blueprint_diagram(top_down, "Structure", comp_status)
            if struct_diag:
                lines.append(struct_diag)
                lines.append("")

            link_diag = _render_link_diagram(architecture, comp_names, feature_status, comp_status)
            if link_diag:
                lines.append("Link (feature → component)")
                lines.append(link_diag)
            elif lines:
                lines.append("Link: (no feature–component mapping)")
            if not lines:
                lines.append("Design: (no features or structure)")
        except Exception as e:
            logger.debug("Design view load failed: %s", e)
            lines.append("Design: (load failed)")
        return "\n".join(lines).strip() or "Design: (no data)"

    def _load_history_view(self) -> str:
        """Design history + git commits."""
        lines = []
        try:
            from manifest.core.design_history import get_design_history
            design_entries = get_design_history(self.manifest_dir)
            if design_entries:
                lines.append(f"Entries: {len(design_entries)}")
                for entry in design_entries[:15]:
                    doc = entry.get("doc", "?")
                    path = entry.get("path", "?")
                    ts = (entry.get("timestamp") or "?")[:10]
                    lines.append(f"  [{doc}] {path} | {ts}")
                if len(design_entries) > 15:
                    lines.append(f"  ... and {len(design_entries) - 15} more")
                lines.append("")
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
                lines.append(f"Branch: {branch}")
                lines.append(f"Commits: {len(commits)}")
                for commit in commits:
                    short_hash = commit.get("short_hash", "?")
                    author = commit.get("author", "?")[:20]
                    message = commit.get("message", "?")[:60].replace("\n", " ")
                    timestamp = commit.get("timestamp", "?")[:10]
                    lines.append(f"  [{short_hash}] {author} | {timestamp}")
                    lines.append(f"    {message}")
            else:
                if not design_entries:
                    lines.append("History: (Git not available; no design history yet)")
        except Exception as e:
            logger.debug("History view load failed: %s", e)
            lines.append("History: (load failed)")
        return "\n".join(lines) if lines else "History: (no data)"

    def _load_inspector_view(self) -> str:
        """Inspect panel: drift / visual / data."""
        lines = []
        try:
            if self.inspector_mode == InspectorMode.DRIFT:
                top_down = BlueprintLoader.load_blueprint(
                    self.manifest_dir,
                    with_metadata=True,
                    default_source="llm_design",
                )
                bottom_up = BlueprintLoader.load_code_blueprint(self.manifest_dir)
                comparator = self._get_blueprint_comparator()
                conflicts = comparator.compare_blueprints(top_down, bottom_up)
                lines.append(f"Drift Conflicts: {len(conflicts)}")
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
                implemented = sum(1 for s in comp_status.values() if s == "implemented")
                design_only = sum(1 for s in comp_status.values() if s == "design_only")
                partial = sum(1 for s in comp_status.values() if s == "partial")
                drift = sum(1 for s in comp_status.values() if s == "drift")
                lines.append("Visual Status:")
                lines.append(f"  {_status_label_markup('implemented', f'Done: {implemented}')}")
                lines.append(f"  {_status_label_markup('design_only', f'Design: {design_only}')}")
                lines.append(f"  {_status_label_markup('partial', f'Partial: {partial}')}")
                lines.append(f"  {_status_label_markup('drift', f'Drift: {drift}')}")
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

    def _load_mission_control_view(self) -> str:
        """Mission: tasks, sprints, channels, resources."""
        lines = []
        try:
            state_mgr = self._get_state_manager()
            mission_tree = state_mgr.get_mission_tree()
            tasks, sprints = self._get_tasks_and_sprints_from_manifest()
            lines.append(f"Tasks: {len(tasks)}")
            for t in tasks[:30]:
                tid = t.get("id", "?")
                name = t.get("name", "?")[:50]
                status = t.get("status", "?")
                stage = t.get("stage", "?")
                progress = t.get("progress", {})
                pct = progress.get("percentage", 0) if isinstance(progress, dict) else 0
                lines.append(f"  [{tid}] {name}")
                lines.append(f"    Status: {status} | Stage: {stage}" + (f" | {pct}%" if pct else ""))
            if len(tasks) > 30:
                lines.append(f"  ... and {len(tasks) - 30} more")
            if sprints:
                lines.append(f"\nSprints: {len(sprints)}")
                for s in sprints[:10]:
                    sid = s.get("id", "?") if isinstance(s, dict) else str(s)
                    name = s.get("name", sid)[:40] if isinstance(s, dict) else sid
                    lines.append(f"  · {name}")
            chat_history = state_mgr.get_state().get("chat_history", {})
            squad_channels = [c for c in chat_history if isinstance(c, str) and c.startswith("squad-")]
            if squad_channels:
                lines.append(f"\nWorker squad channels: {len(squad_channels)}")
                for ch in squad_channels[:10]:
                    msgs = state_mgr.get_chat_history(ch)
                    lines.append(f"  [{ch}] ({len(msgs)} msgs)")
                    for m in msgs[-2:]:
                        role = m.get("role", "?")
                        content = (m.get("content") or "")[:60].replace("\n", " ")
                        lines.append(f"    {role}: {content}...")
            else:
                lines.append("\nWorker squad channels: (none yet)")
            lines.append("\nResources")
            try:
                from manifest.core.config import ConfigManager
                cm = ConfigManager(self.manifest_dir)
                limits = cm.get_setting("resource_limits", {}) or {}
                tokens = limits.get("tokens_per_day")
                model = limits.get("model")
                cost = limits.get("cost_limit")
                lines.append(f"  Limits: tokens_per_day={tokens}, model={model}, cost_limit={cost}")
            except Exception:
                lines.append("  Limits: (see .manifest/settings.json)")
            resource_usage = state_mgr.get_state().get("resource_usage", {})
            if resource_usage:
                lines.append(f"  Last usage: {resource_usage}")
            else:
                lines.append("  Usage: (available when orchestrator/agents run)")
            lines.append("  Manage: .manifest/settings.json (resource_limits)")
        except Exception as e:
            logger.debug("Mission Control view load failed: %s", e)
            lines.append("Mission Control: (load failed)")
        return "\n".join(lines) if lines else "Mission Control: (no data)"

    def _get_current_view_content(self) -> str:
        """Content for current view."""
        if self.current_view == ViewType.DESIGN:
            return self._load_design_view()
        elif self.current_view == ViewType.HISTORY:
            return self._load_history_view()
        elif self.current_view == ViewType.MISSION_CONTROL:
            return self._load_mission_control_view()
        return "Unknown view"

    def _get_sidebar_tasks(self) -> str:
        """Sidebar: numbered tasks, one line each, progress bar per task and overall."""
        try:
            tasks, sprints = self._get_tasks_and_sprints_from_manifest()
            if not tasks:
                return "Tasks (0)"
            name_max = 14
            overall_pct = 0.0
            total_pct = 0.0
            for t in tasks:
                prog = t.get("progress") or {}
                total_pct += prog.get("percentage", 0) if isinstance(prog, dict) else 0
            overall_pct = total_pct / len(tasks) if tasks else 0
            head = f"Sprint {_progress_bar(overall_pct, 8)} {int(overall_pct)}%"
            task_lines = []
            for i, t in enumerate(tasks[:8], 1):
                raw_name = (t.get("name") or t.get("id") or "?").replace("\n", " ").strip()
                name = raw_name[:name_max].ljust(name_max)[:name_max]
                prog = t.get("progress") or {}
                pct = prog.get("percentage", 0) if isinstance(prog, dict) else 0
                bar = _progress_bar(pct, 6)
                task_lines.append(f" {i}. {name} {bar} {pct}%")
            lines = [head] + task_lines
            if len(tasks) > 8:
                lines.append(f" ... +{len(tasks) - 8}")
            return "\n".join(lines)
        except Exception as e:
            logger.debug("Sidebar tasks failed: %s", e)
            return "Tasks (—)"

    def _get_sidebar_status(self) -> str:
        """Sidebar status (in code / design only / drift)."""
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
            imp = sum(1 for s in comp_status.values() if s == "implemented")
            design_only = sum(1 for s in comp_status.values() if s == "design_only")
            partial = sum(1 for s in comp_status.values() if s == "partial")
            drift = sum(1 for s in comp_status.values() if s == "drift")
            return (
                "Status\n"
                f"  {_status_label_markup('implemented', f'Done: {imp}')}\n"
                f"  {_status_label_markup('design_only', f'Design: {design_only}')}\n"
                f"  {_status_label_markup('partial', f'Partial: {partial}')}\n"
                f"  {_status_label_markup('drift', f'Drift: {drift}')}"
            )
        except Exception as e:
            logger.debug("Sidebar status failed: %s", e)
            return "Status (—)"

    def _get_sidebar_viz(self) -> str:
        """Current view name."""
        name = {
            ViewType.ARCHITECT: "Architect",
            ViewType.BLUEPRINT: "Blueprint",
            ViewType.HISTORY: "History",
            ViewType.MISSION_CONTROL: "Mission",
        }.get(self.current_view, "—")
        return f"View: {name}"

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="header-strip"):
            yield Static(
                "Manifest Dashboard | Metrics",
                id="header-metrics",
            )
        with Horizontal(id="body-row"):
            with Container(id="sidebar"):
                with VerticalScroll(id="sidebar-scroll"):
                    yield Static("Tasks\n(loading)", id="sidebar-tasks", classes="sidebar-section")
                    yield Static("Status\n(loading)", id="sidebar-status", classes="sidebar-section")
                    yield Static("View\n(loading)", id="sidebar-viz", classes="sidebar-section")
            with Container(id="main"):
                with VerticalScroll(id="main-scroll"):
                    yield Static("", id="main-content")
        with Container(id="inspect-panel", classes="inspect-panel-hidden"):
            with VerticalScroll(id="inspect-panel-scroll"):
                yield Static("", id="inspect-panel-text")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_sidebar()
        self._refresh_main_content()
        self._refresh_header_metrics()
        self.set_interval(30, self._refresh_sidebar)
        self.set_interval(30, self._refresh_header_metrics)
        self._view_file_watcher = ViewFileWatcher(
            self.manifest_dir,
            on_change=self._on_manifest_change,
        )
        self.set_interval(2, self._check_manifest_changes)
        self._drift_monitor = DriftMonitor(
            project_root=self.manifest_dir.parent,
            manifest_dir=self.manifest_dir,
        )
        self._check_drift()

    def _check_manifest_changes(self) -> None:
        """Check .manifest/ for changes."""
        try:
            self._view_file_watcher.check()
        except Exception as e:
            logger.debug("Manifest watch check failed: %s", e)

    def _on_manifest_change(self, changed_paths: List[Path]) -> None:
        """On .manifest/ change: refresh; trigger drift if task completed."""
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
                    self._check_drift()
                self._last_completed_task_ids = completed
            except Exception as e:
                logger.debug("Task-done drift check failed: %s", e)
        self.refresh_view()

    def _check_drift(self) -> None:
        """Update blueprint_code.json if code changed."""
        try:
            self._drift_monitor.check_and_update()
        except Exception as e:
            logger.debug("Drift check failed: %s", e)

    def _refresh_header_metrics(self) -> None:
        """Header: task count."""
        try:
            tasks, _ = self._get_tasks_and_sprints_from_manifest()
            n = len(tasks)
            self.sub_title = f"Tasks: {n}"
        except Exception:
            self.sub_title = "Metrics"

    def _refresh_main_content(self) -> None:
        """Refresh main content."""
        try:
            main_w = self.query_one("#main-content", Static)
            main_w.update(self._get_current_view_content())
        except Exception as e:
            logger.debug("Main content refresh failed: %s", e)

    def _refresh_sidebar(self) -> None:
        """Refresh sidebar."""
        try:
            tasks_w = self.query_one("#sidebar-tasks", Static)
            tasks_w.update(self._get_sidebar_tasks())
            status_w = self.query_one("#sidebar-status", Static)
            status_w.update(self._get_sidebar_status())
            viz_w = self.query_one("#sidebar-viz", Static)
            viz_w.update(self._get_sidebar_viz())
        except Exception as e:
            logger.debug("Sidebar refresh failed: %s", e)

    def refresh_view(self) -> None:
        """Refresh all."""
        self._refresh_sidebar()
        self._refresh_main_content()
        self._refresh_header_metrics()
        if self._inspect_panel_visible:
            self._refresh_inspect_panel()

    def action_switch_view(self, view_name: str) -> None:
        """Switch view (1–4)."""
        view_map = {
            "Design": ViewType.DESIGN,
            "History": ViewType.HISTORY,
            "Mission": ViewType.MISSION_CONTROL,
        }
        if view_name in view_map:
            self.current_view = view_map[view_name]
            self.refresh_view()

    def action_switch_inspector_mode(self, mode_name: str) -> None:
        """Set Inspect mode (v/d/f) and show panel."""
        mode_map = {
            "Visual": InspectorMode.VISUAL,
            "Data": InspectorMode.DATA,
            "Drift": InspectorMode.DRIFT,
        }
        if mode_name in mode_map:
            self.inspector_mode = mode_map[mode_name]
            if not self._inspect_panel_visible:
                self._inspect_panel_visible = True
                try:
                    panel = self.query_one("#inspect-panel", Container)
                    panel.remove_class("inspect-panel-hidden")
                except Exception as e:
                    logger.debug("Show inspect panel failed: %s", e)
            self._refresh_inspect_panel()

    def action_toggle_inspect_panel(self) -> None:
        """Toggle Inspect panel."""
        self._inspect_panel_visible = not self._inspect_panel_visible
        try:
            panel = self.query_one("#inspect-panel", Container)
            if self._inspect_panel_visible:
                panel.remove_class("inspect-panel-hidden")
                self._refresh_inspect_panel()
            else:
                panel.add_class("inspect-panel-hidden")
        except Exception as e:
            logger.debug("Toggle inspect panel failed: %s", e)

    def _refresh_inspect_panel(self) -> None:
        """Refresh Inspect panel."""
        try:
            content = self._load_inspector_view()
            w = self.query_one("#inspect-panel-text", Static)
            w.update(content)
        except Exception as e:
            logger.debug("Inspect panel refresh failed: %s", e)

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
