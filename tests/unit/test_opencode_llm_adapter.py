"""
Unit tests for OpenCode LLM adapter.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from manifest.runtime.opencode_llm_adapter import OpenCodeLLMAdapter
from manifest.core.config import ConfigManager
from manifest.core.state_manager import StateManager
from pathlib import Path


@pytest.fixture
def mock_config_manager():
    """Create a mock config manager."""
    config = Mock(spec=ConfigManager)
    config.get_setting = Mock(side_effect=lambda key, default=None: default)
    return config


@pytest.fixture
def mock_state_manager(tmp_path):
    """Create a mock state manager."""
    state = Mock(spec=StateManager)
    state.manifest_dir = tmp_path
    return state


@pytest.fixture
def adapter(mock_config_manager, mock_state_manager):
    """Create an OpenCode adapter instance."""
    return OpenCodeLLMAdapter(
        mock_config_manager,
        mock_state_manager,
        server_host="localhost",
        server_port=4096,
        auto_start=False  # Don't auto-start in tests
    )


@pytest.mark.asyncio
async def test_ensure_server_running_when_running(adapter):
    """Test that ensure_server_running returns True when server is running."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

        result = await adapter._ensure_server_running()
        assert result is True


@pytest.mark.asyncio
async def test_ensure_server_running_when_not_running(adapter):
    """Test that ensure_server_running returns False when server is not running."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=Exception("Connection refused"))

        result = await adapter._ensure_server_running()
        assert result is False


@pytest.mark.asyncio
async def test_create_session_success(adapter):
    """Test successful session creation."""
    with patch.object(adapter, "_ensure_server_running", return_value=True):
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json = Mock(return_value={"id": "test-session-123"})
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            session_id = await adapter._create_session("claude-3-5-sonnet-20241022", "anthropic")
            assert session_id == "test-session-123"


@pytest.mark.asyncio
async def test_create_session_failure(adapter):
    """Test session creation failure."""
    with patch.object(adapter, "_ensure_server_running", return_value=False):
        session_id = await adapter._create_session("claude-3-5-sonnet-20241022", "anthropic")
        assert session_id is None


@pytest.mark.asyncio
async def test_convert_opencode_chunk_text(adapter):
    """Test conversion of text chunk."""
    data = {"type": "chunk", "content": "Hello world"}
    chunk = adapter._convert_opencode_chunk(data)
    assert chunk == {"type": "chunk", "content": "Hello world"}


@pytest.mark.asyncio
async def test_convert_opencode_chunk_tool_use(adapter):
    """Test conversion of tool use chunk."""
    data = {
        "type": "tool_use",
        "tool_call": {
            "id": "call_123",
            "name": "read_file",
            "input": {"path": "test.py"}
        }
    }
    chunk = adapter._convert_opencode_chunk(data)
    assert chunk["type"] == "tool_use"
    assert chunk["tool_call"]["id"] == "call_123"
    assert chunk["tool_call"]["name"] == "read_file"


@pytest.mark.asyncio
async def test_convert_opencode_chunk_complete(adapter):
    """Test conversion of complete chunk."""
    data = {"type": "complete", "content": "Done"}
    chunk = adapter._convert_opencode_chunk(data)
    assert chunk is not None
    assert chunk["type"] == "complete"
    assert chunk["content"] == "Done"


@pytest.mark.asyncio
async def test_convert_opencode_chunk_error(adapter):
    """Test conversion of error chunk."""
    data = {"type": "error", "error": "Something went wrong"}
    chunk = adapter._convert_opencode_chunk(data)
    assert chunk["type"] == "error"
    assert "Something went wrong" in chunk["content"]


@pytest.mark.asyncio
async def test_execute_agent_creates_session(adapter):
    """Test that execute_agent creates a session if needed."""
    model_config = {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "api_key": "test-key"
    }

    async def mock_send_prompt(*args, **kwargs):
        yield {"type": "complete", "content": "Response"}

    with patch.object(adapter, "_create_session", return_value="test-session") as mock_create:
        with patch.object(adapter, "_send_prompt", side_effect=mock_send_prompt):
            chunks = []
            async for chunk in adapter.execute_agent(
                "test-agent",
                "coder",
                "Test prompt",
                model_config
            ):
                chunks.append(chunk)

            mock_create.assert_called_once()
            assert len(chunks) > 0


@pytest.mark.asyncio
async def test_execute_agent_reuses_session(adapter):
    """Test that execute_agent reuses existing session."""
    model_config = {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "api_key": "test-key"
    }

    # Pre-create session
    adapter.active_sessions["test-agent"] = {
        "session_id": "existing-session",
        "agent_type": "coder",
        "status": "running"
    }

    async def mock_send_prompt(*args, **kwargs):
        yield {"type": "complete", "content": "Response"}

    with patch.object(adapter, "_create_session") as mock_create:
        with patch.object(adapter, "_send_prompt", side_effect=mock_send_prompt):
            chunks = []
            async for chunk in adapter.execute_agent(
                "test-agent",
                "coder",
                "Test prompt",
                model_config
            ):
                chunks.append(chunk)

            # Should not create new session
            mock_create.assert_not_called()


@pytest.mark.asyncio
async def test_get_session_status(adapter):
    """Test getting session status."""
    adapter.active_sessions["test-agent"] = {
        "session_id": "test-session",
        "agent_type": "coder",
        "status": "running"
    }

    status = adapter.get_session_status("test-agent")
    assert status is not None
    assert status["session_id"] == "test-session"
    assert status["status"] == "running"


@pytest.mark.asyncio
async def test_stop_session(adapter):
    """Test stopping a session."""
    adapter.active_sessions["test-agent"] = {
        "session_id": "test-session",
        "agent_type": "coder",
        "status": "running"
    }

    result = adapter.stop_session("test-agent")
    assert result is True
    assert adapter.active_sessions["test-agent"]["status"] == "stopped"


@pytest.mark.asyncio
async def test_stop_session_not_found(adapter):
    """Test stopping a non-existent session."""
    result = adapter.stop_session("non-existent")
    assert result is False
