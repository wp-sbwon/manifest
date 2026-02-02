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


@pytest.mark.asyncio
async def test_start_orchestrator_with_context(agent_coordinator):
    """Test orchestrator startup with context provisioning."""
    agent_coordinator.context_provider.get_orchestrator_context = Mock(return_value={
        "tier_0": "policy",
        "tier_1": "architecture"
    })
    agent_coordinator.agent_bridge.start_agent_mission = AsyncMock(return_value=True)
    agent_coordinator.config_manager.get_agent_model_config = Mock(return_value={"provider": "opencode"})

    result = await agent_coordinator.start_orchestrator("Test mission")

    assert result is True
    agent_coordinator.context_provider.get_orchestrator_context.assert_called_once()
    agent_coordinator.agent_bridge.start_agent_mission.assert_called_once()
    assert "orchestrator" in agent_coordinator.active_agents


@pytest.mark.asyncio
async def test_start_orchestrator_failure(agent_coordinator):
    """Test orchestrator startup failure."""
    agent_coordinator.agent_bridge.start_agent_mission = AsyncMock(return_value=False)

    result = await agent_coordinator.start_orchestrator("Test mission")

    assert result is False
    assert "orchestrator" not in agent_coordinator.active_agents


@pytest.mark.asyncio
async def test_start_worker_agent_task_validation(agent_coordinator):
    """Test worker agent startup with task validation."""
    # Task doesn't exist
    agent_coordinator.state_manager.get_task_checklist = Mock(return_value=[])

    result = await agent_coordinator.start_worker_agent("nonexistent-task", "coder")

    assert result is False


@pytest.mark.asyncio
async def test_start_worker_agent_with_stage_context(agent_coordinator):
    """Test worker agent startup with stage-specific context."""
    agent_coordinator.state_manager.get_task_checklist = Mock(return_value=[{"id": "task-1"}])
    agent_coordinator.context_provider.get_stage_specific_context = Mock(return_value={
        "task_scope": {"components": ["comp-1"]},
        "previous_stages": {}
    })
    agent_coordinator.context_provider.get_worker_context = Mock(return_value={})
    agent_coordinator.task_scoper.validate_task_granularity = Mock(return_value={"valid": True})
    agent_coordinator.config_manager.get_agent_model_config = Mock(return_value={"provider": "opencode"})
    agent_coordinator.agent_bridge.start_agent_mission = AsyncMock(return_value=True)
    agent_coordinator.container_manager.is_docker_available = Mock(return_value=False)

    result = await agent_coordinator.start_worker_agent("task-1", "coder", stage="planner", previous_stages={"planner": {}})

    assert result is True
    agent_coordinator.context_provider.get_stage_specific_context.assert_called_once_with(
        "task-1", "coder", "planner", {"planner": {}}
    )


@pytest.mark.asyncio
async def test_start_worker_agent_without_scope(agent_coordinator):
    """Test worker agent startup when task has no scope (should warn but continue)."""
    agent_coordinator.state_manager.get_task_checklist = Mock(return_value=[{"id": "task-1"}])
    agent_coordinator.context_provider.get_worker_context = Mock(return_value={
        "task_scope": {}  # No scope
    })
    agent_coordinator.task_scoper.validate_task_granularity = Mock(return_value={"valid": True})
    agent_coordinator.config_manager.get_agent_model_config = Mock(return_value={"provider": "opencode"})
    agent_coordinator.agent_bridge.start_agent_mission = AsyncMock(return_value=True)
    agent_coordinator.container_manager.is_docker_available = Mock(return_value=False)

    result = await agent_coordinator.start_worker_agent("task-1", "coder")

    # Should continue despite no scope
    assert result is True


@pytest.mark.asyncio
async def test_start_worker_agent_granularity_validation(agent_coordinator):
    """Test worker agent startup with granularity validation."""
    agent_coordinator.state_manager.get_task_checklist = Mock(return_value=[{"id": "task-1"}])
    agent_coordinator.context_provider.get_worker_context = Mock(return_value={
        "task_scope": {"components": ["comp-1"]}
    })
    agent_coordinator.task_scoper.validate_task_granularity = Mock(return_value={
        "valid": False,
        "errors": ["Task too large"],
        "warnings": ["Consider splitting"]
    })
    agent_coordinator.config_manager.get_agent_model_config = Mock(return_value={"provider": "opencode"})
    agent_coordinator.agent_bridge.start_agent_mission = AsyncMock(return_value=True)
    agent_coordinator.container_manager.is_docker_available = Mock(return_value=False)

    result = await agent_coordinator.start_worker_agent("task-1", "coder")

    # Should continue despite validation errors (just logs them)
    assert result is True
    agent_coordinator.task_scoper.validate_task_granularity.assert_called_once()


@pytest.mark.asyncio
async def test_start_worker_agent_context_size_validation(agent_coordinator):
    """Test worker agent startup with context size validation."""
    agent_coordinator.state_manager.get_task_checklist = Mock(return_value=[{"id": "task-1"}])
    agent_coordinator.context_provider.get_worker_context = Mock(return_value={
        "task_scope": {"components": ["comp-1"]},
        "context_size_validation": {
            "valid": False,
            "excess_tokens": 1000,
            "suggestions": ["Reduce scope", "Split task"]
        }
    })
    agent_coordinator.task_scoper.validate_task_granularity = Mock(return_value={"valid": True})
    agent_coordinator.config_manager.get_agent_model_config = Mock(return_value={"provider": "opencode"})
    agent_coordinator.agent_bridge.start_agent_mission = AsyncMock(return_value=True)
    agent_coordinator.container_manager.is_docker_available = Mock(return_value=False)

    result = await agent_coordinator.start_worker_agent("task-1", "coder")

    # Should continue despite context size issues (just logs them)
    assert result is True


@pytest.mark.asyncio
async def test_start_worker_agent_container_mode(agent_coordinator):
    """Test worker agent startup in container mode."""
    agent_coordinator.state_manager.get_task_checklist = Mock(return_value=[{"id": "task-1"}])
    agent_coordinator.context_provider.get_worker_context = Mock(return_value={
        "task_scope": {"components": ["comp-1"]}
    })
    agent_coordinator.task_scoper.validate_task_granularity = Mock(return_value={"valid": True})
    agent_coordinator.config_manager.get_agent_model_config = Mock(return_value={"provider": "opencode"})
    agent_coordinator.container_manager.is_docker_available = Mock(return_value=True)
    agent_coordinator.container_manager.start_agent_container = AsyncMock(return_value="container-123")

    result = await agent_coordinator.start_worker_agent("task-1", "coder", use_container=True)

    assert result is True
    agent_coordinator.container_manager.start_agent_container.assert_called_once()
    assert agent_coordinator.active_agents["task-1"]["execution_mode"] == "container"
    assert agent_coordinator.active_agents["task-1"]["container_id"] == "container-123"


@pytest.mark.asyncio
async def test_start_worker_agent_container_fallback(agent_coordinator):
    """Test worker agent startup when container fails, falls back to direct."""
    agent_coordinator.state_manager.get_task_checklist = Mock(return_value=[{"id": "task-1"}])
    agent_coordinator.context_provider.get_worker_context = Mock(return_value={
        "task_scope": {"components": ["comp-1"]}
    })
    agent_coordinator.task_scoper.validate_task_granularity = Mock(return_value={"valid": True})
    agent_coordinator.config_manager.get_agent_model_config = Mock(return_value={"provider": "opencode"})
    agent_coordinator.container_manager.is_docker_available = Mock(return_value=True)
    agent_coordinator.container_manager.start_agent_container = AsyncMock(return_value=None)  # Container fails
    agent_coordinator.agent_bridge.start_agent_mission = AsyncMock(return_value=True)

    result = await agent_coordinator.start_worker_agent("task-1", "coder", use_container=True)

    assert result is True
    # Should fall back to direct execution
    agent_coordinator.agent_bridge.start_agent_mission.assert_called_once()
    assert agent_coordinator.active_agents["task-1"]["execution_mode"] == "direct"


@pytest.mark.asyncio
async def test_start_worker_agent_and_wait_success(agent_coordinator):
    """Test starting worker agent and waiting for completion."""
    agent_coordinator.state_manager.get_task_checklist = Mock(return_value=[{"id": "task-1"}])
    agent_coordinator.context_provider.get_worker_context = Mock(return_value={
        "task_scope": {"components": ["comp-1"]}
    })
    agent_coordinator.task_scoper.validate_task_granularity = Mock(return_value={"valid": True})
    agent_coordinator.config_manager.get_agent_model_config = Mock(return_value={"provider": "opencode"})
    agent_coordinator.agent_bridge.start_agent_mission = AsyncMock(return_value=True)
    agent_coordinator.container_manager.is_docker_available = Mock(return_value=False)

    # Mock agent_bridge._active_agents as a dict
    agent_coordinator.agent_bridge._active_agents = {}
    # Mock executor.active_sessions as a dict
    mock_executor = Mock()
    mock_executor.active_sessions = {}
    agent_coordinator.agent_bridge.executor = mock_executor

    # Mock agent completion detection - agent completes immediately
    agent_coordinator.state_manager.get_chat_history = Mock(return_value=[
        {"role": "assistant", "content": "Task completed"}
    ])
    agent_coordinator._parse_agent_output = Mock(return_value={"success": True, "parsed_data": {}})

    # Start agent
    await agent_coordinator.start_worker_agent("task-1", "coder")

    # Mock the wait loop to complete quickly
    with patch('asyncio.sleep', new_callable=AsyncMock):
        # Mock get_agent_status to return completed immediately
        agent_coordinator.get_agent_status = AsyncMock(return_value={"status": "completed"})
        # Remove from active_agents to simulate completion
        del agent_coordinator.active_agents["task-1"]

        result = await agent_coordinator.start_worker_agent_and_wait("task-1", "coder", timeout=1.0)

    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_start_worker_agent_and_wait_timeout(agent_coordinator):
    """Test starting worker agent and waiting with timeout."""
    agent_coordinator.state_manager.get_task_checklist = Mock(return_value=[{"id": "task-1"}])
    agent_coordinator.context_provider.get_worker_context = Mock(return_value={
        "task_scope": {"components": ["comp-1"]}
    })
    agent_coordinator.task_scoper.validate_task_granularity = Mock(return_value={"valid": True})
    agent_coordinator.config_manager.get_agent_model_config = Mock(return_value={"provider": "opencode"})
    agent_coordinator.agent_bridge.start_agent_mission = AsyncMock(return_value=True)
    agent_coordinator.container_manager.is_docker_available = Mock(return_value=False)

    # Start agent
    await agent_coordinator.start_worker_agent("task-1", "coder")

    # Mock the wait loop to timeout
    with patch('asyncio.sleep', new_callable=AsyncMock), \
         patch('asyncio.get_event_loop') as mock_loop:
        # Mock time to simulate timeout
        mock_time = Mock()
        mock_time.side_effect = [0.0, 0.2]  # Start at 0, then timeout at 0.2 (> 0.1 timeout)
        mock_loop.return_value.time = mock_time

        agent_coordinator.get_agent_status = AsyncMock(return_value={"status": "active"})
        agent_coordinator.state_manager.get_chat_history = Mock(return_value=[])

        result = await agent_coordinator.start_worker_agent_and_wait("task-1", "coder", timeout=0.1)

    assert isinstance(result, dict)
    assert result.get("status") == "timeout" or result.get("success") is False


@pytest.mark.asyncio
async def test_start_worker_agent_and_wait_start_failure(agent_coordinator):
    """Test start_worker_agent_and_wait when agent fails to start."""
    agent_coordinator.state_manager.get_task_checklist = Mock(return_value=[])

    result = await agent_coordinator.start_worker_agent_and_wait("nonexistent-task", "coder")

    assert isinstance(result, dict)
    assert result.get("success") is False
    assert result.get("status") == "failed_to_start"


@pytest.mark.asyncio
async def test_start_worker_agent_and_wait_bridge_completed(agent_coordinator):
    """Test completion is detected when bridge marks agent completed (canonical signal)."""
    agent_coordinator.state_manager.get_task_checklist = Mock(return_value=[{"id": "task-1"}])
    agent_coordinator.context_provider.get_worker_context = Mock(return_value={
        "task_scope": {"components": ["comp-1"]}
    })
    agent_coordinator.task_scoper.validate_task_granularity = Mock(return_value={"valid": True})
    agent_coordinator.config_manager.get_agent_model_config = Mock(return_value={"provider": "opencode"})
    agent_coordinator.agent_bridge.start_agent_mission = AsyncMock(return_value=True)
    agent_coordinator.container_manager.is_docker_available = Mock(return_value=False)

    await agent_coordinator.start_worker_agent("task-1", "coder")
    # Use a real dict so bridge completion signal is visible (canonical completion path)
    agent_coordinator.agent_bridge._active_agents = {
        "task-1": {"completed": True, "status": "completed"},
    }
    agent_coordinator.state_manager.get_chat_history = Mock(return_value=[])
    agent_coordinator.get_agent_status = AsyncMock(return_value={"status": "active"})
    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await agent_coordinator.start_worker_agent_and_wait("task-1", "coder", timeout=5.0)

    assert result.get("status") == "completed"
    assert result.get("success") is True


@pytest.mark.asyncio
async def test_start_worker_agent_direct_execution(agent_coordinator):
    """Test worker agent startup in direct execution mode."""
    agent_coordinator.state_manager.get_task_checklist = Mock(return_value=[{"id": "task-1"}])
    agent_coordinator.context_provider.get_worker_context = Mock(return_value={
        "task_scope": {"components": ["comp-1"]}
    })
    agent_coordinator.task_scoper.validate_task_granularity = Mock(return_value={"valid": True})
    agent_coordinator.config_manager.get_agent_model_config = Mock(return_value={"provider": "opencode"})
    agent_coordinator.agent_bridge.start_agent_mission = AsyncMock(return_value=True)
    agent_coordinator.container_manager.is_docker_available = Mock(return_value=False)

    result = await agent_coordinator.start_worker_agent("task-1", "planner", use_container=False)

    assert result is True
    agent_coordinator.agent_bridge.start_agent_mission.assert_called_once()
    assert agent_coordinator.active_agents["task-1"]["execution_mode"] == "direct"
    assert agent_coordinator.active_agents["task-1"]["agent_type"] == "planner"


@pytest.mark.asyncio
async def test_start_worker_agent_direct_execution_failure(agent_coordinator):
    """Test worker agent startup failure in direct execution mode."""
    agent_coordinator.state_manager.get_task_checklist = Mock(return_value=[{"id": "task-1"}])
    agent_coordinator.context_provider.get_worker_context = Mock(return_value={
        "task_scope": {"components": ["comp-1"]}
    })
    agent_coordinator.task_scoper.validate_task_granularity = Mock(return_value={"valid": True})
    agent_coordinator.config_manager.get_agent_model_config = Mock(return_value={"provider": "opencode"})
    agent_coordinator.agent_bridge.start_agent_mission = AsyncMock(return_value=False)
    agent_coordinator.container_manager.is_docker_available = Mock(return_value=False)

    result = await agent_coordinator.start_worker_agent("task-1", "coder")

    assert result is False
    assert "task-1" not in agent_coordinator.active_agents


def test_get_next_stage(agent_coordinator):
    """Test getting next stage in workflow."""
    # Test stage progression
    assert agent_coordinator._get_next_stage("planner") == "tdd_test"
    assert agent_coordinator._get_next_stage("tdd_test") == "coder"
    assert agent_coordinator._get_next_stage("coder") == "test"
    assert agent_coordinator._get_next_stage("test") == "debug"  # or self_review if tests pass
    assert agent_coordinator._get_next_stage("self_review") == "approver"
    assert agent_coordinator._get_next_stage("approver") is None  # End of workflow


def test_parse_agent_output(agent_coordinator):
    """Test parsing agent output for structured data."""
    # Test planner output parsing
    planner_output = "Plan:\n1. Step one\n2. Step two"
    result = agent_coordinator._parse_agent_output(agent_type="planner", stage="planner", output=planner_output)
    assert isinstance(result, dict)

    # Test coder output parsing
    coder_output = "Implementation complete"
    result = agent_coordinator._parse_agent_output(agent_type="coder", stage="coder", output=coder_output)
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_handle_blueprint_conflict(agent_coordinator):
    """Test handling blueprint conflicts."""
    conflict_issue = {
        "id": "conflict-1",
        "type": "drift",
        "severity": "error",
        "component": "comp-1"
    }
    agent_coordinator.state_manager.get_task_checklist = Mock(return_value=[{"id": "task-1"}])
    agent_coordinator.state_manager.set_task_checklist = Mock()
    agent_coordinator.state_manager.save_state = AsyncMock()

    # Mock BlueprintSynchronizer methods (imported inside the method)
    with patch('manifest.audit.blueprint.blueprint_synchronizer.BlueprintSynchronizer') as mock_sync_class:
        mock_sync = Mock()
        mock_sync.resend_to_worker_squad = Mock(return_value={"resend": True})
        mock_sync.request_planner_review = Mock(return_value={"review": True})
        mock_sync_class.return_value = mock_sync

        agent_coordinator.agent_bridge.send_to_planner = AsyncMock(return_value={
            "success": True,
            "channel": "planner-channel",
            "planner_task_id": "planner-task-1"
        })

        result = await agent_coordinator.handle_blueprint_conflict(conflict_issue, "task-1")

        assert result is True
        agent_coordinator.agent_bridge.send_to_planner.assert_called_once()


@pytest.mark.asyncio
async def test_start_sprint(agent_coordinator):
    """Test starting a sprint."""
    agent_coordinator.sprint_executor.start_sprint = AsyncMock(return_value={
        "success": True,
        "started_tasks": ["task-1"],
        "failed_tasks": []
    })

    result = await agent_coordinator.start_sprint("sprint-1", max_parallel=5)

    assert isinstance(result, dict)
    agent_coordinator.sprint_executor.start_sprint.assert_called_once_with("sprint-1", 5)


@pytest.mark.asyncio
async def test_start_task_worker_squad(agent_coordinator):
    """Test starting worker squad for a task."""
    agent_coordinator.worker_squad_executor.execute = AsyncMock(return_value={"success": True})

    result = await agent_coordinator._start_task_worker_squad("task-1")

    assert isinstance(result, bool)
    agent_coordinator.worker_squad_executor.execute.assert_called_once_with("task-1")
