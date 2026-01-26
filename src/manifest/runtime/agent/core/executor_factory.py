"""
Executor factory for creating agent executors based on configuration.

This module provides a factory that creates the appropriate executor backend
(direct LLM API, OpenCode, Claude Code) based on user settings.
"""
from typing import Optional, Dict, Any, List
from manifest.core.config import ConfigManager
from manifest.core.state_manager import StateManager
from manifest.runtime.agent.core.base_executor import BaseAgentExecutor
from manifest.runtime.agent.core.executor import AgentExecutor
from manifest.core.logger import get_logger

# OpenCodeLLMAdapter imported lazily to avoid circular imports

logger = get_logger(__name__)


class ExecutorFactory:
    """Factory for creating agent executors based on configuration.

    Supports multiple execution backends:
    - "direct": Direct LLM API calls (AgentExecutor)
    - "opencode": OpenCode HTTP API (OpenCodeLLMAdapter)
    - "claude_code": Claude Code SDK (future)
    """

    @staticmethod
    def create_executor(
        config_manager: ConfigManager,
        state_manager: StateManager,
        backend: Optional[str] = None
    ) -> BaseAgentExecutor:
        """Create an agent executor based on configuration.

        Args:
            config_manager: Configuration manager for settings.
            state_manager: State manager for persistence.
            backend: Optional backend name. If None, reads from config.
                Options: "direct", "opencode", "claude_code"

        Returns:
            BaseAgentExecutor instance configured for the selected backend.

        Raises:
            ValueError: If backend is not supported.
        """
        # Get backend from config if not provided
        if backend is None:
            backend = config_manager.get_setting("agent.execution_backend", "opencode")

        logger.info(f"Creating agent executor with backend: {backend}")

        if backend == "direct":
            from manifest.runtime.hooks.prompt_hooks import HookManager
            from manifest.audit.blueprint.blueprint_synchronizer import BlueprintSynchronizer

            hook_manager = HookManager()
            blueprint_synchronizer = BlueprintSynchronizer()
            from manifest.runtime.hooks.prompt_hooks import PolicyInjectionHook, VisualRealityHook
            hook_manager.register_hook(PolicyInjectionHook(state_manager))
            hook_manager.register_hook(VisualRealityHook(state_manager, blueprint_synchronizer))

            return AgentExecutor(
                config_manager,
                state_manager,
                hook_manager=hook_manager
            )

        elif backend == "opencode":
            # Import here to avoid circular import
            from manifest.runtime.opencode_llm_adapter import OpenCodeLLMAdapter

            server_host = config_manager.get_setting("opencode.server_host", "localhost")
            server_port = config_manager.get_setting("opencode.server_port", 4096)
            auto_start = config_manager.get_setting("opencode.auto_start", True)

            return OpenCodeLLMAdapter(
                config_manager,
                state_manager,
                server_host=server_host,
                server_port=server_port,
                auto_start=auto_start
            )

        elif backend == "claude_code":
            # Future implementation
            logger.warning("Claude Code backend not yet implemented, falling back to direct")
            return ExecutorFactory.create_executor(config_manager, state_manager, "direct")

        else:
            raise ValueError(f"Unsupported execution backend: {backend}")

    @staticmethod
    def get_available_backends() -> List[str]:
        """Get list of available execution backends.

        Returns:
            List of backend names.
        """
        return ["direct", "opencode", "claude_code"]
