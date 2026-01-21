"""
Unit tests for agent_coordinator.py
"""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from manifest.agents.agent_coordinator import AgentCoordinator
from manifest.bridge.omoc_bridge import OMOCBridge
from manifest.agents.context_provider import ContextProvider
from manifest.agents.task_scoper import TaskScoper
from manifest.core.config import ConfigManager
from manifest.core.state_manager import StateManager


@pytest.fixture
def mock_components():
    """Create mock components for testing."""
    # Mock terminal router
    terminal_router = Mock()
    terminal_router.active_commands = {}
    terminal_router.execute_command = AsyncMock(return_value={"returncode": 0, "stdout": "", "stderr": ""})
    
    # Mock container manager
    container_manager = Mock()
    container_manager.is_docker_available = Mock(return_value=False)
    container_manager.start_agent_container = AsyncMock(return_value=None)
    container_manager.stop_agent_container = AsyncMock(return_value=False)
    container_manager.get_container_status = AsyncMock(return_value=None)
    
    # Mock orchestrator and agent manager
    orchestrator = Mock()
    orchestrator.start_mission = AsyncMock(return_value=True)
    
    agent_manager = Mock()
    agent_manager.create_agent = AsyncMock(return_value={"id": "task-1", "type": "sisyphus", "status": "created"})
    agent_manager.start_agent = AsyncMock(return_value=True)
    agent_manager.stop_agent = AsyncMock(return_value=True)
    agent_manager.get_agent = Mock(return_value={"id": "task-1", "type": "sisyphus", "status": "active"})
    
    omoc_bridge = Mock(spec=OMOCBridge)
    omoc_bridge.terminal_router = terminal_router
    omoc_bridge.orchestrator = orchestrator
    omoc_bridge.agent_manager = agent_manager
    omoc_bridge.start_agent_mission = AsyncMock(return_value=True)
    omoc_bridge.stop_agent = AsyncMock(return_value=True)
    omoc_bridge.get_agent_status = AsyncMock(return_value={"status": "active", "data": {}})
    
    context_provider = Mock(spec=ContextProvider)
    context_provider.get_orchestrator_context = Mock(return_value={"tier": "orchestrator"})
    context_provider.get_worker_context = Mock(return_value={
        "tier": "worker",
        "task_id": "task-1",
        "task_scope": {"components": [], "allowed_files": []}
    })
    
    task_scoper = Mock(spec=TaskScoper)
    task_scoper.get_task_context = Mock(return_value={"components": [], "files": []})
    
    config_manager = Mock(spec=ConfigManager)
    config_manager.get_agent_model_config = Mock(return_value={"provider": "anthropic", "model": "claude-3-5-sonnet", "api_key": "test-key"})
    
    state_manager = Mock(spec=StateManager)
    state_manager.get_task_checklist = Mock(return_value=[{"id": "task-1", "name": "Test Task"}])
    state_manager.set_task_checklist = Mock()
    state_manager.set_last_action = Mock()
    state_manager.save_state = AsyncMock(return_value=True)
    state_manager.get_chat_history = Mock(return_value=[])
    state_manager.add_chat_message = Mock()
    
    return {
        "omoc_bridge": omoc_bridge,
        "context_provider": context_provider,
        "task_scoper": task_scoper,
        "config_manager": config_manager,
        "state_manager": state_manager
    }


def test_agent_coordinator_init(mock_components):
    """Test AgentCoordinator initialization."""
    coordinator = AgentCoordinator(
        mock_components["omoc_bridge"],
        mock_components["context_provider"],
        mock_components["task_scoper"],
        mock_components["config_manager"],
        mock_components["state_manager"]
    )
    
    assert coordinator.omoc_bridge == mock_components["omoc_bridge"]
    assert coordinator.active_agents == {}


@pytest.mark.asyncio
async def test_start_orchestrator(mock_components):
    """Test starting orchestrator."""
    coordinator = AgentCoordinator(
        mock_components["omoc_bridge"],
        mock_components["context_provider"],
        mock_components["task_scoper"],
        mock_components["config_manager"],
        mock_components["state_manager"]
    )
    
    success = await coordinator.start_orchestrator("Test mission")
    
    assert success == True
    assert "orchestrator" in coordinator.active_agents
    mock_components["omoc_bridge"].start_agent_mission.assert_called_once()


@pytest.mark.asyncio
async def test_start_worker_agent(mock_components):
    """Test starting worker agent."""
    coordinator = AgentCoordinator(
        mock_components["omoc_bridge"],
        mock_components["context_provider"],
        mock_components["task_scoper"],
        mock_components["config_manager"],
        mock_components["state_manager"]
    )
    
    success = await coordinator.start_worker_agent("task-1", "sisyphus")
    
    assert success == True
    assert "task-1" in coordinator.active_agents
    mock_components["omoc_bridge"].start_agent_mission.assert_called_once()


@pytest.mark.asyncio
async def test_stop_agent(mock_components):
    """Test stopping agent."""
    coordinator = AgentCoordinator(
        mock_components["omoc_bridge"],
        mock_components["context_provider"],
        mock_components["task_scoper"],
        mock_components["config_manager"],
        mock_components["state_manager"]
    )
    
    # Start agent first
    await coordinator.start_worker_agent("task-1", "sisyphus")
    
    # Stop agent
    success = await coordinator.stop_agent("task-1")
    
    assert success == True
    assert "task-1" not in coordinator.active_agents


def test_get_active_agents(mock_components):
    """Test getting active agents."""
    coordinator = AgentCoordinator(
        mock_components["omoc_bridge"],
        mock_components["context_provider"],
        mock_components["task_scoper"],
        mock_components["config_manager"],
        mock_components["state_manager"]
    )
    
    # Manually add active agent
    coordinator.active_agents["task-1"] = {"agent_type": "sisyphus", "status": "active"}
    
    active = coordinator.get_active_agents()
    assert "task-1" in active
    assert active["task-1"]["agent_type"] == "sisyphus"