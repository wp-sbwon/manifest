"""
Project View - Integrated view for Tasks and History.
"""
from textual.widgets import Tree, Static, RichLog
from textual.containers import Vertical, Horizontal
from textual import on
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime


class ProjectView(Vertical):
    """Integrated view showing Tasks and History."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tasks: List[Dict[str, Any]] = []
        self.sprints: List[Dict[str, Any]] = []
        self.history: List[Dict[str, Any]] = []
    
    def load_tasks(self, tasks: List[Dict[str, Any]]):
        """Load tasks data."""
        self.tasks = tasks
        self._update_tasks_display()
    
    def load_sprints(self, sprints: List[Dict[str, Any]]):
        """Load sprints data."""
        self.sprints = sprints
        self._update_sprints_display()
    
    def load_history(self, history: List[Dict[str, Any]]):
        """Load history data."""
        self.history = history
        self._update_history_display()
    
    def _update_tasks_display(self):
        """Update tasks display."""
        # This will be implemented with actual Tree widget
        pass
    
    def _update_sprints_display(self):
        """Update sprints display."""
        # This will be implemented with actual Tree widget
        pass
    
    def _update_history_display(self):
        """Update history display."""
        # This will be implemented with actual RichLog widget
        pass


class TaskTreeView(Tree):
    """Tree view for tasks."""
    
    def __init__(self, *args, **kwargs):
        super().__init__("Tasks", *args, **kwargs)
        self.tasks: List[Dict[str, Any]] = []
    
    def load_tasks(self, tasks: List[Dict[str, Any]]):
        """Load tasks into tree."""
        self.tasks = tasks
        self.clear()
        root = self.root
        
        # Group tasks by sprint
        tasks_by_sprint: Dict[str, List[Dict[str, Any]]] = {}
        for task in tasks:
            sprint_id = task.get("sprint_id", "unsorted")
            if sprint_id not in tasks_by_sprint:
                tasks_by_sprint[sprint_id] = []
            tasks_by_sprint[sprint_id].append(task)
        
        # Add sprint nodes
        for sprint_id, sprint_tasks in tasks_by_sprint.items():
            sprint_label = f"Sprint: {sprint_id}" if sprint_id != "unsorted" else "Unsorted Tasks"
            sprint_node = root.add(sprint_label, expand=True)
            sprint_node.data = {"type": "sprint", "id": sprint_id}
            
            # Add tasks
            for task in sprint_tasks:
                task_id = task.get("id", "")
                task_desc = task.get("description", "Unknown Task")
                task_status = task.get("status", "pending")
                
                # Status icon
                status_icon = {
                    "pending": "⏳",
                    "in_progress": "⚡",
                    "done": "✅",
                    "blocked": "🚫",
                    "cancelled": "❌"
                }.get(task_status, "○")
                
                task_label = f"{status_icon} {task_id}: {task_desc[:50]}"
                task_node = sprint_node.add(task_label, expand=False)
                task_node.data = {
                    "type": "task",
                    "id": task_id,
                    "status": task_status,
                    "task": task
                }
                
                # Add worker squad stages if available
                worker_squad_stages = task.get("worker_squad_stages", {})
                if worker_squad_stages:
                    stages_node = task_node.add("Worker Squad Stages", expand=False)
                    for stage_name, stage_data in worker_squad_stages.items():
                        stage_status = stage_data.get("status", "pending")
                        stage_icon = "✅" if stage_status == "completed" else "⏳"
                        stage_label = f"{stage_icon} {stage_name}"
                        stages_node.add(stage_label, expand=False)
        
        root.expand()


class SprintStatusView(Static):
    """View showing sprint status and progress."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sprints: List[Dict[str, Any]] = []
    
    def load_sprints(self, sprints: List[Dict[str, Any]]):
        """Load sprints data."""
        self.sprints = sprints
        self.refresh()
    
    def render(self) -> str:
        """Render sprint status."""
        if not self.sprints:
            return "No sprints available"
        
        lines = []
        for sprint in self.sprints:
            sprint_id = sprint.get("id", "")
            sprint_name = sprint.get("name", f"Sprint {sprint_id}")
            sprint_status = sprint.get("status", "pending")
            
            # Count tasks
            tasks = sprint.get("tasks", [])
            total_tasks = len(tasks)
            completed_tasks = len([t for t in tasks if t.get("status") == "done"])
            
            completion = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            
            status_icon = {
                "pending": "⏳",
                "in_progress": "⚡",
                "done": "✅",
                "cancelled": "❌"
            }.get(sprint_status, "○")
            
            lines.append(f"{status_icon} {sprint_name}: {completed_tasks}/{total_tasks} tasks ({completion:.1f}%)")
        
        return "\n".join(lines) if lines else "No sprints"


class HistoryView(RichLog):
    """View showing project history."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.history: List[Dict[str, Any]] = []
    
    def load_history(self, history: List[Dict[str, Any]]):
        """Load history data."""
        self.history = history
        self.clear()
        
        # Sort by timestamp (newest first)
        sorted_history = sorted(
            history,
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )
        
        for entry in sorted_history[:50]:  # Show last 50 entries
            timestamp = entry.get("timestamp", "")
            action = entry.get("action", "")
            details = entry.get("details", "")
            
            # Format timestamp
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                time_str = timestamp
            
            self.write(f"[dim]{time_str}[/] [bold]{action}[/] {details}")
