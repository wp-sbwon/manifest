"""
Unit tests for AgentCoordinator.

Tests agent coordination, lifecycle management, and workflow execution.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from manifest.agents.agent_coordinator import AgentCoordinator


@pytest.fixture
def mock_agent_bridge():
    """Create a mock agent bridge."""
    bridge = Mock()
    bridge.terminal_router = Mock()
    bridge.orchestrator = Mock()
    bridge.agent_manager = Mock()
    bridge.start_agent_mission = AsyncMock(return_value=True)
    bridge.message_bus = None
    return bridge


@pytest.fixture
def mock_context_provider():
    """Create a mock context provider."""
    provider = Mock()
    provider.get_orchestrator_context = Mock(return_value={})
    provider.get_worker_context = Mock(return_value={})
    return provider


@pytest.fixture
def mock_task_scoper():
    """Create a mock task scoper."""
    scoper = Mock()
    scoper.analyze_dependencies = Mock(return_value=[])
    return scoper


@pytest.fixture
def mock_config_manager():
    """Create a mock config manager."""
    config = Mock()
    config.get_agent_model_config = Mock(return_value={"provider": "opencode"})
    return config


@pytest.fixture
def mock_state_manager():
    """Create a mock state manager."""
    state = Mock()
    state.get_task_checklist = Mock(return_value=[])
    state.set_task_checklist = Mock()
    state.set_last_action = Mock()
    state.save_state = AsyncMock()
    return state


@pytest.fixture
def agent_coordinator(mock_agent_bridge, mock_context_provider, mock_task_scoper, mock_config_manager, mock_state_manager):
    """Create an AgentCoordinator instance."""
    return AgentCoordinator(
        agent_bridge=mock_agent_bridge,
        context_provider=mock_context_provider,
        task_scoper=mock_task_scoper,
        config_manager=mock_config_manager,
        state_manager=mock_state_manager
    )


def test_agent_coordinator_initialization(agent_coordinator, mock_agent_bridge):
    """Test AgentCoordinator initialization."""
    assert agent_coordinator.agent_bridge == mock_agent_bridge
    assert agent_coordinator.worker_squad_executor is not None
    assert agent_coordinator.sprint_executor is not None
    assert isinstance(agent_coordinator.active_agents, dict)


@pytest.mark.asyncio
async def test_start(agent_coordinator):
    """Test starting the coordinator."""
    # Mock state_sync - it may not exist if containers aren't available
    if hasattr(agent_coordinator, 'state_sync') and agent_coordinator.state_sync:
        agent_coordinator.state_sync.start = AsyncMock()
    
    await agent_coordinator.start()
    
    # Verify coordinator started (no exceptions raised)
    # If state_sync exists, verify it was started
    if hasattr(agent_coordinator, 'state_sync') and agent_coordinator.state_sync:
        agent_coordinator.state_sync.start.assert_called_once()


@pytest.mark.asyncio
async def test_start_orchestrator(agent_coordinator):
    """Test starting orchestrator."""
    result = await agent_coordinator.start_orchestrator("Test mission")
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_start_worker_agent(agent_coordinator):
    """Test starting a worker agent."""
    agent_coordinator.agent_bridge.start_agent_mission = AsyncMock(return_value=True)
    
    result = await agent_coordinator.start_worker_agent("task-1", "coder")
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_stop_agent(agent_coordinator):
    """Test stopping an agent."""
    agent_coordinator.active_agents["task-1"] = {
        "agent_type": "coder",
        "status": "active",
        "execution_mode": "direct"
    }
    
    # Mock agent_bridge.stop_agent (the actual method called)
    agent_coordinator.agent_bridge.stop_agent = AsyncMock(return_value=True)
    agent_coordinator.state_manager.get_task_checklist = Mock(return_value=[])
    agent_coordinator.state_manager.set_task_checklist = Mock()
    agent_coordinator.state_manager.save_state = AsyncMock()
    
    result = await agent_coordinator.stop_agent("task-1")
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_get_agent_status(agent_coordinator):
    """Test getting agent status."""
    agent_coordinator.active_agents["task-1"] = {
        "agent_type": "coder",
        "status": "active",
        "started_at": "2026-01-26T00:00:00",
        "execution_mode": "direct"
    }
    
    # get_agent_status IS async, need to await it
    agent_coordinator.agent_bridge.get_agent_status = AsyncMock(return_value={"status": "active", "data": {}})
    
    status = await agent_coordinator.get_agent_status("task-1")
    assert isinstance(status, dict)


def test_get_active_agents(agent_coordinator):
    """Test getting active agents."""
    agent_coordinator.active_agents["task-1"] = {"agent_type": "coder"}
    
    agents = agent_coordinator.get_active_agents()
    assert isinstance(agents, dict)
    assert "task-1" in agents


def test_get_agent_channel(agent_coordinator):
    """Test getting agent channel."""
    agent_coordinator.active_agents["task-1"] = {
        "channel": "squad-task-1-coder"
    }
    
    channel = agent_coordinator.get_agent_channel("task-1")
    assert channel == "squad-task-1-coder"


@pytest.mark.asyncio
async def test_execute_worker_squad(agent_coordinator):
    """Test executing worker squad workflow."""
    agent_coordinator.worker_squad_executor.execute = AsyncMock(return_value={"success": True})
    
    result = await agent_coordinator.execute_worker_squad("task-1")
    assert isinstance(result, dict)
