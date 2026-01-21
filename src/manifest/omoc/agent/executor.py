"""
Agent Executor - Executes agents using LLM APIs.
Handles LLM calls, message processing, and agent state management.
"""
import asyncio
import json
from typing import Dict, Any, Optional, List, AsyncIterator
from pathlib import Path
import httpx
from manifest.core.config import ConfigManager
from manifest.core.state_manager import StateManager


class AgentExecutor:
    """
    Executes agents by making LLM API calls.
    Supports multiple LLM providers (Anthropic, OpenAI, etc.).
    """
    
    def __init__(
        self,
        config_manager: ConfigManager,
        state_manager: StateManager
    ):
        """
        Initialize agent executor.
        
        Args:
            config_manager: Configuration manager for API keys
            state_manager: State manager for persistence
        """
        self.config_manager = config_manager
        self.state_manager = state_manager
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
            agent_type: Type of agent (prometheus, sisyphus, etc.)
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
        
        # Prepare messages
        messages = self._prepare_messages(prompt, message_history or [])
        
        # Create session
        session_id = f"{agent_id}_{asyncio.get_event_loop().time()}"
        self.active_sessions[agent_id] = {
            "session_id": session_id,
            "agent_type": agent_type,
            "status": "running"
        }
        
        try:
            if provider == "anthropic":
                async for chunk in self._call_anthropic(api_key, model, messages):
                    yield chunk
            elif provider == "openai":
                async for chunk in self._call_openai(api_key, model, messages):
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
        """Prepare messages for LLM API."""
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
        """Call Anthropic Claude API."""
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
        messages: List[Dict[str, str]]
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
                                text = delta.get("content", "")
                                if text:
                                    full_content += text
                                    yield {"type": "chunk", "content": text}
                        except json.JSONDecodeError:
                            continue
                
                if full_content:
                    yield {"type": "complete", "content": full_content}
    
    def get_session_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent session status."""
        return self.active_sessions.get(agent_id)
    
    def stop_session(self, agent_id: str) -> bool:
        """Stop an agent session."""
        if agent_id in self.active_sessions:
            self.active_sessions[agent_id]["status"] = "stopped"
            return True
        return False
