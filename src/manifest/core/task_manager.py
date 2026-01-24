"""
Task Manager - Manages task operations.
Separated from StateManager to improve maintainability.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from manifest.core.state_manager import StateManager
from manifest.core.types import TaskDict
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class TaskManager:
    """Manages task operations."""
    
    def __init__(self, state_manager: StateManager):
        """
        Initialize Task Manager.
        
        Args:
            state_manager: StateManager instance
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
        """
        Create a new task (Orchestrator-controlled).
        
        Args:
            name: Task name
            description: Task description
            stage: Task stage (planning, implementation, testing, review, pending)
            status: Task status (pending, in_progress, done, blocked, approved, cancelled)
            sprint_id: Optional Sprint ID this task belongs to
            
        Returns:
            Task ID
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
        """Update task properties."""
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
        """Cancel a task."""
        tasks = self.state_manager.get_task_checklist()
        for task in tasks:
            if task.get("id") == task_id:
                task["status"] = "cancelled"
                task["updated_at"] = datetime.now().isoformat()
                self.state_manager.set_task_checklist(tasks)
                return True
        return False
    
    def rollback_task(self, task_id: str) -> bool:
        """Rollback a task to previous stage and revert code changes."""
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
        """Mark task as completely done (after user approval)."""
        tasks = self.state_manager.get_task_checklist()
        for task in tasks:
            if task.get("id") == task_id:
                task["status"] = "completed"
                task["stage"] = "completed"
                task["updated_at"] = datetime.now().isoformat()
                task["completed_at"] = datetime.now().isoformat()
                
                # Save Git diff when task is completed
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
        """
        Find tasks matching criteria.
        
        Args:
            status: Filter by status (pending, in_progress, done, blocked, approved, cancelled)
            stage: Filter by stage (planning, implementation, testing, review, pending)
            sprint_id: Filter by sprint ID
            agent_type: Filter by agent type (planner, coder, test, etc.)
            
        Returns:
            List of matching tasks
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
        """
        Delete a task.
        
        Args:
            task_id: Task ID to delete
            
        Returns:
            True if task was deleted, False if not found
        """
        tasks = self.state_manager.get_task_checklist()
        original_count = len(tasks)
        tasks = [t for t in tasks if t.get("id") != task_id]
        
        if len(tasks) < original_count:
            self.state_manager.set_task_checklist(tasks)
            return True
        return False
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific task by ID.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task dictionary or None if not found
        """
        tasks = self.state_manager.get_task_checklist()
        return next((t for t in tasks if t.get("id") == task_id), None)
    
    def save_worker_squad_stage(
        self,
        task_id: str,
        stage: str,
        stage_result: Dict[str, Any]
    ) -> bool:
        """
        Save Worker Squad stage result.
        
        Args:
            task_id: Task ID
            stage: Stage name (planner, tdd_test, coder, test, debug, self_review, approver)
            stage_result: Stage result dictionary
            
        Returns:
            True if saved successfully
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
        """Save Worker Squad stage result asynchronously."""
        result = self.save_worker_squad_stage(task_id, stage, stage_result)
        if result:
            await self.state_manager.save_state()
        return result
    
    def get_task_git_diff(self, task_id: str) -> Optional[str]:
        """
        Get Git diff for a task.
        
        Args:
            task_id: Task ID
            
        Returns:
            Git diff string or None if Git is not available or no changes
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
        """
        Save Git diff for a task.
        
        Args:
            task_id: Task ID
            
        Returns:
            True if saved successfully
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
