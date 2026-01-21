"""
Manifest TUI - Main application with 5-view workspace.
"""
import asyncio
import json
from pathlib import Path
from typing import Optional
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll, Grid
from textual.widgets import Header, Footer, Tree, Input, RichLog, TabbedContent, TabPane, Static, Label
from textual import on, work
from textual.binding import Binding

from manifest.core.config import get_config_manager
from manifest.core.state_manager import StateManager
from manifest.bridge.omoc_bridge import OMOCBridge
from manifest.audit.drift_auditor import DriftAuditor
from manifest.audit.blueprint_synchronizer import BlueprintSynchronizer, ConflictReport
from manifest.audit.blueprint_comparator import BlueprintComparator
from manifest.ui.widgets import RequirementMap, ArchitectureGraph, FeatureTree, TaskTree, GateController
from manifest.ui.bootstrap_ui import run_bootstrap
from manifest.agents.task_scoper import TaskScoper
from manifest.agents.context_provider import ContextProvider
from manifest.agents.agent_coordinator import AgentCoordinator

try:
    import git
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False


class ManifestApp(App):
    """Manifest AI Native IDE - Unified Control Edition"""

    CSS = """
    /* --- Global Theme --- */
    Screen { background: #0d1117; color: #c9d1d9; }

    /* --- Layout Regions --- */
    #sidebar {
        width: 30;
        dock: left;
        background: #161b22;
        border-right: solid #30363d;
        height: 100%;
    }

    #main-workspace {
        height: 65%;
        layout: horizontal;
    }

    #bottom-panel {
        height: 35%;
        dock: bottom;
        background: #161b22;
        border-top: solid #30363d;
    }

    /* --- Workspace Split --- */
    #design-side {
        width: 60%;
        background: #0d1117;
        border-right: solid #30363d;
    }

    #inspector-side {
        width: 40%;
        background: #090c10;
        padding: 1;
    }

    /* --- Common Widgets --- */
    Tree { background: #161b22; padding: 1; color: #c9d1d9; }
    RichLog { background: #0d1117; color: #8b949e; border: none; padding: 1; }
    TabbedContent { background: #161b22; height: 100%; }
    ContentSwitcher { background: #0d1117; height: 100%; }
    TabPane { height: 100%; padding: 1; }
    
    #global-input {
        dock: bottom;
        border: none;
        border-top: solid #2ea043;
        background: #1e1e1e;
        color: #c9d1d9;
        height: 3;
    }

    .status-header { background: #21262d; color: #8b949e; text-align: center; text-style: bold; padding: 1; }
    .side-title { color: #8b949e; text-style: bold; margin-bottom: 1; padding: 0 1; }

    /* --- Architect Diagram --- */
    .feature-card {
        width: 100%;
        height: auto;
        border: solid #2ea043;
        background: #161b22;
        margin-bottom: 1;
        padding: 1;
    }
    .card-title { text-align: center; background: #2ea043; color: #0d1117; text-style: bold; margin-bottom: 1; }
    .req-item { color: #c9d1d9; padding-left: 1; }
    .req-done { color: #3fb950; }

    /* --- Blueprint Diagram --- */
    .blueprint-grid {
        layout: grid;
        grid-size: 3 1;
        grid-columns: 1fr 1fr 1fr;
        height: 100%;
    }
    .zone-box { border: dashed #30363d; background: #0d1117; padding: 1; margin: 0 1; }
    .zone-title { text-align: center; text-style: bold; border-bottom: solid #30363d; margin-bottom: 1; }
    .component-box { border: solid #8b949e; background: #21262d; margin-bottom: 1; padding: 0 1; text-align: center; }
    .comp-active { border: solid #2ea043; background: #1a2e1e; }

    /* --- Inspector Styles --- */
    .inspector-card {
        background: #161b22;
        border: round #30363d;
        margin-bottom: 1;
        padding: 1;
    }
    .insp-header { color: #3fb950; text-style: bold; margin-bottom: 1; }
    .visual-preview {
        background: white;
        color: black;
        text-align: center;
        padding: 2;
        margin-bottom: 1;
    }
    .data-trace {
        color: #79c0ff;
        background: #0d1117;
        padding: 1;
    }
    .match-status {
        color: green;
        text-align: center;
    }
    .drift-error { color: #f85149; }
    .drift-warning { color: #d29922; }
    .drift-info { color: #79c0ff; }

    #insp-data {
        display: none;
    }
    #insp-drift {
        display: none;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+b", "toggle_sidebar", "Toggle Sidebar"),
        ("i", "toggle_inspector", "Toggle Inspector"),
        ("h", "show_history", "Show History"),
        ("p", "show_project", "Show Project Info"),
    ]

    def __init__(self):
        super().__init__()
        self.config = get_config_manager()
        self.state_manager = StateManager()
        self.omoc_bridge: Optional[OMOCBridge] = None
        self.drift_auditor = DriftAuditor()
        self.blueprint_synchronizer = BlueprintSynchronizer()
        self.blueprint_comparator = BlueprintComparator()
        self.manifest_dir = Path(".manifest")
        self.intent_data = {}
        self.blueprint_data = {}
        self.project_data = {}
        self.current_view = "architect"
        self.inspector_mode = "visual"
        
        # Initialize agent coordination components
        self.task_scoper = TaskScoper(self.manifest_dir)
        self.context_provider = ContextProvider(self.manifest_dir, self.task_scoper)
        self.agent_coordinator: Optional[AgentCoordinator] = None
        self.squad_channels: Dict[str, str] = {}  # channel_name -> tab_id

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Horizontal():
            # 1. Mission Control (Sidebar)
            with Vertical(id="sidebar"):
                yield Label("MISSION CONTROL", classes="status-header")
                yield TaskTree("Active Missions", id="task-tree")
                yield GateController(id="gate-controller")

            # 2. Unified Workspace (Split Side-by-Side)
            with Container(id="main-workspace"):
                # 2-A. Design Side (Architect / Blueprint)
                with Vertical(id="design-side"):
                    with TabbedContent(id="design-tabs"):
                        # View 1: Architect
                        with TabPane("Architect (Intention)", id="tab-architect"):
                            with VerticalScroll(id="architect-scroll"):
                                yield Label("", id="architect-title", classes="side-title")
                                yield RequirementMap(id="requirement-map")
                                yield Static("", id="architect-content")
                        
                        # View 2: Blueprint
                        with TabPane("Blueprint (Design)", id="tab-blueprint"):
                            with VerticalScroll(id="blueprint-scroll"):
                                yield Label("", id="blueprint-title", classes="side-title")
                                yield ArchitectureGraph(id="architecture-graph")
                                yield Static("", id="blueprint-content")
                        
                        # View 5: History
                        with TabPane("History (Timeline)", id="tab-history"):
                            with VerticalScroll(id="history-scroll"):
                                yield Label("HISTORY", classes="side-title")
                                yield RichLog(id="history-log", markup=True)
                                yield Static("", id="history-timeline")
                        
                        # View 6: Feature Explorer (NEW)
                        with TabPane("Feature Explorer", id="tab-features"):
                            with VerticalScroll(id="feature-scroll"):
                                yield Label("FEATURE EXPLORER", classes="side-title")
                                yield FeatureTree("Features", id="feature-tree")
                                yield Static("", id="feature-details")
                        
                        # View 7: Project Info (NEW)
                        with TabPane("Project Info", id="tab-project"):
                            with VerticalScroll(id="project-scroll"):
                                yield Label("PROJECT MANIFEST", classes="side-title")
                                yield RichLog(id="project-log", markup=True)
                                yield Static("", id="project-content")

                # 2-B. Inspector Side (Verification)
                with Vertical(id="inspector-side"):
                    yield Label("INSPECTOR (Verification)", classes="side-title")
                    
                    with Container(id="inspector-content"):
                        # Visual Mode (default for Architect)
                        with Vertical(id="insp-visual"):
                            with Vertical(classes="inspector-card"):
                                yield Label("LIVE UI PREVIEW", classes="insp-header")
                                yield Static("", id="visual-preview", classes="visual-preview")
                                yield Label("", id="match-status", classes="match-status")
                        
                        # Data Mode (for Blueprint)
                        with Vertical(id="insp-data"):
                            with Vertical(classes="inspector-card"):
                                yield Label("EXECUTION TRACE", classes="insp-header")
                                yield RichLog(id="data-trace", markup=True)
                        
                        # Drift Mode (for conflicts)
                        with Vertical(id="insp-drift"):
                            with Vertical(classes="inspector-card"):
                                yield Label("ARCHITECTURE DRIFT", classes="insp-header")
                                yield RichLog(id="drift-log", markup=True)

            # 3. Bottom Panel
            with Container(id="bottom-panel"):
                with TabbedContent(id="chat-tabs"):
                    with TabPane("Manifest AI", id="tab-main"):
                        yield RichLog(id="log-main", markup=True)
                    # Squad channels will be added dynamically when missions start
                
                yield Input(placeholder="Enter command...", id="global-input")

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize the application."""
        # Check API keys
        if not self.config.has_all_keys():
            log = self.query_one("#log-main", RichLog)
            log.write("[bold yellow]API keys not configured.[/]")
            log.write("[bold yellow]Continuing in demo mode. Configure keys manually in .manifest/keys.json[/]")
            log.write("[bold yellow]Or set environment variables: ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY[/]")
        
        # Load data
        await self.load_intent_data()
        await self.load_blueprint_data()
        await self.load_project_data()
        
        # Initialize task tree
        await self.update_task_tree()
        
        # Try to connect to OMOC
        if self.omoc_bridge is None:
            config_manager = get_config_manager()
            self.omoc_bridge = OMOCBridge(self.state_manager, config_manager)
            await self.omoc_bridge.start()
            if self.omoc_bridge.is_connected:
                self.query_one("#log-main", RichLog).write("[bold green]OMOC bridge initialized.[/]")
            else:
                self.query_one("#log-main", RichLog).write("[bold yellow]OMOC initialization failed.[/]")
        
        # Initialize agent coordinator (works in both OMOC and standalone mode)
        if self.omoc_bridge and self.omoc_bridge.is_connected:
            self.agent_coordinator = AgentCoordinator(
                self.omoc_bridge,
                self.context_provider,
                self.task_scoper,
                self.config,
                self.state_manager
            )
        
        # Load state
        state = self.state_manager.get_state()
        if state.get("last_action"):
            self.query_one("#log-main", RichLog).write(f"[bold blue]Resuming: {state.get('last_action')}[/]")
        
        # Update squad channels based on active tasks
        await self.update_squad_channels()
        
        # Initialize views
        await self.update_architect_view()
        await self.update_blueprint_view()
        await self.update_feature_explorer()
        await self.update_project_view()
        
        # Start drift audit (non-blocking to avoid blocking UI)
        asyncio.create_task(self.audit_drift())
        
        # Focus input field after everything is loaded
        self.query_one("#global-input").focus()

    async def load_intent_data(self):
        """Load intent.json data."""
        intent_file = self.manifest_dir / "intent.json"
        if intent_file.exists():
            try:
                with open(intent_file, "r") as f:
                    self.intent_data = json.load(f)
            except Exception:
                self.intent_data = {"version": "1.0", "sprint": "", "features": []}
        else:
            self.intent_data = {"version": "1.0", "sprint": "", "features": []}

    async def load_blueprint_data(self):
        """Load blueprint.json data."""
        blueprint_file = self.manifest_dir / "blueprint.json"
        if blueprint_file.exists():
            try:
                with open(blueprint_file, "r") as f:
                    self.blueprint_data = json.load(f)
            except Exception:
                self.blueprint_data = {"version": "1.0", "zones": {}, "components": [], "contracts": []}
        else:
            self.blueprint_data = {"version": "1.0", "zones": {}, "components": [], "contracts": []}

    async def load_project_data(self):
        """Load project.json data (strict doc > view).
        
        Note: project.json is now in docs/project-manifest/ for Manifest project documentation.
        For user projects, this would be in .manifest/ directory.
        """
        # For Manifest project itself, load from docs/project-manifest/
        project_file = Path("docs/project-manifest/project.json")
        if not project_file.exists():
            # Fallback: try .manifest/ for user projects
            project_file = self.manifest_dir / "project.json"
        
        if project_file.exists():
            try:
                with open(project_file, "r") as f:
                    self.project_data = json.load(f)
            except Exception:
                self.project_data = {}
        else:
            self.project_data = {}

    async def update_architect_view(self):
        """Update the Architect view with intent data."""
        sprint = self.intent_data.get("sprint", "")
        features = self.intent_data.get("features", [])
        
        # Calculate progress
        total_reqs = sum(len(f.get("reqs", [])) for f in features)
        done_reqs = sum(sum(1 for r in f.get("reqs", []) if r.get("state") == "done") for f in features)
        progress = int((done_reqs / total_reqs * 100)) if total_reqs > 0 else 0
        
        title = self.query_one("#architect-title", Label)
        title.update(f"📊 Sprint: {sprint} | Progress: {progress}%")
        
        # Update requirement map
        req_map = self.query_one("#requirement-map", RequirementMap)
        req_map.update_data({"features": features})
        
        # Update content
        content = self.query_one("#architect-content", Static)
        content_lines = []
        for feature in features:
            name = feature.get("name", "Unknown")
            status = feature.get("status", "pending")
            content_lines.append(f"Feature: {name} ({status})")
        content.update("\n".join(content_lines) if content_lines else "No features defined")

    async def update_feature_explorer(self):
        """Update the Feature Explorer view with feature data."""
        features = self.intent_data.get("features", [])
        
        # Update feature tree
        try:
            feature_tree = self.query_one("#feature-tree", FeatureTree)
            feature_tree.load_features(features)
        except Exception:
            # Feature tree might not be visible yet
            pass
        
        # Update feature details (will be populated when feature is selected)
        try:
            details = self.query_one("#feature-details", Static)
            if features:
                details.update(f"📊 {len(features)} features loaded. Select a feature to view details.")
            else:
                details.update("No features defined. Add features to intent.json")
        except Exception:
            pass

    async def update_blueprint_view(self):
        """Update the Blueprint view with blueprint data."""
        components = self.blueprint_data.get("components", [])
        zones = self.blueprint_data.get("zones", {})
        
        title = self.query_one("#blueprint-title", Label)
        title.update(f"Blueprint: {len(components)} components")
        
        # Update architecture graph
        arch_graph = self.query_one("#architecture-graph", ArchitectureGraph)
        arch_graph.update_data({"components": components})
        
        # Update content with zone-based layout
        content = self.query_one("#blueprint-content", Static)
        content_lines = []
        for zone_name, zone_components in zones.items():
            content_lines.append(f"[{zone_name.upper()}]")
            for comp in zone_components:
                comp_name = comp.get("name", "Unknown")
                comp_status = comp.get("status", "pending")
                content_lines.append(f"  {comp_name} ({comp_status})")
        content.update("\n".join(content_lines) if content_lines else "No components defined")

    async def update_project_view(self):
        """Update the Project Info view with project.json data (strict doc > view)."""
        if not self.project_data:
            return
        
        project_log = self.query_one("#project-log", RichLog)
        project_content = self.query_one("#project-content", Static)
        
        # Display project metadata
        metadata = self.project_data.get("metadata", {})
        project_log.write(f"[bold green]Project:[/] {metadata.get('name', 'Manifest')}")
        project_log.write(f"[bold green]Version:[/] {metadata.get('version', '1.0.0')}")
        project_log.write(f"[bold green]Status:[/] {metadata.get('status', 'unknown')}")
        project_log.write("")
        
        # Display architecture layers
        architecture = self.project_data.get("architecture", {})
        layers = architecture.get("layers", [])
        project_log.write("[bold cyan]Architecture Layers:[/]")
        for layer in layers:
            layer_name = layer.get("name", "Unknown")
            modules = layer.get("modules", [])
            project_log.write(f"  [yellow]{layer_name}[/] ({len(modules)} modules)")
            for module in modules:
                module_name = module.get("name", "Unknown")
                module_status = module.get("status", "unknown")
                status_color = "green" if module_status == "complete" else "yellow"
                project_log.write(f"    - {module_name} [{status_color}]{module_status}[/]")
        project_log.write("")
        
        # Display implementation status
        impl_status = self.project_data.get("implementation_status", {})
        phase = impl_status.get("phase", "unknown")
        completion = impl_status.get("completion_percentage", 0)
        project_log.write(f"[bold cyan]Implementation Status:[/]")
        project_log.write(f"  Phase: [yellow]{phase}[/]")
        project_log.write(f"  Completion: [green]{completion}%[/]")
        
        # Display views
        views = self.project_data.get("views", [])
        project_log.write("")
        project_log.write(f"[bold cyan]Views:[/] {len(views)} implemented")
        for view in views:
            view_name = view.get("name", "Unknown")
            view_status = view.get("status", "unknown")
            status_color = "green" if view_status == "complete" else "yellow"
            project_log.write(f"  - {view_name} [{status_color}]{view_status}[/]")
        
        # Format content for static display
        content_lines = []
        content_lines.append(f"Project: {metadata.get('name', 'Manifest')}")
        content_lines.append(f"Phase: {phase} ({completion}% complete)")
        content_lines.append(f"Views: {len(views)}")
        content_lines.append(f"Layers: {len(layers)}")
        project_content.update("\n".join(content_lines))

    async def update_task_tree(self):
        """Update the task tree with current state."""
        tasks = self.state_manager.get_task_checklist()
        if not tasks:
            # Create default task structure
            tasks = [
                {
                    "id": "task-1",
                    "name": "Sample Task",
                    "status": "pending",
                    "stage": "planning",
                    "subtasks": []
                }
            ]
        
        task_tree = self.query_one("#task-tree", TaskTree)
        task_tree.load_tasks(tasks)

    async def update_history_view(self):
        """Update the History view with git timeline."""
        if not GIT_AVAILABLE:
            history_log = self.query_one("#history-log", RichLog)
            history_log.write("[bold yellow]GitPython not available. Install with: pip install GitPython[/]")
            return
        
        try:
            repo = git.Repo(".")
            commits = list(repo.iter_commits(max_count=20))
            
            history_log = self.query_one("#history-log", RichLog)
            timeline = self.query_one("#history-timeline", Static)
            
            timeline_lines = []
            for commit in commits:
                date = commit.committed_datetime.strftime("%Y-%m-%d %H:%M")
                author = commit.author.name
                message = commit.message.split("\n")[0]
                timeline_lines.append(f"[{date}] {author}: {message}")
                history_log.write(f"[bold blue]{date}[/] [dim]{author}[/]: {message}")
            
            timeline.update("\n".join(timeline_lines[:10]) if timeline_lines else "No git history")
        except Exception as e:
            history_log = self.query_one("#history-log", RichLog)
            history_log.write(f"[bold red]Error loading git history: {e}[/]")

    async def audit_drift(self):
        """Run drift audit and update inspector."""
        # Generate bottom-up blueprint from code
        bottom_up_blueprint = self.drift_auditor.generate_bottom_up_blueprint(Path("src"))
        
        # Load top-down blueprint
        top_down_blueprint = self._load_blueprint_sync()
        
        # Compare blueprints
        blueprint_conflicts = self.blueprint_comparator.compare_blueprints(
            top_down_blueprint,
            bottom_up_blueprint
        )
        
        # Also run traditional drift audit
        drift_conflicts = self.drift_auditor.audit_project()
        
        # Combine conflicts for display
        from manifest.audit.drift_auditor import DriftConflict as DriftConflictClass
        all_conflicts = drift_conflicts + [
            # Convert BlueprintConflict to DriftConflict for display
            DriftConflictClass(
                severity=bc.severity,
                message=bc.message,
                node_id=bc.component_id,
                file_path=bc.file_path
            )
            for bc in blueprint_conflicts
        ]
        
        if all_conflicts:
            drift_log = self.query_one("#drift-log", RichLog)
            grouped = self.drift_auditor.get_conflicts_by_severity(all_conflicts)
            
            for severity, conflict_list in grouped.items():
                if conflict_list:
                    color = {"error": "red", "warning": "yellow", "info": "blue"}.get(severity, "white")
                    drift_log.write(f"[bold {color}]{severity.upper()}: {len(conflict_list)} conflicts[/]")
                    for conflict in conflict_list[:10]:  # Show first 10
                        drift_log.write(f"  • {conflict.message}")
        
        # Check for blueprint mismatches and trigger workflow if needed
        if blueprint_conflicts:
            mismatch_report = self.blueprint_synchronizer.detect_mismatch(
                top_down_blueprint,
                bottom_up_blueprint
            )
            if mismatch_report:
                # Trigger conflict workflow (will be handled by agent coordinator)
                await self.handle_blueprint_conflict(mismatch_report)
        
        # Show drift mode if there are conflicts
        if all_conflicts:
            visual_pane = self.query_one("#insp-visual")
            data_pane = self.query_one("#insp-data")
            drift_pane = self.query_one("#insp-drift")
            visual_pane.styles.display = "none"
            data_pane.styles.display = "none"
            drift_pane.styles.display = "block"
            self.inspector_mode = "drift"

    @on(TabbedContent.TabActivated, "#design-tabs")
    async def on_tab_switched(self, event: TabbedContent.TabActivated) -> None:
        """Handle design tab switching."""
        visual_pane = self.query_one("#insp-visual")
        data_pane = self.query_one("#insp-data")
        drift_pane = self.query_one("#insp-drift")
        
        if event.pane.id == "tab-architect":
            visual_pane.styles.display = "block"
            data_pane.styles.display = "none"
            drift_pane.styles.display = "none"
            self.current_view = "architect"
            self.inspector_mode = "visual"
        elif event.pane.id == "tab-blueprint":
            visual_pane.styles.display = "none"
            data_pane.styles.display = "block"
            drift_pane.styles.display = "none"
            self.current_view = "blueprint"
            self.inspector_mode = "data"
        elif event.pane.id == "tab-history":
            visual_pane.styles.display = "none"
            data_pane.styles.display = "none"
            drift_pane.styles.display = "none"
            self.current_view = "history"
        elif event.pane.id == "tab-project":
            visual_pane.styles.display = "none"
            data_pane.styles.display = "none"
            drift_pane.styles.display = "none"
            self.current_view = "project"

    def action_toggle_inspector(self) -> None:
        """Toggle inspector visibility."""
        side = self.query_one("#inspector-side")
        side.styles.display = "none" if side.styles.display == "block" else "block"

    def action_show_history(self) -> None:
        """Switch to history view."""
        tabs = self.query_one("#design-tabs", TabbedContent)
        tabs.active = "tab-history"

    def action_show_project(self) -> None:
        """Switch to project info view."""
        tabs = self.query_one("#design-tabs", TabbedContent)
        tabs.active = "tab-project"

    @on(Input.Submitted, "#global-input")
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input."""
        input_widget = event.input
        user_input = event.value.strip()
        
        # Clear input immediately to prevent re-submission
        input_widget.value = ""
        
        # Ignore empty input - just return (input field keeps focus naturally)
        if not user_input:
            return
        
        log = self.query_one("#log-main", RichLog)
        log.write(f"[bold blue]User:[/] {user_input}")
        
        # Save to state
        self.state_manager.add_chat_message("main", "user", user_input)
        self.state_manager.set_last_action(f"User command: {user_input}")
        await self.state_manager.save_state()
        
        # Process command (non-blocking, will refocus in finally block)
        await self.process_command(user_input, log)

    @work(exclusive=False)
    async def process_command(self, user_input: str, log: RichLog):
        """Process user command."""
        try:
            await asyncio.sleep(0.1)  # Small delay for UI responsiveness
            
            # Simple command routing
            if user_input.startswith("/"):
                command = user_input[1:].split()[0] if user_input[1:] else ""
                
                if command == "audit":
                    log.write("[bold green]Running drift audit...[/]")
                    await self.audit_drift()
                    log.write("[bold green]Drift audit complete.[/]")
                elif command == "reload":
                    await self.load_intent_data()
                    await self.load_blueprint_data()
                    await self.load_project_data()
                    await self.update_architect_view()
                    await self.update_blueprint_view()
                    await self.update_project_view()
                    log.write("[bold green]Data reloaded.[/]")
                elif command == "status":
                    if self.omoc_bridge and self.omoc_bridge.is_connected:
                        status = await self.omoc_bridge.get_status()
                        log.write(f"[bold green]Status: {status}[/]")
                    else:
                        log.write("[bold yellow]OMOC not connected.[/]")
                elif command == "start_agent" or command.startswith("start_agent"):
                    # Format: /start_agent <task_id> <agent_type>
                    parts = user_input.split()
                    if len(parts) >= 3:
                        task_id = parts[2]
                        agent_type = parts[3] if len(parts) > 3 else "sisyphus"
                        if self.agent_coordinator:
                            log.write(f"[bold green]Starting {agent_type} agent for task {task_id}...[/]")
                            success = await self.agent_coordinator.start_worker_agent(task_id, agent_type)
                            if success:
                                log.write(f"[bold green]Agent started. Channel: squad-{task_id}-{agent_type}[/]")
                                await self.update_squad_channels()
                            else:
                                log.write(f"[bold red]Failed to start agent.[/]")
                        else:
                            log.write("[bold yellow]Agent coordinator not available.[/]")
                    else:
                        log.write("[bold yellow]Usage: /start_agent <task_id> <agent_type>[/]")
                elif command == "stop_agent" or command.startswith("stop_agent"):
                    parts = user_input.split()
                    if len(parts) >= 3:
                        task_id = parts[2]
                        if self.agent_coordinator:
                            success = await self.agent_coordinator.stop_agent(task_id)
                            if success:
                                log.write(f"[bold green]Agent stopped for task {task_id}.[/]")
                                await self.update_squad_channels()
                            else:
                                log.write(f"[bold red]Failed to stop agent.[/]")
                        else:
                            log.write("[bold yellow]Agent coordinator not available.[/]")
                    else:
                        log.write("[bold yellow]Usage: /stop_agent <task_id>[/]")
                elif command.startswith("sync_blueprints"):
                    log.write("[bold green]Synchronizing blueprints...[/]")
                    await self.sync_blueprints()
                    log.write("[bold green]Blueprint sync complete.[/]")
                elif command.startswith("resolve_conflict"):
                    # Format: /resolve_conflict <conflict_id> <action>
                    parts = user_input.split()
                    if len(parts) >= 3:
                        conflict_id = parts[2]
                        action = parts[3] if len(parts) > 3 else "approved"
                        await self.resolve_conflict(conflict_id, action)
                        log.write(f"[bold green]Conflict {conflict_id} {action}.[/]")
                    else:
                        log.write("[bold red]Usage: /resolve_conflict <conflict_id> <approved|rejected>[/]")
                else:
                    log.write(f"[bold yellow]Unknown command: {command}[/]")
            else:
                # Regular AI interaction
                if self.omoc_bridge and self.omoc_bridge.is_connected:
                    # Send to OMOC
                    log.write("[bold green]Processing with OMOC...[/]")
                    # In real implementation, this would send to OMOC and get response
                    self.state_manager.add_chat_message("main", "assistant", f"Processing: {user_input}")
                    await self.state_manager.save_state()
                else:
                    # Simulate response
                    log.write(f"[bold green]Manifest AI:[/] Analyzing '{user_input}'. Check inspector for real-time status.")
                    self.state_manager.add_chat_message("main", "assistant", f"Analyzing: {user_input}")
                    await self.state_manager.save_state()
        finally:
            # Refocus input after command processing completes
            # This ensures the input field is ready for next command
            try:
                input_widget = self.query_one("#global-input", Input)
                if input_widget and input_widget.has_focus is False:
                    # Only refocus if not already focused to prevent loops
                    input_widget.focus()
            except Exception:
                pass  # Ignore if widget not found
    
    @on(GateController.Approved)
    async def on_task_approved(self, message: GateController.Approved):
        """Handle task approval."""
        task_id = message.task_id
        if self.omoc_bridge and self.omoc_bridge.is_connected:
            await self.omoc_bridge.promote_task(task_id, "approved")
        log = self.query_one("#log-main", RichLog)
        log.write(f"[bold green]Task {task_id} approved.[/]")
        await self.state_manager.save_state()
    
    @on(GateController.Rejected)
    async def on_task_rejected(self, message: GateController.Rejected):
        """Handle task rejection."""
        task_id = message.task_id
        log = self.query_one("#log-main", RichLog)
        log.write(f"[bold red]Task {task_id} rejected.[/]")
        await self.state_manager.save_state()
    
    async def create_squad_channel(self, task_id: str, agent_type: str) -> Optional[str]:
        """Create a squad channel for agent output."""
        channel_name = f"squad-{task_id}-{agent_type}"
        tab_id = f"tab-{channel_name}"
        
        # Check if channel already exists
        if channel_name in self.squad_channels:
            return tab_id
        
        try:
            chat_tabs = self.query_one("#chat-tabs", TabbedContent)
            
            # Create new TabPane dynamically
            # Note: Textual doesn't support dynamic TabPane creation easily
            # We'll track channels and display in main log for now
            # Full implementation would require Textual's dynamic widget support
            self.squad_channels[channel_name] = tab_id
            
            # Load existing chat history if any
            history = self.state_manager.get_chat_history(channel_name)
            if history:
                log = self.query_one("#log-main", RichLog)
                log.write(f"[bold cyan]Channel {channel_name} has {len(history)} messages[/]")
            
            return tab_id
        except Exception as e:
            print(f"Error creating squad channel: {e}")
            return None
    
    async def update_squad_channels(self):
        """Update squad channels based on active tasks."""
        if not self.agent_coordinator:
            return
        
        # Get active agents
        active_agents = self.agent_coordinator.get_active_agents()
        active_channels = set()
        
        # Create channels for active agents
        for task_id, agent_info in active_agents.items():
            if agent_info.get("status") == "active":
                channel_name = agent_info.get("channel")
                if channel_name:
                    agent_type = agent_info.get("agent_type", "unknown")
                    tab_id = await self.create_squad_channel(task_id, agent_type)
                    if tab_id:
                        active_channels.add(channel_name)
        
        # Also check tasks for agent assignments
        tasks = self.state_manager.get_task_checklist()
        for task in tasks:
            agent_info = task.get("agent")
            if agent_info and agent_info.get("status") == "active":
                task_id = task.get("id")
                agent_type = agent_info.get("type", "unknown")
                channel_name = agent_info.get("channel")
                if channel_name and channel_name not in self.squad_channels:
                    await self.create_squad_channel(task_id, agent_type)
    
    async def handle_agent_output(self, channel: str, content: str, role: str = "assistant"):
        """Handle agent output and display in appropriate channel."""
        # Update state
        self.state_manager.add_chat_message(channel, role, content)
        await self.state_manager.save_state()
        
        # Display in UI
        try:
            if channel == "main":
                log = self.query_one("#log-main", RichLog)
                if role == "user":
                    log.write(f"[bold blue]User:[/] {content}")
                else:
                    log.write(f"[bold green]Assistant:[/] {content}")
            else:
                # Display in main log with channel prefix for now
                # Full implementation would use dynamic TabPane
                log = self.query_one("#log-main", RichLog)
                agent_type = channel.split("-")[-1] if "-" in channel else "agent"
                if role == "user":
                    log.write(f"[bold blue][{channel}] User:[/] {content}")
                else:
                    log.write(f"[bold green][{channel}] {agent_type.title()}:[/] {content}")
        except Exception as e:
            print(f"Error displaying agent output: {e}")

    async def on_unmount(self) -> None:
        """Cleanup on app exit."""
        if self.omoc_bridge:
            await self.omoc_bridge.stop()
        await self.state_manager.save_state()


if __name__ == "__main__":
    app = ManifestApp()
    app.run()