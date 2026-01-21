"""
OMOC Agent System
Agent orchestration and management from OMOC.
"""
from .orchestrator import Orchestrator
from .manager import AgentManager
from .prometheus_prompt import PROMETHEUS_SYSTEM_PROMPT, get_prometheus_prompt
from .sisyphus_prompt import SISYPHUS_IDENTITY, get_sisyphus_prompt

__all__ = [
    "Orchestrator",
    "AgentManager",
    "PROMETHEUS_SYSTEM_PROMPT",
    "get_prometheus_prompt",
    "SISYPHUS_IDENTITY",
    "get_sisyphus_prompt"
]
