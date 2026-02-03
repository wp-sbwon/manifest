"""
Worker agent registration: update active_agents and task state.

Used by AgentCoordinator when a worker agent (container or in-process) starts.
Single responsibility: keep active_agents and task/scope state in sync.
"""
from typing import Dict, Any, Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from manifest.core.state_manager import StateManager


class WorkerRegistration:
    """Registers a worker agent in active_agents and task state.

    Caller must call state_manager.save_state() after register().
    """

    def __init__(self, state_manager: "StateManager"):
        self.state_manager = state_manager

    def register(
        self,
        active_agents: Dict[str, Dict[str, Any]],
        task_id: str,
        agent_type: str,
        channel: str,
        task_scope: Dict[str, Any],
        task: Dict[str, Any],
        tasks: List[Dict[str, Any]],
        execution_mode: str = "direct",
        container_id: Optional[str] = None,
        last_action_msg: Optional[str] = None,
    ) -> None:
        """Register a worker agent in active_agents and update task state."""
        active_agents[task_id] = {
            "agent_type": agent_type,
            "status": "active",
            "channel": channel,
            "execution_mode": execution_mode,
        }
        if container_id is not None:
            active_agents[task_id]["container_id"] = container_id

        task["agent"] = {
            "type": agent_type,
            "status": "active",
            "channel": channel,
        }
        if container_id is not None:
            task["agent"]["container_id"] = container_id

        task["scope"] = {
            "components": task_scope.get("components", []),
            "files": task_scope.get("allowed_files", []),
            "allowed_modifications": task_scope.get("allowed_modifications", []),
        }

        self.state_manager.set_task_checklist(tasks)
        if last_action_msg:
            self.state_manager.set_last_action(last_action_msg)
