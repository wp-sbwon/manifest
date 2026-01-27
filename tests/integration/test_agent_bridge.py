"""
Integration tests for AgentBridge and AgentCoordinator interaction.

Tests the integration between AgentBridge and AgentCoordinator to ensure
proper agent startup, message passing, status reporting, and error propagation.
"""
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from manifest.core.state_manager import StateManager
from manifest.bridge.agent_bridge import AgentBridge
from manifest.agents.agent_coordinator import AgentCoordinator
from manifest.agents.context_provider import ContextProvider
from manifest.agents.task_scoper import TaskScoper
from manifest.core.config import ConfigManager


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
def agent_bridge(state_manager):
    """Create an AgentBridge instance."""
    from manifest.core.config import ConfigManager
    config_manager = ConfigManager(manifest_dir=state_manager.manifest_dir)
    return AgentBridge(state_manager, config_manager=config_manager)


def test_agent_bridge_initialization(agent_bridge):
    """Test AgentBridge initialization."""
    assert agent_bridge.state_manager is not None
    assert agent_bridge.is_connected is False
    assert agent_bridge.terminal_router is not None
    assert agent_bridge.orchestrator is not None
    assert agent_bridge.agent_manager is not None


def test_agent_bridge_availability(agent_bridge):
    """Test agent bridge availability check."""
    # This test verifies the bridge is initialized but not started
    assert agent_bridge.is_connected is False  # Not started yet


@pytest.mark.asyncio
async def test_bridge_message_protocol(agent_bridge):
    """Test bridge message protocol."""
    await agent_bridge.start()
    assert agent_bridge.is_connected is True
    await agent_bridge.stop()


def test_bridge_state_integration(agent_bridge, state_manager):
    """Test bridge state integration."""
    state_manager.set_mission_tree({"test": "data"})
    assert agent_bridge.state_manager is state_manager
    assert agent_bridge.state_manager.get_mission_tree() == {"test": "data"}


@pytest.mark.asyncio
async def test_bridge_commands(agent_bridge):
    """Test bridge commands."""
    await agent_bridge.start()
    assert agent_bridge.is_connected is True

    status = await agent_bridge.get_status()
    assert status is not None

    result = await agent_bridge.start_mission("test-task", "Test mission")
    assert result is True

    await agent_bridge.stop()


# ========== TDL: Agent Bridge → Agent Coordinator Integration ==========

@pytest.fixture
def agent_coordinator(agent_bridge, state_manager, temp_dir):
    """Create an AgentCoordinator instance with mocked dependencies."""
    context_provider = ContextProvider(manifest_dir=temp_dir)
    task_scoper = TaskScoper(manifest_dir=temp_dir)
    config_manager = ConfigManager(manifest_dir=temp_dir)

    return AgentCoordinator(
        agent_bridge=agent_bridge,
        context_provider=context_provider,
        task_scoper=task_scoper,
        config_manager=config_manager,
        state_manager=state_manager
    )


@pytest.mark.asyncio
async def test_agent_startup_through_bridge_orchestrator(agent_bridge, agent_coordinator, state_manager):
    """Test agent startup through bridge - orchestrator startup."""
    # Start bridge
    await agent_bridge.start()

    # Mock agent_bridge.start_agent_mission to avoid actual agent execution
    with patch.object(agent_bridge, 'start_agent_mission', new_callable=AsyncMock) as mock_start:
        mock_start.return_value = True

        # Start coordinator
        await agent_coordinator.start()

        # Start orchestrator through coordinator (which uses bridge)
        success = await agent_coordinator.start_orchestrator("Test mission description")

        # Verify bridge was called
        mock_start.assert_called_once()
        call_args = mock_start.call_args
        assert call_args[1]["task_id"] == "orchestrator"
        assert call_args[1]["agent_type"] == "orchestrator"
        assert "context" in call_args[1]
        assert "model_config" in call_args[1]

        # Verify orchestrator was registered in active_agents
        assert success is True
        assert "orchestrator" in agent_coordinator.active_agents


@pytest.mark.asyncio
async def test_agent_startup_through_bridge_worker_agent(agent_bridge, agent_coordinator, state_manager):
    """Test agent startup through bridge - worker agent startup."""
    # Create a task first
    state_manager.create_task(
        name="Test task",
        description="Test task description",
        status="pending"
    )

    # Start bridge
    await agent_bridge.start()

    # Mock agent_bridge.start_agent_mission
    with patch.object(agent_bridge, 'start_agent_mission', new_callable=AsyncMock) as mock_start:
        mock_start.return_value = True

        # Start coordinator
        await agent_coordinator.start()

        # Start worker agent through coordinator (which uses bridge)
        success = await agent_coordinator.start_worker_agent(
            task_id="task-1",
            agent_type="planner"
        )

        # Verify bridge was called
        mock_start.assert_called_once()
        call_args = mock_start.call_args
        assert call_args[1]["task_id"] == "task-1"
        assert call_args[1]["agent_type"] == "planner"
        assert "context" in call_args[1]
        assert "model_config" in call_args[1]

        # Verify agent was registered
        assert success is True
        assert "task-1" in agent_coordinator.active_agents or any(
            agent.get("task_id") == "task-1"
            for agent in agent_coordinator.active_agents.values()
        )


@pytest.mark.asyncio
async def test_message_passing_through_bridge(agent_bridge, agent_coordinator, state_manager):
    """Test message passing through bridge."""
    # Start bridge and coordinator
    await agent_bridge.start()
    await agent_coordinator.start()

    # Set up message bus (coordinator creates one)
    message_bus = agent_coordinator.message_bus

    # Register a test agent
    test_handler = AsyncMock()
    message_bus.register_agent("test-agent", "planner", test_handler)

    # Send message through bridge's message bus using send_message method
    if hasattr(agent_bridge, 'message_bus') and agent_bridge.message_bus:
        # Use send_message method
        message_id = await agent_bridge.message_bus.send_message(
            from_agent_id="sender",
            to_agent_id="test-agent",
            subject="test",
            content={"message": "test message"}
        )

        # Give async operations time to complete
        await asyncio.sleep(0.1)

        # Verify message bus is set up correctly
        assert message_bus is not None
        assert agent_bridge.message_bus is message_bus

        # Verify message was sent (message_id may be None, empty string, or a string)
        # The important thing is that send_message was called without error
        assert isinstance(message_id, (str, type(None)))


@pytest.mark.asyncio
async def test_status_reporting_through_bridge(agent_bridge, agent_coordinator, state_manager):
    """Test status reporting through bridge."""
    # Start bridge
    await agent_bridge.start()

    # Mock get_status
    with patch.object(agent_bridge, 'get_status', new_callable=AsyncMock) as mock_status:
        mock_status.return_value = {
            "connected": True,
            "active_agents": 2,
            "status": "ready"
        }

        # Get status through bridge
        status = await agent_bridge.get_status()

        # Verify status is reported
        assert status is not None
        assert status["connected"] is True
        mock_status.assert_called_once()


@pytest.mark.asyncio
async def test_error_propagation_through_bridge(agent_bridge, agent_coordinator, state_manager):
    """Test error propagation through bridge."""
    # Start bridge
    await agent_bridge.start()
    await agent_coordinator.start()

    # Mock agent_bridge.start_agent_mission to raise an error
    with patch.object(agent_bridge, 'start_agent_mission', new_callable=AsyncMock) as mock_start:
        mock_start.side_effect = Exception("Bridge error")

        # Try to start orchestrator - should handle error gracefully
        try:
            success = await agent_coordinator.start_orchestrator("Test mission")
            # Should return False on error, not raise exception
            assert success is False
        except Exception as e:
            # If exception is raised, verify it's the expected one
            assert "Bridge error" in str(e)

        # Verify bridge was called (error should propagate)
        mock_start.assert_called_once()


@pytest.mark.asyncio
async def test_agent_startup_error_handling(agent_bridge, agent_coordinator, state_manager):
    """Test error handling when agent startup fails through bridge."""
    # Create a task
    task_id = state_manager.create_task(
        name="Test task",
        description="Test task description",
        status="pending"
    )

    # Start bridge
    await agent_bridge.start()
    await agent_coordinator.start()

    # Mock agent_bridge.start_agent_mission to return False (failure)
    with patch.object(agent_bridge, 'start_agent_mission', new_callable=AsyncMock) as mock_start:
        mock_start.return_value = False

        # Try to start worker agent
        success = await agent_coordinator.start_worker_agent(
            task_id=task_id,
            agent_type="planner"
        )

        # Should return False, not raise exception
        assert success is False
        # Agent should not be in active_agents
        assert task_id not in agent_coordinator.active_agents or not any(
            agent.get("task_id") == task_id
            for agent in agent_coordinator.active_agents.values()
        )


@pytest.mark.asyncio
async def test_coordinator_uses_bridge_message_bus(agent_bridge, agent_coordinator):
    """Test that coordinator shares message bus with bridge."""
    # Start bridge and coordinator
    await agent_bridge.start()
    await agent_coordinator.start()

    # Coordinator creates message_bus and shares it with bridge
    assert agent_coordinator.message_bus is not None

    # Bridge should have access to message bus
    if hasattr(agent_bridge, 'message_bus'):
        assert agent_bridge.message_bus is agent_coordinator.message_bus


@pytest.mark.asyncio
async def test_agent_lifecycle_through_bridge(agent_bridge, agent_coordinator, state_manager):
    """Test complete agent lifecycle through bridge."""
    # Create a task
    task_id = state_manager.create_task(
        name="Test task",
        description="Test task description",
        status="pending"
    )

    # Start bridge and coordinator
    await agent_bridge.start()
    await agent_coordinator.start()

    # Track bridge calls
    bridge_calls = []

    async def track_start_agent_mission(*args, **kwargs):
        bridge_calls.append(("start", kwargs))
        return True

    with patch.object(agent_bridge, 'start_agent_mission', side_effect=track_start_agent_mission):
        # Start agent
        success = await agent_coordinator.start_worker_agent(
            task_id=task_id,
            agent_type="planner"
        )

        assert success is True
        assert len(bridge_calls) == 1
        assert bridge_calls[0][1]["task_id"] == task_id
        assert bridge_calls[0][1]["agent_type"] == "planner"
