"""
Agent prompt generators.

This package contains prompt generation functions for different agent types:
- Orchestrator prompts: Mission coordination and task delegation
- Planner prompts: Detailed task planning
- Coder prompts: Code implementation guidance
"""
from .orchestrator_prompt import ORCHESTRATOR_SYSTEM_PROMPT, ORCHESTRATOR_IDENTITY, get_orchestrator_prompt, get_ideation_prompt
from .planner_prompt import PLANNER_SYSTEM_PROMPT, PLANNER_IDENTITY, get_planner_prompt
from .coder_prompt import CODER_IDENTITY, get_coder_prompt

__all__ = [
    "ORCHESTRATOR_SYSTEM_PROMPT",
    "ORCHESTRATOR_IDENTITY",
    "get_orchestrator_prompt",
    "get_ideation_prompt",
    "PLANNER_SYSTEM_PROMPT",
    "PLANNER_IDENTITY",
    "get_planner_prompt",
    "CODER_IDENTITY",
    "get_coder_prompt",
]
