import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from manifest.core.logger import get_logger
from manifest.core.constants import STATE_FILE

logger = get_logger(__name__)


class StateManager:
    def __init__(self, manifest_dir: Path = None):
        self.manifest_dir = manifest_dir or Path(".manifest")
        self.state_file = self.manifest_dir / STATE_FILE
        self._state: Dict[str, Any] = {}
        self._load_state()

    def _load_state(self) -> None:
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
        return {
            "version": "1.0",
            "health_metrics": None,
            "chat_history": {},
            "last_action": "",
            "timestamp": datetime.now().isoformat(),
        }

    def get_state(self) -> Dict[str, Any]:
        return self._state.copy()

    def get_chat_history(self, channel: str = "main") -> list:
        return self._state.get("chat_history", {}).get(channel, [])

    def get_health_metrics(self) -> Optional[Dict[str, Any]]:
        return self._state.get("health_metrics")

    def set_health_metrics(self, metrics: Optional[Dict[str, Any]]) -> None:
        self._state["health_metrics"] = metrics
        self._state["timestamp"] = datetime.now().isoformat()

    def add_chat_message(self, channel: str, role: str, content: str) -> None:
        if "chat_history" not in self._state:
            self._state["chat_history"] = {}
        if channel not in self._state["chat_history"]:
            self._state["chat_history"][channel] = []
        self._state["chat_history"][channel].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
        self._state["timestamp"] = datetime.now().isoformat()

    def _prepare_state_for_persist(self) -> str:
        self._state["timestamp"] = datetime.now().isoformat()
        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        return json.dumps(self._state, indent=2)

    def save_state_sync(self) -> bool:
        try:
            content = self._prepare_state_for_persist()
            with open(self.state_file, "w") as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error("Error saving state: %s", e, exc_info=True)
            return False

    def clear_state(self) -> None:
        self._state = self._default_state()

    def get_state_version(self) -> str:
        return self._state.get("version", "1.0")
