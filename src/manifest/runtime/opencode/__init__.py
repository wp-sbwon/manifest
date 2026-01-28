"""
OpenCode-first runtime: tools and agent configs for Manifest orchestrator.

This package provides OpenCode tools (task_management, sprint_management,
worker_squad_spawn, blueprint_sync, drift_check) used by the manifest-orchestrator
and worker agents. Tools read/write .manifest/ files for real-time View sync.
"""
from manifest.runtime.opencode.tools.task_management import TaskManagementTool
from manifest.runtime.opencode.tools.sprint_management import SprintManagementTool
from manifest.runtime.opencode.tools.worker_squad_spawn import WorkerSquadSpawnTool
from manifest.runtime.opencode.tools.blueprint_sync import BlueprintSyncTool, DriftCheckTool

__all__ = [
    "TaskManagementTool",
    "SprintManagementTool",
    "WorkerSquadSpawnTool",
    "BlueprintSyncTool",
    "DriftCheckTool",
]
