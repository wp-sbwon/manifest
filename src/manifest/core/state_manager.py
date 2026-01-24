"""
State persistence and management for Manifest.

This module handles all state persistence operations including session state,
mission tree, task checklist, chat history, PRD, and Sprint data. State is
stored in JSON format in the .manifest directory and can be loaded/saved
synchronously or asynchronously.

The StateManager serves as the central state repository and delegates
specific operations to specialized managers (TaskManager, PRDManager, etc.)
for better separation of concerns.
"""
import json
import aiofiles
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from manifest.core.logger import get_logger

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
    
    Note:
        Task and PRD operations are delegated to TaskManager and PRDManager
        respectively, but convenience methods are provided here for backward
        compatibility.
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
        self.state_file = self.manifest_dir / "state.json"
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
            except Exception:
                # If loading fails, start with clean state rather than crashing
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
            except Exception:
                # Fall back to default state on any error
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
    
    async def save_state(self) -> bool:
        """Save current state to disk asynchronously.
        
        Updates the timestamp before saving and creates the manifest directory
        if it doesn't exist. Uses aiofiles for non-blocking I/O.
        
        Returns:
            True if save was successful, False otherwise. Errors are logged
            but not raised.
        """
        try:
            self._state["timestamp"] = datetime.now().isoformat()
            self.manifest_dir.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(self.state_file, "w") as f:
                await f.write(json.dumps(self._state, indent=2))
            return True
        except Exception as e:
            logger.error(f"Error saving state: {e}", exc_info=True)
            return False
    
    def save_state_sync(self) -> bool:
        """Save current state to disk synchronously.
        
        Updates the timestamp before saving and creates the manifest directory
        if it doesn't exist. This is a blocking operation.
        
        Returns:
            True if save was successful, False otherwise. Errors are logged
            but not raised.
        """
        try:
            self._state["timestamp"] = datetime.now().isoformat()
            self.manifest_dir.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w") as f:
                json.dump(self._state, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving state: {e}", exc_info=True)
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
        """Save PRD data to file.
        
        This method delegates to PRDManager for the actual implementation.
        Provided here for backward compatibility.
        
        Args:
            prd_data: Dictionary containing PRD data to save.
        
        Returns:
            True if save was successful, False otherwise.
        """
        from manifest.core.prd_manager import PRDManager
        prd_manager = PRDManager(self)
        return prd_manager.save_prd(prd_data)
    
    async def save_prd_async(self, prd_data: Dict[str, Any]) -> bool:
        """Save PRD data to file asynchronously.
        
        This method delegates to PRDManager for the actual implementation.
        Provided here for backward compatibility.
        
        Args:
            prd_data: Dictionary containing PRD data to save.
        
        Returns:
            True if save was successful, False otherwise.
        """
        from manifest.core.prd_manager import PRDManager
        prd_manager = PRDManager(self)
        return await prd_manager.save_prd_async(prd_data)
    
    def load_prd(self) -> Optional[Dict[str, Any]]:
        """Load PRD data from file.
        
        This method delegates to PRDManager for the actual implementation.
        Provided here for backward compatibility.
        
        Returns:
            Dictionary containing PRD data if file exists, None otherwise.
        """
        from manifest.core.prd_manager import PRDManager
        prd_manager = PRDManager(self)
        return prd_manager.load_prd()
    
    async def load_prd_async(self) -> Optional[Dict[str, Any]]:
        """Load PRD data from file asynchronously.
        
        This method delegates to PRDManager for the actual implementation.
        Provided here for backward compatibility.
        
        Returns:
            Dictionary containing PRD data if file exists, None otherwise.
        """
        from manifest.core.prd_manager import PRDManager
        prd_manager = PRDManager(self)
        return await prd_manager.load_prd_async()
    
    # Sprint Management
    def get_sprints_dir(self) -> Path:
        """Get the directory where sprint files are stored.
        
        Returns:
            Path object pointing to the sprints subdirectory.
        """
        return self.manifest_dir / "sprints"
    
    def save_sprint(self, sprint_data: Dict[str, Any]) -> bool:
        """Save sprint data to a file.
        
        Sprint files are stored as sprint-{id}.json in the sprints directory.
        The sprint data structure is normalized to ensure test fields exist
        before saving.
        
        Args:
            sprint_data: Dictionary containing sprint data. Must include an "id"
                field to determine the filename.
        
        Returns:
            True if save was successful, False otherwise. Errors are logged.
        """
        try:
            # Normalize sprint data structure to ensure test fields exist
            sprint_data = self._ensure_sprint_test_structure(sprint_data)
            
            sprints_dir = self.get_sprints_dir()
            sprints_dir.mkdir(parents=True, exist_ok=True)
            sprint_id = sprint_data.get("id", "unknown")
            sprint_file = sprints_dir / f"sprint-{sprint_id}.json"
            with open(sprint_file, "w", encoding="utf-8") as f:
                json.dump(sprint_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error saving Sprint: {e}", exc_info=True)
            return False
    
    async def save_sprint_async(self, sprint_data: Dict[str, Any]) -> bool:
        """Save sprint data to a file asynchronously.
        
        Sprint files are stored as sprint-{id}.json in the sprints directory.
        Uses aiofiles for non-blocking I/O.
        
        Args:
            sprint_data: Dictionary containing sprint data. Must include an "id"
                field to determine the filename.
        
        Returns:
            True if save was successful, False otherwise. Errors are logged.
        """
        try:
            # Normalize sprint data structure to ensure test fields exist
            sprint_data = self._ensure_sprint_test_structure(sprint_data)
            
            sprints_dir = self.get_sprints_dir()
            sprints_dir.mkdir(parents=True, exist_ok=True)
            sprint_id = sprint_data.get("id", "unknown")
            sprint_file = sprints_dir / f"sprint-{sprint_id}.json"
            async with aiofiles.open(sprint_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(sprint_data, indent=2, ensure_ascii=False))
            return True
        except Exception as e:
            logger.error(f"Error saving Sprint: {e}", exc_info=True)
            return False
    
    def load_sprint(self, sprint_id: str) -> Optional[Dict[str, Any]]:
        """Load sprint data from file.
        
        Args:
            sprint_id: Identifier of the sprint to load.
        
        Returns:
            Dictionary containing sprint data if found, None if file doesn't
            exist or loading fails. Errors are logged.
        """
        sprints_dir = self.get_sprints_dir()
        sprint_file = sprints_dir / f"sprint-{sprint_id}.json"
        if not sprint_file.exists():
            return None
        
        try:
            with open(sprint_file, "r", encoding="utf-8") as f:
                sprint_data = json.load(f)
                # Normalize structure for backward compatibility with older files
                return self._ensure_sprint_test_structure(sprint_data)
        except Exception as e:
            logger.error(f"Error loading Sprint: {e}", exc_info=True)
            return None
    
    def _ensure_sprint_test_structure(self, sprint_data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure sprint data has the required test structure.
        
        Normalizes sprint data to include integration_tests and e2e_tests
        sections with all required fields. This ensures backward compatibility
        with older sprint files that might be missing these structures.
        
        Args:
            sprint_data: Sprint data dictionary to normalize.
        
        Returns:
            Modified sprint_data dictionary with test structures ensured.
            The input dictionary is modified in place, but also returned
            for convenience.
        """
        # Initialize integration_tests section if missing
        if "integration_tests" not in sprint_data:
            sprint_data["integration_tests"] = {
                "status": "pending",
                "test_files": [],
                "test_cases": [],
                "test_skeleton": "",
                "test_plan": "",
                "written_at": None,
                "execution_results": []
            }
        else:
            # Fill in any missing fields in existing integration_tests
            integration_tests = sprint_data["integration_tests"]
            if "status" not in integration_tests:
                integration_tests["status"] = "pending"
            if "test_files" not in integration_tests:
                integration_tests["test_files"] = []
            if "test_cases" not in integration_tests:
                integration_tests["test_cases"] = []
            if "execution_results" not in integration_tests:
                integration_tests["execution_results"] = []
        
        # Initialize e2e_tests section if missing
        if "e2e_tests" not in sprint_data:
            sprint_data["e2e_tests"] = {
                "status": "pending",
                "test_files": [],
                "test_cases": [],
                "test_skeleton": "",
                "test_plan": "",
                "written_at": None,
                "execution_results": []
            }
        else:
            # Fill in any missing fields in existing e2e_tests
            e2e_tests = sprint_data["e2e_tests"]
            if "status" not in e2e_tests:
                e2e_tests["status"] = "pending"
            if "test_files" not in e2e_tests:
                e2e_tests["test_files"] = []
            if "test_cases" not in e2e_tests:
                e2e_tests["test_cases"] = []
            if "execution_results" not in e2e_tests:
                e2e_tests["execution_results"] = []
        
        return sprint_data
    
    def list_sprints(self) -> List[str]:
        """List all sprint IDs found in the sprints directory.
        
        Scans the sprints directory for files matching the pattern sprint-*.json
        and extracts the sprint ID from each filename.
        
        Returns:
            Sorted list of sprint ID strings. Returns empty list if sprints
            directory doesn't exist.
        """
        sprints_dir = self.get_sprints_dir()
        if not sprints_dir.exists():
            return []
        
        sprint_ids = []
        for sprint_file in sprints_dir.glob("sprint-*.json"):
            # Extract ID from filename: sprint-{id}.json -> {id}
            sprint_id = sprint_file.stem.replace("sprint-", "")
            sprint_ids.append(sprint_id)
        
        return sorted(sprint_ids)
    
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
        """Create a new task.
        
        Delegates to TaskManager for implementation. Provided here for
        backward compatibility.
        
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
        stage: Optional[str] = None
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
        
        Returns:
            True if task was found and updated, False otherwise.
        """
        from manifest.core.task_manager import TaskManager
        task_manager = TaskManager(self)
        return task_manager.update_task(task_id, name, description, status, stage)
    
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
        """Rollback a task to the previous stage.
        
        Moves the task back one stage in the workflow (e.g., from "testing"
        back to "implementation"). Delegates to TaskManager for implementation.
        
        Args:
            task_id: ID of the task to rollback.
        
        Returns:
            True if task was found and rolled back, False otherwise.
        """
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