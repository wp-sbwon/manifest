"""
Agent modules - Multi-agent coordination and context management.
"""
# Lazy imports to avoid circular dependencies
__all__ = ["AgentCoordinator", "ContextProvider", "TaskScoper", "SkillsManager"]

def __getattr__(name):
    """Lazy import for agent modules."""
    if name == "AgentCoordinator":
        from manifest.agents.agent_coordinator import AgentCoordinator
        return AgentCoordinator
    elif name == "ContextProvider":
        from manifest.agents.context_provider import ContextProvider
        return ContextProvider
    elif name == "TaskScoper":
        from manifest.agents.task_scoper import TaskScoper
        return TaskScoper
    elif name == "SkillsManager":
        from manifest.agents.skills_manager import SkillsManager
        return SkillsManager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
