"""
OpenCode Worker Squad Spawn tool: spawn worker agents as OpenCode agent processes.

Orchestrator uses this tool to spawn planner, coder, test, debug, approver agents.
When OpenCode API is available, this tool would call it to start agent processes;
until then it returns a synthetic agent_process_id and records the spawn request
in .manifest/ for View and future integration.
"""
import json
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from manifest.core.logger import get_logger

logger = get_logger(__name__)

SPAWN_LOG_FILE = "worker_spawns.json"
WORKER_AGENTS = ("manifest-planner", "manifest-coder", "manifest-test", "manifest-debug", "manifest-approver")


def _default_spawns_data() -> Dict[str, Any]:
    return {"spawns": [], "version": "1.0"}


class WorkerSquadSpawnTool:
    """Spawn worker squad agents as OpenCode agent processes.

    When OpenCode API is available, spawn_* methods would call it to start
    the agent process. Until then, returns a synthetic agent_process_id and
    logs the spawn request to .manifest/worker_spawns.json for View/debugging.
    """

    def __init__(self, manifest_dir: Optional[Path] = None):
        self.manifest_dir = (manifest_dir or Path(".manifest")).resolve()
        self._spawn_file = self.manifest_dir / SPAWN_LOG_FILE

    def _load(self) -> Dict[str, Any]:
        if not self._spawn_file.exists():
            return _default_spawns_data()
        try:
            with open(self._spawn_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load {self._spawn_file}: {e}")
            return _default_spawns_data()

    def _save(self, data: Dict[str, Any]) -> bool:
        try:
            self.manifest_dir.mkdir(parents=True, exist_ok=True)
            with open(self._spawn_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Could not save {self._spawn_file}: {e}", exc_info=True)
            return False

    def _spawn(
        self,
        agent_name: str,
        task_id: str,
        context: Optional[Dict[str, Any]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Record a spawn request and return a synthetic agent_process_id.

        When OpenCode API is available, call it here to start the agent process.
        """
        agent_process_id = f"oc-{agent_name}-{task_id}-{uuid.uuid4().hex[:8]}"
        record = {
            "agent_process_id": agent_process_id,
            "agent_name": agent_name,
            "task_id": task_id,
            "context": context or {},
            "extra": extra or {},
            "created_at": datetime.now().isoformat() + "Z",
            "status": "requested",
        }
        data = self._load()
        data.setdefault("spawns", []).append(record)
        self._save(data)
        logger.info("Worker spawn requested: %s for task %s -> %s", agent_name, task_id, agent_process_id)
        return agent_process_id

    def spawn_planner(self, task_id: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Spawn planner agent as OpenCode agent process.

        Returns:
            agent_process_id: OpenCode agent process identifier.
        """
        return self._spawn("manifest-planner", task_id, context=context)

    def spawn_coder(
        self,
        task_id: str,
        plan: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Spawn coder agent as OpenCode agent process."""
        return self._spawn(
            "manifest-coder",
            task_id,
            context=context,
            extra={"plan": plan} if plan else None,
        )

    def spawn_test(
        self,
        task_id: str,
        code_changes: Optional[List[str]] = None,
    ) -> str:
        """Spawn test agent as OpenCode agent process."""
        return self._spawn(
            "manifest-test",
            task_id,
            extra={"code_changes": code_changes or []},
        )

    def spawn_debug(
        self,
        task_id: str,
        error_info: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Spawn debug agent as OpenCode agent process."""
        return self._spawn(
            "manifest-debug",
            task_id,
            extra={"error_info": error_info or {}},
        )

    def spawn_approver(
        self,
        task_id: str,
        work_summary: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Spawn approver agent as OpenCode agent process."""
        return self._spawn(
            "manifest-approver",
            task_id,
            extra={"work_summary": work_summary or {}},
        )
