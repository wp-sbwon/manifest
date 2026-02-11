"""
OpenCode backend adapter for agent execution.

One of the supported backends (primary). Handles LLM interactions, context management, and tool execution.
Manifest focuses on workflow orchestration; the backend runs the model and tools.
"""
import asyncio
import json
import subprocess
import time
from typing import Dict, Any, Optional, List, AsyncIterator
from pathlib import Path
import httpx
from manifest.runtime.agent.core.base_executor import BaseAgentExecutor
from manifest.core.config import ConfigManager
from manifest.core.state_manager import StateManager
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class OpenCodeLLMAdapter(BaseAgentExecutor):
    """Adapter for using OpenCode as the LLM execution backend.

    This adapter connects to an OpenCode server (either running or starts one)
    and uses its HTTP API to execute agents. OpenCode handles all LLM interactions,
    context management, and tool execution.

    Attributes:
        config_manager: Configuration manager for settings.
        state_manager: State manager for persistence.
        server_host: OpenCode server hostname.
        server_port: OpenCode server port.
        auto_start: Whether to auto-start OpenCode server if not running.
        server_process: Subprocess handle for auto-started server (if any).
        base_url: Base URL for OpenCode HTTP API.
        active_sessions: Dictionary tracking active agent sessions.
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        state_manager: StateManager,
        server_host: str = "localhost",
        server_port: int = 4096,
        auto_start: bool = True
    ):
        """Initialize the OpenCode LLM adapter.

        Args:
            config_manager: Configuration manager for settings.
            state_manager: State manager for persistence.
            server_host: OpenCode server hostname. Defaults to "localhost".
            server_port: OpenCode server port. Defaults to 4096.
            auto_start: Whether to auto-start OpenCode server if not running.
                Defaults to True.
        """
        self.config_manager = config_manager
        self.state_manager = state_manager
        self.server_host = server_host
        self.server_port = server_port
        self.auto_start = auto_start
        self.server_process: Optional[subprocess.Popen] = None
        self.base_url = f"http://{server_host}:{server_port}"
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

        # Retry configuration
        self.max_retries = config_manager.get_setting("opencode.max_retries", 3)
        self.retry_delay = config_manager.get_setting("opencode.retry_delay", 1.0)
        self.connection_timeout = config_manager.get_setting("opencode.connection_timeout", 5.0)
        self.request_timeout = config_manager.get_setting("opencode.request_timeout", 300.0)
        self.server_start_timeout = config_manager.get_setting("opencode.server_start_timeout", 10.0)

    async def _check_server_health(self, timeout: float = None) -> bool:
        """Check if OpenCode server is accessible.

        Args:
            timeout: Connection timeout in seconds. Defaults to connection_timeout.

        Returns:
            True if server is accessible, False otherwise.
        """
        timeout = timeout or self.connection_timeout
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                # Try health endpoint first
                try:
                    response = await client.get(f"{self.base_url}/global/health")
                    if response.status_code == 200:
                        logger.debug(f"OpenCode server is running at {self.base_url}")
                        return True
                except Exception:
                    pass

                # Try root endpoint when model endpoint is not available
                try:
                    response = await client.get(f"{self.base_url}/")
                    if response.status_code in [200, 404]:  # 404 is OK, means server is responding
                        logger.debug(f"OpenCode server is running at {self.base_url}")
                        return True
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"OpenCode server not accessible: {e}")

        return False

    async def _ensure_server_running(self) -> bool:
        """Ensure OpenCode server is running with retry logic.

        Checks if server is accessible, and if not and auto_start is enabled,
        attempts to start the server with retries.

        Returns:
            True if server is running, False otherwise.
        """
        # Check if server is already running (with retry)
        for attempt in range(self.max_retries):
            if await self._check_server_health():
                return True

            if attempt < self.max_retries - 1:
                logger.debug(f"Server check attempt {attempt + 1}/{self.max_retries} failed, retrying...")
                await asyncio.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff

        # If auto_start is enabled, try to start the server
        if self.auto_start and not self.server_process:
            return await self._start_server_with_retry()

        logger.warning(f"OpenCode server is not running at {self.base_url}")
        return False

    async def _start_server_with_retry(self) -> bool:
        """Start OpenCode server with retry logic.

        Returns:
            True if server started successfully, False otherwise.
        """
        logger.info(f"Attempting to start OpenCode server on port {self.server_port}")

        for attempt in range(self.max_retries):
            try:
                # Check if server is already running (maybe started externally)
                if await self._check_server_health(timeout=2.0):
                    logger.info(f"OpenCode server is already running at {self.base_url}")
                    return True

                # Try to start OpenCode server
                if self.server_process is None or self.server_process.poll() is not None:
                    try:
                        self.server_process = subprocess.Popen(
                            ["opencode", "serve", "--port", str(self.server_port)],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                        )
                    except FileNotFoundError:
                        logger.warning("OpenCode command not found. Please install OpenCode or start server manually.")
                        return False
                    except Exception as e:
                        logger.error(f"Failed to start OpenCode server process: {e}")
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(self.retry_delay * (attempt + 1))
                            continue
                        return False

                # Wait for server to start (with timeout)
                max_wait_time = self.server_start_timeout
                check_interval = 0.5
                waited = 0.0

                while waited < max_wait_time:
                    await asyncio.sleep(check_interval)
                    waited += check_interval

                    if await self._check_server_health(timeout=2.0):
                        logger.info(f"OpenCode server started successfully at {self.base_url}")
                        return True

                    # Check if process died
                    if self.server_process.poll() is not None:
                        logger.warning(f"OpenCode server process exited with code {self.server_process.returncode}")
                        self.server_process = None
                        break

                # If we get here, server didn't start in time
                if attempt < self.max_retries - 1:
                    logger.warning(f"Server start attempt {attempt + 1}/{self.max_retries} timed out, retrying...")
                    if self.server_process:
                        try:
                            self.server_process.terminate()
                            self.server_process.wait(timeout=2)
                        except Exception:
                            pass
                        self.server_process = None
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error(f"Failed to start OpenCode server after {self.max_retries} attempts")
                    if self.server_process:
                        try:
                            self.server_process.terminate()
                            self.server_process.wait(timeout=2)
                        except Exception:
                            pass
                        self.server_process = None
                    return False

            except Exception as e:
                logger.error(f"Error starting OpenCode server (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    return False

        return False

    async def _create_session(
        self,
        model: Optional[str],
        provider: str
    ) -> Optional[str]:
        """Create a new OpenCode session with retry logic.

        Args:
            model: Model name (e.g. anthropic/claude-sonnet-4-5) or None to use OpenCode default.
            provider: Provider name (e.g., "anthropic").

        Returns:
            Session ID if successful, None otherwise.
        """
        if not await self._ensure_server_running():
            return None

        # OpenCode uses format provider/model (e.g. anthropic/claude-sonnet-4-5). If model is None/empty, omit so OpenCode uses its default.
        payload: Dict[str, Any] = {"config": {}}
        if model and model.strip():
            opencode_model = model if "/" in model else f"{provider}/{model}"
            payload["model"] = opencode_model

        # Retry session creation
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.connection_timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/session/create",
                        json=payload
                    )
                    if response.status_code == 200:
                        data = response.json()
                        session_id = data.get("id") or data.get("sessionId")
                        logger.debug(f"Created OpenCode session: {session_id}")
                        return session_id
                    elif response.status_code in [429, 503]:  # Rate limit or service unavailable
                        if attempt < self.max_retries - 1:
                            wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                            logger.warning(f"Rate limited or service unavailable, retrying in {wait_time}s...")
                            await asyncio.sleep(wait_time)
                            continue
                    else:
                        logger.error(f"Failed to create OpenCode session: {response.status_code} {response.text}")
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(self.retry_delay * (attempt + 1))
                            continue
                        return None
            except httpx.TimeoutException:
                logger.warning(f"Session creation timed out (attempt {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                return None
            except Exception as e:
                logger.error(f"Error creating OpenCode session (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                return None

        return None

    REFLECTOR_AGENT_ID = "reflector"

    async def call_llm_once(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Send a single prompt to OpenCode and return the full response text.

        Creates or reuses a dedicated session when a single LLM call is needed.

        Args:
            prompt: Full prompt text to send.
            context: Optional context dict (passed to OpenCode).

        Returns:
            Concatenated text content from all chunks. Empty string on error.
        """
        # Use opencode.model if set; otherwise None so OpenCode uses its default (no hardcoded model).
        model_config = {
            "provider": self.config_manager.get_setting("opencode.model_provider", "anthropic"),
            "model": self.config_manager.get_setting("opencode.model"),
        }
        session_id = self.active_sessions.get(self.REFLECTOR_AGENT_ID, {}).get("session_id")
        if not session_id:
            session_id = await self._create_session(
                model_config.get("model"),
                model_config.get("provider", "anthropic"),
            )
            if not session_id:
                return ""
            self.active_sessions[self.REFLECTOR_AGENT_ID] = {
                "session_id": session_id,
                "agent_type": "reflector",
                "status": "running",
            }
        parts: List[str] = []
        async for chunk in self._send_prompt(session_id, prompt, context, tools=None):
            if chunk.get("type") in ("chunk", "complete") and chunk.get("content"):
                parts.append(chunk["content"])
            if chunk.get("type") == "error":
                logger.warning("call_llm_once error chunk: %s", chunk.get("content"))
                break
        if self.REFLECTOR_AGENT_ID in self.active_sessions:
            self.active_sessions[self.REFLECTOR_AGENT_ID]["status"] = "completed"
        return "".join(parts)

    async def _send_prompt(
        self,
        session_id: str,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        agent: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Send a prompt to OpenCode session and stream response.

        Args:
            session_id: OpenCode session ID.
            prompt: Prompt text to send.
            context: Optional context dictionary.
            tools: Optional tool definitions.
            agent: Optional agent name; if set, the server runs that agent for this message.

        Yields:
            Chunks in Manifest format.
        """
        if not await self._ensure_server_running():
            yield {"type": "error", "content": "OpenCode server is not running"}
            return

        try:
            payload: Dict[str, Any] = {"prompt": prompt}
            if context:
                payload["context"] = context
            if tools:
                payload["tools"] = tools
            if agent:
                payload["agent"] = agent

            async with httpx.AsyncClient(timeout=self.request_timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/session/{session_id}/prompt",
                    json=payload
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        yield {"type": "error", "content": f"OpenCode API error: {error_text.decode()}"}
                        return

                    full_content = ""
                    tool_calls = []

                    # OpenCode may use SSE or JSON streaming
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue

                        # Try to parse as JSON (OpenCode may use JSON streaming)
                        try:
                            data = json.loads(line)
                            # Convert OpenCode response format to Manifest format
                            if "type" in data:
                                event_type = data.get("type")
                                if event_type == "chunk" or event_type == "text":
                                    text = data.get("content") or data.get("text", "")
                                    if text:
                                        full_content += text
                                        yield {"type": "chunk", "content": text}
                                elif event_type == "tool_use" or event_type == "tool":
                                    tool_call = data.get("tool_call") or data.get("tool")
                                    if tool_call:
                                        tool_calls.append(tool_call)
                                        yield {
                                            "type": "tool_use",
                                            "tool_call": tool_call
                                        }
                                elif event_type == "complete" or event_type == "done":
                                    if full_content:
                                        yield {"type": "complete", "content": full_content}
                                    if tool_calls:
                                        yield {"type": "tool_use_complete", "tool_calls": tool_calls}
                                    break
                                elif event_type == "error":
                                    yield {"type": "error", "content": data.get("content") or data.get("error", "Unknown error")}
                                    return
                        except json.JSONDecodeError:
                            # If not JSON, treat as plain text chunk
                            if line.strip():
                                full_content += line + "\n"
                                yield {"type": "chunk", "content": line + "\n"}

                    # If we didn't get a complete event, yield it now
                    if full_content and not any(c.get("type") == "complete" for c in [{"type": "complete"}]):
                        yield {"type": "complete", "content": full_content}
                    if tool_calls:
                        yield {"type": "tool_use_complete", "tool_calls": tool_calls}

        except Exception as e:
            logger.error(f"Error sending prompt to OpenCode: {e}", exc_info=True)
            yield {"type": "error", "content": str(e)}

    def _convert_opencode_chunk(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert OpenCode response chunk to Manifest format.

        Args:
            data: OpenCode response data dictionary.

        Returns:
            Manifest-format chunk dictionary or None if not convertible.
        """
        # Handle various OpenCode response formats
        event_type = data.get("type") or data.get("event")

        # Check for complete/done/stop first (before text content check)
        if event_type == "complete" or event_type == "done" or event_type == "stop":
            content = data.get("content") or ""
            return {"type": "complete", "content": content}

        elif event_type == "chunk" or event_type == "text" or ("text" in data and event_type not in ["complete", "done", "stop"]) or ("content" in data and event_type not in ["complete", "done", "stop"]):
            text = data.get("content") or data.get("text") or data.get("delta", "")
            if text:
                return {"type": "chunk", "content": text}

        elif event_type == "tool_use" or event_type == "tool" or "tool_call" in data or "tool" in data:
            tool_call = data.get("tool_call") or data.get("tool") or {}
            # Normalize tool call format
            if isinstance(tool_call, dict):
                return {
                    "type": "tool_use",
                    "tool_call": {
                        "id": tool_call.get("id") or tool_call.get("call_id"),
                        "name": tool_call.get("name") or tool_call.get("tool_name"),
                        "input": tool_call.get("input") or tool_call.get("arguments") or {}
                    }
                }

        elif event_type == "complete" or event_type == "done" or event_type == "stop":
            content = data.get("content") or ""
            return {"type": "complete", "content": content}

        elif event_type == "error":
            return {
                "type": "error",
                "content": data.get("content") or data.get("error") or data.get("message") or "Unknown error"
            }

        # If no recognized type, try to extract text content
        if "content" in data:
            return {"type": "chunk", "content": str(data["content"])}

        return None

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
        """Execute an agent using OpenCode.

        Args:
            agent_id: Agent identifier.
            agent_type: Type of agent.
            prompt: Agent prompt.
            model_config: Model configuration.
            context: Additional context.
            message_history: Previous message history.
            tools: Optional tool definitions.

        Yields:
            Chunks in Manifest format.
        """
        provider = model_config.get("provider", "anthropic")
        # Use agent model, then opencode.model setting; None means OpenCode default.
        model = model_config.get("model")
        if model is None:
            model = self.config_manager.get_setting("opencode.model")

        # Create or reuse session for this agent
        session_id = self.active_sessions.get(agent_id, {}).get("session_id")
        if not session_id:
            session_id = await self._create_session(model, provider)
            if not session_id:
                yield {"type": "error", "content": "Failed to create OpenCode session"}
                return

            self.active_sessions[agent_id] = {
                "session_id": session_id,
                "agent_type": agent_type,
                "status": "running"
            }

        # Prepare prompt (combine system and user if needed)
        full_prompt = prompt or ""
        if message_history:
            # Append message history to prompt
            history_text = "\n".join([
                f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                for msg in message_history[-5:]  # Last 5 messages
            ])
            if history_text:
                full_prompt = f"{full_prompt}\n\nPrevious conversation:\n{history_text}"

        async for chunk in self._send_prompt(
            session_id, full_prompt, context, tools, agent=agent_type
        ):
            yield chunk

        # Update session status
        if agent_id in self.active_sessions:
            self.active_sessions[agent_id]["status"] = "completed"
            self.active_sessions[agent_id]["completed_at"] = time.time()

    def get_session_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of an agent session.

        Args:
            agent_id: Agent identifier.

        Returns:
            Session status dictionary or None.
        """
        return self.active_sessions.get(agent_id)

    def stop_session(self, agent_id: str) -> bool:
        """Stop an active agent session.

        Args:
            agent_id: Agent identifier.

        Returns:
            True if stopped, False otherwise.
        """
        if agent_id in self.active_sessions:
            self.active_sessions[agent_id]["status"] = "stopped"
            self.active_sessions[agent_id]["stopped_at"] = time.time()
            return True
        return False

    async def cleanup_old_sessions(self, max_age_seconds: float = 3600.0) -> int:
        """Clean up old completed/stopped sessions.

        Args:
            max_age_seconds: Maximum age in seconds for sessions to keep.

        Returns:
            Number of sessions cleaned up.
        """
        current_time = time.time()
        cleaned = 0

        sessions_to_remove = []
        for agent_id, session_data in self.active_sessions.items():
            status = session_data.get("status")
            if status in ["completed", "stopped"]:
                completed_at = session_data.get("completed_at") or session_data.get("stopped_at")
                if completed_at and (current_time - completed_at) > max_age_seconds:
                    sessions_to_remove.append(agent_id)

        for agent_id in sessions_to_remove:
            del self.active_sessions[agent_id]
            cleaned += 1

        if cleaned > 0:
            logger.debug(f"Cleaned up {cleaned} old OpenCode sessions")

        return cleaned

    def __del__(self):
        """Stop server process if we started it."""
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            except Exception:
                pass
