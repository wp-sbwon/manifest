"""
Agent System - Agent orchestration and management.

- Core: BaseAgentExecutor, AgentManager, Orchestrator, ExecutorFactory
- Agent implementations: orchestrator, planner, coder, test, etc.
- Prompts: Prompt generation for different agent types
"""
from .core.orchestrator import Orchestrator
from .core.manager import AgentManager
from .core.base_executor import BaseAgentExecutor
from .agents.orchestrator_agent import OrchestratorAgent
from .agents.planner_agent import PlannerAgent
from .agents.coder_agent import CoderAgent
from .prompts.orchestrator_prompt import ORCHESTRATOR_SYSTEM_PROMPT, get_orchestrator_prompt
from .prompts.planner_prompt import PLANNER_SYSTEM_PROMPT, get_planner_prompt
from .prompts.coder_prompt import CODER_IDENTITY, get_coder_prompt

__all__ = [
    "Orchestrator",
    "AgentManager",
    "BaseAgentExecutor",
    "OrchestratorAgent",
    "PlannerAgent",
    "CoderAgent",
    "ORCHESTRATOR_SYSTEM_PROMPT",
    "get_orchestrator_prompt",
    "PLANNER_SYSTEM_PROMPT",
    "get_planner_prompt",
    "CODER_IDENTITY",
    "get_coder_prompt"
]
