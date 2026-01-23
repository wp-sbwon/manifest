"""
State persistence handler for Manifest.
Manages session state, mission tree, task checklist, and chat history.
"""
import json
import aiofiles
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class StateManager:
    """Manages application state persistence and resumption."""
    
    def __init__(self, manifest_dir: Path = None):
        self.manifest_dir = manifest_dir or Path(".manifest")
        self.state_file = self.manifest_dir / "state.json"
        self._state: Dict[str, Any] = {}
        self._load_state()
    
    def _load_state(self):
        """Load state from file synchronously."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    self._state = json.load(f)
            except Exception:
                self._state = self._default_state()
        else:
            self._state = self._default_state()
    
    def _default_state(self) -> Dict[str, Any]:
        """Return default state structure."""
        return {
            "version": "1.0",
            "mission_tree": {},
            "task_checklist": [],
            "chat_history": {},
            "last_action": "",
            "timestamp": datetime.now().isoformat()
        }
    
    async def load_state_async(self) -> Dict[str, Any]:
        """Load state from file asynchronously."""
        if self.state_file.exists():
            try:
                async with aiofiles.open(self.state_file, "r") as f:
                    content = await f.read()
                    self._state = json.loads(content)
                    return self._state
            except Exception:
                self._state = self._default_state()
                return self._state
        else:
            self._state = self._default_state()
            return self._state
    
    def get_state(self) -> Dict[str, Any]:
        """Get current state."""
        return self._state.copy()
    
    def get_mission_tree(self) -> Dict[str, Any]:
        """Get mission tree."""
        return self._state.get("mission_tree", {})
    
    def get_task_checklist(self) -> list:
        """Get task checklist."""
        return self._state.get("task_checklist", [])
    
    def get_chat_history(self, channel: str = "main") -> list:
        """Get chat history for a channel."""
        return self._state.get("chat_history", {}).get(channel, [])
    
    def get_last_action(self) -> str:
        """Get last action."""
        return self._state.get("last_action", "")
    
    def set_mission_tree(self, tree: Dict[str, Any]):
        """Set mission tree."""
        self._state["mission_tree"] = tree
        self._state["timestamp"] = datetime.now().isoformat()
    
    def set_task_checklist(self, checklist: list):
        """Set task checklist."""
        self._state["task_checklist"] = checklist
        self._state["timestamp"] = datetime.now().isoformat()
    
    def add_chat_message(self, channel: str, role: str, content: str):
        """Add a chat message to history."""
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
    
    def set_last_action(self, action: str):
        """Set last action."""
        self._state["last_action"] = action
        self._state["timestamp"] = datetime.now().isoformat()
    
    async def save_state(self) -> bool:
        """Save state to file asynchronously."""
        try:
            self._state["timestamp"] = datetime.now().isoformat()
            self.manifest_dir.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(self.state_file, "w") as f:
                await f.write(json.dumps(self._state, indent=2))
            return True
        except Exception as e:
            print(f"Error saving state: {e}")
            return False
    
    def save_state_sync(self) -> bool:
        """Save state to file synchronously."""
        try:
            self._state["timestamp"] = datetime.now().isoformat()
            self.manifest_dir.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w") as f:
                json.dump(self._state, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving state: {e}")
            return False
    
    def get_next_action_prompt(self) -> Optional[str]:
        """Get a prompt for resuming from last action."""
        last_action = self.get_last_action()
        if last_action:
            return f"Resuming from: {last_action}"
        return None
    
    def clear_state(self):
        """Clear all state (for testing)."""
        self._state = self._default_state()
    
    def get_state_version(self) -> str:
        """Get state version."""
        return self._state.get("version", "1.0")
    
    # PRD Management
    def get_prd_file(self) -> Path:
        """Get PRD file path."""
        return self.manifest_dir / "prd.json"
    
    def save_prd(self, prd_data: Dict[str, Any]) -> bool:
        """Save PRD to file."""
        try:
            prd_file = self.get_prd_file()
            prd_file.parent.mkdir(parents=True, exist_ok=True)
            with open(prd_file, "w", encoding="utf-8") as f:
                json.dump(prd_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving PRD: {e}")
            return False
    
    async def save_prd_async(self, prd_data: Dict[str, Any]) -> bool:
        """Save PRD to file asynchronously."""
        try:
            prd_file = self.get_prd_file()
            prd_file.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(prd_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(prd_data, indent=2, ensure_ascii=False))
            return True
        except Exception as e:
            print(f"Error saving PRD: {e}")
            return False
    
    def load_prd(self) -> Optional[Dict[str, Any]]:
        """Load PRD from file."""
        prd_file = self.get_prd_file()
        if not prd_file.exists():
            return None
        
        try:
            with open(prd_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading PRD: {e}")
            return None
    
    async def load_prd_async(self) -> Optional[Dict[str, Any]]:
        """Load PRD from file asynchronously."""
        prd_file = self.get_prd_file()
        if not prd_file.exists():
            return None
        
        try:
            async with aiofiles.open(prd_file, "r", encoding="utf-8") as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            print(f"Error loading PRD: {e}")
            return None
    
    # Sprint Management
    def get_sprints_dir(self) -> Path:
        """Get sprints directory path."""
        return self.manifest_dir / "sprints"
    
    def save_sprint(self, sprint_data: Dict[str, Any]) -> bool:
        """Save Sprint to file."""
        try:
            sprints_dir = self.get_sprints_dir()
            sprints_dir.mkdir(parents=True, exist_ok=True)
            sprint_id = sprint_data.get("id", "unknown")
            sprint_file = sprints_dir / f"sprint-{sprint_id}.json"
            with open(sprint_file, "w", encoding="utf-8") as f:
                json.dump(sprint_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving Sprint: {e}")
            return False
    
    async def save_sprint_async(self, sprint_data: Dict[str, Any]) -> bool:
        """Save Sprint to file asynchronously."""
        try:
            sprints_dir = self.get_sprints_dir()
            sprints_dir.mkdir(parents=True, exist_ok=True)
            sprint_id = sprint_data.get("id", "unknown")
            sprint_file = sprints_dir / f"sprint-{sprint_id}.json"
            async with aiofiles.open(sprint_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(sprint_data, indent=2, ensure_ascii=False))
            return True
        except Exception as e:
            print(f"Error saving Sprint: {e}")
            return False
    
    def load_sprint(self, sprint_id: str) -> Optional[Dict[str, Any]]:
        """Load Sprint from file."""
        sprints_dir = self.get_sprints_dir()
        sprint_file = sprints_dir / f"sprint-{sprint_id}.json"
        if not sprint_file.exists():
            return None
        
        try:
            with open(sprint_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading Sprint: {e}")
            return None
    
    def list_sprints(self) -> List[str]:
        """List all Sprint IDs."""
        sprints_dir = self.get_sprints_dir()
        if not sprints_dir.exists():
            return []
        
        sprint_ids = []
        for sprint_file in sprints_dir.glob("sprint-*.json"):
            # Extract sprint ID from filename: sprint-{id}.json
            sprint_id = sprint_file.stem.replace("sprint-", "")
            sprint_ids.append(sprint_id)
        
        return sorted(sprint_ids)
    
    # Task Management (Orchestrator-controlled)
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
        tasks = self.get_task_checklist()
        task_id = f"task-{len(tasks) + 1}"
        
        task = {
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
        
        tasks.append(task)
        self.set_task_checklist(tasks)
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
        tasks = self.get_task_checklist()
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
                self.set_task_checklist(tasks)
                return True
        return False
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task."""
        tasks = self.get_task_checklist()
        for task in tasks:
            if task.get("id") == task_id:
                task["status"] = "cancelled"
                task["updated_at"] = datetime.now().isoformat()
                self.set_task_checklist(tasks)
                return True
        return False
    
    def rollback_task(self, task_id: str) -> bool:
        """Rollback a task to previous stage and revert code changes."""
        tasks = self.get_task_checklist()
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
                        self.set_task_checklist(tasks)
                        return True
                except ValueError:
                    pass
        return False
    
    def complete_task(self, task_id: str) -> bool:
        """Mark task as completely done (after user approval)."""
        tasks = self.get_task_checklist()
        for task in tasks:
            if task.get("id") == task_id:
                task["status"] = "completed"
                task["stage"] = "completed"
                task["updated_at"] = datetime.now().isoformat()
                task["completed_at"] = datetime.now().isoformat()
                self.set_task_checklist(tasks)
                return True
        return False
    
    def find_tasks(
        self,
        status: Optional[str] = None,
        stage: Optional[str] = None,
        sprint_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Find tasks matching criteria."""
        tasks = self.get_task_checklist()
        filtered = tasks
        
        if status:
            filtered = [t for t in filtered if t.get("status") == status]
        if stage:
            filtered = [t for t in filtered if t.get("stage") == stage]
        if sprint_id:
            filtered = [t for t in filtered if t.get("sprint_id") == sprint_id]
        
        return filtered