"""
Agent modules - Multi-agent coordination and context management.
"""
from manifest.agents.agent_coordinator import AgentCoordinator
from manifest.agents.context_provider import ContextProvider
from manifest.agents.task_scoper import TaskScoper

__all__ = ["AgentCoordinator", "ContextProvider", "TaskScoper"]
