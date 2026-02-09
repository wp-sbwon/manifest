"""
OpenCode Sprint Management tool: sprints in .manifest/tasks.json for View sync.

Orchestrator uses this tool to create/list sprints. Sprints are stored in the
same tasks.json file so View can watch one file for tasks + sprints.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from manifest.core.logger import get_logger
from manifest.core.constants import TASKS_FILE

logger = get_logger(__name__)


def _default_data() -> Dict[str, Any]:
    return {"tasks": [], "sprints": []}


class SprintManagementTool:
    """OpenCode tool for sprint management. Uses .manifest/tasks.json (sprints key)."""

    def __init__(self, manifest_dir: Optional[Path] = None):
        self.manifest_dir = (manifest_dir or Path(".manifest")).resolve()
        self._tasks_file = self.manifest_dir / TASKS_FILE

    def _load(self) -> Dict[str, Any]:
        if not self._tasks_file.exists():
            return _default_data()
        try:
            with open(self._tasks_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "sprints" not in data:
                    data["sprints"] = []
                return data
        except Exception as e:
            logger.warning(f"Could not load {self._tasks_file}: {e}")
            return _default_data()

    def _save(self, data: Dict[str, Any]) -> bool:
        try:
            self.manifest_dir.mkdir(parents=True, exist_ok=True)
            with open(self._tasks_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Could not save {self._tasks_file}: {e}", exc_info=True)
            return False

    def create_sprint(
        self,
        name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new sprint. start_date/end_date in YYYY-MM-DD."""
        data = self._load()
        sprints = data.get("sprints", [])
        next_num = len(sprints) + 1
        sprint_id = f"sprint_{next_num:03d}"
        today = datetime.now().strftime("%Y-%m-%d")
        sprint = {
            "id": sprint_id,
            "name": name,
            "status": "active",
            "tasks": [],
            "start_date": start_date or today,
            "end_date": end_date or today,
        }
        sprints.append(sprint)
        data["sprints"] = sprints
        if not self._save(data):
            return {"ok": False, "error": "Failed to save tasks.json", "sprint_id": sprint_id}
        return {"ok": True, "sprint": sprint, "sprint_id": sprint_id}

    def list_sprints(self) -> List[Dict[str, Any]]:
        """List all sprints."""
        data = self._load()
        return data.get("sprints", [])

    def get_sprint(self, sprint_id: str) -> Optional[Dict[str, Any]]:
        """Get sprint by id."""
        data = self._load()
        for s in data.get("sprints", []):
            if s.get("id") == sprint_id:
                return s
        return None

    def update_sprint(
        self,
        sprint_id: str,
        name: Optional[str] = None,
        status: Optional[str] = None,
        task_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Update sprint name, status, or task list."""
        data = self._load()
        for sprint in data.get("sprints", []):
            if sprint.get("id") == sprint_id:
                if name is not None:
                    sprint["name"] = name
                if status is not None:
                    sprint["status"] = status
                if task_ids is not None:
                    sprint["tasks"] = list(task_ids)
                if not self._save(data):
                    return {"ok": False, "error": "Failed to save tasks.json"}
                return {"ok": True, "sprint": sprint}
        return {"ok": False, "error": f"Sprint not found: {sprint_id}"}
