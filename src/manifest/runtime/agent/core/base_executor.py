"""
Base executor interface for agent execution.

This module defines the abstract base class that all agent executors must implement.
This allows Manifest to support multiple execution backends (direct LLM API calls,
OpenCode, Claude Code) while maintaining a consistent interface.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, AsyncIterator
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class BaseAgentExecutor(ABC):
    """Abstract base class for agent executors.

    All agent executors must implement this interface to ensure compatibility
    with the agent system. This allows Manifest to support multiple execution
    backends while maintaining a consistent interface.
    """

    @abstractmethod
    async def execute_agent(
        self,
        agent_id: str,
        agent_type: str,
        prompt: Optional[str],
        model_config: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        message_history: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """Execute an agent by making LLM calls.

        This is the main entry point for agent execution. The executor should
        handle all aspects of LLM interaction including prompt preparation,
        context management, tool calls, and response streaming.

        Args:
            agent_id: Unique identifier for this agent instance.
            agent_type: Type of agent (orchestrator, planner, coder, test, etc.).
            prompt: Agent prompt (system + user prompt). Can be None for continuing
                conversation.
            model_config: Model configuration dictionary containing:
                - provider: Provider name (e.g., "anthropic", "openai")
                - model: Model name (e.g., "claude-3-5-sonnet-20241022")
                - api_key: API key for the provider
            context: Additional context dictionary. Structure depends on agent type
                but typically includes tiered context (Tier 0-3), task scope, etc.
            message_history: Previous conversation messages. Format should match
                the provider's expected format (may include tool_result content blocks).
            tools: Optional list of tool definitions. Each tool should have:
                - name: Tool name
                - description: Tool description
                - input_schema: JSON schema for tool inputs

        Yields:
            Dictionary with the following structure:
            - type: One of "chunk", "complete", "tool_use", "tool_use_start",
              "tool_use_complete", "error"
            - content: Text content (for "chunk" and "complete" types)
            - tool_call: Tool call information (for "tool_use" types)
            - tool_calls: List of tool calls (for "tool_use_complete" type)
        """
        pass

    @abstractmethod
    def get_session_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of an agent session.

        Args:
            agent_id: Agent identifier.

        Returns:
            Dictionary with session status information, or None if session not found.
            Should include at least:
            - status: "running", "completed", "failed", "stopped"
            - session_id: Session identifier
            - agent_type: Type of agent
        """
        pass

    @abstractmethod
    def stop_session(self, agent_id: str) -> bool:
        """Stop an active agent session.

        Args:
            agent_id: Agent identifier.

        Returns:
            True if session was stopped, False if session not found or already stopped.
        """
        pass
