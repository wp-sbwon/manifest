"""
OpenCode Task Management tool: .manifest/tasks.json for real-time View sync.

Orchestrator uses this tool to create/update tasks and progress. View watches
.manifest/tasks.json and updates Task View in real time.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from manifest.core.logger import get_logger
from manifest.core.constants import TASKS_FILE
from manifest.core.task_constants import TASK_STATUSES, TASK_STAGES

logger = get_logger(__name__)
VALID_STATUSES = TASK_STATUSES
VALID_STAGES = TASK_STAGES


def _default_tasks_data() -> Dict[str, Any]:
    return {"tasks": [], "sprints": []}


class TaskManagementTool:
    """OpenCode tool for task management. Updates .manifest/tasks.json."""

    def __init__(self, manifest_dir: Optional[Path] = None):
        self.manifest_dir = (manifest_dir or Path(".manifest")).resolve()
        self._tasks_file = self.manifest_dir / TASKS_FILE

    def _load(self) -> Dict[str, Any]:
        if not self._tasks_file.exists():
            return _default_tasks_data()
        try:
            with open(self._tasks_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load {self._tasks_file}: {e}")
            return _default_tasks_data()

    def _save(self, data: Dict[str, Any]) -> bool:
        try:
            self.manifest_dir.mkdir(parents=True, exist_ok=True)
            with open(self._tasks_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Could not save {self._tasks_file}: {e}", exc_info=True)
            return False

    def create_task(
        self,
        name: str,
        sprint_id: Optional[str] = None,
        blueprint_entity_ids: Optional[List[str]] = None,
        mission_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new task. Updates .manifest/tasks.json; View can watch for changes."""
        data = self._load()
        tasks = data.get("tasks", [])
        next_num = len(tasks) + 1
        task_id = f"task_{next_num:03d}"
        now = datetime.now().isoformat() + "Z"
        task = {
            "id": task_id,
            "name": name,
            "status": "pending",
            "stage": "planning",
            "assigned_agent": None,
            "sprint_id": sprint_id,
            "mission_id": mission_id,
            "blueprint_entity_ids": blueprint_entity_ids or [],
            "created_at": now,
            "updated_at": now,
            "progress": {"percentage": 0, "last_update": now},
        }
        tasks.append(task)
        data["tasks"] = tasks
        if not self._save(data):
            return {"ok": False, "error": "Failed to save tasks.json", "task_id": task_id}
        return {"ok": True, "task": task, "task_id": task_id}

    def update_task_status(self, task_id: str, status: str) -> Dict[str, Any]:
        """Update task status. Valid: pending, in_progress, paused, blocked, completed, cancelled."""
        if status not in VALID_STATUSES:
            return {"ok": False, "error": f"Invalid status: {status}"}
        data = self._load()
        for task in data.get("tasks", []):
            if task.get("id") == task_id:
                task["status"] = status
                task["updated_at"] = datetime.now().isoformat() + "Z"
                if not self._save(data):
                    return {"ok": False, "error": "Failed to save tasks.json"}
                return {"ok": True, "task": task}
        return {"ok": False, "error": f"Task not found: {task_id}"}

    def assign_task(self, task_id: str, agent_name: str) -> Dict[str, Any]:
        """Assign task to an agent (e.g. manifest-coder)."""
        data = self._load()
        for task in data.get("tasks", []):
            if task.get("id") == task_id:
                task["assigned_agent"] = agent_name
                task["updated_at"] = datetime.now().isoformat() + "Z"
                if not self._save(data):
                    return {"ok": False, "error": "Failed to save tasks.json"}
                return {"ok": True, "task": task}
        return {"ok": False, "error": f"Task not found: {task_id}"}

    def update_task_progress(self, task_id: str, percentage: float) -> Dict[str, Any]:
        """Update task progress (0–100)."""
        p = max(0.0, min(100.0, float(percentage)))
        data = self._load()
        for task in data.get("tasks", []):
            if task.get("id") == task_id:
                task["progress"] = {
                    "percentage": round(p, 1),
                    "last_update": datetime.now().isoformat() + "Z",
                }
                task["updated_at"] = datetime.now().isoformat() + "Z"
                if not self._save(data):
                    return {"ok": False, "error": "Failed to save tasks.json"}
                return {"ok": True, "task": task}
        return {"ok": False, "error": f"Task not found: {task_id}"}

    def update_task_stage(self, task_id: str, stage: str) -> Dict[str, Any]:
        """Update task stage. Valid: planning, coding, testing, review, done."""
        if stage not in VALID_STAGES:
            return {"ok": False, "error": f"Invalid stage: {stage}"}
        data = self._load()
        for task in data.get("tasks", []):
            if task.get("id") == task_id:
                task["stage"] = stage
                task["updated_at"] = datetime.now().isoformat() + "Z"
                if not self._save(data):
                    return {"ok": False, "error": "Failed to save tasks.json"}
                return {"ok": True, "task": task}
        return {"ok": False, "error": f"Task not found: {task_id}"}

    def list_tasks(self, sprint_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List tasks, optionally filtered by sprint_id."""
        data = self._load()
        tasks = data.get("tasks", [])
        if sprint_id:
            tasks = [t for t in tasks if t.get("sprint_id") == sprint_id]
        return tasks

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task details by id."""
        data = self._load()
        for task in data.get("tasks", []):
            if task.get("id") == task_id:
                return task
        return None
