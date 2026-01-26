"""
Extended unit tests for AgentExecutor.
Tests additional functionality like tool calls, context optimization, hooks, etc.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import AsyncIterator
from manifest.runtime.agent.core.executor import AgentExecutor
from manifest.core.config import ConfigManager
from manifest.core.state_manager import StateManager
from manifest.runtime.hooks.prompt_hooks import HookManager


@pytest.fixture
def mock_config_manager():
    """Create mock config manager."""
    config = Mock(spec=ConfigManager)
    config.get_api_key = Mock(return_value="test-api-key")
    return config


@pytest.fixture
def mock_state_manager():
    """Create mock state manager."""
    state = Mock(spec=StateManager)
    state.add_chat_message = Mock()
    state.save_state = AsyncMock(return_value=True)
    return state


@pytest.fixture
def mock_hook_manager():
    """Create mock hook manager."""
    hook_manager = Mock(spec=HookManager)
    hook_manager.apply_hooks = AsyncMock(side_effect=lambda **kwargs: kwargs.get("prompt", ""))
    return hook_manager


@pytest.fixture
def executor(mock_config_manager, mock_state_manager, mock_hook_manager):
    """Create AgentExecutor instance with hook manager."""
    return AgentExecutor(mock_config_manager, mock_state_manager, hook_manager=mock_hook_manager)


@pytest.mark.asyncio
async def test_execute_agent_with_tools(executor):
    """Test execute_agent with tool definitions."""
    model_config = {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "api_key": "test-key"
    }

    tools = [
        {
            "name": "read_file",
            "description": "Read a file",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"}
                }
            }
        }
    ]

    # Mock response with tool use
    async def mock_aiter_lines():
        lines = [
            'data: {"type": "message_start"}',
            'data: {"type": "content_block_start", "content_block": {"type": "text"}}',
            'data: {"type": "content_block_delta", "delta": {"text": "I will"}}',
            'data: {"type": "content_block_delta", "delta": {"type": "tool_use", "id": "toolu_123", "name": "read_file", "input": {"file_path": "test.py"}}}',
            'data: {"type": "content_block_stop"}',
            'data: {"type": "message_delta"}',
            'data: {"type": "message_stop"}',
            "data: [DONE]"
        ]
        for line in lines:
            yield line

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.aiter_lines = mock_aiter_lines

    mock_stream_context = AsyncMock()
    mock_stream_context.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream_context.__aexit__ = AsyncMock(return_value=None)

    mock_client = AsyncMock()
    mock_client.stream = Mock(return_value=mock_stream_context)

    mock_client_context = AsyncMock()
    mock_client_context.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client_context.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client_context):
        chunks = []
        async for chunk in executor.execute_agent(
            agent_id="test-agent",
            agent_type="coder",
            prompt="Test prompt",
            model_config=model_config,
            tools=tools
        ):
            chunks.append(chunk)

        # Should have chunks and potentially tool_use
        assert len(chunks) >= 1
        chunk_types = [c.get("type") for c in chunks]
        assert "chunk" in chunk_types or "tool_use" in chunk_types


@pytest.mark.asyncio
async def test_execute_agent_with_hooks(executor):
    """Test execute_agent with prompt hooks."""
    model_config = {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "api_key": "test-key"
    }

    # Mock hook to modify prompt
    executor.hook_manager.apply_hooks = AsyncMock(return_value="Modified prompt")

    async def mock_aiter_lines():
        yield 'data: {"type": "content_block_delta", "delta": {"text": "Response"}}'
        yield "data: [DONE]"

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.aiter_lines = mock_aiter_lines

    mock_stream_context = AsyncMock()
    mock_stream_context.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream_context.__aexit__ = AsyncMock(return_value=None)

    mock_client = AsyncMock()
    mock_client.stream = Mock(return_value=mock_stream_context)

    mock_client_context = AsyncMock()
    mock_client_context.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client_context.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client_context):
        chunks = []
        async for chunk in executor.execute_agent(
            agent_id="test-agent",
            agent_type="coder",
            prompt="Original prompt",
            model_config=model_config
        ):
            chunks.append(chunk)

        # Verify hook was called
        executor.hook_manager.apply_hooks.assert_called_once()
        assert len(chunks) >= 1


@pytest.mark.asyncio
async def test_execute_agent_with_context(executor):
    """Test execute_agent with context."""
    model_config = {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "api_key": "test-key"
    }

    context = {
        "tier_0": "Core context",
        "tier_1": "Extended context"
    }

    # Mock ContextSizeCalculator to avoid AttributeError
    with patch("manifest.runtime.agent.core.executor.ContextSizeCalculator") as mock_calc:
        mock_calc.estimate_tokens = Mock(return_value=100)
        mock_calc.estimate_context_tokens = Mock(return_value=50)
        mock_calc.get_model_token_limit = Mock(return_value=200000)
        # Mock RESPONSE_TOKEN_RESERVE if it doesn't exist
        if not hasattr(mock_calc, "RESPONSE_TOKEN_RESERVE"):
            mock_calc.RESPONSE_TOKEN_RESERVE = 4096

        async def mock_aiter_lines():
            yield 'data: {"type": "content_block_delta", "delta": {"text": "Response"}}'
            yield "data: [DONE]"

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.aiter_lines = mock_aiter_lines

        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_context.__aexit__ = AsyncMock(return_value=None)

        mock_client = AsyncMock()
        mock_client.stream = Mock(return_value=mock_stream_context)

        mock_client_context = AsyncMock()
        mock_client_context.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_context.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client_context):
            chunks = []
            async for chunk in executor.execute_agent(
                agent_id="test-agent",
                agent_type="coder",
                prompt="Test prompt",
                model_config=model_config,
                context=context
            ):
                chunks.append(chunk)

            # Verify context was passed to hooks
            executor.hook_manager.apply_hooks.assert_called_once()
            call_kwargs = executor.hook_manager.apply_hooks.call_args[1]
            assert call_kwargs["context"] == context
            assert len(chunks) >= 1


@pytest.mark.asyncio
async def test_execute_agent_network_error(executor):
    """Test execute_agent with network error."""
    model_config = {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "api_key": "test-key"
    }

    # Mock network error
    mock_client_context = AsyncMock()
    mock_client_context.__aenter__ = AsyncMock(side_effect=Exception("Network error"))
    mock_client_context.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client_context):
        chunks = []
        async for chunk in executor.execute_agent(
            agent_id="test-agent",
            agent_type="coder",
            prompt="Test prompt",
            model_config=model_config
        ):
            chunks.append(chunk)

        assert len(chunks) >= 1
        assert chunks[0]["type"] == "error"
        assert "Network error" in chunks[0]["content"]


@pytest.mark.asyncio
async def test_execute_agent_timeout(executor):
    """Test execute_agent with timeout."""
    model_config = {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "api_key": "test-key"
    }

    # Mock timeout error
    import httpx
    mock_client_context = AsyncMock()
    mock_client_context.__aenter__ = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))
    mock_client_context.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client_context):
        chunks = []
        async for chunk in executor.execute_agent(
            agent_id="test-agent",
            agent_type="coder",
            prompt="Test prompt",
            model_config=model_config
        ):
            chunks.append(chunk)

        assert len(chunks) >= 1
        assert chunks[0]["type"] == "error"


@pytest.mark.asyncio
async def test_execute_agent_rate_limit(executor):
    """Test execute_agent with rate limit error."""
    model_config = {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "api_key": "test-key"
    }

    # Mock rate limit response
    mock_response = AsyncMock()
    mock_response.status_code = 429
    mock_response.aread = AsyncMock(return_value=b"Rate limit exceeded")

    mock_stream_context = AsyncMock()
    mock_stream_context.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream_context.__aexit__ = AsyncMock(return_value=None)

    mock_client = AsyncMock()
    mock_client.stream = Mock(return_value=mock_stream_context)

    mock_client_context = AsyncMock()
    mock_client_context.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client_context.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client_context):
        chunks = []
        async for chunk in executor.execute_agent(
            agent_id="test-agent",
            agent_type="coder",
            prompt="Test prompt",
            model_config=model_config
        ):
            chunks.append(chunk)

        assert len(chunks) >= 1
        assert chunks[0]["type"] == "error"


def test_prepare_messages_with_tool_results(executor):
    """Test _prepare_messages with tool result content blocks."""
    prompt = "System message\n\n## User message"
    history = [
        {"role": "user", "content": "Previous message"},
        {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu_123",
                    "name": "read_file",
                    "input": {"file_path": "test.py"}
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_123",
                    "content": "File content"
                }
            ]
        }
    ]

    messages = executor._prepare_messages(prompt, history)

    # Should include tool result content blocks
    assert len(messages) >= 3
    # Find tool result message
    tool_result_found = False
    for msg in messages:
        if isinstance(msg.get("content"), list):
            for content_block in msg["content"]:
                if content_block.get("type") == "tool_result":
                    tool_result_found = True
                    break
    assert tool_result_found


def test_prepare_messages_empty_prompt(executor):
    """Test _prepare_messages with None prompt (continuing conversation)."""
    history = [
        {"role": "user", "content": "Previous message"},
        {"role": "assistant", "content": "Previous response"}
    ]

    messages = executor._prepare_messages(None, history)

    # Should only have history, no system message
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_execute_agent_session_tracking(executor):
    """Test that sessions are properly tracked."""
    model_config = {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "api_key": "test-key"
    }

    async def mock_aiter_lines():
        yield 'data: {"type": "content_block_delta", "delta": {"text": "Response"}}'
        yield "data: [DONE]"

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.aiter_lines = mock_aiter_lines

    mock_stream_context = AsyncMock()
    mock_stream_context.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream_context.__aexit__ = AsyncMock(return_value=None)

    mock_client = AsyncMock()
    mock_client.stream = Mock(return_value=mock_stream_context)

    mock_client_context = AsyncMock()
    mock_client_context.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client_context.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client_context):
        chunks = []
        async for chunk in executor.execute_agent(
            agent_id="test-agent-1",
            agent_type="coder",
            prompt="Test prompt",
            model_config=model_config
        ):
            chunks.append(chunk)

        # Check session was created
        status = executor.get_session_status("test-agent-1")
        assert status is not None
        assert status["status"] == "completed"
        assert status["agent_type"] == "coder"


@pytest.mark.asyncio
async def test_execute_agent_multiple_sessions(executor):
    """Test that multiple sessions can run concurrently."""
    model_config = {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "api_key": "test-key"
    }

    async def mock_aiter_lines():
        yield 'data: {"type": "content_block_delta", "delta": {"text": "Response"}}'
        yield "data: [DONE]"

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.aiter_lines = mock_aiter_lines

    mock_stream_context = AsyncMock()
    mock_stream_context.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream_context.__aexit__ = AsyncMock(return_value=None)

    mock_client = AsyncMock()
    mock_client.stream = Mock(return_value=mock_stream_context)

    mock_client_context = AsyncMock()
    mock_client_context.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client_context.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client_context):
        # Execute two agents
        chunks1 = []
        chunks2 = []

        async for chunk in executor.execute_agent(
            agent_id="agent-1",
            agent_type="planner",
            prompt="Prompt 1",
            model_config=model_config
        ):
            chunks1.append(chunk)

        async for chunk in executor.execute_agent(
            agent_id="agent-2",
            agent_type="coder",
            prompt="Prompt 2",
            model_config=model_config
        ):
            chunks2.append(chunk)

        # Both sessions should exist
        assert executor.get_session_status("agent-1") is not None
        assert executor.get_session_status("agent-2") is not None
        assert executor.get_session_status("agent-1")["agent_type"] == "planner"
        assert executor.get_session_status("agent-2")["agent_type"] == "coder"
