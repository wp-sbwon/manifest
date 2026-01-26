"""
Agent execution engine using LLM APIs.

This module provides the AgentExecutor class which is responsible for actually
executing agents by making API calls to LLM providers (Anthropic, OpenAI, etc.).
It handles message preparation, streaming responses, prompt hooks, and
session management.

The executor supports multiple providers and can stream responses in real-time,
making it suitable for interactive agent execution.
"""
import asyncio
import json
from typing import Dict, Any, Optional, List, AsyncIterator
from pathlib import Path
import httpx
from manifest.core.config import ConfigManager
from manifest.core.state_manager import StateManager
from manifest.runtime.hooks.prompt_hooks import HookManager
from manifest.runtime.tools.tool_definitions import get_tool_definitions
from manifest.runtime.tools.tool_call_parser import ToolCallParser
from manifest.agents.context_size_calculator import ContextSizeCalculator
from manifest.core.logger import get_logger
from manifest.runtime.agent.core.base_executor import BaseAgentExecutor

logger = get_logger(__name__)


class AgentExecutor(BaseAgentExecutor):
    """
    Executes agents by making LLM API calls.
    Supports multiple LLM providers (Anthropic, OpenAI, etc.).
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        state_manager: StateManager,
        hook_manager: Optional[HookManager] = None
    ):
        """
        Initialize agent executor.

        Args:
            config_manager: Configuration manager for API keys
            state_manager: State manager for persistence
            hook_manager: Optional hook manager for prompt interception
        """
        self.config_manager = config_manager
        self.state_manager = state_manager
        self.hook_manager = hook_manager or HookManager()
        self.active_sessions: Dict[str, Dict[str, Any]] = {}  # agent_id -> session

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
        """
        Execute an agent by making LLM API calls.

        Args:
            agent_id: Agent identifier
            agent_type: Type of agent (orchestrator, planner, coder, etc.)
            prompt: Agent prompt (system + user prompt). Can be None for continuing conversation.
            model_config: Model configuration (provider, model, api_key)
            context: Additional context
            message_history: Previous message history (can contain tool_result content blocks)
            tools: Optional tool definitions. If None, uses default tools.

        Yields:
            Dict with 'type' (chunk/complete/error/tool_use/tool_result) and 'content'
        """
        provider = model_config.get("provider", "anthropic")
        model = model_config.get("model", "claude-3-5-sonnet-20241022")
        api_key = model_config.get("api_key")

        if not api_key:
            yield {"type": "error", "content": "API key not provided"}
            return

        # Apply prompt hooks (intercept and modify prompt) - only if prompt is provided
        if prompt:
            modified_prompt = await self.hook_manager.apply_hooks(
                agent_id=agent_id,
                agent_type=agent_type,
                prompt=prompt,
                context=context,
                message_history=message_history
            )
        else:
            modified_prompt = None

        # Prepare messages (prompt can be None for continuing conversation)
        messages = self._prepare_messages(modified_prompt, message_history or [])

        # Validate and optimize context size before API call
        if context:
            validation_result = self._validate_and_optimize_context(
                messages=messages,
                context=context,
                model=model,
                provider=provider,
                tools=tools
            )

            if validation_result.get("optimized"):
                logger.info(
                    f"Context optimized for {agent_id}: "
                    f"{validation_result.get('original_tokens')} -> "
                    f"{validation_result.get('optimized_tokens')} tokens"
                )

            if not validation_result.get("valid"):
                warnings = validation_result.get("warnings", [])
                for warning in warnings:
                    logger.warning(f"Context size warning for {agent_id}: {warning}")

        # Create session
        session_id = f"{agent_id}_{asyncio.get_event_loop().time()}"
        self.active_sessions[agent_id] = {
            "session_id": session_id,
            "agent_type": agent_type,
            "status": "running"
        }

        # Prepare tools for API - optimize tool list based on agent type and context
        api_tools = self._optimize_tool_list(
            tools=tools,
            agent_type=agent_type,
            context=context
        )

        try:
            if provider == "anthropic":
                async for chunk in self._call_anthropic(api_key, model, messages, api_tools):
                    yield chunk
            elif provider == "openai":
                async for chunk in self._call_openai(api_key, model, messages, api_tools):
                    yield chunk
            else:
                yield {"type": "error", "content": f"Unsupported provider: {provider}"}
        except Exception as e:
            yield {"type": "error", "content": str(e)}
            # Mark session as failed on error
            if agent_id in self.active_sessions:
                self.active_sessions[agent_id]["status"] = "failed"
                self.active_sessions[agent_id]["error"] = str(e)
        finally:
            # Mark session as completed when execution finishes (successfully or not)
            if agent_id in self.active_sessions:
                if self.active_sessions[agent_id].get("status") != "failed":
                    self.active_sessions[agent_id]["status"] = "completed"
                # Add completion timestamp
                import time
                self.active_sessions[agent_id]["completed_at"] = time.time()
                logger.debug(f"AgentExecutor session {agent_id} marked as {self.active_sessions[agent_id]['status']}")

    def _prepare_messages(
        self,
        prompt: Optional[str],
        history: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Prepare message list for LLM API from prompt and history.

        Extracts system message from the prompt if present (separated by "##"),
        then adds conversation history, and finally adds the current user message.
        The format matches what LLM APIs expect (list of role/content dictionaries).

        Supports Anthropic's tool_result content blocks in message history.

        Args:
            prompt: Complete prompt string that may contain system and user parts.
                If None, only history is used (for continuing conversation).
            history: Previous conversation messages as list of role/content dicts.
                Can contain Anthropic-style content blocks for tool_result.

        Returns:
            List of message dictionaries with "role" and "content" keys,
            formatted for LLM API consumption.
        """
        messages = []

        # Add system message (extract from prompt if needed)
        if prompt:
            system_parts = prompt.split("\n\n##", 1)
            if len(system_parts) > 1:
                system_message = system_parts[0].strip()
                user_message = "##" + system_parts[1]
            else:
                system_message = ""
                user_message = prompt

            if system_message:
                messages.append({"role": "system", "content": system_message})

            # Add current user message
            messages.append({"role": "user", "content": user_message})

        # Add history (may contain tool_result content blocks for Anthropic)
        messages.extend(history)

        return messages

    async def _call_anthropic(
        self,
        api_key: str,
        model: str,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """Make API call to Anthropic Claude and stream responses.

        Handles Anthropic's streaming API format, extracting text deltas
        from Server-Sent Events (SSE) format. Yields chunks as they arrive
        for real-time display.

        Args:
            api_key: Anthropic API key.
            model: Model name (e.g., "claude-3-5-sonnet-20241022").
            messages: List of conversation messages.

        Yields:
            Dictionaries with type "chunk" (streaming) or "complete" (finished).
            On error, yields type "error" with error message.
        """
        # Extract system message if present
        system_message = None
        api_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            elif msg["role"] == "user":
                # Handle Anthropic content blocks (for tool_result)
                content = msg.get("content")
                if isinstance(content, list):
                    # Content is already in Anthropic format (list of content blocks)
                    api_messages.append({
                        "role": "user",
                        "content": content
                    })
                else:
                    # Regular string content
                    api_messages.append({
                        "role": "user",
                        "content": content
                    })
            elif msg["role"] == "assistant":
                api_messages.append({
                    "role": "assistant",
                    "content": msg.get("content", "")
                })

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        payload = {
            "model": model,
            "max_tokens": 4096,
            "messages": api_messages
        }

        if system_message:
            payload["system"] = system_message

        # Add tools if provided
        if tools:
            # Convert tool definitions to Anthropic format
            anthropic_tools = []
            for tool in tools:
                anthropic_tools.append({
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "input_schema": tool.get("input_schema", {})
                })
            payload["tools"] = anthropic_tools

        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    yield {"type": "error", "content": f"API error: {error_text.decode()}"}
                    return

                full_content = ""
                tool_use_blocks = []
                current_tool_use = None
                current_tool_input = ""

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)
                            event_type = data.get("type")

                            # Handle content_block_start (tool_use or text)
                            if event_type == "content_block_start":
                                content_block = data.get("content_block", {})
                                block_type = content_block.get("type")

                                if block_type == "tool_use":
                                    # Start of a tool_use block
                                    current_tool_use = {
                                        "id": content_block.get("id"),
                                        "name": content_block.get("name"),
                                        "input": {}
                                    }
                                    current_tool_input = ""
                                    yield {
                                        "type": "tool_use_start",
                                        "tool_call": {
                                            "id": current_tool_use["id"],
                                            "name": current_tool_use["name"]
                                        }
                                    }

                            # Handle content_block_delta (text or tool input)
                            elif event_type == "content_block_delta":
                                delta = data.get("delta", {})

                                if "text" in delta:
                                    # Text content
                                    text = delta.get("text", "")
                                    if text:
                                        full_content += text
                                        yield {"type": "chunk", "content": text}

                                elif "partial_json" in delta and current_tool_use:
                                    # Tool input is being streamed as partial JSON
                                    current_tool_input += delta.get("partial_json", "")

                            # Handle content_block_stop (tool_use complete)
                            elif event_type == "content_block_stop" and current_tool_use:
                                # Try to parse the complete tool input
                                try:
                                    if current_tool_input:
                                        current_tool_use["input"] = json.loads(current_tool_input)
                                    else:
                                        # If no input was streamed, check if it was in the start block
                                        pass
                                except json.JSONDecodeError:
                                    # Partial JSON might be incomplete, try to fix it
                                    try:
                                        # Try to complete the JSON
                                        if not current_tool_input.strip().endswith("}"):
                                            current_tool_input += "}"
                                        current_tool_use["input"] = json.loads(current_tool_input)
                                    except json.JSONDecodeError:
                                        logger.warning(f"Failed to parse tool input JSON: {current_tool_input}")
                                        current_tool_use["input"] = {}

                                # Tool use block is complete
                                tool_use_blocks.append(current_tool_use)
                                yield {
                                    "type": "tool_use",
                                    "tool_call": current_tool_use
                                }
                                current_tool_use = None
                                current_tool_input = ""

                            # Handle message_stop (entire message complete)
                            elif event_type == "message_stop":
                                # Message is complete
                                pass

                        except json.JSONDecodeError:
                            continue

                if full_content:
                    yield {"type": "complete", "content": full_content}

                if tool_use_blocks:
                    yield {"type": "tool_use_complete", "tool_calls": tool_use_blocks}

    async def _call_openai(
        self,
        api_key: str,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """Call OpenAI API."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": messages,
            "stream": True
        }

        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    yield {"type": "error", "content": f"API error: {error_text.decode()}"}
                    return

                full_content = ""
                function_calls = []
                current_function_call = None

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)
                            choices = data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})

                                # Handle function calls
                                if "function_call" in delta:
                                    func_call = delta["function_call"]
                                    if "name" in func_call:
                                        current_function_call = {
                                            "name": func_call["name"],
                                            "arguments": ""
                                        }
                                    elif "arguments" in func_call and current_function_call:
                                        current_function_call["arguments"] += func_call["arguments"]

                                # Handle text content
                                text = delta.get("content", "")
                                if text:
                                    full_content += text
                                    yield {"type": "chunk", "content": text}

                                # Check if function call is complete
                                if choices[0].get("finish_reason") == "function_call" and current_function_call:
                                    try:
                                        arguments = json.loads(current_function_call["arguments"])
                                        tool_call = {
                                            "id": f"openai_{id(current_function_call)}",
                                            "name": current_function_call["name"],
                                            "input": arguments
                                        }
                                        function_calls.append(tool_call)
                                        yield {
                                            "type": "tool_use",
                                            "tool_call": tool_call
                                        }
                                    except json.JSONDecodeError:
                                        pass
                                    current_function_call = None
                        except json.JSONDecodeError:
                            continue

                if full_content:
                    yield {"type": "complete", "content": full_content}

                if function_calls:
                    yield {"type": "tool_use_complete", "tool_calls": function_calls}

    def _validate_and_optimize_context(
        self,
        messages: List[Dict[str, Any]],
        context: Dict[str, Any],
        model: str,
        provider: str,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Validate and optimize context size.

        Checks if the total context (messages + context dict) fits within
        model token limits. If not, suggests optimizations or trims message history.

        Args:
            messages: Prepared message list for API.
            context: Context dictionary.
            model: Model name.
            provider: Provider name.
            tools: Optional tool definitions.

        Returns:
            Dictionary with validation result and optimization info.
        """
        # Estimate tokens in messages
        messages_text = json.dumps(messages, indent=2)
        messages_tokens = ContextSizeCalculator.estimate_tokens(messages_text)

        # Estimate tokens in context
        context_tokens = ContextSizeCalculator.estimate_context_tokens(context)

        # Estimate tokens in tools (if provided)
        tools_tokens = 0
        if tools:
            tools_text = json.dumps(tools, indent=2)
            tools_tokens = ContextSizeCalculator.estimate_tokens(tools_text)

        total_tokens = messages_tokens + context_tokens + tools_tokens
        model_limit = ContextSizeCalculator.get_model_token_limit(model, provider)
        available_tokens = model_limit - ContextSizeCalculator.RESPONSE_TOKEN_RESERVE

        result = {
            "valid": total_tokens <= available_tokens,
            "estimated_tokens": total_tokens,
            "model_limit": model_limit,
            "available_tokens": available_tokens,
            "messages_tokens": messages_tokens,
            "context_tokens": context_tokens,
            "tools_tokens": tools_tokens,
            "optimized": False,
            "warnings": [],
            "suggestions": []
        }

        if total_tokens > available_tokens:
            excess = total_tokens - available_tokens
            result["warnings"].append(
                f"Total context ({total_tokens} tokens) exceeds available limit "
                f"({available_tokens} tokens) by {excess} tokens"
            )
            result["suggestions"].append("Reduce message history length")
            result["suggestions"].append("Reduce context tier sizes")
            result["suggestions"].append("Use fewer tools")

        elif total_tokens > available_tokens * 0.8:
            result["warnings"].append(
                f"Context size ({total_tokens} tokens) is {total_tokens/available_tokens*100:.1f}% "
                "of available limit. Consider reducing context."
            )

        return result

    def _optimize_tool_list(
        self,
        tools: Optional[List[Dict[str, Any]]],
        agent_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Optimize tool list based on agent type and context.

        Returns only the tools that are relevant for the agent type,
        reducing token usage and improving focus.

        Args:
            tools: Full tool list (or None to use defaults).
            agent_type: Type of agent (coder, test, debug, etc.).
            context: Optional context to determine tool needs.

        Returns:
            Optimized list of tool definitions.
        """
        if tools is None:
            tools = get_tool_definitions()

        # Agent-specific tool filtering
        agent_tool_map = {
            "coder": ["edit", "write", "read", "grep", "glob", "list", "bash"],
            "test": ["read", "bash", "grep", "glob"],
            "debug": ["read", "edit", "grep", "bash"],
            "planner": ["read", "grep", "glob"],
            "orchestrator": ["read", "grep", "glob"],
        }

        # Get relevant tools for this agent type
        relevant_tool_names = agent_tool_map.get(agent_type, [])

        if not relevant_tool_names:
            # If no specific mapping, return all tools
            return tools

        # Filter tools to only include relevant ones
        optimized_tools = [
            tool for tool in tools
            if tool.get("name") in relevant_tool_names
        ]

        # If filtering resulted in empty list, return all tools (fallback)
        if not optimized_tools:
            logger.warning(
                f"No tools matched for agent type '{agent_type}', "
                "returning all tools"
            )
            return tools

        logger.debug(
            f"Optimized tools for {agent_type}: "
            f"{len(optimized_tools)}/{len(tools)} tools"
        )

        return optimized_tools

    def get_session_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent session status."""
        return self.active_sessions.get(agent_id)

    def stop_session(self, agent_id: str) -> bool:
        """Stop an agent session."""
        if agent_id in self.active_sessions:
            self.active_sessions[agent_id]["status"] = "stopped"
            return True
        return False
