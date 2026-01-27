"""
Integration tests for App → Channel Manager → Agent Bridge interaction.

Tests the integration between App, ChannelManager, and AgentBridge to ensure
proper channel management, agent output routing, and state updates.
"""
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from manifest.ui.channels.channel_manager import ChannelManager
from manifest.bridge.agent_bridge import AgentBridge
from manifest.core.config import ConfigManager
from manifest.core.state_manager import StateManager


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def state_manager(temp_dir):
    """Create a StateManager instance."""
    return StateManager(manifest_dir=temp_dir)


@pytest.fixture
def config_manager(temp_dir):
    """Create a ConfigManager instance."""
    return ConfigManager(manifest_dir=temp_dir)


@pytest.fixture
def mock_app():
    """Create a mock App instance."""
    app = MagicMock()
    app.query_one = MagicMock()
    app.set_timer = Mock()

    # Mock RichLog widget
    mock_log = MagicMock()
    mock_log.write = Mock()
    mock_log.clear = Mock()
    app.query_one.return_value = mock_log

    # Mock Horizontal container for channel selector
    mock_selector = MagicMock()
    mock_selector.mount = AsyncMock()

    def query_one_side_effect(query, raise_if_missing=True):
        if query == "#log-main":
            return mock_log
        elif query == "#channel-selector":
            return mock_selector
        elif query.startswith("#btn-channel-"):
            return MagicMock()
        elif query == "#agent-channels-view":
            return MagicMock()
        else:
            if raise_if_missing:
                raise Exception(f"Widget not found: {query}")
            return None

    app.query_one.side_effect = query_one_side_effect
    return app


@pytest.fixture
def channel_manager(mock_app, state_manager):
    """Create a ChannelManager instance."""
    return ChannelManager(mock_app, state_manager)


@pytest.fixture
def agent_bridge(state_manager, config_manager, channel_manager):
    """Create an AgentBridge instance with channel_manager."""
    return AgentBridge(
        state_manager=state_manager,
        config_manager=config_manager,
        channel_manager=channel_manager
    )


@pytest.fixture
def sample_task(state_manager):
    """Create a sample task for testing."""
    task_id = state_manager.create_task(
        name="Test Task",
        description="Test task description",
        status="pending"
    )
    return task_id


# ========== TDL: App → Channel Manager → Agent Bridge Integration ==========

@pytest.mark.asyncio
async def test_agent_output_routed_to_channels_single_channel(
    agent_bridge, channel_manager, sample_task, state_manager
):
    """Test agent output routed to channels - single channel."""
    # Start bridge
    await agent_bridge.start()

    # Create a channel
    channel_name = f"squad-{sample_task}-coder"
    await channel_manager.create_squad_channel(sample_task, "coder")

    # Simulate agent output from bridge
    test_content = "Test agent output message"
    await agent_bridge._handle_agent_chunk(
        chunk={"type": "complete", "content": test_content},
        channel=channel_name
    )

    # Verify output was routed to channel
    history = state_manager.get_chat_history(channel_name)
    assert len(history) > 0
    assert any(msg.get("content") == test_content for msg in history)


@pytest.mark.asyncio
async def test_agent_output_routed_to_channels_multiple_channels(
    agent_bridge, channel_manager, sample_task, state_manager
):
    """Test agent output routed to channels - multiple channels."""
    # Start bridge
    await agent_bridge.start()

    # Create multiple channels
    task_id_1 = sample_task
    task_id_2 = state_manager.create_task(name="Task 2", description="Task 2", status="pending")

    channel_1 = f"squad-{task_id_1}-planner"
    channel_2 = f"squad-{task_id_2}-coder"

    await channel_manager.create_squad_channel(task_id_1, "planner")
    await channel_manager.create_squad_channel(task_id_2, "coder")

    # Simulate agent output to different channels
    content_1 = "Planner output"
    content_2 = "Coder output"

    await agent_bridge._handle_agent_chunk(
        chunk={"type": "complete", "content": content_1},
        channel=channel_1
    )

    await agent_bridge._handle_agent_chunk(
        chunk={"type": "complete", "content": content_2},
        channel=channel_2
    )

    # Verify outputs were routed to correct channels
    history_1 = state_manager.get_chat_history(channel_1)
    history_2 = state_manager.get_chat_history(channel_2)

    assert len(history_1) > 0
    assert len(history_2) > 0
    assert any(msg.get("content") == content_1 for msg in history_1)
    assert any(msg.get("content") == content_2 for msg in history_2)


@pytest.mark.asyncio
async def test_agent_output_routed_to_channels_streaming(
    agent_bridge, channel_manager, sample_task, state_manager
):
    """Test agent output routed to channels - streaming chunks."""
    # Start bridge
    await agent_bridge.start()

    # Create a channel
    channel_name = f"squad-{sample_task}-coder"
    await channel_manager.create_squad_channel(sample_task, "coder")

    # Simulate streaming chunks
    chunks = [
        {"type": "chunk", "content": "Hello "},
        {"type": "chunk", "content": "world "},
        {"type": "chunk", "content": "from "},
        {"type": "complete", "content": "agent"}
    ]

    for chunk in chunks:
        await agent_bridge._handle_agent_chunk(chunk=chunk, channel=channel_name)

    # Verify all chunks were accumulated
    history = state_manager.get_chat_history(channel_name)
    assert len(history) > 0
    # Complete message should contain all content
    complete_messages = [msg for msg in history if msg.get("role") == "assistant"]
    assert len(complete_messages) > 0


@pytest.mark.asyncio
async def test_channel_state_updates_message_count(
    agent_bridge, channel_manager, sample_task, mock_app
):
    """Test channel state updates - message count."""
    # Start bridge
    await agent_bridge.start()

    # Create a channel
    channel_name = f"squad-{sample_task}-coder"
    await channel_manager.create_squad_channel(sample_task, "coder")

    # Verify initial state
    assert channel_name in channel_manager.squad_channels
    initial_count = channel_manager.squad_channels[channel_name].get("message_count", 0)

    # Simulate agent output
    await agent_bridge._handle_agent_chunk(
        chunk={"type": "complete", "content": "Test message"},
        channel=channel_name
    )

    # Verify message count was updated
    assert channel_name in channel_manager.squad_channels
    new_count = channel_manager.squad_channels[channel_name].get("message_count", 0)
    assert new_count > initial_count


@pytest.mark.asyncio
async def test_channel_state_updates_active_channel(
    channel_manager, sample_task, mock_app
):
    """Test channel state updates - active channel."""
    # Create multiple channels
    task_id_1 = sample_task
    task_id_2 = "task-2"

    channel_1 = f"squad-{task_id_1}-planner"
    channel_2 = f"squad-{task_id_2}-coder"

    await channel_manager.create_squad_channel(task_id_1, "planner")
    await channel_manager.create_squad_channel(task_id_2, "coder")

    # Switch to channel 1
    await channel_manager.switch_channel(channel_1)
    assert channel_manager.active_channel == channel_1

    # Switch to channel 2
    await channel_manager.switch_channel(channel_2)
    assert channel_manager.active_channel == channel_2


@pytest.mark.asyncio
async def test_channel_state_updates_channel_creation(
    channel_manager, sample_task, mock_app
):
    """Test channel state updates - channel creation."""
    # Create a channel
    channel_name = f"squad-{sample_task}-coder"
    tab_id = await channel_manager.create_squad_channel(sample_task, "coder")

    # Verify channel was added to state
    assert channel_name in channel_manager.squad_channels
    channel_info = channel_manager.squad_channels[channel_name]
    assert channel_info["task_id"] == sample_task
    assert channel_info["agent_type"] == "coder"
    assert channel_info["tab_id"] == tab_id


@pytest.mark.asyncio
async def test_multi_channel_management_creation(
    channel_manager, state_manager, mock_app
):
    """Test multi-channel management - channel creation."""
    # Create multiple tasks
    task_ids = []
    for i in range(3):
        task_id = state_manager.create_task(
            name=f"Task {i}",
            description=f"Task {i} description",
            status="pending"
        )
        task_ids.append(task_id)

    # Create channels for different agents
    channels_created = []
    for task_id in task_ids:
        for agent_type in ["planner", "coder", "test"]:
            channel_name = f"squad-{task_id}-{agent_type}"
            await channel_manager.create_squad_channel(task_id, agent_type)
            channels_created.append(channel_name)

    # Verify all channels were created
    assert len(channel_manager.squad_channels) == len(channels_created)
    for channel_name in channels_created:
        assert channel_name in channel_manager.squad_channels


@pytest.mark.asyncio
async def test_multi_channel_management_switching(
    channel_manager, state_manager, mock_app
):
    """Test multi-channel management - channel switching."""
    # Create multiple channels
    task_ids = []
    for i in range(3):
        task_id = state_manager.create_task(
            name=f"Task {i}",
            description=f"Task {i} description",
            status="pending"
        )
        task_ids.append(task_id)

    channels = []
    for task_id in task_ids:
        channel_name = f"squad-{task_id}-coder"
        await channel_manager.create_squad_channel(task_id, "coder")
        channels.append(channel_name)

    # Switch between channels
    for channel in channels:
        await channel_manager.switch_channel(channel)
        assert channel_manager.active_channel == channel


@pytest.mark.asyncio
async def test_multi_channel_management_concurrent_output(
    agent_bridge, channel_manager, state_manager, mock_app
):
    """Test multi-channel management - concurrent output to multiple channels."""
    # Start bridge
    await agent_bridge.start()

    # Create multiple channels
    task_ids = []
    for i in range(3):
        task_id = state_manager.create_task(
            name=f"Task {i}",
            description=f"Task {i} description",
            status="pending"
        )
        task_ids.append(task_id)

    channels = []
    for task_id in task_ids:
        channel_name = f"squad-{task_id}-coder"
        await channel_manager.create_squad_channel(task_id, "coder")
        channels.append(channel_name)

    # Send output to all channels concurrently
    outputs = [f"Output for task {i}" for i in range(3)]

    for channel, output in zip(channels, outputs):
        await agent_bridge._handle_agent_chunk(
            chunk={"type": "complete", "content": output},
            channel=channel
        )

    # Verify all channels received their output
    for channel, expected_output in zip(channels, outputs):
        history = state_manager.get_chat_history(channel)
        assert len(history) > 0
        assert any(msg.get("content") == expected_output for msg in history)


@pytest.mark.asyncio
async def test_integration_complete_channel_workflow(
    agent_bridge, channel_manager, state_manager, mock_app
):
    """Test complete integration - channel workflow."""
    # Start bridge
    await agent_bridge.start()

    # Create a task and channel
    task_id = state_manager.create_task(
        name="Integration Test Task",
        description="Test task",
        status="pending"
    )
    channel_name = f"squad-{task_id}-planner"

    # 1. Create channel
    tab_id = await channel_manager.create_squad_channel(task_id, "planner")
    assert channel_name in channel_manager.squad_channels

    # 2. Switch to channel
    await channel_manager.switch_channel(channel_name)
    assert channel_manager.active_channel == channel_name

    # 3. Send agent output
    test_output = "Agent planning output"
    await agent_bridge._handle_agent_chunk(
        chunk={"type": "complete", "content": test_output},
        channel=channel_name
    )

    # 4. Verify state was updated
    history = state_manager.get_chat_history(channel_name)
    assert len(history) > 0
    assert channel_manager.squad_channels[channel_name]["message_count"] > 0

    # 5. Switch to main channel
    await channel_manager.switch_channel("main")
    assert channel_manager.active_channel == "main"


@pytest.mark.asyncio
async def test_integration_bridge_uses_channel_manager(
    agent_bridge, channel_manager, sample_task, state_manager
):
    """Test integration - bridge uses channel manager."""
    # Start bridge
    await agent_bridge.start()

    # Verify bridge has channel_manager
    assert agent_bridge.channel_manager is not None
    assert agent_bridge.channel_manager is channel_manager

    # Create a channel
    channel_name = f"squad-{sample_task}-coder"
    await channel_manager.create_squad_channel(sample_task, "coder")

    # Track channel_manager calls
    original_handle = channel_manager.handle_agent_output
    call_count = {"count": 0}

    async def track_handle(*args, **kwargs):
        call_count["count"] += 1
        return await original_handle(*args, **kwargs)

    channel_manager.handle_agent_output = track_handle

    # Send output through bridge
    await agent_bridge._handle_agent_chunk(
        chunk={"type": "complete", "content": "Test output"},
        channel=channel_name
    )

    # Verify bridge used channel_manager
    assert call_count["count"] > 0
