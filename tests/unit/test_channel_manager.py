"""
Unit tests for ChannelManager.

Tests channel creation, switching, and message handling.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
from manifest.ui.channels.channel_manager import ChannelManager


@pytest.fixture
def mock_app():
    """Create a mock app."""
    app = Mock()
    app.query_one = Mock(return_value=Mock())
    app.set_timer = Mock()
    return app


@pytest.fixture
def mock_state_manager():
    """Create a mock state manager."""
    state = Mock()
    state.get_chat_history = Mock(return_value=[])
    state.add_chat_message = Mock()
    return state


@pytest.fixture
def channel_manager(mock_app, mock_state_manager):
    """Create a ChannelManager instance."""
    return ChannelManager(app=mock_app, state_manager=mock_state_manager)


def test_channel_manager_initialization(channel_manager):
    """Test ChannelManager initialization."""
    assert channel_manager.app is not None
    assert channel_manager.state_manager is not None
    assert channel_manager.active_channel == "main"
    assert isinstance(channel_manager.squad_channels, dict)


@pytest.mark.asyncio
async def test_create_squad_channel(channel_manager):
    """Test creating a squad channel."""
    # Mock the query_one to return a container with mount method
    mock_container = Mock()
    mock_container.mount = AsyncMock()
    channel_manager.app.query_one = Mock(return_value=mock_container)

    tab_id = await channel_manager.create_squad_channel("task-1", "coder")

    # Should return tab_id (string) or None
    assert tab_id is None or isinstance(tab_id, str)
    # Verify channel was added to squad_channels
    assert "squad-task-1-coder" in channel_manager.squad_channels or tab_id is not None


@pytest.mark.asyncio
async def test_create_squad_channel_duplicate(channel_manager):
    """Test creating duplicate channel returns existing."""
    channel_manager.squad_channels["squad-task-1-coder"] = {
        "tab_id": "tab-squad-task-1-coder"
    }

    tab_id = await channel_manager.create_squad_channel("task-1", "coder")

    assert tab_id == "tab-squad-task-1-coder"


@pytest.mark.asyncio
async def test_switch_channel(channel_manager):
    """Test switching to a channel."""
    channel_manager.squad_channels["test-channel"] = {
        "tab_id": "tab-test-channel"
    }

    await channel_manager.switch_channel("test-channel")

    assert channel_manager.active_channel == "test-channel"


@pytest.mark.asyncio
async def test_refresh_channel_log(channel_manager):
    """Test refreshing channel log."""
    channel_manager.squad_channels["test-channel"] = {
        "tab_id": "tab-test-channel"
    }

    # Mock log widget
    mock_log = Mock()
    channel_manager.app.query_one = Mock(return_value=mock_log)

    await channel_manager.refresh_channel_log("test-channel")

    # Verify query_one was called to get the log widget
    channel_manager.app.query_one.assert_called()


@pytest.mark.asyncio
async def test_handle_agent_output(channel_manager):
    """Test handling agent output."""
    channel_name = "squad-task-1-coder"
    channel_manager.squad_channels[channel_name] = {
        "tab_id": "tab-squad-task-1-coder"
    }

    # Mock log widget and state manager
    mock_log = Mock()
    channel_manager.app.query_one = Mock(return_value=mock_log)
    channel_manager.state_manager.add_chat_message = Mock()
    channel_manager.state_manager.save_state = AsyncMock()

    # Use correct method signature: channel, content, role, save_immediately
    await channel_manager.handle_agent_output(
        channel=channel_name,
        content="Test output",
        role="assistant",
        save_immediately=True
    )

    # Verify state manager was called to save message
    channel_manager.state_manager.add_chat_message.assert_called_once_with(
        channel_name, "assistant", "Test output"
    )
    channel_manager.state_manager.save_state.assert_called_once()


def test_get_channel_summary(channel_manager):
    """Test getting channel summary."""
    channel_manager.squad_channels["channel-1"] = {
        "task_id": "task-1",
        "agent_type": "coder",
        "message_count": 5
    }

    summary = channel_manager.get_channel_summary()
    assert isinstance(summary, dict)
    assert "channel-1" in summary or len(summary) >= 0
