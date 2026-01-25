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


class AgentExecutor:
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
        prompt: str,
        model_config: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        message_history: Optional[List[Dict[str, str]]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute an agent by making LLM API calls.
        
        Args:
            agent_id: Agent identifier
            agent_type: Type of agent (orchestrator, planner, coder, etc.)
            prompt: Agent prompt (system + user prompt)
            model_config: Model configuration (provider, model, api_key)
            context: Additional context
            message_history: Previous message history
            
        Yields:
            Dict with 'type' (chunk/complete/error) and 'content'
        """
        provider = model_config.get("provider", "anthropic")
        model = model_config.get("model", "claude-3-5-sonnet-20241022")
        api_key = model_config.get("api_key")
        
        if not api_key:
            yield {"type": "error", "content": "API key not provided"}
            return
        
        # Apply prompt hooks (intercept and modify prompt)
        modified_prompt = await self.hook_manager.apply_hooks(
            agent_id=agent_id,
            agent_type=agent_type,
            prompt=prompt,
            context=context,
            message_history=message_history
        )
        
        # Prepare messages
        messages = self._prepare_messages(modified_prompt, message_history or [])
        
        # Create session
        session_id = f"{agent_id}_{asyncio.get_event_loop().time()}"
        self.active_sessions[agent_id] = {
            "session_id": session_id,
            "agent_type": agent_type,
            "status": "running"
        }
        
        # Prepare tools for API
        api_tools = tools if tools is not None else get_tool_definitions()
        
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
        finally:
            if agent_id in self.active_sessions:
                self.active_sessions[agent_id]["status"] = "completed"
    
    def _prepare_messages(
        self,
        prompt: str,
        history: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """Prepare message list for LLM API from prompt and history.
        
        Extracts system message from the prompt if present (separated by "##"),
        then adds conversation history, and finally adds the current user message.
        The format matches what LLM APIs expect (list of role/content dictionaries).
        
        Args:
            prompt: Complete prompt string that may contain system and user parts.
            history: Previous conversation messages as list of role/content dicts.
        
        Returns:
            List of message dictionaries with "role" and "content" keys,
            formatted for LLM API consumption.
        """
        messages = []
        
        # Add system message (extract from prompt if needed)
        system_parts = prompt.split("\n\n##", 1)
        if len(system_parts) > 1:
            system_message = system_parts[0].strip()
            user_message = "##" + system_parts[1]
        else:
            system_message = ""
            user_message = prompt
        
        if system_message:
            messages.append({"role": "system", "content": system_message})
        
        # Add history
        messages.extend(history)
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
    async def _call_anthropic(
        self,
        api_key: str,
        model: str,
        messages: List[Dict[str, str]]
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
            else:
                api_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
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
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        
                        try:
                            data = json.loads(data_str)
                            if data.get("type") == "content_block_delta":
                                delta = data.get("delta", {})
                                text = delta.get("text", "")
                                if text:
                                    full_content += text
                                    yield {"type": "chunk", "content": text}
                        except json.JSONDecodeError:
                            continue
                
                if full_content:
                    yield {"type": "complete", "content": full_content}
    
    async def _call_openai(
        self,
        api_key: str,
        model: str,
        messages: List[Dict[str, str]],
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
    
    def get_session_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent session status."""
        return self.active_sessions.get(agent_id)
    
    def stop_session(self, agent_id: str) -> bool:
        """Stop an agent session."""
        if agent_id in self.active_sessions:
            self.active_sessions[agent_id]["status"] = "stopped"
            return True
        return False
