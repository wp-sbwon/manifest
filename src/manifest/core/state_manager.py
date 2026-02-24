"""
State persistence and management for Manifest.

Core state: mission tree, task checklist, chat history. State is stored in JSON
in .manifest. Delegates to SprintManager (sprints), PRDManager, TaskManager.
"""
import json
import aiofiles
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from manifest.core.logger import get_logger
from manifest.core.constants import STATE_FILE

logger = get_logger(__name__)


class StateManager:
    """Manages application state persistence and resumption.

    This class is responsible for loading, saving, and managing all application
    state including tasks, sprints, PRD, and chat history. State is persisted
    to disk in JSON format and can be accessed synchronously or asynchronously.

    Attributes:
        manifest_dir: Directory where state files are stored (default: .manifest)
        state_file: Path to the main state.json file
        _state: Internal state dictionary (loaded from disk on initialization)

    """

    def __init__(self, manifest_dir: Path = None):
        """Initialize the state manager.

        Sets up the state directory and loads existing state from disk if
        available. If no state file exists, initializes with default empty state.

        Args:
            manifest_dir: Optional path to the manifest directory. If not provided,
                defaults to .manifest in the current directory.
        """
        self.manifest_dir = manifest_dir or Path(".manifest")
        self.state_file = self.manifest_dir / STATE_FILE
        self._state: Dict[str, Any] = {}
        self._load_state()

    def _load_state(self) -> None:
        """Load state from file synchronously.

        Attempts to load state from state.json. If the file doesn't exist or
        loading fails (corrupted file, permission issues, etc.), initializes
        with default empty state instead of raising an exception.
        """
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    self._state = json.load(f)
            except Exception as e:
                logger.debug("state_manager load failed: %s", e)
                self._state = self._default_state()
        else:
            self._state = self._default_state()

    def _default_state(self) -> Dict[str, Any]:
        """Create and return a default empty state structure.

        Returns:
            Dictionary with default state structure containing empty mission tree,
            task checklist, chat history, and current timestamp.
        """
        return {
            "version": "1.0",
            "mission_tree": {},
            "task_checklist": [],
            "active_task_ids": [],
            "health_metrics": None,
            "chat_history": {},
            "last_action": "",
            "timestamp": datetime.now().isoformat()
        }

    async def load_state_async(self) -> Dict[str, Any]:
        """Load state from file asynchronously.

        Uses aiofiles for non-blocking file I/O. This is useful when loading
        state in async contexts to avoid blocking the event loop.

        Returns:
            Dictionary containing the loaded state, or default state if loading
            fails or file doesn't exist.
        """
        if self.state_file.exists():
            try:
                async with aiofiles.open(self.state_file, "r") as f:
                    content = await f.read()
                    self._state = json.loads(content)
                    return self._state
            except Exception as e:
                logger.debug("state_manager load_async failed: %s", e)
                self._state = self._default_state()
                return self._state
        else:
            self._state = self._default_state()
            return self._state

    def get_state(self) -> Dict[str, Any]:
        """Get a copy of the current state.

        Returns a shallow copy to prevent external modifications from affecting
        the internal state directly.

        Returns:
            Copy of the current state dictionary.
        """
        return self._state.copy()

    def get_mission_tree(self) -> Dict[str, Any]:
        """Get the mission tree structure.

        Returns:
            Dictionary containing the mission tree, or empty dict if not set.
        """
        return self._state.get("mission_tree", {})

    def get_task_checklist(self) -> list:
        """Get the list of all tasks.

        Returns:
            List of task dictionaries, or empty list if no tasks exist.
        """
        return self._state.get("task_checklist", [])

    def get_chat_history(self, channel: str = "main") -> list:
        """Get chat message history for a specific channel.

        Args:
            channel: Name of the channel to retrieve history for. Defaults to
                "main" if not specified.

        Returns:
            List of chat messages for the channel, or empty list if channel
            doesn't exist or has no messages.
        """
        return self._state.get("chat_history", {}).get(channel, [])

    def get_last_action(self) -> str:
        """Get the last recorded action.

        Returns:
            String describing the last action, or empty string if no action
            has been recorded.
        """
        return self._state.get("last_action", "")

    def set_mission_tree(self, tree: Dict[str, Any]) -> None:
        """Set the mission tree structure.

        Args:
            tree: Dictionary containing the mission tree structure to store.
        """
        self._state["mission_tree"] = tree
        self._state["timestamp"] = datetime.now().isoformat()

    def set_task_checklist(self, checklist: list) -> None:
        """Set the task checklist.

        Args:
            checklist: List of task dictionaries to store.
        """
        self._state["task_checklist"] = checklist
        self._state["timestamp"] = datetime.now().isoformat()

    def get_active_task_ids(self) -> list:
        """Task IDs that currently have an active agent (for observed status)."""
        return list(self._state.get("active_task_ids", []) or [])

    def set_active_task_ids(self, task_ids: list) -> None:
        """Set which task IDs currently have an active agent (persisted for View)."""
        self._state["active_task_ids"] = list(task_ids) if task_ids is not None else []
        self._state["timestamp"] = datetime.now().isoformat()

    def get_health_metrics(self) -> Optional[Dict[str, Any]]:
        """Project health from bottom-up (code_quality, test_coverage, binary_size). Updated when bottom-up runs."""
        return self._state.get("health_metrics")

    def set_health_metrics(self, metrics: Optional[Dict[str, Any]]) -> None:
        """Set project health metrics (from bottom-up). Call save_state_sync() to persist."""
        self._state["health_metrics"] = metrics
        self._state["timestamp"] = datetime.now().isoformat()

    def add_chat_message(self, channel: str, role: str, content: str) -> None:
        """Add a chat message to the history for a specific channel.

        Creates the channel if it doesn't exist. Automatically adds a timestamp
        to the message and updates the state timestamp.

        Args:
            channel: Name of the channel to add the message to.
            role: Role of the message sender (e.g., "user", "assistant").
            content: Text content of the message.
        """
        if "chat_history" not in self._state:
            self._state["chat_history"] = {}
        if channel not in self._state["chat_history"]:
            self._state["chat_history"][channel] = []

        self._state["chat_history"][channel].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self._state["timestamp"] = datetime.now().isoformat()

    def set_last_action(self, action: str) -> None:
        """Record the last action performed.

        Args:
            action: String description of the action to record.
        """
        self._state["last_action"] = action
        self._state["timestamp"] = datetime.now().isoformat()

    def _prepare_state_for_persist(self) -> str:
        """Update timestamp, ensure dir exists; return JSON string to persist."""
        self._state["timestamp"] = datetime.now().isoformat()
        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        return json.dumps(self._state, indent=2)

    async def save_state(self) -> bool:
        """Save current state to disk asynchronously."""
        try:
            content = self._prepare_state_for_persist()
            async with aiofiles.open(self.state_file, "w") as f:
                await f.write(content)
            return True
        except Exception as e:
            logger.error("Error saving state: %s", e, exc_info=True)
            return False

    def save_state_sync(self) -> bool:
        """Save current state to disk synchronously. Same content as save_state()."""
        try:
            content = self._prepare_state_for_persist()
            with open(self.state_file, "w") as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error("Error saving state: %s", e, exc_info=True)
            return False

    def get_next_action_prompt(self) -> Optional[str]:
        """Generate a prompt string for resuming from the last action.

        Useful for providing context when resuming a session after interruption.

        Returns:
            String prompt if a last action was recorded, None otherwise.
        """
        last_action = self.get_last_action()
        if last_action:
            return f"Resuming from: {last_action}"
        return None

    def clear_state(self) -> None:
        """Clear all state and reset to default empty state.

        This is primarily useful for testing. In production, you typically
        want to preserve state across sessions.
        """
        self._state = self._default_state()

    def get_state_version(self) -> str:
        """Get the version of the state format.

        Returns:
            Version string (defaults to "1.0" if not set).
        """
        return self._state.get("version", "1.0")

    # PRD Management - Delegated to PRDManager
    def get_prd_file(self) -> Path:
        """Get the path to the PRD file.

        Returns:
            Path object pointing to prd.json in the manifest directory.
        """
        return self.manifest_dir / "prd.json"

    def save_prd(self, prd_data: Dict[str, Any]) -> bool:
        """Save PRD data to file. Delegates to PRDManager.

        Args:
            prd_data: Dictionary containing PRD data to save.

        Returns:
            True if save was successful, False otherwise.
        """
        from manifest.core.prd_manager import PRDManager
        prd_manager = PRDManager(self)
        ok, _ = prd_manager.save_prd(prd_data)
        return ok

    async def save_prd_async(self, prd_data: Dict[str, Any]) -> bool:
        """Save PRD data to file asynchronously. Delegates to PRDManager.

        Args:
            prd_data: Dictionary containing PRD data to save.

        Returns:
            True if save was successful, False otherwise.
        """
        from manifest.core.prd_manager import PRDManager
        prd_manager = PRDManager(self)
        ok, _ = await prd_manager.save_prd_async(prd_data)
        return ok

    def load_prd(self) -> Optional[Dict[str, Any]]:
        """Load PRD data from file. Delegates to PRDManager.

        Returns:
            Dictionary containing PRD data if file exists, None otherwise.
        """
        from manifest.core.prd_manager import PRDManager
        prd_manager = PRDManager(self)
        return prd_manager.load_prd()

    async def load_prd_async(self) -> Optional[Dict[str, Any]]:
        """Load PRD data from file asynchronously. Delegates to PRDManager.

        Returns:
            Dictionary containing PRD data if file exists, None otherwise.
        """
        from manifest.core.prd_manager import PRDManager
        prd_manager = PRDManager(self)
        return await prd_manager.load_prd_async()

    # Sprint Management - Delegated to SprintManager
    def get_sprints_dir(self) -> Path:
        return self._sprint_manager().get_sprints_dir()

    def save_sprint(self, sprint_data: Dict[str, Any]) -> bool:
        return self._sprint_manager().save_sprint(sprint_data)

    async def save_sprint_async(self, sprint_data: Dict[str, Any]) -> bool:
        return await self._sprint_manager().save_sprint_async(sprint_data)

    def load_sprint(self, sprint_id: str) -> Optional[Dict[str, Any]]:
        return self._sprint_manager().load_sprint(sprint_id)

    def list_sprints(self) -> List[str]:
        return self._sprint_manager().list_sprints()

    def _sprint_manager(self):
        from manifest.core.sprint_manager import SprintManager
        return SprintManager(self.manifest_dir)

    # Task Management - Delegated to TaskManager
    def create_task(
        self,
        name: str,
        description: str = "",
        stage: str = "planning",
        status: str = "pending",
        sprint_id: Optional[str] = None,
        dependencies: Optional[List[str]] = None
    ) -> str:
        """Create a new task. Delegates to TaskManager.

        Args:
            name: Name of the task.
            description: Optional description of what the task involves.
            stage: Current stage of the task (default: "planning").
            status: Current status of the task (default: "pending").
            sprint_id: Optional ID of the sprint this task belongs to.
            dependencies: Optional list of task IDs that this task depends on.

        Returns:
            String ID of the newly created task.
        """
        from manifest.core.task_manager import TaskManager
        task_manager = TaskManager(self)
        return task_manager.create_task(name, description, stage, status, sprint_id, dependencies)

    def update_task(
        self,
        task_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        stage: Optional[str] = None,
        sprint_id: Optional[str] = None
    ) -> bool:
        """Update properties of an existing task.

        Delegates to TaskManager for implementation. Only provided fields
        will be updated; None values are ignored.

        Args:
            task_id: ID of the task to update.
            name: New name for the task (optional).
            description: New description for the task (optional).
            status: New status for the task (optional).
            stage: New stage for the task (optional).
            sprint_id: Sprint to assign the task to (optional).

        Returns:
            True if task was found and updated, False otherwise.
        """
        from manifest.core.task_manager import TaskManager
        task_manager = TaskManager(self)
        return task_manager.update_task(task_id, name, description, status, stage, sprint_id)

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task by setting its status to "cancelled".

        Delegates to TaskManager for implementation.

        Args:
            task_id: ID of the task to cancel.

        Returns:
            True if task was found and cancelled, False otherwise.
        """
        from manifest.core.task_manager import TaskManager
        task_manager = TaskManager(self)
        return task_manager.cancel_task(task_id)

    def rollback_task(self, task_id: str) -> bool:
        """Rollback to the previous stage in the workflow. Delegates to TaskManager."""
        from manifest.core.task_manager import TaskManager
        task_manager = TaskManager(self)
        return task_manager.rollback_task(task_id)

    def complete_task(self, task_id: str) -> bool:
        """Mark a task as completely done.

        Sets the task status to "completed" and saves the Git diff at the
        time of completion. Delegates to TaskManager for implementation.

        Args:
            task_id: ID of the task to mark as complete.

        Returns:
            True if task was found and marked complete, False otherwise.
        """
        from manifest.core.task_manager import TaskManager
        task_manager = TaskManager(self)
        return task_manager.complete_task(task_id)

    def find_tasks(
        self,
        status: Optional[str] = None,
        stage: Optional[str] = None,
        sprint_id: Optional[str] = None,
        agent_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Find tasks matching the specified criteria.

        All criteria are optional and can be combined. Tasks must match
        all provided criteria to be included in results.

        Args:
            status: Filter by task status (e.g., "pending", "in_progress").
            stage: Filter by task stage (e.g., "planning", "implementation").
            sprint_id: Filter by sprint ID.
            agent_type: Filter by agent type assigned to the task.

        Returns:
            List of task dictionaries matching the criteria.
        """
        from manifest.core.task_manager import TaskManager
        task_manager = TaskManager(self)
        return task_manager.find_tasks(status, stage, sprint_id, agent_type)

    def delete_task(self, task_id: str) -> bool:
        """Delete a task from the checklist.

        Delegates to TaskManager for implementation.

        Args:
            task_id: ID of the task to delete.

        Returns:
            True if task was found and deleted, False otherwise.
        """
        from manifest.core.task_manager import TaskManager
        task_manager = TaskManager(self)
        return task_manager.delete_task(task_id)

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific task by its ID.

        Delegates to TaskManager for implementation.

        Args:
            task_id: ID of the task to retrieve.

        Returns:
            Task dictionary if found, None otherwise.
        """
        from manifest.core.task_manager import TaskManager
        task_manager = TaskManager(self)
        return task_manager.get_task(task_id)

    def is_task_blocked(self, task_id: str) -> tuple:
        """Check if a task is blocked by its dependencies.

        Delegates to TaskManager for implementation.

        Args:
            task_id: ID of the task to check.

        Returns:
            Tuple of (is_blocked, list_of_blocking_task_ids).
        """
        from manifest.core.task_manager import TaskManager
        task_manager = TaskManager(self)
        return task_manager.is_task_blocked(task_id)

    def save_worker_squad_stage(
        self,
        task_id: str,
        stage: str,
        stage_result: Dict[str, Any]
    ) -> bool:
        """Save the result of a Worker Squad stage execution.

        Worker Squad stages include: planner, tdd_test, coder, test, debug,
        self_review, and approver. Delegates to TaskManager for implementation.

        Args:
            task_id: ID of the task this stage belongs to.
            stage: Name of the stage (e.g., "planner", "coder").
            stage_result: Dictionary containing the stage execution results.

        Returns:
            True if save was successful, False otherwise.
        """
        from manifest.core.task_manager import TaskManager
        task_manager = TaskManager(self)
        return task_manager.save_worker_squad_stage(task_id, stage, stage_result)

    async def save_worker_squad_stage_async(
        self,
        task_id: str,
        stage: str,
        stage_result: Dict[str, Any]
    ) -> bool:
        """Save the result of a Worker Squad stage execution asynchronously.

        Worker Squad stages include: planner, tdd_test, coder, test, debug,
        self_review, and approver. Delegates to TaskManager for implementation.

        Args:
            task_id: ID of the task this stage belongs to.
            stage: Name of the stage (e.g., "planner", "coder").
            stage_result: Dictionary containing the stage execution results.

        Returns:
            True if save was successful, False otherwise.
        """
        from manifest.core.task_manager import TaskManager
        task_manager = TaskManager(self)
        return await task_manager.save_worker_squad_stage_async(task_id, stage, stage_result)

    def get_task_git_diff(self, task_id: str) -> Optional[str]:
        """Get the Git diff for a task.

        Retrieves uncommitted changes in the repository. Delegates to
        TaskManager for implementation.

        Args:
            task_id: ID of the task to get diff for.

        Returns:
            Git diff string if available, None if Git is not available or
            there are no changes.
        """
        from manifest.core.task_manager import TaskManager
        task_manager = TaskManager(self)
        return task_manager.get_task_git_diff(task_id)

    def save_task_git_diff(self, task_id: str) -> bool:
        """Save the current Git diff for a task.

        Captures the current uncommitted changes and stores them with the
        task. Delegates to TaskManager for implementation.

        Args:
            task_id: ID of the task to save diff for.

        Returns:
            True if diff was saved successfully, False otherwise.
        """
        from manifest.core.task_manager import TaskManager
        task_manager = TaskManager(self)
        return task_manager.save_task_git_diff(task_id)
