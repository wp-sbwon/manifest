"""
Agent System
Agent orchestration and management.
"""
from .orchestrator import Orchestrator
from .manager import AgentManager
from .executor import AgentExecutor
from .orchestrator_agent import OrchestratorAgent
from .planner_agent import PlannerAgent
from .coder_agent import CoderAgent
from .orchestrator_prompt import ORCHESTRATOR_SYSTEM_PROMPT, get_orchestrator_prompt
from .planner_prompt import PLANNER_SYSTEM_PROMPT, get_planner_prompt
from .coder_prompt import CODER_IDENTITY, get_coder_prompt

__all__ = [
    "Orchestrator",
    "AgentManager",
    "AgentExecutor",
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
