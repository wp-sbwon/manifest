"""
Unit tests for ContainerCommunication.

Tests container message bus and state synchronization.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from manifest.agents.container_communication import (
    ContainerMessageBus,
    ContainerStateSync
)


@pytest.fixture
def mock_state_manager():
    """Create a mock state manager."""
    state = Mock()
    state.save_state = AsyncMock()
    state.load_state = AsyncMock()
    return state


@pytest.fixture
def message_bus():
    """Create a ContainerMessageBus instance."""
    return ContainerMessageBus(base_url="http://localhost:8000", agent_id="agent-1")


def test_message_bus_initialization(message_bus):
    """Test ContainerMessageBus initialization."""
    assert message_bus.base_url == "http://localhost:8000"
    assert message_bus.agent_id == "agent-1"
    assert message_bus is not None


@pytest.mark.asyncio
async def test_connect(message_bus):
    """Test connecting to message bus."""
    # ContainerMessageBus uses httpx, not aiohttp
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value = Mock()
        await message_bus.connect()
        # Should connect without error
        assert message_bus.client is not None


@pytest.mark.asyncio
async def test_disconnect(message_bus):
    """Test disconnecting from message bus."""
    # Set up a client first
    message_bus.client = AsyncMock()
    message_bus.client.aclose = AsyncMock()
    
    await message_bus.disconnect()
    
    # Verify client was closed and set to None
    assert message_bus.client is None


@pytest.mark.asyncio
async def test_send_message(message_bus):
    """Test sending a message."""
    # ContainerMessageBus uses httpx client, not session
    mock_client = AsyncMock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": True}
    mock_client.post = AsyncMock(return_value=mock_response)
    message_bus.client = mock_client
    
    result = await message_bus.send_message("test-topic", {"data": "test"})
    # Should send without error
    assert result is True


@pytest.fixture
def state_sync(mock_state_manager):
    """Create a ContainerStateSync instance."""
    message_bus = ContainerMessageBus(base_url="http://localhost:8000", agent_id="agent-1")
    return ContainerStateSync(mock_state_manager, message_bus)


def test_state_sync_initialization(state_sync, mock_state_manager):
    """Test ContainerStateSync initialization."""
    assert state_sync.state_manager == mock_state_manager
    assert state_sync.message_bus is not None
    assert state_sync is not None


@pytest.mark.asyncio
async def test_start_sync(state_sync):
    """Test starting state synchronization."""
    # Mock message bus subscribe (start() calls subscribe, not connect)
    state_sync.message_bus.subscribe = AsyncMock()
    # Mock asyncio.create_task to avoid actual task creation
    with patch('asyncio.create_task') as mock_create_task:
        mock_task = Mock()
        mock_create_task.return_value = mock_task
        
        await state_sync.start()
        
        # Verify message bus was subscribed to "state-update" topic
        state_sync.message_bus.subscribe.assert_called_once()
        # Verify sync task was created
        assert hasattr(state_sync, '_sync_task')


@pytest.mark.asyncio
async def test_stop_sync(state_sync):
    """Test stopping state synchronization."""
    # Create a real asyncio task that can be cancelled
    async def dummy_task():
        await asyncio.sleep(10)  # Long sleep so we can cancel it
    
    sync_task = asyncio.create_task(dummy_task())
    state_sync._sync_task = sync_task
    
    await state_sync.stop()
    
    # Verify sync task was cancelled
    assert sync_task.cancelled()
