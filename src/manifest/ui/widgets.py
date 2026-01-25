"""
Custom Textual widgets for Manifest TUI.

This module provides custom widget classes that extend Textual's built-in
widgets for displaying project data. Widgets include RequirementMap for
feature/requirement visualization, ArchitectureGraph for component status,
FeatureTree for hierarchical feature display, TaskTree for task organization,
and GateController for approval workflows.
"""
from textual.widgets import Tree, Button, Static, Label, ProgressBar
from textual.containers import Container, Vertical, Horizontal
from textual import on
from textual.message import Message
from typing import Dict, Any, List, Optional
import json


class RequirementMap(Static):
    """Visualizes high-level feature dependencies and goal hierarchies."""
    
    def __init__(self, data: Optional[Dict[str, Any]] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = data or {}
    
    def render(self):
        """Render the requirement map."""
        if not self.data:
            return "No requirements data"
        
        features = self.data.get("features", [])
        if not features:
            return "No features defined"
        
        lines = []
        for feature in features:
            name = feature.get("name", "Unknown")
            status = feature.get("status", "pending")
            reqs = feature.get("reqs", [])
            
            status_icon = {
                "done": "✅",
                "wip": "⚡",
                "pending": "⏳",
                "blocked": "🚫"
            }.get(status, "⏳")
            
            lines.append(f"{status_icon} {name}")
            for req in reqs:
                req_id = req.get("id", "")
                req_desc = req.get("desc", "")
                req_state = req.get("state", "pending")
                state_icon = "✔" if req_state == "done" else "○"
                lines.append(f"  {state_icon} {req_id}: {req_desc}")
        
        return "\n".join(lines)
    
    def update_data(self, data: Dict[str, Any]):
        """Update the requirement map data."""
        self.data = data
        self.refresh()


class ArchitectureGraph(Static):
    """Node-edge visualization with status overlays."""
    
    def __init__(self, data: Optional[Dict[str, Any]] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = data or {}
    
    def render(self):
        """Render the architecture graph."""
        if not self.data:
            return "No architecture data"
        
        components = self.data.get("components", [])
        if not components:
            return "No components defined"
        
        lines = []
        for comp in components:
            name = comp.get("name", "Unknown")
            status = comp.get("status", "pending")
            zone = comp.get("zone", "unknown")
            
            status_color = {
                "active": "green",
                "ghost": "yellow",
                "pending": "gray",
                "error": "red"
            }.get(status, "gray")
            
            status_icon = {
                "active": "●",
                "ghost": "○",
                "pending": "○",
                "error": "✗"
            }.get(status, "○")
            
            lines.append(f"{status_icon} [{zone.upper()}] {name}")
        
        return "\n".join(lines)
    
    def update_data(self, data: Dict[str, Any]):
        """Update the architecture graph data."""
        self.data = data
        self.refresh()


class FeatureTree(Tree):
    """AST-aware code navigation tree."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.feature_data = {}
    
    def load_features(self, features: List[Dict[str, Any]]):
        """Load features into the tree."""
        self.feature_data = {f.get("id"): f for f in features}
        self.root.expand()
        
        for feature in features:
            feature_id = feature.get("id", "")
            feature_name = feature.get("name", "Unknown")
            feature_status = feature.get("status", "pending")
            
            status_icon = {
                "done": "✅",
                "wip": "⚡",
                "pending": "⏳"
            }.get(feature_status, "⏳")
            
            feature_node = self.root.add(f"{status_icon} {feature_name}", expand=False)
            feature_node.data = {"type": "feature", "id": feature_id}
            
            # Add classes
            classes = feature.get("classes", [])
            for cls in classes:
                cls_name = cls.get("name", "Unknown")
                cls_node = feature_node.add(f"📦 {cls_name}", expand=False)
                cls_node.data = {"type": "class", "id": cls.get("id", "")}
                
                # Add methods
                methods = cls.get("methods", [])
                for method in methods:
                    method_name = method.get("name", "Unknown")
                    method_node = cls_node.add(f"  ⚙️  {method_name}")
                    method_node.data = {"type": "method", "id": method.get("id", "")}


class TaskTree(Tree):
    """Status-aware mission tracker."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tasks = []
    
    def load_tasks(self, tasks: List[Dict[str, Any]]):
        """Load tasks into the tree."""
        self.tasks = tasks
        self.root.expand()
        
        for task in tasks:
            task_id = task.get("id", "")
            task_name = task.get("name", "Unknown")
            task_status = task.get("status", "pending")
            task_stage = task.get("stage", "pending")
            
            status_icon = {
                "done": "✅",
                "in_progress": "⚡",
                "pending": "⏳",
                "blocked": "🚫",
                "approved": "✓"
            }.get(task_status, "⏳")
            
            task_label = f"{status_icon} [{task_stage}] {task_name}"
            task_node = self.root.add(task_label, expand=True)
            task_node.data = {"type": "task", "id": task_id, "status": task_status, "stage": task_stage}
            
            # Add subtasks
            subtasks = task.get("subtasks", [])
            for subtask in subtasks:
                subtask_id = subtask.get("id", "")
                subtask_name = subtask.get("name", "Unknown")
                subtask_status = subtask.get("status", "pending")
                
                subtask_icon = {
                    "done": "✔",
                    "in_progress": "⚡",
                    "pending": "○"
                }.get(subtask_status, "○")
                
                subtask_node = task_node.add(f"  {subtask_icon} {subtask_name}", expand=False)
                subtask_node.data = {"type": "subtask", "id": subtask_id, "status": subtask_status}
    
    def get_selected_task(self) -> Optional[Dict[str, Any]]:
        """Get the currently selected task."""
        selected = self.hover_node
        if selected and selected.data:
            task_id = selected.data.get("id")
            return next((t for t in self.tasks if t.get("id") == task_id), None)
        return None


class GateController(Container):
    """Approval buttons panel for task gates."""
    
    def __init__(self, task_id: Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_id = task_id
    
    def compose(self):
        """Compose the gate controller."""
        with Horizontal():
            yield Button("✅ Approve", id="approve-btn", variant="success")
            yield Button("❌ Reject", id="reject-btn", variant="error")
            yield Button("💬 Feedback", id="feedback-btn", variant="default")
    
    @on(Button.Pressed, "#approve-btn")
    def on_approve(self):
        """Handle approve button press."""
        self.post_message(GateController.Approved(self.task_id))
    
    @on(Button.Pressed, "#reject-btn")
    def on_reject(self):
        """Handle reject button press."""
        self.post_message(GateController.Rejected(self.task_id))
    
    @on(Button.Pressed, "#feedback-btn")
    def on_feedback(self):
        """Handle feedback button press."""
        self.post_message(GateController.FeedbackRequested(self.task_id))


# Message classes for GateController (using Textual's Message class)
class Approved(Message):
    """Message sent when task is approved."""
    def __init__(self, task_id: Optional[str]):
        super().__init__()
        self.task_id = task_id


class Rejected(Message):
    """Message sent when task is rejected."""
    def __init__(self, task_id: Optional[str]):
        super().__init__()
        self.task_id = task_id


class FeedbackRequested(Message):
    """Message sent when feedback is requested."""
    def __init__(self, task_id: Optional[str]):
        super().__init__()
        self.task_id = task_id


# Attach message classes to GateController for easier access
GateController.Approved = Approved
GateController.Rejected = Rejected
GateController.FeedbackRequested = FeedbackRequested


class WorkerSquadProgress(Static):
    """Displays Worker Squad progress through stages."""
    
    def __init__(self, task_id: Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_id = task_id
        self.stages = {
            "planner": {"status": "pending", "output": ""},
            "coder": {"status": "pending", "output": ""},
            "test": {"status": "pending", "output": ""},
            "debug": {"status": "pending", "output": "", "iterations": 0},
            "self_review": {"status": "pending", "output": ""},
            "approver": {"status": "pending", "output": "", "decision": "pending"}
        }
    
    def update_stages(self, stages: Dict[str, Any]):
        """Update Worker Squad stages."""
        self.stages.update(stages)
        self.refresh()
    
    def render(self):
        """Render Worker Squad progress."""
        lines = []
        lines.append(f"[bold]Worker Squad Progress[/]")
        if self.task_id:
            lines.append(f"Task: {self.task_id}")
        lines.append("")
        
        stage_order = ["planner", "coder", "test", "debug", "self_review", "approver"]
        stage_names = {
            "planner": "📋 Planner",
            "coder": "💻 Coder",
            "test": "🧪 Test",
            "debug": "🐛 Debug",
            "self_review": "🔍 Self Review",
            "approver": "✅ Approver"
        }
        
        for stage in stage_order:
            stage_data = self.stages.get(stage, {})
            status = stage_data.get("status", "pending")
            stage_name = stage_names.get(stage, stage.title())
            
            status_icon = {
                "completed": "✅",
                "in_progress": "⚡",
                "failed": "❌",
                "pending": "⏳",
                "approved": "✅",
                "rejected": "❌"
            }.get(status, "⏳")
            
            line = f"{status_icon} {stage_name}: {status}"
            
            # Add iteration count for debug
            if stage == "debug" and stage_data.get("iterations", 0) > 0:
                line += f" (iterations: {stage_data['iterations']})"
            
            # Add decision for approver
            if stage == "approver" and stage_data.get("decision") != "pending":
                decision = stage_data.get("decision", "pending")
                line += f" - {decision}"
            
            lines.append(line)
        
        return "\n".join(lines)


class TaskManagementWidget(Container):
    """Task management controls (cancel, rollback, approve)."""
    
    def __init__(self, task_id: Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_id = task_id
    
    def compose(self):
        """Compose task management controls."""
        with Vertical():
            yield Label(f"Task: {self.task_id or 'No task selected'}", id="task-label")
            with Horizontal():
                yield Button("🚫 Cancel", id="cancel-btn", variant="error")
                yield Button("↩️ Rollback", id="rollback-btn", variant="warning")
                yield Button("✅ Complete", id="complete-btn", variant="success")
    
    @on(Button.Pressed, "#cancel-btn")
    def on_cancel(self):
        """Handle cancel button press."""
        self.post_message(TaskManagementWidget.Cancelled(self.task_id))
    
    @on(Button.Pressed, "#rollback-btn")
    def on_rollback(self):
        """Handle rollback button press."""
        self.post_message(TaskManagementWidget.RollbackRequested(self.task_id))
    
    @on(Button.Pressed, "#complete-btn")
    def on_complete(self):
        """Handle complete button press."""
        self.post_message(TaskManagementWidget.Completed(self.task_id))


# Message classes for TaskManagementWidget
class Cancelled(Message):
    """Message sent when task is cancelled."""
    def __init__(self, task_id: Optional[str]):
        super().__init__()
        self.task_id = task_id


class RollbackRequested(Message):
    """Message sent when task rollback is requested."""
    def __init__(self, task_id: Optional[str]):
        super().__init__()
        self.task_id = task_id


class Completed(Message):
    """Message sent when task is completed."""
    def __init__(self, task_id: Optional[str]):
        super().__init__()
        self.task_id = task_id


# Attach message classes to TaskManagementWidget
TaskManagementWidget.Cancelled = Cancelled
TaskManagementWidget.RollbackRequested = RollbackRequested
TaskManagementWidget.Completed = Completed


class SprintApprovalWidget(Container):
    """Approval buttons panel for sprint gates."""
    
    def __init__(self, sprint_id: Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sprint_id = sprint_id
    
    def compose(self):
        """Compose the sprint approval widget."""
        with Vertical():
            yield Label(f"Sprint: {self.sprint_id or 'No sprint selected'}", id="sprint-label")
            with Horizontal():
                yield Button("✅ Approve Sprint", id="approve-sprint-btn", variant="success")
                yield Button("❌ Reject Sprint", id="reject-sprint-btn", variant="error")
                yield Button("⚡ Start Sprint", id="start-sprint-btn", variant="primary")
    
    @on(Button.Pressed, "#approve-sprint-btn")
    def on_approve(self):
        """Handle approve button press."""
        self.post_message(SprintApprovalWidget.Approved(self.sprint_id))
    
    @on(Button.Pressed, "#reject-sprint-btn")
    def on_reject(self):
        """Handle reject button press."""
        self.post_message(SprintApprovalWidget.Rejected(self.sprint_id))
        
    @on(Button.Pressed, "#start-sprint-btn")
    def on_start(self):
        """Handle start button press."""
        self.post_message(SprintApprovalWidget.Started(self.sprint_id))


class PermissionApprovalWidget(Container):
    """Approval widget for permission requests (permission="ask")."""
    
    def __init__(self, request_id: Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_id = request_id
        self.request_data: Optional[Dict[str, Any]] = None
    
    def compose(self):
        """Compose the permission approval widget."""
        with Vertical():
            yield Label("Permission Approval Required", id="permission-label")
            yield Static("", id="permission-details")
            with Horizontal():
                yield Button("✅ Approve", id="permission-approve-btn", variant="success")
                yield Button("❌ Deny", id="permission-deny-btn", variant="error")
    
    def set_request(self, request_data: Dict[str, Any]):
        """Set the permission request data to display.
        
        Args:
            request_data: Dictionary with request details including:
                - permission_type: Type of permission (edit, write, bash, etc.)
                - resource: Resource being accessed
                - agent_type: Type of agent requesting
                - tool_name: Name of the tool
        """
        self.request_data = request_data
        self.request_id = request_data.get("id")
        
        # Update display
        details = self.query_one("#permission-details", Static)
        permission_type = request_data.get("permission_type", "unknown")
        resource = request_data.get("resource", "unknown")
        agent_type = request_data.get("agent_type", "unknown")
        tool_name = request_data.get("tool_name", "unknown")
        
        details.update(
            f"[bold]Agent:[/] {agent_type}\n"
            f"[bold]Tool:[/] {tool_name}\n"
            f"[bold]Permission:[/] {permission_type}\n"
            f"[bold]Resource:[/] {resource}"
        )
    
    @on(Button.Pressed, "#permission-approve-btn")
    def on_approve(self):
        """Handle approve button press."""
        if self.request_id:
            self.post_message(PermissionApprovalWidget.Approved(self.request_id))
    
    @on(Button.Pressed, "#permission-deny-btn")
    def on_deny(self):
        """Handle deny button press."""
        if self.request_id:
            self.post_message(PermissionApprovalWidget.Denied(self.request_id))


# Message classes for PermissionApprovalWidget
class PermissionApproved(Message):
    """Message sent when permission is approved."""
    def __init__(self, request_id: str):
        super().__init__()
        self.request_id = request_id


class PermissionDenied(Message):
    """Message sent when permission is denied."""
    def __init__(self, request_id: str):
        super().__init__()
        self.request_id = request_id


# Attach message classes to PermissionApprovalWidget
PermissionApprovalWidget.Approved = PermissionApproved
PermissionApprovalWidget.Denied = PermissionDenied


class SprintApproved(Message):
    """Message sent when sprint is approved."""
    def __init__(self, sprint_id: Optional[str]):
        super().__init__()
        self.sprint_id = sprint_id


class SprintRejected(Message):
    """Message sent when sprint is rejected."""
    def __init__(self, sprint_id: Optional[str]):
        super().__init__()
        self.sprint_id = sprint_id


class SprintStarted(Message):
    """Message sent when sprint is started."""
    def __init__(self, sprint_id: Optional[str]):
        super().__init__()
        self.sprint_id = sprint_id


# Attach message classes to SprintApprovalWidget
SprintApprovalWidget.Approved = SprintApproved
SprintApprovalWidget.Rejected = SprintRejected
SprintApprovalWidget.Started = SprintStarted