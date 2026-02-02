"""
Unit tests for AgentBridge.

Tests agent communication, execution, and lifecycle management.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
from manifest.bridge.agent_bridge import AgentBridge
from manifest.runtime.agent.core.executor_factory import ExecutorFactory


@pytest.fixture
def mock_state_manager(tmp_path):
    """Create a mock state manager."""
    state = Mock()
    state.get_task_checklist = Mock(return_value=[])
    state.add_chat_message = Mock()
    state.save_state = AsyncMock()
    state.manifest_dir = tmp_path / ".manifest"
    return state


@pytest.fixture
def mock_config_manager():
    """Create a mock config manager."""
    config = Mock()
    config.get_agent_model_config = Mock(return_value={"provider": "opencode"})
    return config


@pytest.fixture
def mock_executor():
    """Create a mock executor."""
    executor = AsyncMock()

    # Mock execute_agent to return an async generator that yields chunks
    # This properly handles async iteration to avoid coroutine warnings
    async def mock_execute_agent(*args, **kwargs):
        yield {"type": "complete", "content": "Test output"}
        return

    executor.execute_agent = mock_execute_agent
    return executor


@pytest.fixture
def agent_bridge(mock_state_manager, mock_config_manager, mock_executor, tmp_path):
    """Create an AgentBridge instance."""
    with patch('manifest.runtime.agent.core.executor_factory.ExecutorFactory') as mock_factory:
        mock_factory.create_executor = Mock(return_value=mock_executor)
        bridge = AgentBridge(
            state_manager=mock_state_manager,
            config_manager=mock_config_manager,
            working_dir=tmp_path
        )
        return bridge


def test_agent_bridge_initialization(agent_bridge):
    """Test AgentBridge initialization."""
    assert agent_bridge.state_manager is not None
    assert agent_bridge.config_manager is not None
    assert agent_bridge is not None


@pytest.mark.asyncio
async def test_start_agent_mission(agent_bridge):
    """Test starting an agent mission."""
    result = await agent_bridge.start_agent_mission(
        task_id="task-1",
        agent_type="coder",
        context={},
        model_config={"provider": "opencode"}
    )
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_get_agent_status(agent_bridge):
    """Test getting agent status."""
    status = await agent_bridge.get_agent_status("task-1")
    assert isinstance(status, dict) or status is None


def test_is_connected(agent_bridge):
    """Test checking connection status."""
    is_connected = agent_bridge.is_connected
    assert isinstance(is_connected, bool)
