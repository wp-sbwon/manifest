"""
Project View - Integrated view for Tasks and History.
"""
from textual.widgets import Tree, Static, RichLog, Input, Select
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual import on
from textual.message import Message
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

    def compose(self):
        """Compose the project view."""
        with VerticalScroll(id="project-scroll"):
            yield Label("PROJECT", classes="side-title")

            # Task Filter Controls
            with Horizontal(id="task-filters"):
                yield Select(
                    [
                        (None, "All Status"),
                        ("pending", "Pending"),
                        ("in_progress", "In Progress"),
                        ("done", "Done"),
                        ("blocked", "Blocked"),
                        ("cancelled", "Cancelled")
                    ],
                    prompt="Filter Status",
                    id="filter-status-select"
                )
                yield Input(placeholder="Search tasks...", id="task-search-input")

            # Tasks Tree
            yield TaskTreeView(id="task-tree-view")
            yield Static("", classes="spacer")

            # Sprint Status
            yield Label("SPRINT STATUS", classes="side-title")
            yield SprintStatusView(id="sprint-status-view")
            yield Static("", classes="spacer")

            # History
            yield Label("HISTORY", classes="side-title")
            yield HistoryView(id="history-view")

    @on(Select.Changed, "#filter-status-select")
    def on_filter_status_changed(self, event: Select.Changed):
        """Handle status filter change."""
        status = event.value
        search = self.query_one("#task-search-input", Input).value
        self.query_one("#task-tree-view", TaskTreeView).apply_filter(status, search)

    @on(Input.Changed, "#task-search-input")
    def on_search_changed(self, event: Input.Changed):
        """Handle search query change."""
        search = event.value
        status = self.query_one("#filter-status-select", Select).value
        self.query_one("#task-tree-view", TaskTreeView).apply_filter(status, search)

    def load_tasks(self, tasks: List[Dict[str, Any]]):
        """Load tasks data."""
        self.tasks = tasks
        try:
            self.query_one("#task-tree-view", TaskTreeView).load_tasks(tasks)
        except Exception:
            pass

    def load_sprints(self, sprints: List[Dict[str, Any]]):
        """Load sprints data."""
        self.sprints = sprints
        try:
            self.query_one("#sprint-status-view", SprintStatusView).load_sprints(sprints)
        except Exception:
            pass

    def load_history(self, history: List[Dict[str, Any]]):
        """Load history data."""
        self.history = history
        try:
            self.query_one("#history-view", HistoryView).load_history(history)
        except Exception:
            pass


class TaskTreeView(Tree):
    """Tree view for tasks."""

    def __init__(self, *args, **kwargs):
        super().__init__("Tasks", *args, **kwargs)
        self.tasks: List[Dict[str, Any]] = []
        self.filter_status: Optional[str] = None
        self.search_query: str = ""

    def load_tasks(self, tasks: List[Dict[str, Any]]):
        """Load tasks into tree."""
        self.tasks = tasks
        self._update_tree()

    def apply_filter(self, status: Optional[str] = None, search: str = ""):
        """Apply filter to tasks."""
        self.filter_status = status
        self.search_query = search.lower()
        self._update_tree()

    def _update_tree(self):
        """Update the tree with filtered tasks."""
        self.clear()
        root = self.root

        # Filter tasks
        filtered_tasks = self.tasks
        if self.filter_status:
            filtered_tasks = [t for t in filtered_tasks if t.get("status") == self.filter_status]
        if self.search_query:
            filtered_tasks = [
                t for t in filtered_tasks
                if self.search_query in t.get("id", "").lower() or
                   self.search_query in t.get("name", "").lower() or
                   self.search_query in t.get("description", "").lower()
            ]

        # Group tasks by sprint
        tasks_by_sprint: Dict[str, List[Dict[str, Any]]] = {}
        for task in filtered_tasks:
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
                task_name = task.get("name", "Unknown Task")
                task_desc = task.get("description", "")
                task_status = task.get("status", "pending")

                # Status icon
                status_icon = {
                    "pending": "⏳",
                    "in_progress": "⚡",
                    "done": "✅",
                    "blocked": "🚫",
                    "cancelled": "❌"
                }.get(task_status, "○")

                # Check if blocked by dependencies
                is_blocked = False
                blocking_info = ""
                dependencies = task.get("dependencies", [])
                if dependencies:
                    # Status is updated by task manager when dependencies block the task
                    blocking_info = f" (deps: {len(dependencies)})"

                # Calculate progress if worker squad stages exist
                worker_squad = task.get("worker_squad", {})
                stages = worker_squad.get("stages", {})
                progress_info = ""
                if stages:
                    completed = sum(1 for s in stages.values() if s.get("status") == "completed")
                    total = len(stages)
                    progress_pct = (completed / total * 100) if total > 0 else 0
                    progress_info = f" [{progress_pct:.0f}%]"

                label = f"{status_icon} {task_id}: {task_name or task_desc[:50]}{progress_info}{blocking_info}"
                task_node = sprint_node.add(label, expand=False)
                task_node.data = {
                    "type": "task",
                    "id": task_id,
                    "status": task_status,
                    "task": task
                }

                # Add worker squad stages if available
                worker_squad_stages = task.get("worker_squad_stages", {})
                if not worker_squad_stages and stages:
                    worker_squad_stages = stages

                if worker_squad_stages:
                    stages_node = task_node.add("Worker Squad Stages", expand=False)
                    stages_node.data = {"type": "stages", "task_id": task_id}

                    # Calculate progress percentage
                    completed_stages = sum(
                        1 for s in worker_squad_stages.values()
                        if s.get("status") == "completed"
                    )
                    total_stages = len(worker_squad_stages)
                    progress_pct = (completed_stages / total_stages * 100) if total_stages > 0 else 0

                    for stage_name, stage_data in worker_squad_stages.items():
                        stage_status = stage_data.get("status", "pending")
                        stage_icon = "✅" if stage_status == "completed" else "⚡" if stage_status == "in_progress" else "⏳"
                        stage_label = f"{stage_icon} {stage_name}: {stage_status}"
                        stage_node = stages_node.add(stage_label, expand=False)
                        stage_node.data = {
                            "type": "stage",
                            "task_id": task_id,
                            "stage_name": stage_name,
                            "stage_status": stage_status
                        }

                    # Add progress indicator
                    progress_label = f"Progress: {progress_pct:.0f}% ({completed_stages}/{total_stages} stages)"
                    progress_node = stages_node.add(progress_label, expand=False)
                    progress_node.data = {"type": "progress", "task_id": task_id, "progress": progress_pct}

        root.expand()

    @on(Tree.NodeSelected)
    def on_task_selected(self, event: Tree.NodeSelected) -> None:
        """Handle task node selection for status changes.

        When a task node is selected, emits a TaskSelected message that
        the app can handle to show task details or allow status changes.

        Args:
            event: Tree node selection event.
        """
        node_data = event.node.data
        if node_data and node_data.get("type") == "task":
            task_id = node_data.get("id")
            task = node_data.get("task", {})
            current_status = node_data.get("status", "pending")

            # Emit message for app to handle
            self.post_message(TaskSelected(task_id, task, current_status))

    @on(Tree.NodeExpanded)
    def on_node_expanded(self, event: Tree.NodeExpanded) -> None:
        """Handle node expansion to show task details.

        When a task node is expanded, shows worker squad stages and
        progress information.

        Args:
            event: Tree node expansion event.
        """
        node_data = event.node.data
        if node_data and node_data.get("type") == "task":
            # Node is already expanded, stages should be visible
            pass


class TaskSelected(Message):
    """Message sent when a task is selected in the tree.

    Attributes:
        task_id: ID of the selected task.
        task: Full task dictionary.
        current_status: Current status of the task.
    """

    def __init__(self, task_id: str, task: Dict[str, Any], current_status: str):
        """Initialize task selected message.

        Args:
            task_id: ID of the selected task.
            task: Full task dictionary.
            current_status: Current status of the task.
        """
        super().__init__()
        self.task_id = task_id
        self.task = task
        self.current_status = current_status


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

            lines.append(f"[@click=select_sprint('{sprint_id}')]{status_icon} {sprint_name}: {completed_tasks}/{total_tasks} tasks ({completion:.1f}%)[/]")

        return "\n".join(lines) if lines else "No sprints"

    def action_select_sprint(self, sprint_id: str) -> None:
        """Handle sprint selection via click."""
        sprint = next((s for s in self.sprints if s.get("id") == sprint_id), None)
        if sprint:
            self.post_message(SprintSelected(sprint_id, sprint))


class SprintSelected(Message):
    """Message sent when a sprint is selected in the view.

    Attributes:
        sprint_id: ID of the selected sprint.
        sprint: Full sprint dictionary.
    """

    def __init__(self, sprint_id: str, sprint: Dict[str, Any]):
        """Initialize sprint selected message.

        Args:
            sprint_id: ID of the selected sprint.
            sprint: Full sprint dictionary.
        """
        super().__init__()
        self.sprint_id = sprint_id
        self.sprint = sprint


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
