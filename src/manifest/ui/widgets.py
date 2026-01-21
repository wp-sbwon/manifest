"""
Custom Textual widgets for Manifest TUI.
"""
from textual.widgets import Tree, Button, Static, Label
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