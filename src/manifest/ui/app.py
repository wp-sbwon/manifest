"""
Manifest TUI - Main Textual-based user interface application.

This module provides the main application class (ManifestApp) which implements
a 5-view workspace using the Textual framework. The application handles user
input, displays project data, manages agent communication, and provides a
unified interface for interacting with the Manifest system.

The UI is organized into:
- Sidebar: Navigation and project structure
- Main workspace: Design and inspector views
- Bottom panel: Command input and agent output logs
- Multiple tabs: Different views of project data

The app delegates command processing to CommandHandler, data loading to
DataLoader, and channel management to ChannelManager for better organization.
"""
import asyncio
import json
import os
import threading
import uvicorn
from pathlib import Path
from typing import Optional, List, Dict, Any
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll, Grid
from textual.widgets import Header, Footer, Tree, Input, RichLog, TabbedContent, TabPane, Static, Label, Button
from manifest.ui.widgets.structure_hierarchy_view import StructureHierarchyView
from manifest.ui.widgets.structure_graph_view import StructureGraphView
from manifest.ui.widgets.project_view import TaskTreeView, SprintStatusView, HistoryView, TaskSelected, SprintSelected
from textual import on, work
from manifest.agents.container_api import create_container_api
from textual.binding import Binding

from manifest.core.config import get_config_manager
from manifest.core.state_manager import StateManager
from manifest.core.git_manager import GitManager
from manifest.bridge.agent_bridge import AgentBridge
from manifest.audit.code.drift_auditor import DriftAuditor
from manifest.audit.blueprint.blueprint_synchronizer import BlueprintSynchronizer, ConflictReport
from manifest.audit.blueprint.blueprint_comparator import BlueprintComparator
from manifest.ui.widgets import RequirementMap, ArchitectureGraph, FeatureTree, TaskTree, GateController, SprintApprovalWidget, PermissionApprovalWidget
from manifest.runtime.permissions.permission_approval_manager import PermissionApprovalManager
from manifest.audit.metadata.architecture_metadata import load_architecture_with_metadata
from manifest.ui.settings_screen import SettingsScreen
from manifest.ui.task_edit_screen import TaskEditScreen
from manifest.agents.task_scoper import TaskScoper
from manifest.agents.context_provider import ContextProvider
from manifest.agents.agent_coordinator import AgentCoordinator
from manifest.ui.commands.command_handler import CommandHandler
from manifest.ui.data.data_loader import DataLoader
from manifest.ui.channels.channel_manager import ChannelManager
from manifest.core.logger import get_logger

try:
    import git
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False

logger = get_logger(__name__)


class DashboardHeader(Static):
    """Header widget showing real-time project metrics."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metrics = {
            "match_pct": 0,
            "active_tasks": 0,
            "completed_tasks": 0,
            "running_agents": 0
        }

    def update_metrics(self, metrics: Dict[str, Any]):
        """Update the metrics display."""
        self.metrics.update(metrics)
        self.refresh()

    def render(self) -> str:
        """Render the dashboard header."""
        m = self.metrics
        match_color = "green" if m["match_pct"] > 90 else "yellow" if m["match_pct"] > 70 else "red"
        
        return (
            f"[bold cyan]Manifest Dashboard[/] | "
            f"Architecture Match: [bold {match_color}]{m['match_pct']}%[/] | "
            f"Tasks: [bold]{m['completed_tasks']}/{m['active_tasks'] + m['completed_tasks']}[/] | "
            f"Active Agents: [bold green]{m['running_agents']}[/]"
        )


class ContextBar(RichLog):
    """Context bar showing real-time agent activity streaming."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_lines = 1
        self.activities: List[Dict[str, Any]] = []
    
    def add_activity(self, task_id: str, agent_type: str, activity: str):
        """Add or update an agent activity."""
        # Remove existing activity for this task/agent
        self.activities = [a for a in self.activities if not (a.get("task_id") == task_id and a.get("agent_type") == agent_type)]
        # Add new activity
        self.activities.append({
            "task_id": task_id,
            "agent_type": agent_type,
            "activity": activity,
            "timestamp": time.time()
        })
        # Keep only recent activities (last 3)
        self.activities = self.activities[-3:]
        self.update_display()
    
    def remove_activity(self, task_id: str, agent_type: str):
        """Remove an activity."""
        self.activities = [a for a in self.activities if not (a.get("task_id") == task_id and a.get("agent_type") == agent_type)]
        self.update_display()
    
    def update_display(self):
        """Update the displayed activities."""
        self.clear()
        if not self.activities:
            self.write("[dim]No active agents[/]")
        else:
            activity_texts = []
            for activity in self.activities:
                agent_type = activity.get("agent_type", "agent")
                task_id = activity.get("task_id", "unknown")
                activity_text = activity.get("activity", "")
                # Truncate long activities
                if len(activity_text) > 40:
                    activity_text = activity_text[:37] + "..."
                activity_texts.append(f"[cyan]{agent_type}[/] on [bold]{task_id[:8]}[/]: {activity_text}")
            self.write(" | ".join(activity_texts))


class ManifestApp(App):
    """Main application class for the Manifest TUI.
    
    This is the root application class that manages the entire user interface.
    It provides a 5-view workspace with sidebar navigation, main workspace area,
    and bottom panel for commands and logs. The app handles user interactions,
    displays project data, and coordinates with agents through the AgentBridge.
    
    The application uses Textual framework for the TUI and follows a modular
    architecture with separate handlers for commands, data loading, and channel
    management.
    
    Attributes:
        manifest_dir: Path to the .manifest directory for project data.
        state_manager: Manages application state persistence.
        agent_bridge: Bridge for agent communication and execution.
        agent_coordinator: Coordinates agent workflows.
        command_handler: Handles user command processing.
        data_loader: Loads project data (intent, blueprint, project).
        channel_manager: Manages agent output channels.
        Various UI widgets and components for displaying data.
    """

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

    /* --- Project View Filters --- */
    #task-filters {
        height: 3;
        margin-bottom: 1;
        padding: 0 1;
    }
    #filter-status-select {
        width: 30%;
        margin-right: 1;
    }
    #task-search-input {
        width: 70%;
    }

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

    /* --- Dashboard Header --- */
    #dashboard-header {
        height: 3;
        dock: top;
        background: #161b22;
        border-bottom: solid #30363d;
        padding: 0 1;
        text-align: center;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+b", "toggle_sidebar", "Toggle Sidebar"),
        ("i", "toggle_inspector", "Toggle Inspector"),
        ("h", "show_history", "Show History"),
        ("p", "show_project", "Show Project Info"),
        ("ctrl+comma", "open_settings", "Open Settings"),
        ("s", "change_task_status", "Change Task Status"),
        ("e", "edit_task", "Edit Task"),
        ("d", "delete_task", "Delete Task"),
    ]

    def __init__(self):
        """Initialize the Manifest application.
        
        Sets up all managers, coordinators, and handlers needed for the
        application to function. Initializes state management, agent
        coordination, command processing, data loading, and channel
        management components.
        """
        super().__init__()
        self.config = get_config_manager()
        self.state_manager = StateManager()
        self.agent_bridge: Optional[AgentBridge] = None
        self.drift_auditor = DriftAuditor()
        self.blueprint_synchronizer = BlueprintSynchronizer()
        self.blueprint_comparator = BlueprintComparator()
        
        # Structure Manager for Spec-First Management
        from manifest.audit.monitoring.structure_manager import StructureManager
        self.structure_manager = StructureManager(self.manifest_dir, Path.cwd())
        self.manifest_dir = Path(".manifest")
        self.intent_data = {}
        self.blueprint_data = {}
        self.project_data = {}
        self.current_view = "architect"
        self.inspector_mode = "visual"
        
        # Pending suggestions for approval
        self._pending_blueprint_suggestions: List = []
        self._pending_code_suggestions: List = []
        
        # Initialize agent coordination components
        self.task_scoper = TaskScoper(self.manifest_dir)
        self.context_provider = ContextProvider(self.manifest_dir, self.task_scoper)
        self.agent_coordinator: Optional[AgentCoordinator] = None
        
        # Command handler for processing user commands
        self.command_handler: Optional[CommandHandler] = None
        
        # Data loader for loading project data
        self.data_loader = DataLoader(self.manifest_dir)
        
        # Git manager for version control integration
        self.git_manager = GitManager(Path.cwd())
        
        # Channel manager for agent output channels
        self.channel_manager: Optional[ChannelManager] = None

    def compose(self) -> ComposeResult:
        """Compose the UI layout with all widgets and containers.
        
        This method is called by Textual to build the initial UI structure.
        It creates the sidebar, main workspace, bottom panel, and all
        nested widgets. The layout uses Textual's container system for
        organization.
        
        Returns:
            ComposeResult containing all widgets to be mounted.
        """
        yield Header(show_clock=True)
        yield DashboardHeader(id="dashboard-header")
        yield ContextBar(id="context-bar")
        
        with Horizontal():
            # 1. Mission Control (Sidebar)
            with Vertical(id="sidebar"):
                yield Label("MISSION CONTROL", classes="status-header")
                yield TaskTree("Active Missions", id="task-tree")
                yield GateController(id="gate-controller")
                yield SprintApprovalWidget(id="sprint-approval-widget")
                yield PermissionApprovalWidget(id="permission-approval-widget")

            # 2. Unified Workspace (Split Side-by-Side)
            with Container(id="main-workspace"):
                # 2-A. Design Side (Architect / Blueprint)
                with Vertical(id="design-side"):
                    with TabbedContent(id="design-tabs"):
                        # View 1: Structure (Hierarchy + Graph)
                        with TabPane("Structure", id="tab-structure"):
                            with TabbedContent(id="structure-sub-tabs"):
                                # Hierarchy Tab
                                with TabPane("Hierarchy", id="tab-structure-hierarchy"):
                                    with VerticalScroll(id="structure-hierarchy-scroll"):
                                        yield StructureHierarchyView(id="structure-hierarchy-view")
                                
                                # Graph Tab
                                with TabPane("Graph", id="tab-structure-graph"):
                                    with VerticalScroll(id="structure-graph-scroll"):
                                        yield StructureGraphView(id="structure-graph-view")
                        
                        # View 2: Project (Tasks + History)
                        with TabPane("Project", id="tab-project"):
                            yield ProjectView(id="project-view")
                        
                        # View 3: Agent Status
                        with TabPane("Agent Status", id="tab-agent-status"):
                            from manifest.ui.widgets.agent_status_view import AgentStatusView
                            yield AgentStatusView(id="agent-status-view")

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
                
                # Channel selector (horizontal container with buttons)
                with Horizontal(id="channel-selector"):
                    yield Button("Manifest AI", id="btn-channel-main", variant="primary")
                    # Squad channel buttons will be added dynamically
                
                yield Input(placeholder="Enter command...", id="global-input")

        yield Footer()

    async def _start_container_api(self):
        """Start the Container API server in a background thread."""
        def run_server():
            api_app = create_container_api(self.state_manager)
            # Use a fixed port for the container API
            uvicorn.run(api_app, host="0.0.0.0", port=8000, log_level="error")

        self._api_thread = threading.Thread(target=run_server, daemon=True)
        self._api_thread.start()
        
        # Give the server a moment to start
        await asyncio.sleep(1.0)
        self.query_one("#log-main", RichLog).write("[bold green]Container API server started on port 8000.[/]")

    async def _stop_container_api(self):
        """Stop the Container API server."""
        # Since it's a daemon thread, it will stop when the main process exits.
        # For a more graceful shutdown, we would need to handle uvicorn's server instance.
        pass

    async def on_mount(self) -> None:
        """Initialize the application after UI is mounted.
        
        This method is called by Textual after the UI is composed and mounted.
        It performs all initialization tasks including:
        - Checking API key configuration
        - Loading project data (intent, blueprint, project)
        - Initializing agent bridge and coordinator
        - Setting up command handler and channel manager
        - Loading initial views and data
        - Starting background drift audit
        
        If API keys are missing, the app continues in demo mode with warnings.
        """
        # Start Container API server for inter-container communication
        await self._start_container_api()
        
        # Check API keys
        if not self.config.has_all_keys():
            log = self.query_one("#log-main", RichLog)
            log.write("[bold yellow]API keys not configured.[/]")
            log.write("[bold yellow]Continuing in demo mode. Configure keys manually in .manifest/keys.json[/]")
            log.write("[bold yellow]Or set environment variables: ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY[/]")
        
        # Load data
        self.intent_data = await self.data_loader.load_intent_data()
        self.blueprint_data = await self.data_loader.load_blueprint_data()
        self.project_data = await self.data_loader.load_project_data()
        
        # Initialize task tree
        await self.update_task_tree()
        
        # Initialize permission approval manager
        self.approval_manager = PermissionApprovalManager()
        
        # Initialize channel manager first (needed for agent_bridge)
        self.channel_manager = ChannelManager(self, self.state_manager)
        
        # Hide permission approval widget initially
        try:
            self.query_one("#permission-approval-widget").styles.display = "none"
        except Exception:
            pass  # Widget might not be mounted yet
        
        # Initialize agent bridge
        if self.agent_bridge is None:
            config_manager = get_config_manager()
            self.agent_bridge = AgentBridge(
                self.state_manager, 
                config_manager,
                channel_manager=self.channel_manager,  # Pass channel_manager for real-time UI updates
                approval_manager=self.approval_manager  # Pass approval_manager for permission requests
            )
            await self.agent_bridge.start()
            if self.agent_bridge.is_connected:
                self.query_one("#log-main", RichLog).write("[bold green]Agent bridge initialized.[/]")
            else:
                self.query_one("#log-main", RichLog).write("[bold yellow]Agent bridge initialization failed.[/]")
        
        # Initialize agent coordinator
        if self.agent_bridge and self.agent_bridge.is_connected:
            self.agent_coordinator = AgentCoordinator(
                self.agent_bridge,
                self.context_provider,
                self.task_scoper,
                self.config,
                self.state_manager
            )
            # Start agent coordinator (this will start container state sync if enabled)
            await self.agent_coordinator.start()
        
        # Initialize command handler
        self.command_handler = CommandHandler(self)
        
        # Load state
        state = self.state_manager.get_state()
        if state.get("last_action"):
            self.query_one("#log-main", RichLog).write(f"[bold blue]Resuming: {state.get('last_action')}[/]")
        
        # Update squad channels based on active tasks
        if self.channel_manager:
            await self.channel_manager.update_squad_channels(self.agent_coordinator)
            
            # Set up main channel button click handler
            try:
                main_button = self.query_one("#btn-channel-main", Button)
                async def switch_to_main():
                    await self.channel_manager.switch_channel("main")
                main_button.on_click = lambda: asyncio.create_task(switch_to_main())
            except Exception as e:
                logger.debug(f"Could not set up main channel button: {e}")
            
            # Activate main channel and refresh display
            await self.channel_manager.switch_channel("main")
        
        # Initialize views
        await self._load_structure_data()
        await self._load_project_data()
        
        # Start drift audit (non-blocking to avoid blocking UI)
        asyncio.create_task(self.audit_drift())
        
        # Initialize dashboard metrics
        await self.update_dashboard_metrics()
        
        # Set up periodic dashboard updates
        self.set_interval(5.0, self.update_dashboard_metrics)
        # Set up periodic context bar updates
        self.set_interval(2.0, self.update_context_bar)
        # Set up periodic agent status updates
        self.set_interval(3.0, self.update_agent_status)
        
        # Focus input field after everything is loaded
        self.query_one("#global-input").focus()

    async def load_intent_data(self) -> None:
        """Load intent.json data into the application.
        
        Delegates to DataLoader to load the intent file which contains
        project goals, sprints, and features. Updates self.intent_data.
        """
        self.intent_data = await self.data_loader.load_intent_data()

    async def load_blueprint_data(self) -> None:
        """Load blueprint.json data with metadata.
        
        Delegates to DataLoader to load the blueprint file which contains
        architecture components and zones. Updates self.blueprint_data.
        """
        self.blueprint_data = await self.data_loader.load_blueprint_data()

    async def load_project_data(self) -> None:
        """Load project.json data.
        
        Delegates to DataLoader to load project metadata. For the Manifest
        project itself, this is in docs/project-manifest/. For user projects,
        it would be in .manifest/ directory.
        
        Updates self.project_data with project information.
        """
        self.project_data = await self.data_loader.load_project_data()

    async def update_architect_view(self) -> None:
        """Update the Architect view with current intent data.
        
        Refreshes the architect diagram showing features, requirements,
        and sprint information. Calculates and displays progress metrics.
        """
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

    async def update_feature_explorer(self) -> None:
        """Update the Feature Explorer view with current feature data.
        
        Refreshes the feature tree widget to show the current list of
        features from intent data.
        """
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

    async def update_blueprint_view(self) -> None:
        """Update the Blueprint view with current blueprint data.
        
        Refreshes the blueprint diagram showing components organized by
        zones. Updates component status and visual representation.
        """
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

    async def update_project_view(self) -> None:
        """Update the Project Info view with current project data.
        
        Displays project metadata, status, and information from project.json.
        This view shows high-level project information and documentation.
        """
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

    async def show_sprint_history(self):
        """Show Sprint history view."""
        sprints = self.state_manager.list_sprints()
        history_log = self.query_one("#history-log", RichLog)
        history_log.clear()
        
        if not sprints:
            history_log.write("[bold yellow]No Sprint history found.[/]")
            return
        
        history_log.write(f"[bold]Sprint History ({len(sprints)} sprints)[/]")
        for sprint_id in sprints:
            sprint_data = self.state_manager.load_sprint(sprint_id)
            if sprint_data:
                status = sprint_data.get("status", "unknown")
                name = sprint_data.get("name", sprint_id)
                created = sprint_data.get("created_at", "unknown")
                tasks = sprint_data.get("tasks", [])
                completed_tasks = sum(1 for t in tasks if t.get("status") == "completed")
                
                history_log.write(f"\n[bold]{name}[/] ({sprint_id})")
                history_log.write(f"  Status: {status}")
                history_log.write(f"  Created: {created}")
                history_log.write(f"  Tasks: {completed_tasks}/{len(tasks)} completed")
    
    async def show_orchestrator_chat(self):
        """Show Orchestrator chat channel."""
        # Create or show Orchestrator channel
        channel_name = "orchestrator"
        if self.channel_manager and channel_name not in self.channel_manager.squad_channels:
            await self.channel_manager.create_squad_channel("orchestrator", "orchestrator")
        
        # Switch to Orchestrator tab
        chat_tabs = self.query_one("#chat-tabs", TabbedContent)
        try:
            chat_tabs.active = f"tab-{channel_name}"
        except Exception:
            pass
    
    async def show_sprint_approval_ui(self, sprint_id: str):
        """Show Sprint plan approval UI."""
        sprint_data = self.state_manager.load_sprint(sprint_id)
        if not sprint_data:
            log = self.query_one("#log-main", RichLog)
            log.write(f"[bold red]Sprint {sprint_id} not found.[/]")
            return
        
        # Show Sprint plan in main log
        log = self.query_one("#log-main", RichLog)
        log.write(f"[bold]Sprint Plan: {sprint_data.get('name', sprint_id)}[/]")
        log.write(f"Status: {sprint_data.get('status', 'planned')}")
        log.write(f"Tasks: {len(sprint_data.get('tasks', []))}")
        
        # Permission approval widgets are now implemented (PermissionApprovalWidget)
        # For now, user can approve via command: /approve_sprint {sprint_id}
    
    async def _update_task_inspector(self, task_id: str, task: Dict[str, Any]) -> None:
        """Update inspector with task logs and diff."""
        try:
            # Switch inspector to data mode
            visual_pane = self.query_one("#insp-visual")
            data_pane = self.query_one("#insp-data")
            drift_pane = self.query_one("#insp-drift")
            visual_pane.styles.display = "none"
            drift_pane.styles.display = "none"
            data_pane.styles.display = "block"
            self.inspector_mode = "data"
            
            data_trace = self.query_one("#data-trace", RichLog)
            data_trace.clear()
            
            # Show task header
            task_name = task.get("name", task_id)
            task_status = task.get("status", "unknown")
            data_trace.write(f"[bold cyan]Task: {task_name} ({task_id})[/]")
            data_trace.write(f"Status: [bold]{task_status}[/]")
            data_trace.write("")
            
            # Show task logs from channels
            worker_squad = task.get("worker_squad", {})
            stages = worker_squad.get("stages", {})
            
            if stages:
                data_trace.write("[bold yellow]Worker Squad Logs:[/]")
                for stage_name, stage_data in stages.items():
                    status = stage_data.get("status", "pending")
                    output = stage_data.get("output", "")
                    if output:
                        data_trace.write(f"\n[bold]{stage_name.upper()}[/] [{status}]:")
                        # Truncate very long outputs
                        if len(output) > 500:
                            data_trace.write(output[:500] + "\n... (truncated)")
                        else:
                            data_trace.write(output)
                data_trace.write("")
            
            # Also check agent channels
            if self.agent_coordinator:
                agent_info = self.agent_coordinator.get_active_agents().get(task_id)
                if agent_info:
                    channel = agent_info.get("channel")
                    if channel:
                        history = self.state_manager.get_chat_history(channel)
                        if history:
                            data_trace.write("[bold cyan]Agent Channel Logs:[/]")
                            for msg in history[-10:]:  # Last 10 messages
                                role = msg.get("role", "unknown")
                                content = msg.get("content", "")
                                if role == "user":
                                    data_trace.write(f"[dim]User:[/] {content[:200]}")
                                elif role == "assistant":
                                    data_trace.write(f"[cyan]Agent:[/] {content[:200]}")
                                elif role == "system":
                                    data_trace.write(f"[yellow]System:[/] {content[:200]}")
                            data_trace.write("")
            
            # Show Git diff if available
            from manifest.core.task_manager import TaskManager
            task_manager = TaskManager(self.state_manager)
            git_diff = task_manager.get_task_git_diff(task_id)
            
            if git_diff:
                data_trace.write("[bold green]Git Diff:[/]")
                # Truncate very long diffs
                if len(git_diff) > 2000:
                    data_trace.write(git_diff[:2000] + "\n... (truncated)")
                else:
                    data_trace.write(git_diff)
            else:
                # Check if diff is stored in task changes
                changes = task.get("changes", {})
                stored_diff = changes.get("git_diff")
                if stored_diff:
                    data_trace.write("[bold green]Stored Git Diff:[/]")
                    if len(stored_diff) > 2000:
                        data_trace.write(stored_diff[:2000] + "\n... (truncated)")
                    else:
                        data_trace.write(stored_diff)
                else:
                    data_trace.write("[dim]No Git diff available for this task[/]")
        except Exception as e:
            logger.error(f"Error updating task inspector: {e}", exc_info=True)

    async def update_context_bar(self) -> None:
        """Update context bar with current agent activities."""
        try:
            context_bar = self.query_one("#context-bar", ContextBar)
            
            if not self.agent_coordinator:
                context_bar.clear()
                context_bar.write("[dim]No agent coordinator[/]")
                return
            
            # Get active agents
            active_agents = self.agent_coordinator.get_active_agents()
            
            # Clear existing activities
            context_bar.activities = []
            
            # Add activities for each active agent
            for task_id, agent_info in active_agents.items():
                if agent_info.get("status") == "active":
                    agent_type = agent_info.get("agent_type", "agent")
                    stage = agent_info.get("stage", "working")
                    
                    # Get more detailed activity from state
                    task = self.state_manager.get_task(task_id)
                    if task:
                        worker_squad = task.get("worker_squad", {})
                        stages = worker_squad.get("stages", {})
                        current_stage = None
                        for stage_name, stage_data in stages.items():
                            if stage_data.get("status") == "in_progress":
                                current_stage = stage_name
                                break
                        
                        if current_stage:
                            activity = f"{current_stage}"
                        else:
                            activity = stage
                    else:
                        activity = stage
                    
                    context_bar.add_activity(task_id, agent_type, activity)
            
            context_bar.update_display()
        except Exception:
            # Silently fail if context bar not available
            pass

    async def update_dashboard_metrics(self) -> None:
        """Update dashboard header with current project metrics."""
        try:
            dashboard = self.query_one("#dashboard-header", DashboardHeader)
            
            # Calculate architecture match percentage
            match_pct = 0
            try:
                from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
                top_down = BlueprintLoader.load_blueprint(
                    self.manifest_dir,
                    with_metadata=True,
                    default_source="llm_design"
                )
                bottom_up = BlueprintLoader.load_code_blueprint(self.manifest_dir)
                
                status_info = self.blueprint_synchronizer.calculate_implementation_status(
                    top_down,
                    bottom_up,
                    getattr(self, 'architecture_data', None)
                )
                
                # Calculate match percentage from component statuses
                component_statuses = status_info.get("component_statuses", {})
                if component_statuses:
                    total = len(component_statuses)
                    matched = sum(1 for status in component_statuses.values() if status == "implemented")
                    match_pct = int((matched / total) * 100) if total > 0 else 0
            except Exception:
                pass
            
            # Get task counts
            tasks = self.state_manager.get_task_checklist()
            active_tasks = sum(1 for t in tasks if t.get("status") in ["pending", "in_progress"])
            completed_tasks = sum(1 for t in tasks if t.get("status") == "done")
            
            # Count running agents
            running_agents = 0
            if self.agent_coordinator:
                # Check active worker squads
                state = self.state_manager.get_state()
                tasks = state.get("tasks", [])
                for task in tasks:
                    worker_squad = task.get("worker_squad", {})
                    stages = worker_squad.get("stages", {})
                    for stage_data in stages.values():
                        if stage_data.get("status") == "in_progress":
                            running_agents += 1
            
            dashboard.update_metrics({
                "match_pct": match_pct,
                "active_tasks": active_tasks,
                "completed_tasks": completed_tasks,
                "running_agents": running_agents
            })
        except Exception:
            # Silently fail if dashboard not available
            pass
    
    async def update_agent_status(self) -> None:
        """Update agent status view with current agent information."""
        try:
            agent_status_view = self.query_one("#agent-status-view", raise_if_missing=False)
            if agent_status_view:
                from manifest.ui.widgets.agent_status_view import AgentStatusView
                if isinstance(agent_status_view, AgentStatusView):
                    agent_status_view.set_app(self)
                    await agent_status_view.update_agents()
        except Exception:
            # Silently fail if agent status view not available
            pass

    async def update_task_tree(self) -> None:
        """Update the task tree widget with current tasks from state.
        
        Refreshes the sidebar task tree to show all current tasks with
        their status and hierarchy. If no tasks exist, shows a default
        empty structure.
        """
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
        
        # Update sidebar task tree
        try:
            task_tree = self.query_one("#task-tree", TaskTree)
            task_tree.load_tasks(tasks)
        except Exception:
            pass
        
        # Update project view task tree
        try:
            project_view = self.query_one("#project-view", ProjectView)
            project_view.load_tasks(tasks)
        except Exception:
            pass

    async def update_history_view(self) -> None:
        """Update the History view with Git commit timeline.
        
        Displays recent Git commits in chronological order. Requires
        GitPython to be installed. Shows a warning if GitPython is
        not available.
        """
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
        from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
        top_down_blueprint = BlueprintLoader.load_blueprint(
            self.manifest_dir,
            with_metadata=True,
            default_source="llm_design"
        )
        
        # Compare blueprints
        blueprint_conflicts = self.blueprint_comparator.compare_blueprints(
            top_down_blueprint,
            bottom_up_blueprint
        )
        
        # Also run traditional drift audit
        drift_conflicts = self.drift_auditor.audit_project()
        
        # Combine conflicts for display
        from manifest.audit.code.drift_auditor import DriftConflict as DriftConflictClass
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
        
        # Check for structural changes and suggest Blueprint updates
        try:
            suggestions = self.structure_manager.check_and_suggest_updates()
            if suggestions:
                drift_log.write(f"[bold yellow]Blueprint Update Suggestions: {len(suggestions)}[/]")
                for suggestion in suggestions[:5]:  # Show first 5
                    drift_log.write(f"  • {suggestion.suggestion_type}: {suggestion.reason}")
                if len(suggestions) > 5:
                    drift_log.write(f"  ... and {len(suggestions) - 5} more suggestions")
                
                # Store suggestions for potential approval
                self._pending_blueprint_suggestions = suggestions
                drift_log.write(f"[bold cyan]Use /apply_blueprint_updates to apply all suggestions, or /apply_blueprint_update <index> for specific one[/]")
        except Exception as e:
            # Silently fail if structure manager has issues
            pass
        
        # Check for Blueprint changes and suggest code updates
        try:
            code_suggestions, impact = self.structure_manager.check_blueprint_and_suggest_code_changes()
            if code_suggestions:
                drift_log.write(f"[bold cyan]Code Change Suggestions: {len(code_suggestions)}[/]")
                for suggestion in code_suggestions[:5]:  # Show first 5
                    drift_log.write(f"  • {suggestion.suggestion_type}: {suggestion.action}")
                    drift_log.write(f"    Reason: {suggestion.reason}")
                if len(code_suggestions) > 5:
                    drift_log.write(f"  ... and {len(code_suggestions) - 5} more suggestions")
                
                # Show impact analysis
                if impact:
                    affected_files = impact.get("affected_files", [])
                    breaking_changes = impact.get("breaking_changes", [])
                    migration_steps = impact.get("migration_steps", [])
                    
                    if affected_files:
                        drift_log.write(f"[bold yellow]Affected Files: {len(affected_files)}[/]")
                        for file_path in affected_files[:5]:
                            drift_log.write(f"  • {file_path}")
                    
                    if breaking_changes:
                        drift_log.write(f"[bold red]Breaking Changes: {len(breaking_changes)}[/]")
                        for change in breaking_changes[:3]:
                            drift_log.write(f"  • {change.get('description', 'Unknown')}")
                    
                    if migration_steps:
                        drift_log.write(f"[bold green]Migration Plan: {len(migration_steps)} steps[/]")
                        for step in migration_steps:
                            drift_log.write(f"  Step {step.get('step', '?')}: {step.get('action', 'Unknown')} (Priority: {step.get('priority', 'unknown')})")
                
                # Store code suggestions for potential approval
                self._pending_code_suggestions = code_suggestions
                if code_suggestions:
                    drift_log.write(f"[bold cyan]Use /apply_code_changes to apply all code changes, or /apply_code_change <index> for specific one[/]")
        except Exception as e:
            # Silently fail if structure manager has issues
            pass
        
        # Show drift mode if there are conflicts
        if all_conflicts:
            visual_pane = self.query_one("#insp-visual")
            data_pane = self.query_one("#insp-data")
            drift_pane = self.query_one("#insp-drift")
            visual_pane.styles.display = "none"
            data_pane.styles.display = "none"
            drift_pane.styles.display = "block"
            self.inspector_mode = "drift"

    async def sync_blueprints(self):
        """Synchronize blueprints using blueprint_synchronizer."""
        from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
        
        top_down_blueprint = BlueprintLoader.load_blueprint(
            self.manifest_dir,
            with_metadata=True,
            default_source="llm_design"
        )
        bottom_up_blueprint = BlueprintLoader.load_code_blueprint(self.manifest_dir)
        
        # Use workflow mode by default
        result = self.blueprint_synchronizer.sync_blueprints(
            top_down_blueprint,
            bottom_up_blueprint,
            mode="workflow"
        )
        
        return result
    
    async def resolve_conflict(self, conflict_id: str, action: str):
        """
        Resolve a blueprint conflict.
        
        Args:
            conflict_id: Conflict identifier
            action: Resolution action ("approved" or "rejected")
        """
        # Load conflict report if it exists
        conflict_file = self.manifest_dir / "conflicts" / f"{conflict_id}.json"
        if conflict_file.exists():
            report = self.blueprint_synchronizer.load_conflict_report(conflict_file)
            if report:
                # Update conflict status
                report.status = "resolved" if action == "approved" else "rejected"
                report.user_decision = action
                self.blueprint_synchronizer.save_conflict_report(report, conflict_file)
                
                # If approved and agent coordinator available, handle the resolution
                if action == "approved" and self.agent_coordinator:
                    # Get task_id from report
                    task_id = report.task_id
                    if task_id:
                        # Handle blueprint conflict through agent coordinator
                        await self.agent_coordinator.handle_blueprint_conflict(
                            report.to_dict(),
                            task_id
                        )
    
    async def handle_blueprint_conflict(self, mismatch_report: ConflictReport):
        """
        Handle blueprint conflict by delegating to agent coordinator.
        
        Args:
            mismatch_report: ConflictReport from blueprint synchronizer
        """
        if self.agent_coordinator:
            task_id = mismatch_report.task_id
            await self.agent_coordinator.handle_blueprint_conflict(
                mismatch_report.to_dict(),
                task_id
            )

    @on(TabbedContent.TabActivated, "#design-tabs")
    async def on_tab_switched(self, event: TabbedContent.TabActivated) -> None:
        """Handle design tab switching."""
        visual_pane = self.query_one("#insp-visual")
        data_pane = self.query_one("#insp-data")
        drift_pane = self.query_one("#insp-drift")
        
        if event.pane.id == "tab-structure":
            visual_pane.styles.display = "block"
            data_pane.styles.display = "none"
            drift_pane.styles.display = "none"
            self.current_view = "structure"
            self.inspector_mode = "visual"
            # Load structure data when tab is activated
            await self._load_structure_data()
        elif event.pane.id == "tab-project":
            visual_pane.styles.display = "none"
            data_pane.styles.display = "block"
            drift_pane.styles.display = "none"
            self.current_view = "project"
            self.inspector_mode = "data"
            # Load project data when tab is activated
            await self._load_project_data()

    def action_toggle_inspector(self) -> None:
        """Toggle inspector visibility."""
        side = self.query_one("#inspector-side")
        side.styles.display = "none" if side.styles.display == "block" else "block"

    def action_show_project(self) -> None:
        """Switch to project view."""
        tabs = self.query_one("#design-tabs", TabbedContent)
        tabs.active = "tab-project"
    
    async def _load_structure_data(self):
        """Load and update structure view data."""
        # Load architecture
        architecture_file = self.manifest_dir / "architecture.json"
        self.architecture_data = load_architecture_with_metadata(architecture_file)
        
        # Calculate status using BlueprintSynchronizer
        from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
        
        top_down_blueprint = BlueprintLoader.load_blueprint(
            self.manifest_dir,
            with_metadata=True,
            default_source="llm_design"
        )
        bottom_up_blueprint = BlueprintLoader.load_code_blueprint(self.manifest_dir)
        
        # Calculate implementation status
        status_info = self.blueprint_synchronizer.calculate_implementation_status(
            top_down_blueprint,
            bottom_up_blueprint,
            self.architecture_data
        )
        
        # Update hierarchy view
        try:
            hierarchy_view = self.query_one("#structure-hierarchy-view", StructureHierarchyView)
            hierarchy_view.set_app(self)  # Set app reference for task association
            hierarchy_view.load_data(self.architecture_data, top_down_blueprint, status_info)
        except Exception:
            pass
        
        # Update graph view
        try:
            graph_view = self.query_one("#structure-graph-view", StructureGraphView)
            graph_view.load_data(self.architecture_data, top_down_blueprint, status_info)
        except Exception:
            pass
    
    async def _load_project_data(self):
        """Load and update project view data."""
        # Load tasks from state
        state = self.state_manager.get_state()
        tasks = state.get("tasks", [])
        sprints = state.get("sprints", [])
        
        # Update project view
        try:
            project_view = self.query_one("#project-view", ProjectView)
            project_view.load_tasks(tasks)
            project_view.load_sprints(sprints)
        except Exception:
            pass
        
        # Load history (from git or state)
        history = []
        if GIT_AVAILABLE:
            try:
                repo = git.Repo(".")
                commits = list(repo.iter_commits(max_count=50))
                for commit in commits:
                    history.append({
                        "timestamp": commit.committed_datetime.isoformat(),
                        "action": "commit",
                        "details": f"{commit.message.split(chr(10))[0]} ({commit.hexsha[:8]})"
                    })
            except Exception:
                pass
        
        # Update history view in project view
        try:
            project_view = self.query_one("#project-view", ProjectView)
            project_view.load_history(history)
        except Exception:
            pass
    
    def action_open_settings(self, initial_tab: str = "api_keys") -> None:
        """Open settings screen."""
        settings_screen = SettingsScreen(
            manifest_dir=self.manifest_dir,
            project_root=Path.cwd(),
            initial_tab=initial_tab
        )
        self.push_screen(settings_screen)

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
    async def process_command(self, user_input: str, log: RichLog) -> None:
        """Process a user command entered in the input field.
        
        Delegates command processing to CommandHandler which routes commands
        to appropriate handlers. Commands can start agents, load data, audit
        drift, sync blueprints, and more.
        
        Args:
            user_input: The command string entered by the user.
            log: RichLog widget to write output and feedback to.
        """
        try:
            await asyncio.sleep(0.1)  # Small delay for UI responsiveness
            
            # Use command handler if available
            if user_input.startswith("/") and self.command_handler:
                handled = await self.command_handler.handle(user_input, log)
                if handled:
                    return
                # If not handled, fall through to orchestrator
            
            # Regular AI interaction - send to Orchestrator
            if not user_input.startswith("/"):
                if self.agent_bridge and self.agent_bridge.is_connected and self.agent_coordinator:
                    # Get orchestrator context
                    context = self.context_provider.get_orchestrator_context()
                    
                    # Get model config
                    config_manager = get_config_manager()
                    model_config = config_manager.get_agent_model_config("orchestrator")
                    
                    # Create orchestrator agent
                    orchestrator_agent = await self.agent_bridge.agent_manager.create_agent(
                        agent_type="orchestrator",
                        context=context,
                        model_config=model_config,
                        task_id="main-orchestrator"
                    )
                    
                    if orchestrator_agent and orchestrator_agent.get("instance"):
                        # Add user message to history via channel_manager
                        channel = "main-orchestrator"
                        if self.channel_manager:
                            await self.channel_manager.handle_agent_output(channel, user_input, "user", save_immediately=True)
                        else:
                            # Fallback to direct state manager
                            self.state_manager.add_chat_message(channel, "user", user_input)
                            await self.state_manager.save_state()
                        
                        orchestrator_instance = orchestrator_agent["instance"]
                        orchestrator_instance.message_history.append({
                            "role": "user",
                            "content": user_input
                        })
                        
                        # Process with orchestrator
                        if self.channel_manager:
                            await self.channel_manager.handle_agent_output(
                                channel, "[bold green]Processing with Orchestrator...[/]", "system", save_immediately=False
                            )
                        else:
                            log.write("[bold green]Processing with Orchestrator...[/]")
                        
                        response_content = ""
                        
                        async for chunk in orchestrator_instance.coordinate(
                            mission_description=user_input,
                            context=context,
                            model_config=model_config
                        ):
                            chunk_type = chunk.get("type")
                            
                            if chunk_type == "chunk":
                                content = chunk.get("content", "")
                                response_content += content
                                # Stream to UI via channel_manager
                                if self.channel_manager:
                                    await self.channel_manager.handle_agent_output(
                                        channel, content, "assistant", save_immediately=False
                                    )
                                else:
                                    log.write(content)
                            elif chunk_type == "complete":
                                content = chunk.get("content", "")
                                if content and content != response_content:
                                    # Write remaining content if any
                                    remaining = content[len(response_content):]
                                    if remaining:
                                        if self.channel_manager:
                                            await self.channel_manager.handle_agent_output(
                                                channel, remaining, "assistant", save_immediately=True
                                            )
                                        else:
                                            log.write(remaining)
                                    response_content = content
                                elif content:
                                    # Save complete response
                                    if self.channel_manager:
                                        await self.channel_manager.handle_agent_output(
                                            channel, content, "assistant", save_immediately=True
                                        )
                            elif chunk_type == "tool_use" or chunk_type == "tool_use_start":
                                # Display tool call via channel_manager
                                tool_call = chunk.get("tool_call", {})
                                tool_name = tool_call.get("name", "unknown")
                                tool_id = tool_call.get("id", "unknown")
                                tool_input = tool_call.get("input", {})
                                
                                import json
                                tool_display = f"[cyan]🔧 Tool: {tool_name}[/] (id: {tool_id[:8]}...)\n"
                                if tool_input:
                                    tool_display += f"  Input: {json.dumps(tool_input, indent=2)[:200]}...\n"
                                
                                if self.channel_manager:
                                    await self.channel_manager.handle_agent_output(
                                        channel, tool_display, "system", save_immediately=False
                                    )
                                else:
                                    log.write(tool_display)
                            elif chunk_type == "tool_result":
                                # Display tool result via channel_manager
                                tool_name = chunk.get("tool_name", "unknown")
                                tool_call_id = chunk.get("tool_call_id", "unknown")
                                result = chunk.get("result")
                                error = chunk.get("error")
                                
                                if error:
                                    result_display = f"[red]❌ Tool {tool_name} failed:[/] {error}\n"
                                else:
                                    import json
                                    result_str = json.dumps(result, indent=2) if result else "null"
                                    result_display = f"[green]✅ Tool {tool_name} completed[/] (id: {tool_call_id[:8]}...)\n"
                                    if len(result_str) > 300:
                                        result_display += f"  Result: {result_str[:300]}...\n"
                                    else:
                                        result_display += f"  Result: {result_str}\n"
                                
                                if self.channel_manager:
                                    await self.channel_manager.handle_agent_output(
                                        channel, result_display, "system", save_immediately=False
                                    )
                                else:
                                    log.write(result_display)
                            elif chunk_type == "error":
                                error_msg = chunk.get("content", "Unknown error")
                                error_display = f"[bold red]Error: {error_msg}[/]"
                                if self.channel_manager:
                                    await self.channel_manager.handle_agent_output(
                                        channel, error_display, "system", save_immediately=True
                                    )
                                else:
                                    log.write(error_display)
                        
                        # Try to extract and create tasks from orchestrator response
                        if response_content:
                            await self._process_orchestrator_response(response_content, log)
                    else:
                        error_msg = "[bold yellow]Failed to create orchestrator agent.[/]"
                        if self.channel_manager:
                            await self.channel_manager.handle_agent_output(
                                "main", error_msg, "system", save_immediately=True
                            )
                        else:
                            log.write(error_msg)
                            # Save error to state
                            self.state_manager.add_chat_message("main", "user", user_input)
                            self.state_manager.add_chat_message("main", "assistant", "Error: Failed to create orchestrator agent.")
                            await self.state_manager.save_state()
                else:
                    # Agent bridge not connected - provide helpful message
                    error_msg = ""
                    if not self.agent_bridge:
                        error_msg = "[bold yellow]Agent system not initialized. Please wait for initialization...[/]"
                    elif not self.agent_bridge.is_connected:
                        error_msg = "[bold yellow]Agent system not connected. Use /start_agent to initialize.[/]"
                    elif not self.agent_coordinator:
                        error_msg = "[bold yellow]Agent coordinator not available.[/]"
                    
                    if error_msg:
                        if self.channel_manager:
                            await self.channel_manager.handle_agent_output("main", error_msg, "system", save_immediately=True)
                        else:
                            log.write(error_msg)
                    
                    # Save to state anyway
                    if self.channel_manager:
                        await self.channel_manager.handle_agent_output("main", user_input, "user", save_immediately=False)
                        await self.channel_manager.handle_agent_output(
                            "main", "Agent system not available. Please check connection.", "assistant", save_immediately=True
                        )
                    else:
                        self.state_manager.add_chat_message("main", "user", user_input)
                        self.state_manager.add_chat_message("main", "assistant", "Agent system not available. Please check connection.")
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
    
    async def _process_orchestrator_response(self, response: str, log: RichLog):
        """
        Process orchestrator response and extract actionable items.
        Automatically creates tasks and starts worker squads when appropriate.
        
        Args:
            response: Orchestrator response text
            log: Log widget for output
        """
        import re
        
        # Look for task creation patterns
        # Pattern 1: "Create task: <name>" or "Task: <name>"
        # Pattern 2: JSON-like task definitions
        # Pattern 3: Structured task lists
        task_patterns = [
            r"(?:Create|Add|New)\s+task[:\s]+(.+?)(?:\n|$)",
            r"Task[:\s]+(.+?)(?:\n|$)",
            r"^\s*[-*]\s*(.+?)(?:\n|$)",  # Bullet points
            r"^\s*\d+\.\s*(.+?)(?:\n|$)",  # Numbered list
        ]
        
        tasks_found = []
        existing_tasks = self.state_manager.get_task_checklist()
        existing_names = [t.get("name", "").lower() for t in existing_tasks]
        
        for pattern in task_patterns:
            matches = re.finditer(pattern, response, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                task_name = match.group(1).strip()
                # Filter out very short matches and common false positives
                if task_name and len(task_name) > 3 and not task_name.lower().startswith(('the', 'a ', 'an ')):
                    # Remove common prefixes
                    task_name = re.sub(r'^(?:to|for|implement|create|add|build|develop|fix|refactor)\s+', '', task_name, flags=re.IGNORECASE).strip()
                    # Remove trailing punctuation
                    task_name = re.sub(r'[.:;]$', '', task_name).strip()
                    
                    if task_name and task_name.lower() not in existing_names and task_name not in tasks_found:
                        tasks_found.append(task_name)
        
        # Also look for JSON task definitions
        json_task_pattern = r'\{[^}]*"task"[^}]*"name"[^}]*\}'
        json_matches = re.finditer(json_task_pattern, response, re.IGNORECASE | re.DOTALL)
        for match in json_matches:
            try:
                import json
                task_json = json.loads(match.group(0))
                if "name" in task_json:
                    task_name = task_json["name"]
                    if task_name and task_name.lower() not in existing_names and task_name not in tasks_found:
                        tasks_found.append(task_name)
            except:
                pass
        
        # If tasks found, create them automatically
        if tasks_found:
            log.write(f"[bold cyan]Orchestrator suggested {len(tasks_found)} task(s). Creating tasks...[/]")
            created_tasks = []
            
            for task_name in tasks_found[:10]:  # Limit to first 10
                try:
                    # Create task
                    task_id = self.state_manager.create_task(
                        name=task_name,
                        description=f"Task created from Orchestrator suggestion: {task_name}",
                        stage="planning",
                        status="pending"
                    )
                    created_tasks.append({"id": task_id, "name": task_name})
                    log.write(f"[bold green]✓ Created task: {task_name} (ID: {task_id})[/]")
                except Exception as e:
                    log.write(f"[bold red]✗ Failed to create task '{task_name}': {str(e)}[/]")
            
            if len(tasks_found) > 10:
                log.write(f"[bold yellow]... and {len(tasks_found) - 10} more tasks (limit reached)[/]")
            
            # Update task tree in UI
            await self.update_task_tree()
            # Update dashboard metrics
            await self.update_dashboard_metrics()
            
            # Optionally auto-start worker squads for created tasks
            # Check if orchestrator response suggests immediate execution
            auto_start = "start" in response.lower() or "execute" in response.lower() or "begin" in response.lower()
            
            if created_tasks:
                if auto_start and self.agent_coordinator:
                    # Auto-start worker squads
                    log.write(f"[bold cyan]Auto-starting worker squads for {len(created_tasks)} task(s)...[/]")
                    for task_info in created_tasks:
                        task_id = task_info["id"]
                        try:
                            # Start worker squad in background
                            success = await self.agent_coordinator._start_task_worker_squad(task_id)
                            if success:
                                log.write(f"[bold green]✓ Started worker squad for task: {task_info['name']} (ID: {task_id})[/]")
                            else:
                                log.write(f"[bold yellow]⚠ Failed to start worker squad for task: {task_info['name']}[/]")
                        except Exception as e:
                            log.write(f"[bold red]✗ Error starting worker squad for task {task_info['name']}: {str(e)}[/]")
                    
                    # Update task tree
                    await self.update_task_tree()
                else:
                    # Manual start required
                    log.write(f"[bold cyan]Created {len(created_tasks)} task(s). Use /start_task <task_id> to start worker squad, or /start_sprint to start all tasks in a sprint.[/]")
            
            await self.state_manager.save_state()
    
    @on(GateController.Approved)
    async def on_task_approved(self, message: GateController.Approved):
        """Handle task approval."""
        task_id = message.task_id
        if self.agent_bridge and self.agent_bridge.is_connected:
            await self.agent_bridge.promote_task(task_id, "approved")
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
    
    @on(TaskSelected)
    async def on_task_selected(self, message: TaskSelected) -> None:
        """Handle task selection from TaskTreeView.
        
        When a task is selected, shows task details in inspector with logs and diff,
        and allows status changes via keyboard shortcuts.
        
        Args:
            message: TaskSelected message with task information.
        """
        task_id = message.task_id
        task = message.task
        current_status = message.current_status
        
        log = self.query_one("#log-main", RichLog)
        
        # Show task details
        task_desc = task.get("description", "No description")
        task_stage = task.get("stage", "unknown")
        worker_squad = task.get("worker_squad", {})
        stages = worker_squad.get("stages", {})
        
        log.write(f"[bold cyan]Task Selected: {task_id}[/]")
        log.write(f"Status: [bold]{current_status}[/] | Stage: {task_stage}")
        log.write(f"Description: {task_desc[:100]}")
        
        # Show worker squad progress if available
        if stages:
            completed = sum(1 for s in stages.values() if s.get("status") == "completed")
            total = len(stages)
            progress = (completed / total * 100) if total > 0 else 0
            log.write(f"Worker Squad Progress: {progress:.0f}% ({completed}/{total} stages)")
            log.write("[dim]Press 's' to change status, 'Enter' to view details[/]")
        else:
            log.write("[dim]Press 's' to change status, 'Enter' to view details[/]")
        
        # Update inspector with task logs and diff
        await self._update_task_inspector(task_id, task)
        
        # Store selected task for status change
        self._selected_task_id = task_id
        self._selected_task_status = current_status

    @on(SprintSelected)
    async def on_sprint_selected(self, message: SprintSelected) -> None:
        """Handle sprint selection from SprintStatusView.
        
        When a sprint is selected, shows sprint details and allows approval/start
        via the SprintApprovalWidget.
        
        Args:
            message: SprintSelected message with sprint information.
        """
        sprint_id = message.sprint_id
        sprint = message.sprint
        
        log = self.query_one("#log-main", RichLog)
        
        # Show sprint details
        sprint_name = sprint.get("name", f"Sprint {sprint_id}")
        sprint_status = sprint.get("status", "pending")
        tasks = sprint.get("tasks", [])
        completed = len([t for t in tasks if t.get("status") == "done"])
        total = len(tasks)
        progress = (completed / total * 100) if total > 0 else 0
        
        log.write(f"[bold cyan]Sprint Selected: {sprint_name} ({sprint_id})[/]")
        log.write(f"Status: [bold]{sprint_status}[/] | Progress: {progress:.1f}% ({completed}/{total} tasks)")
        
        # Show sprint approval widget
        try:
            approval_widget = self.query_one("#sprint-approval-widget", SprintApprovalWidget)
            approval_widget.sprint_id = sprint_id
            approval_widget.query_one("#sprint-label").update(f"Sprint: {sprint_name}")
            approval_widget.styles.display = "block"
            
            # Hide gate controller if showing sprint approval
            self.query_one("#gate-controller").styles.display = "none"
        except Exception:
            pass

    @on(SprintApprovalWidget.Approved)
    async def on_sprint_approved(self, message: SprintApprovalWidget.Approved):
        """Handle sprint approval."""
        sprint_id = message.sprint_id
        log = self.query_one("#log-main", RichLog)
        
        # Promoting sprint status
        if hasattr(self.state_manager, 'update_sprint_status'):
            success = self.state_manager.update_sprint_status(sprint_id, "approved")
            if success:
                log.write(f"[bold green]Sprint {sprint_id} approved.[/]")
                await self.state_manager.save_state()
                await self._load_project_data()
            else:
                log.write(f"[bold red]Failed to approve sprint {sprint_id}.[/]")
        
        self.query_one("#sprint-approval-widget").styles.display = "none"

    @on(SprintApprovalWidget.Rejected)
    async def on_sprint_rejected(self, message: SprintApprovalWidget.Rejected):
        """Handle sprint rejection."""
        sprint_id = message.sprint_id
        log = self.query_one("#log-main", RichLog)
        log.write(f"[bold red]Sprint {sprint_id} rejected.[/]")
        
        if hasattr(self.state_manager, 'update_sprint_status'):
            self.state_manager.update_sprint_status(sprint_id, "rejected")
            await self.state_manager.save_state()
            await self._load_project_data()
        
        self.query_one("#sprint-approval-widget").styles.display = "none"

    @on(SprintApprovalWidget.Started)
    async def on_sprint_started(self, message: SprintApprovalWidget.Started):
        """Handle sprint start."""
        sprint_id = message.sprint_id
        log = self.query_one("#log-main", RichLog)
        
        if self.agent_coordinator:
            log.write(f"[bold green]Starting sprint {sprint_id}...[/]")
            success = await self.agent_coordinator.start_sprint(sprint_id)
            if success:
                log.write(f"[bold green]Sprint {sprint_id} started successfully.[/]")
            else:
                log.write(f"[bold red]Failed to start sprint {sprint_id}.[/]")
    
    @on(PermissionApprovalWidget.Approved)
    async def on_permission_approved(self, message: PermissionApprovalWidget.Approved):
        """Handle permission approval."""
        request_id = message.request_id
        log = self.query_one("#log-main", RichLog)
        
        if self.approval_manager:
            success = await self.approval_manager.approve_request(request_id)
            if success:
                log.write(f"[bold green]Permission request {request_id[:8]}... approved.[/]")
                # Hide approval widget
                try:
                    widget = self.query_one("#permission-approval-widget", PermissionApprovalWidget)
                    widget.styles.display = "none"
                except Exception:
                    pass
                
                # Check for more pending requests
                await self.check_pending_permissions()
            else:
                log.write(f"[bold yellow]Permission request {request_id[:8]}... not found or already processed.[/]")
    
    @on(PermissionApprovalWidget.Denied)
    async def on_permission_denied(self, message: PermissionApprovalWidget.Denied):
        """Handle permission denial."""
        request_id = message.request_id
        log = self.query_one("#log-main", RichLog)
        
        if self.approval_manager:
            success = await self.approval_manager.deny_request(request_id)
            if success:
                log.write(f"[bold red]Permission request {request_id[:8]}... denied.[/]")
                # Hide approval widget
                try:
                    widget = self.query_one("#permission-approval-widget", PermissionApprovalWidget)
                    widget.styles.display = "none"
                except Exception:
                    pass
                
                # Check for more pending requests
                await self.check_pending_permissions()
            else:
                log.write(f"[bold yellow]Permission request {request_id[:8]}... not found or already processed.[/]")
    
    async def check_pending_permissions(self):
        """Check for pending permission requests and display them in UI.
        
        This method is called when a permission request is created or when
        a previous request is approved/denied. It displays the next pending
        request in the PermissionApprovalWidget.
        """
        if not self.approval_manager:
            return
        
        pending_requests = self.approval_manager.get_pending_requests()
        
        if pending_requests:
            # Show the first pending request
            request = pending_requests[0]
            try:
                widget = self.query_one("#permission-approval-widget", PermissionApprovalWidget)
                widget.set_request(request)
                widget.styles.display = "block"
                
                # Log to main log
                log = self.query_one("#log-main", RichLog)
                log.write(
                    f"[yellow]⏸ Permission approval required: "
                    f"{request.get('agent_type', 'unknown')} wants to "
                    f"{request.get('permission_type', 'unknown')} "
                    f"{request.get('resource', 'unknown')}[/]"
                )
            except Exception as e:
                logger.error(f"Error displaying permission request: {e}")
        else:
            # No pending requests, hide widget
            try:
                widget = self.query_one("#permission-approval-widget", PermissionApprovalWidget)
                widget.styles.display = "none"
            except Exception:
                pass
                log.write(f"[bold red]Failed to start sprint {sprint_id}.[/]")
        
        self.query_one("#sprint-approval-widget").styles.display = "none"
    
    def action_change_task_status(self) -> None:
        """Change status of the currently selected task.
        
        Cycles through status values: pending -> in_progress -> done -> blocked -> cancelled -> pending
        """
        if not hasattr(self, '_selected_task_id') or not self._selected_task_id:
            log = self.query_one("#log-main", RichLog)
            log.write("[bold yellow]No task selected. Select a task first.[/]")
            return
        
        task_id = self._selected_task_id
        current_status = getattr(self, '_selected_task_status', 'pending')
        
        # Status cycle
        status_cycle = ["pending", "in_progress", "done", "blocked", "cancelled"]
        try:
            current_index = status_cycle.index(current_status)
            next_index = (current_index + 1) % len(status_cycle)
            new_status = status_cycle[next_index]
        except ValueError:
            new_status = "pending"
        
        # Update task status
        success = self.state_manager.update_task(task_id, status=new_status)
        if success:
            # Save state
            import asyncio
            asyncio.create_task(self.state_manager.save_state())
            
            # Update UI
            asyncio.create_task(self.update_task_tree())
            
            log = self.query_one("#log-main", RichLog)
            log.write(f"[bold green]Task {task_id} status changed: {current_status} → {new_status}[/]")
            
            # Update selected status
            self._selected_task_status = new_status
        else:
            log = self.query_one("#log-main", RichLog)
            log.write(f"[bold red]Failed to update task {task_id} status.[/]")

    async def action_delete_task(self) -> None:
        """Delete the currently selected task."""
        if not hasattr(self, '_selected_task_id') or not self._selected_task_id:
            log = self.query_one("#log-main", RichLog)
            log.write("[bold yellow]No task selected. Select a task first.[/]")
            return
        
        task_id = self._selected_task_id
        
        # Delete task
        success = self.state_manager.delete_task(task_id)
        if success:
            # Save state
            await self.state_manager.save_state()
            
            # Update UI
            await self.update_task_tree()
            
            log = self.query_one("#log-main", RichLog)
            log.write(f"[bold red]Task {task_id} deleted.[/]")
            
            # Clear selection
            self._selected_task_id = None
            self._selected_task_status = None
        else:
            log = self.query_one("#log-main", RichLog)
            log.write(f"[bold red]Failed to delete task {task_id}.[/]")

    async def action_edit_task(self) -> None:
        """Edit the currently selected task."""
        if not hasattr(self, '_selected_task_id') or not self._selected_task_id:
            log = self.query_one("#log-main", RichLog)
            log.write("[bold yellow]No task selected. Select a task first.[/]")
            return
        
        task_id = self._selected_task_id
        task = self.state_manager.get_task(task_id)
        
        if not task:
            log = self.query_one("#log-main", RichLog)
            log.write(f"[bold red]Task {task_id} not found.[/]")
            return
            
        async def handle_edit_result(result: Optional[Dict[str, str]]):
            if result:
                # Update task
                success = self.state_manager.update_task(
                    task_id, 
                    name=result.get("name"), 
                    description=result.get("description")
                )
                if success:
                    await self.state_manager.save_state()
                    await self.update_task_tree()
                    log = self.query_one("#log-main", RichLog)
                    log.write(f"[bold green]Task {task_id} updated.[/]")
                else:
                    log = self.query_one("#log-main", RichLog)
                    log.write(f"[bold red]Failed to update task {task_id}.[/]")
        
        self.push_screen(TaskEditScreen(task), handle_edit_result)
    
    async def create_squad_channel(self, task_id: str, agent_type: str) -> Optional[str]:
        """Create a squad channel for agent output."""
        if self.channel_manager:
            return await self.channel_manager.create_squad_channel(task_id, agent_type)
        return None
    
    async def update_squad_channels(self):
        """Update squad channels based on active tasks."""
        if self.channel_manager:
            await self.channel_manager.update_squad_channels(self.agent_coordinator)
    
    async def handle_agent_output(self, channel: str, content: str, role: str = "assistant"):
        """
        Handle agent output and display in appropriate channel.
        
        Args:
            channel: Channel name (e.g., "main", "squad-task-1-planner")
            content: Message content
            role: Message role ("user" or "assistant")
        """
        if self.channel_manager:
            await self.channel_manager.handle_agent_output(channel, content, role)

    async def on_unmount(self) -> None:
        """Cleanup on app exit."""
        await self._stop_container_api()
        if self.agent_bridge:
            await self.agent_bridge.stop()
        await self.state_manager.save_state()


if __name__ == "__main__":
    app = ManifestApp()
    app.run()