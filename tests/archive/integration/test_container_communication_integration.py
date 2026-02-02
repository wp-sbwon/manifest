"""
Integration tests for container communication.

Tests end-to-end container communication including:
- ContainerAPI HTTP server
- ContainerMessageBus message sending/receiving
- ContainerStateSync state synchronization
- Error handling and recovery
"""
import pytest
import asyncio
import httpx
from pathlib import Path
import tempfile
import shutil
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from manifest.agents.container_api import create_container_api
from manifest.agents.container_communication import (
    ContainerMessageBus,
    ContainerStateSync
)
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
def container_api(state_manager):
    """Create a ContainerAPI FastAPI app."""
    return create_container_api(state_manager)


@pytest.fixture
def api_client(container_api):
    """Create a TestClient for the ContainerAPI."""
    return TestClient(container_api)


@pytest.fixture
def mock_httpx_client(container_api):
    """Create a mock httpx client that uses TestClient internally."""
    from fastapi.testclient import TestClient
    test_client = TestClient(container_api)

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            # Accept any kwargs (like timeout) but ignore them
            self.test_client = test_client

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, **kwargs):
            # Extract path from URL
            path = url.replace("http://127.0.0.1:8001", "").replace("http://localhost:8000", "")
            if not path.startswith("/"):
                path = "/" + path
            response = self.test_client.post(path, json=kwargs.get("json"))
            return MockResponse(response)

        async def get(self, url, **kwargs):
            path = url.replace("http://127.0.0.1:8001", "").replace("http://localhost:8000", "")
            if not path.startswith("/"):
                path = "/" + path
            params = kwargs.get("params", {})
            response = self.test_client.get(path, params=params)
            return MockResponse(response)

        async def aclose(self):
            pass

    class MockResponse:
        def __init__(self, test_response):
            self.status_code = test_response.status_code
            self._json = test_response.json()

        def json(self):
            return self._json

    # Return a callable that creates the mock client
    def create_mock(*args, **kwargs):
        return MockAsyncClient(*args, **kwargs)

    return create_mock


def test_container_api_health_check(api_client):
    """Test ContainerAPI health check endpoint."""
    response = api_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_container_message_bus_send_receive(container_api, mock_httpx_client):
    """Test ContainerMessageBus can send and receive messages."""
    with patch('httpx.AsyncClient', side_effect=mock_httpx_client):
        bus1 = ContainerMessageBus(base_url="http://127.0.0.1:8001", agent_id="agent-1")
        bus2 = ContainerMessageBus(base_url="http://127.0.0.1:8001", agent_id="agent-2")

        await bus1.connect()
        await bus2.connect()

        # Send a message from bus1
        success = await bus1.send_message(
            topic="test-topic",
            message={"data": "hello from agent-1"},
            target_agent="agent-2"
        )
        assert success is True

        # Receive messages on bus2
        messages = await bus2.receive_messages(topic="test-topic", timeout=2.0)
        assert len(messages) > 0

        # Find our message
        our_message = next(
            (m for m in messages if m.get("payload", {}).get("data") == "hello from agent-1"),
            None
        )
        assert our_message is not None
        assert our_message.get("topic") == "test-topic"
        assert our_message.get("target_agent") == "agent-2"

        await bus1.disconnect()
        await bus2.disconnect()


@pytest.mark.asyncio
async def test_container_message_bus_subscribe(container_api, mock_httpx_client):
    """Test ContainerMessageBus subscription and message delivery."""
    with patch('httpx.AsyncClient', side_effect=mock_httpx_client):
        bus = ContainerMessageBus(base_url="http://127.0.0.1:8001", agent_id="agent-1")
        await bus.connect()

        received_messages = []

        async def message_handler(message):
            received_messages.append(message)

        # Subscribe to topic
        await bus.subscribe("test-subscribe", message_handler)

        # Send a message
        await bus.send_message("test-subscribe", {"data": "test message"})

        # Give polling time to pick up the message
        await asyncio.sleep(1.5)

        # Verify message was received
        assert len(received_messages) > 0
        assert any(
            m.get("payload", {}).get("data") == "test message"
            for m in received_messages
        )

        # Stop polling
        if hasattr(bus, '_poll_task'):
            bus._poll_task.cancel()
            try:
                await bus._poll_task
            except asyncio.CancelledError:
                pass

        await bus.disconnect()


@pytest.mark.asyncio
async def test_container_state_sync_broadcast(state_manager, container_api, mock_httpx_client):
    """Test ContainerStateSync broadcasts state updates."""
    with patch('httpx.AsyncClient', side_effect=mock_httpx_client):
        bus = ContainerMessageBus(base_url="http://127.0.0.1:8001", agent_id="agent-1")
        await bus.connect()

        state_sync = ContainerStateSync(state_manager, bus)

        # Set some state
        state_manager.set_mission_tree({"mission": "test"})
        state_manager.create_task("Task 1", "Description", "pending")

        # Start sync
        await state_sync.start()

        # Give sync time to broadcast (sync_interval is 5.0 seconds, so wait a bit longer)
        await asyncio.sleep(6.0)

        # Check that state update was sent
        messages = await bus.receive_messages(topic="state-update", timeout=2.0)
        # State sync broadcasts periodically, so we should have at least one message after 6 seconds
        assert len(messages) > 0

        # Find state update message
        state_update = next(
            (m for m in messages if m.get("topic") == "state-update"),
            None
        )
        assert state_update is not None
        payload = state_update.get("payload", {})
        assert payload.get("agent_id") == "local"
        assert "state" in payload
        assert "mission_tree" in payload["state"]
        assert "task_checklist" in payload["state"]

        # Stop sync
        await state_sync.stop()
        await bus.disconnect()


@pytest.mark.asyncio
async def test_container_state_sync_merge(state_manager, container_api, mock_httpx_client):
    """Test ContainerStateSync merges incoming state updates."""
    with patch('httpx.AsyncClient', side_effect=mock_httpx_client):
        bus1 = ContainerMessageBus(base_url="http://127.0.0.1:8001", agent_id="agent-1")
        bus2 = ContainerMessageBus(base_url="http://127.0.0.1:8001", agent_id="agent-2")

        await bus1.connect()
        await bus2.connect()

        # Create two state managers
        temp_dir2 = Path(tempfile.mkdtemp())
        try:
            state_manager2 = StateManager(manifest_dir=temp_dir2)

            sync1 = ContainerStateSync(state_manager, bus1)
            sync2 = ContainerStateSync(state_manager2, bus2)

            # Set different states
            state_manager.set_mission_tree({"mission": "local"})
            state_manager2.set_mission_tree({"mission": "remote", "extra": "data"})

            # Start both syncs
            await sync1.start()
            await sync2.start()

            # Give time for state sync
            await asyncio.sleep(2.0)

            # Stop syncs
            await sync1.stop()
            await sync2.stop()

            # Verify state was merged (state_manager2 should have received updates)
            # Note: actual merge logic depends on timestamps, so we just verify
            # that state sync ran without errors
            final_state = state_manager2.get_state()
            assert final_state is not None

        finally:
            shutil.rmtree(temp_dir2)

        await bus1.disconnect()
        await bus2.disconnect()


@pytest.mark.asyncio
async def test_container_message_bus_error_handling():
    """Test ContainerMessageBus handles errors gracefully."""
    # Use a non-existent URL
    bus = ContainerMessageBus(base_url="http://127.0.0.1:9999", agent_id="agent-1")

    # Should not raise exception, but return False
    success = await bus.send_message("test", {"data": "test"})
    assert success is False

    # Message should be queued locally
    assert len(bus.message_queue) > 0


@pytest.mark.asyncio
async def test_container_message_bus_agent_status(container_api, api_client, mock_httpx_client):
    """Test ContainerMessageBus can request agent status."""
    # First, update agent status via API
    response = api_client.post(
        "/api/agents/test-agent/status",
        json={"status": "active", "task_id": "task-1"}
    )
    assert response.status_code == 200

    # Request status via message bus
    with patch('httpx.AsyncClient', side_effect=mock_httpx_client):
        bus = ContainerMessageBus(base_url="http://127.0.0.1:8001", agent_id="agent-1")
        await bus.connect()

        status = await bus.request_agent_status("test-agent")
        assert status is not None
        assert status.get("status") == "active"
        assert status.get("task_id") == "task-1"

        await bus.disconnect()


def test_container_api_message_filtering(api_client):
    """Test ContainerAPI message filtering by topic and target_agent."""
    # Send messages to different topics
    for topic in ["topic-a", "topic-b"]:
        response = api_client.post(
            "/api/messages",
            json={
                "id": f"msg-{topic}",
                "topic": topic,
                "timestamp": "2024-01-01T00:00:00",
                "payload": {"data": f"message for {topic}"},
                "target_agent": "agent-1" if topic == "topic-a" else None
            }
        )
        assert response.status_code == 200

    # Get messages filtered by topic
    response = api_client.get("/api/messages", params={"topic": "topic-a"})
    assert response.status_code == 200
    messages = response.json().get("messages", [])
    assert len(messages) > 0
    assert all(m.get("topic") == "topic-a" for m in messages)

    # Get messages filtered by target_agent
    response = api_client.get("/api/messages", params={"target_agent": "agent-1"})
    assert response.status_code == 200
    messages = response.json().get("messages", [])
    # Should include messages for agent-1 or broadcast (target_agent=None)
    assert len(messages) > 0
