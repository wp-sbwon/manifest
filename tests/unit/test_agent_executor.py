"""
Unit tests for AgentExecutor.
Tests LLM API integration using mocks (no real API keys needed).
"""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import AsyncIterator
from manifest.runtime.agent.core.executor import AgentExecutor
from manifest.core.config import ConfigManager
from manifest.core.state_manager import StateManager


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
def executor(mock_config_manager, mock_state_manager):
    """Create AgentExecutor instance."""
    return AgentExecutor(mock_config_manager, mock_state_manager)


@pytest.mark.asyncio
async def test_executor_initialization(executor):
    """Test AgentExecutor initialization."""
    assert executor.config_manager is not None
    assert executor.state_manager is not None
    assert executor.active_sessions == {}


@pytest.mark.asyncio
async def test_execute_agent_no_api_key(executor):
    """Test execute_agent without API key."""
    model_config = {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "api_key": None  # No API key
    }

    chunks = []
    async for chunk in executor.execute_agent(
        agent_id="test-agent",
        agent_type="coder",
        prompt="Test prompt",
        model_config=model_config
    ):
        chunks.append(chunk)

    assert len(chunks) == 1
    assert chunks[0]["type"] == "error"
    assert "API key not provided" in chunks[0]["content"]


@pytest.mark.asyncio
async def test_execute_agent_unsupported_provider(executor):
    """Test execute_agent with unsupported provider."""
    model_config = {
        "provider": "unsupported",
        "model": "test-model",
        "api_key": "test-key"
    }

    chunks = []
    async for chunk in executor.execute_agent(
        agent_id="test-agent",
        agent_type="coder",
        prompt="Test prompt",
        model_config=model_config
    ):
        chunks.append(chunk)

    assert len(chunks) == 1
    assert chunks[0]["type"] == "error"
    assert "Unsupported provider" in chunks[0]["content"]


@pytest.mark.asyncio
async def test_execute_agent_anthropic_mock(executor):
    """Test execute_agent with Anthropic provider (mocked)."""
    model_config = {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "api_key": "test-key"
    }

    # Mock httpx.AsyncClient.stream response
    async def mock_aiter_lines():
        lines = [
            "data: {\"type\": \"content_block_delta\", \"delta\": {\"text\": \"Hello\"}}",
            "data: {\"type\": \"content_block_delta\", \"delta\": {\"text\": \" World\"}}",
            "data: [DONE]"
        ]
        for line in lines:
            yield line

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.aiter_lines = mock_aiter_lines

    # Create proper async context manager for stream
    mock_stream_context = AsyncMock()
    mock_stream_context.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream_context.__aexit__ = AsyncMock(return_value=None)

    mock_client = AsyncMock()
    mock_client.stream = Mock(return_value=mock_stream_context)

    # Mock AsyncClient as context manager
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

    # Should have chunks and complete
    assert len(chunks) >= 2
    chunk_types = [c["type"] for c in chunks]
    assert "chunk" in chunk_types
    assert "complete" in chunk_types

    # Check session was created
    status = executor.get_session_status("test-agent")
    assert status is not None
    assert status["status"] == "completed"


@pytest.mark.asyncio
async def test_execute_agent_openai_mock(executor):
    """Test execute_agent with OpenAI provider (mocked)."""
    model_config = {
        "provider": "openai",
        "model": "gpt-4",
        "api_key": "test-key"
    }

    # Mock httpx.AsyncClient.stream response
    async def mock_aiter_lines():
        lines = [
            "data: {\"choices\": [{\"delta\": {\"content\": \"Hello\"}}]}",
            "data: {\"choices\": [{\"delta\": {\"content\": \" World\"}}]}",
            "data: [DONE]"
        ]
        for line in lines:
            yield line

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.aiter_lines = mock_aiter_lines

    # Create proper async context manager for stream
    mock_stream_context = AsyncMock()
    mock_stream_context.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream_context.__aexit__ = AsyncMock(return_value=None)

    mock_client = AsyncMock()
    mock_client.stream = Mock(return_value=mock_stream_context)

    # Mock AsyncClient as context manager
    mock_client_context = AsyncMock()
    mock_client_context.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client_context.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client_context):
        chunks = []
        async for chunk in executor.execute_agent(
            agent_id="test-agent",
            agent_type="planner",
            prompt="Test prompt",
            model_config=model_config
        ):
            chunks.append(chunk)

    # Should have chunks and complete
    assert len(chunks) >= 2
    chunk_types = [c["type"] for c in chunks]
    assert "chunk" in chunk_types
    assert "complete" in chunk_types


@pytest.mark.asyncio
async def test_execute_agent_api_error(executor):
    """Test execute_agent with API error."""
    model_config = {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "api_key": "test-key"
    }

    # Mock httpx.AsyncClient.stream response with error
    mock_response = AsyncMock()
    mock_response.status_code = 401
    mock_response.aread = AsyncMock(return_value=b"Unauthorized")

    # Create proper async context manager for stream
    mock_stream_context = AsyncMock()
    mock_stream_context.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream_context.__aexit__ = AsyncMock(return_value=None)

    mock_client = AsyncMock()
    mock_client.stream = Mock(return_value=mock_stream_context)

    # Mock AsyncClient as context manager
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

    assert len(chunks) == 1
    assert chunks[0]["type"] == "error"
    assert "API error" in chunks[0]["content"]


def test_prepare_messages(executor):
    """Test _prepare_messages method."""
    prompt = "System message\n\n## User message"
    history = [{"role": "user", "content": "Previous message"}]

    messages = executor._prepare_messages(prompt, history)

    assert len(messages) == 3
    assert messages[0]["role"] == "system"
    assert "System message" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "Previous message"
    assert messages[2]["role"] == "user"
    assert "User message" in messages[2]["content"]


def test_prepare_messages_no_system(executor):
    """Test _prepare_messages without system message."""
    prompt = "Just a user message"
    history = []

    messages = executor._prepare_messages(prompt, history)

    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == prompt


def test_get_session_status(executor):
    """Test get_session_status."""
    # No session yet
    assert executor.get_session_status("nonexistent") is None

    # Create a session manually
    executor.active_sessions["test-agent"] = {
        "session_id": "test-session",
        "agent_type": "coder",
        "status": "running"
    }

    status = executor.get_session_status("test-agent")
    assert status is not None
    assert status["session_id"] == "test-session"
    assert status["status"] == "running"


def test_stop_session(executor):
    """Test stop_session."""
    # Create a session
    executor.active_sessions["test-agent"] = {
        "session_id": "test-session",
        "agent_type": "coder",
        "status": "running"
    }

    result = executor.stop_session("test-agent")
    assert result is True
    assert executor.active_sessions["test-agent"]["status"] == "stopped"

    # Stop non-existent session
    result = executor.stop_session("nonexistent")
    assert result is False


@pytest.mark.asyncio
async def test_execute_agent_with_message_history(executor):
    """Test execute_agent with message history."""
    model_config = {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "api_key": "test-key"
    }

    message_history = [
        {"role": "user", "content": "Previous question"},
        {"role": "assistant", "content": "Previous answer"}
    ]

    # Mock httpx response
    async def mock_aiter_lines():
        lines = [
            "data: {\"type\": \"content_block_delta\", \"delta\": {\"text\": \"Response\"}}",
            "data: [DONE]"
        ]
        for line in lines:
            yield line

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.aiter_lines = mock_aiter_lines

    # Create proper async context manager for stream
    mock_stream_context = AsyncMock()
    mock_stream_context.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream_context.__aexit__ = AsyncMock(return_value=None)

    mock_client = AsyncMock()
    mock_client.stream = Mock(return_value=mock_stream_context)

    # Mock AsyncClient as context manager
    mock_client_context = AsyncMock()
    mock_client_context.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client_context.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client_context):
        chunks = []
        async for chunk in executor.execute_agent(
            agent_id="test-agent",
            agent_type="coder",
            prompt="New prompt",
            model_config=model_config,
            message_history=message_history
        ):
            chunks.append(chunk)

    # Verify history was included in the call
    assert len(chunks) >= 1
    # The mock should have been called with messages including history
    assert mock_client.stream.called
