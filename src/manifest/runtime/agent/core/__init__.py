"""
Core agent system components.

This package contains the foundational components of the agent system:
- AgentExecutor: LLM API execution engine
- AgentManager: Agent lifecycle management
- Orchestrator: High-level mission coordination
- BaseAgentExecutor: Base interface for executors
- ExecutorFactory: Factory for creating executors
"""
from .executor import AgentExecutor
from .manager import AgentManager
from .orchestrator import Orchestrator
from .base_executor import BaseAgentExecutor

# ExecutorFactory imported lazily to avoid circular imports
# It imports OpenCodeLLMAdapter which may cause import issues at module level

__all__ = [
    "AgentExecutor",
    "AgentManager",
    "Orchestrator",
    "BaseAgentExecutor",
    "ExecutorFactory",
]

def __getattr__(name):
    """Lazy import for ExecutorFactory to avoid circular imports."""
    if name == "ExecutorFactory":
        from .executor_factory import ExecutorFactory
        return ExecutorFactory
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
