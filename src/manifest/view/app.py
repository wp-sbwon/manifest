"""
Manifest View App - UI Redesign Plan (Phase 1).

Layout: Header (Dashboard | Metrics) | Sidebar (Tasks, Status, Viz) | Main Chat Area.
Chat runs in OpenCode; this view shows compact sidebar + placeholder for chat.
Task panel is toggleable (keybind t). Watches .manifest/ for real-time sync.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
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

# Main chat area placeholder (chat runs in OpenCode)
MAIN_CHAT_PLACEHOLDER = """Main Chat Area (OpenCode style)

Chat runs in the OpenCode terminal. Use that window for:
  · Conversation and agent commands
  · @ file references
  · ! bash commands
  · / slash commands

This panel shows dashboard and compact viz; switch sidebar views with 1–5."""


class ViewType(Enum):
    """뷰 타입."""
    ARCHITECT = "architect"
    BLUEPRINT = "blueprint"
    HISTORY = "history"
    INSPECTOR = "inspector"
    MISSION_CONTROL = "mission_control"


class InspectorMode(Enum):
    """Inspector View 모드."""
    VISUAL = "visual"
    DATA = "data"
    DRIFT = "drift"


class ManifestViewApp(App[None]):
    """View app per UI Redesign Plan: Header | Sidebar (Tasks, Status, Viz) | Main Chat Area. Task panel toggle."""

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
    """

    BINDINGS = [
        Binding("1", "switch_view('Architect')", "Architect", key_display="1"),
        Binding("2", "switch_view('Blueprint')", "Blueprint", key_display="2"),
        Binding("3", "switch_view('History')", "History", key_display="3"),
        Binding("4", "switch_view('Inspector')", "Inspector", key_display="4"),
        Binding("5", "switch_view('Mission')", "Mission", key_display="5"),
        Binding("t", "toggle_task_panel", "Task panel", key_display="t"),
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
            self._git_manager = GitManager(self.manifest_dir.parent)
        return self._git_manager

    def _get_blueprint_comparator(self) -> BlueprintComparator:
        if self._blueprint_comparator is None:
            self._blueprint_comparator = BlueprintComparator()
        return self._blueprint_comparator

    def _get_tasks_and_sprints_from_manifest(self) -> Tuple[List[Dict[str, Any]], List[Any]]:
        """Load tasks and sprints from .manifest/tasks.json if present; else from state."""
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
        """Load Architect View data (intent.json, architecture.json)."""
        lines = []
        try:
            intent_file = self.manifest_dir / "intent.json"
            if intent_file.exists():
                with open(intent_file, "r", encoding="utf-8") as f:
                    intent = json.load(f)
                features = intent.get("features", [])
                lines.append(f"Features: {len(features)}")
                for feat in features[:20]:
                    fid = feat.get("id", "?")
                    name = feat.get("name", "?")[:50]
                    lines.append(f"  · [{fid}] {name}")
                if len(features) > 20:
                    lines.append(f"  ... and {len(features) - 20} more")
            else:
                lines.append("Intent: (no intent.json)")

            arch_file = self.manifest_dir / "architecture.json"
            architecture = load_architecture_with_metadata(arch_file)
            features = architecture.get("features", [])
            if features:
                lines.append(f"\nArchitecture Features: {len(features)}")
                for feat in features[:10]:
                    fid = feat.get("id", "?")
                    name = feat.get("name", "?")[:50]
                    lines.append(f"  · [{fid}] {name}")
        except Exception as e:
            logger.debug("Architect view load failed: %s", e)
            lines.append("Architect: (load failed)")
        return "\n".join(lines) if lines else "Architect: (no data)"

    def _load_blueprint_view(self) -> str:
        """Load Blueprint View data (blueprint.json)."""
        lines = []
        try:
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
            components = top_down.get("components", []) or bottom_up.get("components", [])
            comp_status = status_info.get("component_statuses", {})
            lines.append(f"Components: {len(components)}")
            for c in components[:30]:
                cid = c.get("id", c.get("name", ""))
                st = comp_status.get(cid, "unknown")
                name = c.get("name", cid)[:50]
                lines.append(f"  · {name}: {st}")
            if len(components) > 30:
                lines.append(f"  ... and {len(components) - 30} more")
        except Exception as e:
            logger.debug("Blueprint view load failed: %s", e)
            lines.append("Blueprint: (load failed)")
        return "\n".join(lines) if lines else "Blueprint: (no data)"

    def _load_history_view(self) -> str:
        """Load History View data (Git commits)."""
        lines = []
        try:
            git_mgr = self._get_git_manager()
            if not git_mgr.is_available():
                return "History: (Git not available or not a git repository)"
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
        except Exception as e:
            logger.debug("History view load failed: %s", e)
            lines.append("History: (load failed)")
        return "\n".join(lines) if lines else "History: (no commits)"

    def _load_inspector_view(self) -> str:
        """Load Inspector View data (모드에 따라 다름)."""
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
                ghost = sum(1 for s in comp_status.values() if s == "ghost")
                drift = sum(1 for s in comp_status.values() if s == "drift")
                lines.append(f"Visual Status:")
                lines.append(f"  Implemented: {implemented}")
                lines.append(f"  Ghost: {ghost}")
                lines.append(f"  Drift: {drift}")
            else:  # DATA mode
                lines.append("Data Mode: (execution trace and I/O flow)")
                lines.append("(Use orchestrator commands in OpenCode to view execution data)")
        except Exception as e:
            logger.debug("Inspector view load failed: %s", e)
            lines.append("Inspector: (load failed)")
        return "\n".join(lines) if lines else "Inspector: (no data)"

    def _load_mission_control_view(self) -> str:
        """Load Mission Control View data (Task/Mission 상태만, read-only). Prefers tasks.json."""
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
        except Exception as e:
            logger.debug("Mission Control view load failed: %s", e)
            lines.append("Mission Control: (load failed)")
        return "\n".join(lines) if lines else "Mission Control: (no data)"

    def _get_current_view_content(self) -> str:
        """Get content for current view."""
        if self.current_view == ViewType.ARCHITECT:
            return self._load_architect_view()
        elif self.current_view == ViewType.BLUEPRINT:
            return self._load_blueprint_view()
        elif self.current_view == ViewType.HISTORY:
            return self._load_history_view()
        elif self.current_view == ViewType.INSPECTOR:
            return self._load_inspector_view()
        elif self.current_view == ViewType.MISSION_CONTROL:
            return self._load_mission_control_view()
        return "Unknown view"

    def _get_sidebar_tasks(self) -> str:
        """Compact task list for sidebar. Prefers .manifest/tasks.json when present."""
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
        """Component/implementation status summary for sidebar."""
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
            ghost = sum(1 for s in comp_status.values() if s == "ghost")
            drift = sum(1 for s in comp_status.values() if s == "drift")
            return f"Status\n  Implemented: {imp}\n  Ghost: {ghost}\n  Drift: {drift}"
        except Exception as e:
            logger.debug("Sidebar status failed: %s", e)
            return "Status (—)"

    def _get_sidebar_viz(self) -> str:
        """Compact viz (current view) for sidebar."""
        content = self._get_current_view_content()
        lines = content.split("\n")[:18]
        if len(content.split("\n")) > 18:
            lines.append("  ...")
        return "\n".join(lines) if lines else "Viz (no data)"

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="header-strip"):
            yield Static("Manifest Dashboard | Metrics", id="header-metrics")
        with Horizontal(id="body-row"):
            with Container(id="sidebar"):
                with VerticalScroll(id="sidebar-scroll"):
                    yield Static("Tasks\n(loading)", id="sidebar-tasks", classes="sidebar-section")
                    yield Static("Status\n(loading)", id="sidebar-status", classes="sidebar-section")
                    yield Static("Viz\n(loading)", id="sidebar-viz", classes="sidebar-section")
            with Container(id="main"):
                with VerticalScroll(id="main-scroll"):
                    yield Static(MAIN_CHAT_PLACEHOLDER, id="main-chat-text")
        with Container(id="task-panel", classes="task-panel-hidden"):
            with VerticalScroll(id="task-panel-scroll"):
                yield Static("", id="task-panel-text")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_sidebar()
        self._refresh_header_metrics()
        self.set_interval(30, self._refresh_sidebar)
        self.set_interval(30, self._refresh_header_metrics)
        # Real-time sync: watch .manifest/ and refresh on change
        self._view_file_watcher = ViewFileWatcher(
            self.manifest_dir,
            on_change=self._on_manifest_change,
        )
        self.set_interval(2, self._check_manifest_changes)
        # Drift: periodically update blueprint_code.json from code; View will refresh on file change
        self._drift_monitor = DriftMonitor(
            project_root=self.manifest_dir.parent,
            manifest_dir=self.manifest_dir,
        )
        self._drift_monitor.start_monitoring(interval_seconds=10.0)
        self.set_interval(10, self._check_drift)

    def _check_manifest_changes(self) -> None:
        """Poll .manifest/ for file changes; watcher calls _on_manifest_change if any."""
        try:
            self._view_file_watcher.check()
        except Exception as e:
            logger.debug("Manifest watch check failed: %s", e)

    def _on_manifest_change(self, changed_paths: List[Path]) -> None:
        """Called when .manifest/ files change; refresh View."""
        if not changed_paths:
            return
        self.refresh_view()

    def _check_drift(self) -> None:
        """Check code changes and update blueprint_code.json; View file watcher will refresh."""
        try:
            self._drift_monitor.check_and_update()
        except Exception as e:
            logger.debug("Drift check failed: %s", e)

    def _refresh_header_metrics(self) -> None:
        """Update header metrics (tasks count, etc.). Prefers tasks.json when present."""
        try:
            tasks, _ = self._get_tasks_and_sprints_from_manifest()
            n = len(tasks)
            self.sub_title = f"Tasks: {n}"
        except Exception:
            self.sub_title = "Metrics"

    def _refresh_sidebar(self) -> None:
        """Refresh sidebar: Tasks, Status, Viz."""
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
        """Refresh sidebar (viz follows current view) and task panel if visible."""
        self._refresh_sidebar()
        self._refresh_header_metrics()
        if self._task_panel_visible:
            self._refresh_task_panel()

    def action_switch_view(self, view_name: str) -> None:
        """Switch to a different view."""
        view_map = {
            "Architect": ViewType.ARCHITECT,
            "Blueprint": ViewType.BLUEPRINT,
            "History": ViewType.HISTORY,
            "Inspector": ViewType.INSPECTOR,
            "Mission": ViewType.MISSION_CONTROL,
        }
        if view_name in view_map:
            self.current_view = view_map[view_name]
            self.refresh_view()

    def action_switch_inspector_mode(self, mode_name: str) -> None:
        """Switch Inspector View mode (only when Inspector is active)."""
        if self.current_view != ViewType.INSPECTOR:
            return
        mode_map = {
            "Visual": InspectorMode.VISUAL,
            "Data": InspectorMode.DATA,
            "Drift": InspectorMode.DRIFT,
        }
        if mode_name in mode_map:
            self.inspector_mode = mode_map[mode_name]
            self.refresh_view()

    def action_toggle_task_panel(self) -> None:
        """Toggle optional Task panel (keybind t)."""
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
        """Refresh task panel content."""
        try:
            content = self._load_mission_control_view()
            w = self.query_one("#task-panel-text", Static)
            w.update(content)
        except Exception as e:
            logger.debug("Task panel refresh failed: %s", e)

    def action_refresh(self) -> None:
        self.refresh_view()

    def action_quit(self) -> None:
        self.exit()


def run_view(manifest_dir: Optional[Path] = None) -> None:
    """Run the View app (for launcher or standalone)."""
    app = ManifestViewApp(manifest_dir=manifest_dir)
    app.run()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Manifest View (Read-only Visualization)")
    parser.add_argument("--manifest-dir", type=Path, default=None, help="Path to .manifest")
    args = parser.parse_args()
    run_view(manifest_dir=args.manifest_dir)
