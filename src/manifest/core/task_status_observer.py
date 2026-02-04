"""
Observed task status: derive status from runtime state instead of stored field.

Status is computed from:
- active_task_ids: task has an active agent → in_progress
- task.worker_squad.status: completed | failed
- task.status == "cancelled" (explicit user cancel)
- else: pending

Used by the View so task status reflects what the system is doing without
relying on the LLM to call update_task_status.
"""
from typing import Dict, Any, List


def observe_task_status(
    task_id: str,
    task: Dict[str, Any],
    active_task_ids: List[str],
) -> str:
    """Compute task status from observed state (no LLM-written status).

    Args:
        task_id: Task ID.
        task: Task dict (may have worker_squad, status, etc.).
        active_task_ids: List of task IDs that currently have an active agent.

    Returns:
        One of: pending, in_progress, paused, blocked, completed, cancelled.
    """
    # Explicit cancel (user or tool)
    if task.get("status") == "cancelled":
        return "cancelled"

    # Currently has an active agent
    if task_id in active_task_ids:
        return "in_progress"

    # Worker squad completed (persisted by executor)
    ws = task.get("worker_squad") or {}
    ws_status = ws.get("status")
    if ws_status == "completed":
        return "completed"
    if ws_status == "failed":
        return "blocked"

    # Had agent/scope but no active agent and no completed workflow → paused or pending
    if task.get("agent") and not ws_status:
        return "paused"

    return "pending"


def observe_tasks_with_status(
    tasks: List[Dict[str, Any]],
    active_task_ids: List[str],
) -> List[Dict[str, Any]]:
    """Return tasks with observed status set on each (copy; does not mutate)."""
    result = []
    for t in tasks:
        tid = t.get("id")
        if not tid:
            result.append({**t, "observed_status": "pending"})
            continue
        observed = observe_task_status(tid, t, active_task_ids)
        result.append({**t, "observed_status": observed})
    return result
