"""
Executor factory: creates the agent executor for the configured backend.

Architecture supports multiple backends; the primary one is OpenCode.
Chat, terminal, and tool execution are handled by the active backend.
"""
from typing import Optional, Dict, Any, List
from manifest.core.config import ConfigManager
from manifest.core.state_manager import StateManager
from manifest.runtime.agent.core.base_executor import BaseAgentExecutor
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class ExecutorFactory:
    """Creates the executor for the configured backend. Multiple backends supported; primary is OpenCode."""

    @staticmethod
    def create_executor(
        config_manager: ConfigManager,
        state_manager: StateManager,
        backend: Optional[str] = None
    ) -> BaseAgentExecutor:
        """Create the executor for the given backend. Default/primary backend is opencode."""
        if backend is None:
            backend = config_manager.get_setting("agent.execution_backend", "opencode")

        if backend == "opencode":
            logger.info("Creating agent executor (backend: opencode)")
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

        raise ValueError(
            f"Unsupported execution backend: {backend!r}. "
            "Supported backends: opencode (others may be added via config)."
        )

    @staticmethod
    def get_available_backends() -> List[str]:
        """Backends that can be used for execution. Primary is opencode; more can be added."""
        return ["opencode"]
