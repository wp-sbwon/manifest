"""
Core agent system components.

- BaseAgentExecutor: Base interface for backend executors
- AgentManager: Agent lifecycle management
- Orchestrator: High-level mission coordination
- ExecutorFactory: Factory for creating the configured backend executor
"""
from .manager import AgentManager
from .orchestrator import Orchestrator
from .base_executor import BaseAgentExecutor

__all__ = [
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
