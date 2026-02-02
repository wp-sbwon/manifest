"""TUI dashboard: views 1–4 (Architect, Blueprint, History, Mission), panels t/i, v/d/f for Inspect."""
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
        return "in code"
    if status == "design_only":
        return "design only"
    if status == "drift":
        return "drift"
    if status == "extra":
        return "extra"
    return status


def _status_color_tag(status: str) -> str:
    """Rich color tag for status."""
    if status == "implemented":
        return "green"
    if status == "design_only":
        return "dim"
    if status == "drift":
        return "red"
    if status == "extra":
        return "cyan"
    return "white"


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
    status_labels: List[str] = []
    for c in comp_list:
        cid = c.get("id")
        name = id_to_name.get(cid, (c.get("name") or cid or "?")[:20])
        w = max(len(name), 2)
        t, m, b = _box(name, w)
        boxes_top.append(t)
        boxes_mid.append(m)
        boxes_bot.append(b)
        st = (comp_status or {}).get(cid or "", "?")
        plain = _status_label(st)[: w + 2].ljust(w + 2)
        label = _status_label_markup(st, plain)
        status_labels.append(label)
    lines.append(title)
    lines.append("  " + arrow.join(boxes_top))
    lines.append("  " + arrow.join(boxes_mid))
    lines.append("  " + arrow.join(boxes_bot))
    if comp_status:
        lines.append("  " + arrow.join(status_labels))
    return "\n".join(lines).strip()


def _render_architecture_diagram(architecture: Dict[str, Any]) -> str:
    """Feature boxes in a row with arrows."""
    lines: List[str] = []
    features = architecture.get("features", [])
    if not features:
        return ""
    lines.append("Diagram (architecture):")
    names: List[str] = []
    for feat in features[:12]:
        if isinstance(feat, dict):
            name = (feat.get("name") or feat.get("id") or "?")[:20]
            names.append(name)
    if not names:
        return "Diagram (architecture):\n  (no features)"
    arrow = " ───► "
    boxes_top = []
    boxes_mid = []
    boxes_bot = []
    for name in names:
        w = max(len(name), 2)
        t, m, b = _box(name, w)
        boxes_top.append(t)
        boxes_mid.append(m)
        boxes_bot.append(b)
    sep = "   "
    lines.append("  " + arrow.join(boxes_top))
    lines.append("  " + arrow.join(boxes_mid))
    lines.append("  " + arrow.join(boxes_bot))
    if len(features) > 12:
        lines.append("  ...")
    return "\n".join(lines)


class ViewType(Enum):
    ARCHITECT = "architect"
    BLUEPRINT = "blueprint"
    HISTORY = "history"
    INSPECTOR = "inspector"
    MISSION_CONTROL = "mission_control"


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
    .sidebar-title { color: #58a6ff; text-style: bold; }
    .nav-item { padding: 0 1; margin-right: 1; }
    .nav-item.active { background: #1f6feb; color: white; }
    #task-panel { height: auto; max-height: 40%; border-top: solid #30363d; background: #161b22; padding: 0 1; }
    .task-panel-hidden { display: none; }
    #inspect-panel { height: auto; max-height: 40%; border-top: solid #30363d; background: #161b22; padding: 0 1; }
    .inspect-panel-hidden { display: none; }
    """

    BINDINGS = [
        Binding("1", "switch_view('Architect')", "Architect", key_display="1"),
        Binding("2", "switch_view('Blueprint')", "Blueprint", key_display="2"),
        Binding("3", "switch_view('History')", "History", key_display="3"),
        Binding("4", "switch_view('Mission')", "Mission", key_display="4"),
        Binding("t", "toggle_task_panel", "Task panel", key_display="t"),
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
        self.current_view = ViewType.BLUEPRINT
        self.inspector_mode = InspectorMode.DRIFT
        self._task_panel_visible = False
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

    def _load_architect_view(self) -> str:
        """Intent + architecture features."""
        lines = []
        try:
            lines.append("Intent + architecture: features/capabilities and requirements. (Blueprint = structure & contracts.)")
            lines.append("")
            intent_file = self.manifest_dir / "intent.json"
            if intent_file.exists():
                with open(intent_file, "r", encoding="utf-8") as f:
                    intent = json.load(f)
                features = intent.get("features", [])
                lines.append(f"Intent Features: {len(features)}")
                for feat in features[:20]:
                    if isinstance(feat, dict):
                        fid = feat.get("id", "?")
                        name = (feat.get("name") or "?")[:50]
                        lines.append(f"  · [{fid}] {name}")
                if len(features) > 20:
                    lines.append(f"  ... and {len(features) - 20} more")
            else:
                lines.append("Intent: (no intent.json)")

            arch_file = self.manifest_dir / "architecture.json"
            architecture = load_architecture_with_metadata(arch_file)
            features = architecture.get("features", [])
            comp_names = _blueprint_component_names(self.manifest_dir)
            if features:
                lines.append(f"\nArchitecture Features: {len(features)} (→ structure = Blueprint component)")
                for feat in features[:10]:
                    if isinstance(feat, dict):
                        fid = feat.get("id", "?")
                        name = feat.get("name", "?")[:50]
                        comp_ids = feat.get("components", []) or []
                        linked = ", ".join(comp_names.get(c, c) for c in comp_ids[:5]) if comp_ids else "—"
                        lines.append(f"  · [{fid}] {name}  → [{linked}]")
                diagram = _render_architecture_diagram(architecture)
                if diagram:
                    lines.append("")
                    lines.append(diagram)
        except Exception as e:
            logger.debug("Architect view load failed: %s", e)
            lines.append("Architect: (load failed)")
        return "\n".join(lines) if lines else "Architect: (no data)"

    def _load_blueprint_view(self) -> str:
        """Blueprint: components, contracts, status."""
        lines = []
        try:
            lines.append("Blueprint: structure — components and contracts (who talks to whom). (Architect = intent & features.)")
            lines.append("")
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
            drift = sum(1 for s in comp_status.values() if s == "drift")
            lines.append(
                "Summary: "
                f"{_status_label_markup('implemented', f'{implemented} in code')}, "
                f"{_status_label_markup('design_only', f'{design_only} design only')}, "
                f"{_status_label_markup('drift', f'{drift} drift')}."
            )
            lines.append("")
            diagram = _render_blueprint_diagram(top_down, "Design", comp_status)
            if diagram:
                lines.append(diagram)
            else:
                lines.append("(no components or contracts)")
            comp_to_feats = _architecture_features_by_component(architecture)
            id_to_name = {c.get("id"): (c.get("name") or c.get("id") or "?")[:30] for c in top_down.get("components", []) if c.get("id")}
            if comp_to_feats and id_to_name:
                lines.append("")
                lines.append("Linked to Architect (feature per component):")
                for cid, names in comp_to_feats.items():
                    comp_name = id_to_name.get(cid, cid)
                    feats = ", ".join(n[:25] for n in names[:3])
                    lines.append(f"  {comp_name}  ↔  {feats}")
        except Exception as e:
            logger.debug("Blueprint view load failed: %s", e)
            lines.append("Blueprint: (load failed)")
        return "\n".join(lines) if lines else "Blueprint: (no data)"

    def _load_history_view(self) -> str:
        """Design history + git commits."""
        lines = []
        try:
            from manifest.core.design_history import get_design_history
            design_entries = get_design_history(self.manifest_dir)
            if design_entries:
                lines.append("Design history (PRD / architecture / blueprint)")
                lines.append(f"  Entries: {len(design_entries)}")
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
            lines.append("Inspect: drill-down from Blueprint (v=Visual, d=Data, f=Drift).")
            lines.append("")
            if self.inspector_mode == InspectorMode.DRIFT:
                lines.append("Mode: Drift — design vs code conflicts.")
                lines.append("")
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
                lines.append("Mode: Visual — component status counts (implemented / design only / drift).")
                lines.append("")
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
                drift = sum(1 for s in comp_status.values() if s == "drift")
                lines.append("Visual Status:")
                lines.append(f"  {_status_label_markup('implemented', f'In code: {implemented}')}")
                lines.append(f"  {_status_label_markup('design_only', f'Design only: {design_only}')}")
                lines.append(f"  {_status_label_markup('drift', f'Drift: {drift}')}")
            else:
                lines.append("Mode: Data — execution trace and I/O flow from orchestrator/agents.")
                lines.append("(Use OpenCode/orchestrator to run tasks; data appears when agents run.)")
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
            lines.append(f"Mission Tree: {len(mission_tree.get('nodes', []))} nodes")
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
            shadow_channels = [c for c in chat_history if isinstance(c, str) and c.startswith("shadow-")]
            if shadow_channels:
                lines.append(f"\nComponent / shadow output: {len(shadow_channels)}")
                for ch in shadow_channels[:8]:
                    msgs = state_mgr.get_chat_history(ch)
                    lines.append(f"  [{ch}] ({len(msgs)} msgs)")
                    for m in msgs[-2:]:
                        role = m.get("role", "?")
                        content = (m.get("content") or "")[:60].replace("\n", " ")
                        lines.append(f"    {role}: {content}...")
            else:
                lines.append("\nComponent / shadow output: (none yet)")
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
        if self.current_view == ViewType.ARCHITECT:
            return self._load_architect_view()
        elif self.current_view == ViewType.BLUEPRINT:
            return self._load_blueprint_view()
        elif self.current_view == ViewType.HISTORY:
            return self._load_history_view()
        elif self.current_view == ViewType.MISSION_CONTROL:
            return self._load_mission_control_view()
        return "Unknown view"

    def _get_sidebar_tasks(self) -> str:
        """Sidebar task list."""
        try:
            tasks, _ = self._get_tasks_and_sprints_from_manifest()
            lines = [f"Tasks ({len(tasks)})"]
            for t in tasks[:8]:
                name = (t.get("name") or t.get("id", "?"))[:22]
                status = t.get("status", "?")
                lines.append(f"  {name} [{status}]")
            if len(tasks) > 8:
                lines.append(f"  ... +{len(tasks) - 8}")
            return "\n".join(lines) if lines else "Tasks (0)"
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
            drift = sum(1 for s in comp_status.values() if s == "drift")
            return (
                "Status\n"
                f"  {_status_label_markup('implemented', f'In code: {imp}')}\n"
                f"  {_status_label_markup('design_only', f'Design only: {design_only}')}\n"
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
        with Container(id="task-panel", classes="task-panel-hidden"):
            with VerticalScroll(id="task-panel-scroll"):
                yield Static("", id="task-panel-text")
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
        if self._task_panel_visible:
            self._refresh_task_panel()
        if self._inspect_panel_visible:
            self._refresh_inspect_panel()

    def action_switch_view(self, view_name: str) -> None:
        """Switch view (1–4)."""
        view_map = {
            "Architect": ViewType.ARCHITECT,
            "Blueprint": ViewType.BLUEPRINT,
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

    def action_toggle_task_panel(self) -> None:
        """Toggle Task panel."""
        self._task_panel_visible = not self._task_panel_visible
        try:
            panel = self.query_one("#task-panel", Container)
            if self._task_panel_visible:
                panel.remove_class("task-panel-hidden")
                self._refresh_task_panel()
            else:
                panel.add_class("task-panel-hidden")
        except Exception as e:
            logger.debug("Toggle task panel failed: %s", e)

    def _refresh_task_panel(self) -> None:
        """Refresh Task panel."""
        try:
            content = self._load_mission_control_view()
            w = self.query_one("#task-panel-text", Static)
            w.update(content)
        except Exception as e:
            logger.debug("Task panel refresh failed: %s", e)

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
