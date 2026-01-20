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