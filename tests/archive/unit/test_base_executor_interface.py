"""
Tests for BaseAgentExecutor interface compliance.
"""
import pytest
from unittest.mock import Mock, AsyncMock
from manifest.runtime.agent.core.base_executor import BaseAgentExecutor
from manifest.runtime.agent.core.executor import AgentExecutor
from manifest.runtime.opencode_llm_adapter import OpenCodeLLMAdapter
from manifest.core.config import ConfigManager
from manifest.core.state_manager import StateManager


def test_base_executor_is_abstract():
    """Test that BaseAgentExecutor is abstract and cannot be instantiated."""
    with pytest.raises(TypeError):
        BaseAgentExecutor()


def test_agent_executor_implements_interface():
    """Test that AgentExecutor implements BaseAgentExecutor interface."""
    config_manager = Mock(spec=ConfigManager)
    state_manager = Mock(spec=StateManager)

    executor = AgentExecutor(config_manager, state_manager)

    # Check that it's an instance of BaseAgentExecutor
    assert isinstance(executor, BaseAgentExecutor)

    # Check that required methods exist
    assert hasattr(executor, "execute_agent")
    assert hasattr(executor, "get_session_status")
    assert hasattr(executor, "stop_session")

    # Check that execute_agent is async generator (returns AsyncIterator)
    import inspect
    # execute_agent is an async generator, not a coroutine function
    assert inspect.isasyncgenfunction(executor.execute_agent) or inspect.iscoroutinefunction(executor.execute_agent)


def test_opencode_adapter_implements_interface():
    """Test that OpenCodeLLMAdapter implements BaseAgentExecutor interface."""
    config_manager = Mock(spec=ConfigManager)
    config_manager.get_setting = Mock(return_value=None)
    state_manager = Mock(spec=StateManager)

    adapter = OpenCodeLLMAdapter(config_manager, state_manager, auto_start=False)

    # Check that it's an instance of BaseAgentExecutor
    assert isinstance(adapter, BaseAgentExecutor)

    # Check that required methods exist
    assert hasattr(adapter, "execute_agent")
    assert hasattr(adapter, "get_session_status")
    assert hasattr(adapter, "stop_session")

    # Check that execute_agent is async generator (returns AsyncIterator)
    import inspect
    # execute_agent is an async generator, not a coroutine function
    assert inspect.isasyncgenfunction(adapter.execute_agent) or inspect.iscoroutinefunction(adapter.execute_agent)


@pytest.mark.asyncio
async def test_executor_chunk_format_consistency():
    """Test that executors return consistent chunk formats."""
    config_manager = Mock(spec=ConfigManager)
    config_manager.get_api_key = Mock(return_value="test-key")
    config_manager.get_setting = Mock(return_value=None)
    state_manager = Mock(spec=StateManager)

    executor = AgentExecutor(config_manager, state_manager)

    model_config = {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "api_key": "test-key"
    }

    # Mock response
    async def mock_aiter_lines():
        yield 'data: {"type": "content_block_delta", "delta": {"text": "Hello"}}'
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

    from unittest.mock import patch
    with patch("httpx.AsyncClient", return_value=mock_client_context):
        chunks = []
        async for chunk in executor.execute_agent(
            agent_id="test",
            agent_type="test",
            prompt="Test",
            model_config=model_config
        ):
            chunks.append(chunk)

        # Verify chunk format
        for chunk in chunks:
            assert "type" in chunk
            assert chunk["type"] in ["chunk", "complete", "error", "tool_use", "tool_use_complete"]

            if chunk["type"] in ["chunk", "complete", "error"]:
                assert "content" in chunk
            elif chunk["type"] in ["tool_use"]:
                assert "tool_call" in chunk
            elif chunk["type"] == "tool_use_complete":
                assert "tool_calls" in chunk


def test_get_session_status_returns_dict_or_none():
    """Test that get_session_status returns dict or None."""
    config_manager = Mock(spec=ConfigManager)
    state_manager = Mock(spec=StateManager)

    executor = AgentExecutor(config_manager, state_manager)

    # Non-existent session
    status = executor.get_session_status("nonexistent")
    assert status is None

    # Existing session
    executor.active_sessions["test"] = {
        "session_id": "sess_123",
        "agent_type": "test",
        "status": "running"
    }

    status = executor.get_session_status("test")
    assert isinstance(status, dict)
    assert "status" in status
    assert "session_id" in status


def test_stop_session_returns_bool():
    """Test that stop_session returns boolean."""
    config_manager = Mock(spec=ConfigManager)
    state_manager = Mock(spec=StateManager)

    executor = AgentExecutor(config_manager, state_manager)

    # Non-existent session
    result = executor.stop_session("nonexistent")
    assert isinstance(result, bool)
    assert result is False

    # Existing session
    executor.active_sessions["test"] = {
        "session_id": "sess_123",
        "agent_type": "test",
        "status": "running"
    }

    result = executor.stop_session("test")
    assert isinstance(result, bool)
    assert result is True
    assert executor.active_sessions["test"]["status"] == "stopped"
