"""
Task management for Manifest.

This module handles all task-related operations including creation, updates,
deletion, and querying. Tasks represent work items that agents execute as
part of sprints. The TaskManager was separated from StateManager to improve
code organization and maintainability.

Tasks go through various stages (planning, implementation, testing, review)
and have statuses (pending, in_progress, done, blocked, etc.). The manager
also handles Worker Squad stage results and Git diff tracking for tasks.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from manifest.core.state_manager import StateManager
from manifest.core.types import TaskDict
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class TaskManager:
    """Manages all task-related operations.
    
    Handles the complete lifecycle of tasks from creation through completion.
    Tasks are stored in the state's task checklist and can be queried,
    updated, and managed through this class.
    
    Attributes:
        state_manager: Reference to the StateManager for persistence.
    """
    
    def __init__(self, state_manager: StateManager):
        """Initialize the task manager.
        
        Args:
            state_manager: StateManager instance used for persisting task data.
        """
        self.state_manager = state_manager
    
    def create_task(
        self,
        name: str,
        description: str = "",
        stage: str = "planning",
        status: str = "pending",
        sprint_id: Optional[str] = None
    ) -> str:
        """Create a new task and add it to the checklist.
        
        Tasks are typically created by the Orchestrator agent when breaking
        down work. The task is assigned a unique ID based on the current
        number of tasks, and timestamps are automatically set.
        
        Args:
            name: Short name or title for the task.
            description: Detailed description of what the task involves.
            stage: Initial stage of the task. Valid values: "planning",
                "implementation", "testing", "review", "pending".
            status: Initial status of the task. Valid values: "pending",
                "in_progress", "done", "blocked", "approved", "cancelled".
            sprint_id: Optional ID of the sprint this task belongs to.
                Tasks can exist outside of sprints if None.
        
        Returns:
            String ID of the newly created task (e.g., "task-1").
        """
        tasks = self.state_manager.get_task_checklist()
        task_id = f"task-{len(tasks) + 1}"
        
        task: TaskDict = {
            "id": task_id,
            "name": name,
            "description": description,
            "status": status,
            "stage": stage,
            "sprint_id": sprint_id,
            "subtasks": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        tasks.append(task)  # type: ignore
        self.state_manager.set_task_checklist(tasks)
        return task_id
    
    def update_task(
        self,
        task_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        stage: Optional[str] = None
    ) -> bool:
        """Update one or more properties of an existing task.
        
        Only the fields provided (non-None) will be updated. The task's
        updated_at timestamp is automatically refreshed.
        
        Args:
            task_id: ID of the task to update.
            name: New name for the task (optional).
            description: New description for the task (optional).
            status: New status for the task (optional).
            stage: New stage for the task (optional).
        
        Returns:
            True if the task was found and updated, False if task doesn't
            exist.
        """
        tasks = self.state_manager.get_task_checklist()
        for task in tasks:
            if task.get("id") == task_id:
                if name is not None:
                    task["name"] = name
                if description is not None:
                    task["description"] = description
                if status is not None:
                    task["status"] = status
                if stage is not None:
                    task["stage"] = stage
                task["updated_at"] = datetime.now().isoformat()
                self.state_manager.set_task_checklist(tasks)
                return True
        return False
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task by setting its status to "cancelled".
        
        Cancelled tasks remain in the checklist but are marked as cancelled
        and typically won't be processed further.
        
        Args:
            task_id: ID of the task to cancel.
        
        Returns:
            True if task was found and cancelled, False otherwise.
        """
        tasks = self.state_manager.get_task_checklist()
        for task in tasks:
            if task.get("id") == task_id:
                task["status"] = "cancelled"
                task["updated_at"] = datetime.now().isoformat()
                self.state_manager.set_task_checklist(tasks)
                return True
        return False
    
    def rollback_task(self, task_id: str) -> bool:
        """Rollback a task to the previous stage in the workflow.
        
        Moves the task back one stage (e.g., from "testing" to "implementation").
        The status is reset to "pending". Note that this only updates the
        state; actual code rollback would be handled by AgentCoordinator
        using Git.
        
        Args:
            task_id: ID of the task to rollback.
        
        Returns:
            True if task was found and rolled back, False otherwise.
        """
        tasks = self.state_manager.get_task_checklist()
        for task in tasks:
            if task.get("id") == task_id:
                # Rollback stage
                current_stage = task.get("stage", "planning")
                stage_order = ["pending", "planning", "implementation", "testing", "review"]
                try:
                    current_index = stage_order.index(current_stage)
                    if current_index > 0:
                        task["stage"] = stage_order[current_index - 1]
                        task["status"] = "pending"
                        task["updated_at"] = datetime.now().isoformat()
                        
                        # Note: Git revert would be handled by AgentCoordinator
                        # This just updates the state
                        self.state_manager.set_task_checklist(tasks)
                        return True
                except ValueError:
                    pass
        return False
    
    def complete_task(self, task_id: str) -> bool:
        """Mark a task as completely done after user approval.
        
        Sets both status and stage to "completed" and records a completion
        timestamp. Also captures the current Git diff to preserve a snapshot
        of what was changed for this task.
        
        Args:
            task_id: ID of the task to mark as complete.
        
        Returns:
            True if task was found and marked complete, False otherwise.
        """
        tasks = self.state_manager.get_task_checklist()
        for task in tasks:
            if task.get("id") == task_id:
                task["status"] = "completed"
                task["stage"] = "completed"
                task["updated_at"] = datetime.now().isoformat()
                task["completed_at"] = datetime.now().isoformat()
                
                # Capture Git diff snapshot when task completes
                self.save_task_git_diff(task_id)
                
                self.state_manager.set_task_checklist(tasks)
                return True
        return False
    
    def find_tasks(
        self,
        status: Optional[str] = None,
        stage: Optional[str] = None,
        sprint_id: Optional[str] = None,
        agent_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Find tasks matching the specified criteria.
        
        All criteria are optional and can be combined. Tasks must match
        all provided criteria to be included in results. If no criteria
        are provided, returns all tasks.
        
        Args:
            status: Filter by task status (e.g., "pending", "in_progress",
                "done", "blocked", "approved", "cancelled").
            stage: Filter by task stage (e.g., "planning", "implementation",
                "testing", "review", "pending").
            sprint_id: Filter by sprint ID. Only tasks belonging to this
                sprint will be returned.
            agent_type: Filter by agent type assigned to the task (e.g.,
                "planner", "coder", "test").
        
        Returns:
            List of task dictionaries matching all provided criteria.
        """
        tasks = self.state_manager.get_task_checklist()
        filtered = tasks
        
        if status:
            filtered = [t for t in filtered if t.get("status") == status]
        if stage:
            filtered = [t for t in filtered if t.get("stage") == stage]
        if sprint_id:
            filtered = [t for t in filtered if t.get("sprint_id") == sprint_id]
        if agent_type:
            filtered = [t for t in filtered if t.get("agent", {}).get("type") == agent_type]
        
        return filtered
    
    def delete_task(self, task_id: str) -> bool:
        """Permanently delete a task from the checklist.
        
        Removes the task from the task checklist. This operation cannot
        be undone, so use with caution.
        
        Args:
            task_id: ID of the task to delete.
        
        Returns:
            True if task was found and deleted, False if task doesn't exist.
        """
        tasks = self.state_manager.get_task_checklist()
        original_count = len(tasks)
        tasks = [t for t in tasks if t.get("id") != task_id]
        
        if len(tasks) < original_count:
            self.state_manager.set_task_checklist(tasks)
            return True
        return False
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific task by its ID.
        
        Args:
            task_id: ID of the task to retrieve.
        
        Returns:
            Task dictionary if found, None if the task doesn't exist.
        """
        tasks = self.state_manager.get_task_checklist()
        return next((t for t in tasks if t.get("id") == task_id), None)
    
    def save_worker_squad_stage(
        self,
        task_id: str,
        stage: str,
        stage_result: Dict[str, Any]
    ) -> bool:
        """Save the result of a Worker Squad stage execution.
        
        Worker Squad stages include: planner, tdd_test, coder, test, debug,
        self_review, and approver. Stage results are stored with the task
        and include timestamps for tracking execution history.
        
        Args:
            task_id: ID of the task this stage belongs to.
            stage: Name of the stage (e.g., "planner", "coder", "test").
            stage_result: Dictionary containing stage execution results,
                including status, output, and any stage-specific data.
        
        Returns:
            True if the stage result was saved successfully, False if the
            task doesn't exist.
        """
        tasks = self.state_manager.get_task_checklist()
        task = next((t for t in tasks if t.get("id") == task_id), None)
        if not task:
            return False
        
        # Initialize worker_squad_stages if not exists
        if "worker_squad_stages" not in task:
            task["worker_squad_stages"] = {}
        
        # Add timestamp to stage result
        stage_result_with_timestamp = {
            **stage_result,
            "timestamp": datetime.now().isoformat()
        }
        
        # Save stage result
        task["worker_squad_stages"][stage] = stage_result_with_timestamp
        
        # Update task updated_at
        task["updated_at"] = datetime.now().isoformat()
        
        self.state_manager.set_task_checklist(tasks)
        return True
    
    async def save_worker_squad_stage_async(
        self,
        task_id: str,
        stage: str,
        stage_result: Dict[str, Any]
    ) -> bool:
        """Save Worker Squad stage result asynchronously.
        
        Same as save_worker_squad_stage but also persists state to disk
        asynchronously after saving the stage result.
        
        Args:
            task_id: ID of the task this stage belongs to.
            stage: Name of the stage.
            stage_result: Dictionary containing stage execution results.
        
        Returns:
            True if saved successfully, False otherwise.
        """
        result = self.save_worker_squad_stage(task_id, stage, stage_result)
        if result:
            await self.state_manager.save_state()
        return result
    
    def get_task_git_diff(self, task_id: str) -> Optional[str]:
        """Get the current Git diff for uncommitted changes.
        
        Executes git diff to retrieve uncommitted changes in the repository.
        Checks both unstaged and staged changes. This is useful for capturing
        what code was modified for a task.
        
        Args:
            task_id: ID of the task (used for context, not directly in Git command).
        
        Returns:
            Git diff string if changes exist and Git is available, None if
            Git is not available, not a Git repository, or there are no changes.
        """
        import subprocess
        try:
            # Check if Git is available
            manifest_dir = self.state_manager.manifest_dir
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=manifest_dir.parent if manifest_dir.parent.exists() else Path.cwd()
            )
            
            if result.returncode != 0:
                # Git not available or not a Git repository
                return None
            
            # Get diff of unstaged changes
            diff_result = subprocess.run(
                ["git", "diff"],
                capture_output=True,
                text=True,
                cwd=manifest_dir.parent if manifest_dir.parent.exists() else Path.cwd()
            )
            
            if diff_result.returncode == 0 and diff_result.stdout.strip():
                return diff_result.stdout
            else:
                # Try staged changes
                diff_staged_result = subprocess.run(
                    ["git", "diff", "--staged"],
                    capture_output=True,
                    text=True,
                    cwd=manifest_dir.parent if manifest_dir.parent.exists() else Path.cwd()
                )
                
                if diff_staged_result.returncode == 0 and diff_staged_result.stdout.strip():
                    return diff_staged_result.stdout
            
            return None
        except Exception:
            # Git not available or error
            return None
    
    def save_task_git_diff(self, task_id: str) -> bool:
        """Capture and save the current Git diff for a task.
        
        Retrieves the current uncommitted changes using get_task_git_diff
        and stores them with the task. This creates a snapshot of what code
        was changed, which is useful when the task is completed.
        
        Args:
            task_id: ID of the task to save diff for.
        
        Returns:
            True if the task was found and diff was saved, False otherwise.
        """
        tasks = self.state_manager.get_task_checklist()
        task = next((t for t in tasks if t.get("id") == task_id), None)
        if not task:
            return False
        
        # Get Git diff
        git_diff = self.get_task_git_diff(task_id)
        
        # Initialize changes if not exists
        if "changes" not in task:
            task["changes"] = {}
        
        # Save Git diff
        task["changes"]["git_diff"] = git_diff
        task["changes"]["git_diff_timestamp"] = datetime.now().isoformat()
        
        # Update task
        task["updated_at"] = datetime.now().isoformat()
        self.state_manager.set_task_checklist(tasks)
        return True
