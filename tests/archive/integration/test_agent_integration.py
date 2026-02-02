"""
Integration tests for full agent coordination flow.
"""
import pytest
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock
from manifest.agents.agent_coordinator import AgentCoordinator
from manifest.bridge.agent_bridge import AgentBridge
from manifest.agents.context_provider import ContextProvider
from manifest.agents.task_scoper import TaskScoper
from manifest.core.config import ConfigManager
from manifest.core.state_manager import StateManager


@pytest.fixture
def temp_manifest_dir(tmp_path):
    """Create temporary manifest directory with test data."""
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir()

    # Create blueprint.json
    blueprint = {
        "version": "1.0",
        "zones": {
            "server": [
                {"id": "comp-1", "name": "TestComponent", "files": ["test.py"]}
            ]
        },
        "components": [
            {"id": "comp-1", "name": "TestComponent", "files": ["test.py"], "directory": "."}
        ],
        "contracts": []
    }
    with open(manifest_dir / "blueprint.json", "w") as f:
        json.dump(blueprint, f)

    # Create intent.json
    intent = {
        "version": "1.0",
        "sprint": "Test Sprint",
        "features": [
            {
                "id": "feature-1",
                "name": "Test Feature",
                "tasks": ["task-1"],
                "reqs": [{"id": "REQ-1", "desc": "Test requirement"}]
            }
        ]
    }
    with open(manifest_dir / "intent.json", "w") as f:
        json.dump(intent, f)

    # Create architecture.json
    architecture = {
        "version": "1.0",
        "features": [],
        "requirements": [],
        "goals": []
    }
    with open(manifest_dir / "architecture.json", "w") as f:
        json.dump(architecture, f)

    # Create policy file
    policy_dir = tmp_path / ".rules"
    policy_dir.mkdir(parents=True)
    with open(policy_dir / "manifest-policy.md", "w") as f:
        f.write("# Test Policy")

    return manifest_dir


@pytest.fixture
def mock_agent_bridge():
    """Create mock agent bridge."""
    # Mock terminal router
    terminal_router = Mock()
    terminal_router.active_commands = {}

    # Mock orchestrator and agent manager
    orchestrator = Mock()
    orchestrator.start_mission = AsyncMock(return_value=True)

    agent_manager = Mock()
    agent_manager.create_agent = AsyncMock(return_value={"id": "task-1", "type": "coder", "status": "created"})
    agent_manager.start_agent = AsyncMock(return_value=True)
    agent_manager.stop_agent = AsyncMock(return_value=True)
    agent_manager.get_agent = Mock(return_value={"id": "task-1", "type": "coder", "status": "active"})

    bridge = Mock(spec=AgentBridge)
    bridge.terminal_router = terminal_router
    bridge.orchestrator = orchestrator
    bridge.agent_manager = agent_manager
    bridge.is_connected = True
    bridge.start_agent_mission = AsyncMock(return_value=True)
    bridge.stop_agent = AsyncMock(return_value=True)
    bridge.get_agent_status = AsyncMock(return_value={"status": "active", "data": {}})
    return bridge


@pytest.fixture
def mock_config_manager():
    """Create mock config manager."""
    config = Mock(spec=ConfigManager)
    config.get_agent_model_config = Mock(return_value={
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "api_key": "test-key"
    })
    return config


@pytest.mark.asyncio
async def test_full_agent_flow(temp_manifest_dir, mock_agent_bridge, mock_config_manager):
    """Test full agent coordination flow."""
    # Initialize components
    state_manager = StateManager(temp_manifest_dir)
    task_scoper = TaskScoper(temp_manifest_dir)
    context_provider = ContextProvider(temp_manifest_dir, task_scoper)

    # Add task to state
    state_manager.set_task_checklist([
        {"id": "task-1", "name": "Test Task", "status": "pending"}
    ])

    # Create coordinator
    coordinator = AgentCoordinator(
        mock_agent_bridge,
        context_provider,
        task_scoper,
        mock_config_manager,
        state_manager
    )

    # Start worker agent
    success = await coordinator.start_worker_agent("task-1", "coder")

    assert success == True
    assert "task-1" in coordinator.active_agents

    # Verify context was provided
    mock_agent_bridge.start_agent_mission.assert_called_once()
    call_args = mock_agent_bridge.start_agent_mission.call_args
    assert call_args[1]["task_id"] == "task-1"
    assert call_args[1]["agent_type"] == "coder"
    assert "context" in call_args[1]
    assert "model_config" in call_args[1]

    # Verify task was updated
    tasks = state_manager.get_task_checklist()
    task = next((t for t in tasks if t.get("id") == "task-1"), None)
    assert task is not None
    assert "agent" in task
    assert task["agent"]["type"] == "coder"
    assert "scope" in task


@pytest.mark.asyncio
async def test_orchestrator_flow(temp_manifest_dir, mock_agent_bridge, mock_config_manager):
    """Test orchestrator flow."""
    state_manager = StateManager(temp_manifest_dir)
    task_scoper = TaskScoper(temp_manifest_dir)
    context_provider = ContextProvider(temp_manifest_dir, task_scoper)

    coordinator = AgentCoordinator(
        mock_agent_bridge,
        context_provider,
        task_scoper,
        mock_config_manager,
        state_manager
    )

    # Start orchestrator
    success = await coordinator.start_orchestrator("Test mission description")

    assert success == True
    assert "orchestrator" in coordinator.active_agents

    # Verify context includes mission description
    mock_agent_bridge.start_agent_mission.assert_called_once()
    call_args = mock_agent_bridge.start_agent_mission.call_args
    context = call_args[1]["context"]
    assert context["tier"] == "orchestrator"
    assert "mission_description" in context
