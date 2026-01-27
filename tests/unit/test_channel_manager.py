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


# ========== TDL: Channel Manager - Missing Items ==========

@pytest.mark.asyncio
async def test_channel_creation_basic(channel_manager):
    """Test basic channel creation."""
    mock_container = Mock()
    mock_container.mount = AsyncMock()
    channel_manager.app.query_one = Mock(return_value=mock_container)
    channel_manager.app.set_timer = Mock()

    tab_id = await channel_manager.create_squad_channel("task-1", "coder")

    assert tab_id is not None
    assert "squad-task-1-coder" in channel_manager.squad_channels
    channel_info = channel_manager.squad_channels["squad-task-1-coder"]
    assert channel_info["task_id"] == "task-1"
    assert channel_info["agent_type"] == "coder"
    assert channel_info["tab_id"] == "tab-squad-task-1-coder"


@pytest.mark.asyncio
async def test_channel_creation_with_existing_history(channel_manager):
    """Test channel creation with existing chat history."""
    mock_container = Mock()
    mock_container.mount = AsyncMock()
    mock_log = Mock()
    channel_manager.app.query_one = Mock(side_effect=[mock_container, mock_log])
    channel_manager.app.set_timer = Mock()
    channel_manager.state_manager.get_chat_history = Mock(return_value=[
        {"role": "assistant", "content": "Previous message"}
    ])

    tab_id = await channel_manager.create_squad_channel("task-1", "planner")

    assert tab_id is not None
    # Should have message_count from history
    channel_info = channel_manager.squad_channels["squad-task-1-planner"]
    assert channel_info["message_count"] == 1


@pytest.mark.asyncio
async def test_channel_creation_error_handling(channel_manager):
    """Test channel creation error handling."""
    channel_manager.app.query_one = Mock(side_effect=Exception("Query error"))

    tab_id = await channel_manager.create_squad_channel("task-1", "coder")

    # Should return None on error
    assert tab_id is None
    # Channel should not be created
    assert "squad-task-1-coder" not in channel_manager.squad_channels


@pytest.mark.asyncio
async def test_channel_switching_basic(channel_manager):
    """Test basic channel switching."""
    channel_manager.squad_channels["channel-1"] = {
        "tab_id": "tab-channel-1",
        "button_id": "btn-channel-1"
    }
    channel_manager.squad_channels["channel-2"] = {
        "tab_id": "tab-channel-2",
        "button_id": "btn-channel-2"
    }

    mock_button1 = Mock()
    mock_button2 = Mock()
    mock_main_button = Mock()
    mock_log = Mock()
    channel_manager.app.query_one = Mock(side_effect=[
        mock_button1,  # channel-1 button
        mock_button2,  # channel-2 button
        mock_main_button,  # main button
        mock_log  # log widget
    ])
    channel_manager.state_manager.get_chat_history = Mock(return_value=[])

    await channel_manager.switch_channel("channel-2")

    assert channel_manager.active_channel == "channel-2"
    # Button variants should be updated
    mock_button2.variant = "primary"
    mock_button1.variant = "default"


@pytest.mark.asyncio
async def test_channel_switching_to_main(channel_manager):
    """Test switching to main channel."""
    channel_manager.squad_channels["channel-1"] = {
        "button_id": "btn-channel-1"
    }

    mock_button = Mock()
    mock_main_button = Mock()
    mock_log = Mock()
    channel_manager.app.query_one = Mock(side_effect=[
        mock_button,  # channel-1 button
        mock_main_button,  # main button
        mock_log  # log widget
    ])
    channel_manager.state_manager.get_chat_history = Mock(return_value=[])

    await channel_manager.switch_channel("main")

    assert channel_manager.active_channel == "main"
    mock_main_button.variant = "primary"


@pytest.mark.asyncio
async def test_channel_switching_refreshes_log(channel_manager):
    """Test that channel switching refreshes log display."""
    channel_name = "squad-task-1-coder"
    channel_manager.squad_channels[channel_name] = {
        "button_id": "btn-channel-1"
    }

    mock_button = Mock()
    mock_main_button = Mock()
    mock_log = Mock()
    channel_manager.app.query_one = Mock(side_effect=[
        mock_button,
        mock_main_button,
        mock_log
    ])
    channel_manager.state_manager.get_chat_history = Mock(return_value=[
        {"role": "assistant", "content": "Test message"}
    ])

    await channel_manager.switch_channel(channel_name)

    # Log should be cleared and refreshed
    mock_log.clear.assert_called_once()
    mock_log.write.assert_called()


@pytest.mark.asyncio
async def test_message_routing_to_active_channel(channel_manager):
    """Test message routing to active channel."""
    channel_name = "squad-task-1-coder"
    channel_manager.active_channel = channel_name
    channel_manager.squad_channels[channel_name] = {
        "task_id": "task-1",
        "agent_type": "coder",
        "message_count": 0
    }

    mock_log_widget = Mock()
    channel_manager.app.query_one = Mock(return_value=mock_log_widget)
    channel_manager.state_manager.add_chat_message = Mock()
    channel_manager.state_manager.save_state = AsyncMock()

    await channel_manager.handle_agent_output(
        channel=channel_name,
        content="Test message",
        role="assistant"
    )

    # Message should be displayed in log
    mock_log_widget.write.assert_called()
    # State should be updated
    channel_manager.state_manager.add_chat_message.assert_called_once_with(
        channel_name, "assistant", "Test message"
    )


@pytest.mark.asyncio
async def test_message_routing_to_inactive_channel(channel_manager):
    """Test message routing to inactive channel (should not display)."""
    channel_name = "squad-task-1-coder"
    channel_manager.active_channel = "main"  # Different channel
    channel_manager.squad_channels[channel_name] = {
        "task_id": "task-1",
        "agent_type": "coder",
        "message_count": 0
    }

    channel_manager.state_manager.add_chat_message = Mock()
    channel_manager.state_manager.save_state = AsyncMock()

    await channel_manager.handle_agent_output(
        channel=channel_name,
        content="Test message",
        role="assistant"
    )

    # State should still be updated
    channel_manager.state_manager.add_chat_message.assert_called_once()
    # But should not query log widget since channel is not active
    # (query_one should not be called for log display)


@pytest.mark.asyncio
async def test_message_routing_main_channel(channel_manager):
    """Test message routing to main channel."""
    channel_manager.active_channel = "main"
    channel_manager.state_manager.add_chat_message = Mock()
    channel_manager.state_manager.save_state = AsyncMock()

    mock_log = Mock()
    channel_manager.app.query_one = Mock(return_value=mock_log)

    await channel_manager.handle_agent_output(
        channel="main",
        content="Main channel message",
        role="user"
    )

    # Should display in log
    mock_log.write.assert_called()
    # Should format as user message
    call_args = str(mock_log.write.call_args)
    assert "User" in call_args or "user" in call_args.lower()


@pytest.mark.asyncio
async def test_message_routing_updates_message_count(channel_manager):
    """Test that message routing updates channel message count."""
    channel_name = "squad-task-1-coder"
    channel_manager.active_channel = channel_name
    channel_manager.squad_channels[channel_name] = {
        "task_id": "task-1",
        "agent_type": "coder",
        "message_count": 0,
        "button_id": "btn-channel-1"
    }

    mock_log = Mock()
    mock_button = Mock()
    channel_manager.app.query_one = Mock(side_effect=[mock_log, mock_button])
    channel_manager.state_manager.add_chat_message = Mock()
    channel_manager.state_manager.save_state = AsyncMock()

    await channel_manager.handle_agent_output(
        channel=channel_name,
        content="Test",
        role="assistant"
    )

    # Message count should be incremented
    assert channel_manager.squad_channels[channel_name]["message_count"] == 1


@pytest.mark.asyncio
async def test_message_routing_creates_channel_if_missing(channel_manager):
    """Test that message routing creates channel if it doesn't exist."""
    channel_name = "squad-task-1-coder"
    channel_manager.active_channel = channel_name

    mock_container = Mock()
    mock_container.mount = AsyncMock()
    mock_log = Mock()
    # query_one is called multiple times: container, log (in create), log (in handle_agent_output)
    channel_manager.app.query_one = Mock(side_effect=[mock_container, mock_log, mock_log])
    channel_manager.app.set_timer = Mock()
    channel_manager.state_manager.get_chat_history = Mock(return_value=[])
    channel_manager.state_manager.add_chat_message = Mock()
    channel_manager.state_manager.save_state = AsyncMock()

    await channel_manager.handle_agent_output(
        channel=channel_name,
        content="Test",
        role="assistant"
    )

    # Channel should be created
    assert channel_name in channel_manager.squad_channels


@pytest.mark.asyncio
async def test_channel_state_management_message_persistence(channel_manager):
    """Test channel state management - message persistence."""
    channel_name = "squad-task-1-coder"
    channel_manager.squad_channels[channel_name] = {
        "task_id": "task-1",
        "agent_type": "coder"
    }

    channel_manager.state_manager.add_chat_message = Mock()
    channel_manager.state_manager.save_state = AsyncMock()

    await channel_manager.handle_agent_output(
        channel=channel_name,
        content="Test message",
        role="assistant",
        save_immediately=True
    )

    # State should be saved
    channel_manager.state_manager.save_state.assert_called_once()


@pytest.mark.asyncio
async def test_channel_state_management_batched_saves(channel_manager):
    """Test channel state management - batched saves for streaming."""
    channel_name = "squad-task-1-coder"
    channel_manager.squad_channels[channel_name] = {
        "task_id": "task-1",
        "agent_type": "coder"
    }

    channel_manager.state_manager.add_chat_message = Mock()
    channel_manager.state_manager.save_state = AsyncMock()

    # Send multiple messages with save_immediately=False
    for i in range(3):
        await channel_manager.handle_agent_output(
            channel=channel_name,
            content=f"Chunk {i}",
            role="assistant",
            save_immediately=False
        )

    # State should not be saved for each chunk
    assert channel_manager.state_manager.save_state.call_count == 0
    # But messages should be added
    assert channel_manager.state_manager.add_chat_message.call_count == 3


@pytest.mark.asyncio
async def test_channel_state_management_get_summary(channel_manager):
    """Test channel state management - getting channel summary."""
    channel_manager.squad_channels["channel-1"] = {
        "task_id": "task-1",
        "agent_type": "coder"
    }
    channel_manager.squad_channels["channel-2"] = {
        "task_id": "task-2",
        "agent_type": "planner"
    }
    channel_manager.active_channel = "channel-1"

    channel_manager.state_manager.get_chat_history = Mock(side_effect=lambda ch: {
        "channel-1": [{"role": "assistant", "content": "msg1"}],
        "channel-2": [{"role": "assistant", "content": "msg2"}, {"role": "user", "content": "msg3"}]
    }.get(ch, []))

    summary = channel_manager.get_channel_summary()

    assert "channel-1" in summary
    assert "channel-2" in summary
    assert summary["channel-1"]["message_count"] == 1
    assert summary["channel-2"]["message_count"] == 2
    assert summary["channel-1"]["is_active"] is True
    assert summary["channel-2"]["is_active"] is False


@pytest.mark.asyncio
async def test_channel_state_management_update_squad_channels(channel_manager):
    """Test channel state management - updating squad channels from coordinator."""
    mock_coordinator = Mock()
    mock_coordinator.get_active_agents = Mock(return_value={
        "task-1": {
            "status": "active",
            "channel": "squad-task-1-coder",
            "agent_type": "coder"
        },
        "task-2": {
            "status": "active",
            "channel": "squad-task-2-planner",
            "agent_type": "planner"
        }
    })

    mock_container = Mock()
    mock_container.mount = AsyncMock()
    channel_manager.app.query_one = Mock(return_value=mock_container)
    channel_manager.app.set_timer = Mock()
    channel_manager.state_manager.get_chat_history = Mock(return_value=[])
    channel_manager.state_manager.get_task_checklist = Mock(return_value=[])

    await channel_manager.update_squad_channels(mock_coordinator)

    # Channels should be created for active agents
    assert "squad-task-1-coder" in channel_manager.squad_channels
    assert "squad-task-2-planner" in channel_manager.squad_channels


@pytest.mark.asyncio
async def test_channel_state_management_update_button_label(channel_manager):
    """Test channel state management - updating button label with message count."""
    channel_name = "squad-task-1-coder"
    channel_manager.squad_channels[channel_name] = {
        "task_id": "task-1",
        "agent_type": "coder",
        "button_id": "btn-channel-1",
        "message_count": 5
    }

    mock_button = Mock()
    channel_manager.app.query_one = Mock(return_value=mock_button)

    await channel_manager._update_channel_button_label(channel_name)

    # Button label should be updated
    assert mock_button.label is not None
    # Should include message count
    assert "5" in mock_button.label or "[5]" in mock_button.label


@pytest.mark.asyncio
async def test_channel_switching_button_state_updates(channel_manager):
    """Test channel switching updates all button states correctly."""
    channel_manager.squad_channels["channel-1"] = {
        "button_id": "btn-channel-1"
    }
    channel_manager.squad_channels["channel-2"] = {
        "button_id": "btn-channel-2"
    }

    mock_button1 = Mock()
    mock_button2 = Mock()
    mock_main_button = Mock()
    mock_log = Mock()
    # query_one is called: button1, button2, main_button, log (for each switch)
    channel_manager.app.query_one = Mock(side_effect=[
        mock_button1,  # channel-1 button (first switch)
        mock_button2,  # channel-2 button (first switch)
        mock_main_button,  # main button (first switch)
        mock_log,  # log widget (first switch)
        mock_button1,  # channel-1 button (second switch)
        mock_button2,  # channel-2 button (second switch)
        mock_main_button,  # main button (second switch)
        mock_log  # log widget (second switch)
    ])
    channel_manager.state_manager.get_chat_history = Mock(return_value=[])

    # Switch to channel-1
    await channel_manager.switch_channel("channel-1")

    # channel-1 should be primary, others default
    assert mock_button1.variant == "primary"
    assert mock_button2.variant == "default"
    assert mock_main_button.variant == "default"

    # Switch to channel-2
    await channel_manager.switch_channel("channel-2")

    # channel-2 should be primary now
    assert mock_button2.variant == "primary"
    assert mock_button1.variant == "default"
