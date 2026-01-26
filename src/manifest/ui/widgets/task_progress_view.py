"""
Task Progress View Widget.

Displays detailed progress information for a selected task, including:
- Worker Squad stages progress
- Modified files list
- Git diff information
"""
from typing import Dict, Any, Optional, List
from textual.widgets import Static, RichLog
from textual.containers import Vertical, VerticalScroll
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class TaskProgressView(Vertical):
    """View showing task progress details including stages and modified files."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_task_id: Optional[str] = None
        self.current_task: Optional[Dict[str, Any]] = None

    def compose(self):
        """Compose the widget."""
        with VerticalScroll(id="task-progress-scroll"):
            yield Static("", id="task-progress-header")
            yield Static("", id="task-progress-stages")
            yield Static("", id="task-progress-files")
            yield RichLog(id="task-progress-diff", markup=True, wrap=True)

    def update_task(self, task_id: str, task: Dict[str, Any]) -> None:
        """Update the view with task information.

        Args:
            task_id: ID of the task.
            task: Task dictionary with all task data.
        """
        self.current_task_id = task_id
        self.current_task = task

        try:
            # Update header
            header = self.query_one("#task-progress-header", Static)
            task_name = task.get("name", task_id)
            task_status = task.get("status", "unknown")
            task_desc = task.get("description", "No description")
            header.update(f"[bold cyan]Task: {task_name} ({task_id})[/]\n"
                         f"Status: [bold]{task_status}[/]\n"
                         f"Description: {task_desc[:200]}")

            # Update stages
            self._update_stages(task)

            # Update modified files
            self._update_modified_files(task)

            # Update Git diff
            self._update_git_diff(task_id, task)

        except Exception as e:
            logger.error(f"Error updating task progress view: {e}", exc_info=True)

    def _update_stages(self, task: Dict[str, Any]) -> None:
        """Update Worker Squad stages display.

        Args:
            task: Task dictionary.
        """
        stages_widget = self.query_one("#task-progress-stages", Static)
        worker_squad = task.get("worker_squad", {})
        stages = worker_squad.get("stages", {})

        if not stages:
            stages_widget.update("[dim]No Worker Squad stages available[/]")
            return

        # Calculate progress
        completed = sum(1 for s in stages.values() if s.get("status") == "completed")
        total = len(stages)
        progress_pct = (completed / total * 100) if total > 0 else 0

        lines = [f"[bold]Worker Squad Progress: {progress_pct:.0f}% ({completed}/{total} stages)[/]\n"]

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
            if stage not in stages:
                continue

            stage_data = stages[stage]
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

        stages_widget.update("\n".join(lines))

    def _update_modified_files(self, task: Dict[str, Any]) -> None:
        """Update modified files list.

        Args:
            task: Task dictionary.
        """
        files_widget = self.query_one("#task-progress-files", Static)

        # Collect modified files from all stages
        modified_files = set()
        worker_squad = task.get("worker_squad", {})
        stages = worker_squad.get("stages", {})

        for stage_data in stages.values():
            tool_execution = stage_data.get("tool_execution", {})
            stage_files = tool_execution.get("modified_files", [])
            modified_files.update(stage_files)

        # Also check task-level tool_execution
        tool_execution = task.get("tool_execution", {})
        task_summary = tool_execution.get("last_summary", {})
        task_files = task_summary.get("modified_files", [])
        modified_files.update(task_files)

        if not modified_files:
            files_widget.update("[dim]No modified files tracked for this task[/]")
            return

        lines = [f"[bold]Modified Files ({len(modified_files)}):[/]"]
        for file_path in sorted(modified_files):
            lines.append(f"  • {file_path}")

        files_widget.update("\n".join(lines))

    def _update_git_diff(self, task_id: str, task: Dict[str, Any]) -> None:
        """Update Git diff display.

        Args:
            task_id: ID of the task.
            task: Task dictionary.
        """
        diff_log = self.query_one("#task-progress-diff", RichLog)
        diff_log.clear()

        # Try to get Git diff from task manager
        try:
            from manifest.core.task_manager import TaskManager
            from manifest.core.state_manager import StateManager

            # Get state manager from app reference if available
            app_ref = getattr(self, "app_ref", None)
            if app_ref and hasattr(app_ref, "state_manager"):
                state_manager = app_ref.state_manager
                task_manager = TaskManager(state_manager)
                git_diff = task_manager.get_task_git_diff(task_id)

                if git_diff:
                    diff_log.write("[bold green]Git Diff:[/]")
                    # Truncate very long diffs
                    if len(git_diff) > 5000:
                        diff_log.write(git_diff[:5000] + "\n... (truncated)")
                    else:
                        diff_log.write(git_diff)
                    return
        except Exception as e:
            logger.debug(f"Could not get Git diff from task manager: {e}")

        # Fallback: check stored diff in task changes
        changes = task.get("changes", {})
        stored_diff = changes.get("git_diff")
        if stored_diff:
            diff_log.write("[bold green]Stored Git Diff:[/]")
            if len(stored_diff) > 5000:
                diff_log.write(stored_diff[:5000] + "\n... (truncated)")
            else:
                diff_log.write(stored_diff)
        else:
            diff_log.write("[dim]No Git diff available for this task[/]")
            diff_log.write("[dim]Run 'git diff' manually to see changes[/]")

    def set_app(self, app: Any) -> None:
        """Set reference to app for accessing state manager.

        Args:
            app: ManifestApp instance.
        """
        self.app_ref = app
