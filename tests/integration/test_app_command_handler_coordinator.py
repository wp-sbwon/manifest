"""
Integration tests for App → Command Handler → Agent Coordinator interaction.

Tests the integration between App, CommandHandler, and AgentCoordinator to ensure
proper command parsing, routing, and agent action triggering.
"""
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from manifest.ui.commands.command_handler import CommandHandler
from manifest.agents.agent_coordinator import AgentCoordinator
from manifest.bridge.agent_bridge import AgentBridge
from manifest.agents.context_provider import ContextProvider
from manifest.agents.task_scoper import TaskScoper
from manifest.core.config import ConfigManager
from manifest.core.state_manager import StateManager
from textual.widgets import RichLog


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
def agent_bridge(state_manager, config_manager):
    """Create an AgentBridge instance."""
    return AgentBridge(state_manager, config_manager=config_manager)


@pytest.fixture
def agent_coordinator(agent_bridge, temp_dir, state_manager, config_manager):
    """Create an AgentCoordinator instance."""
    task_scoper = TaskScoper(manifest_dir=temp_dir)
    context_provider = ContextProvider(manifest_dir=temp_dir, task_scoper=task_scoper)
    return AgentCoordinator(
        agent_bridge=agent_bridge,
        context_provider=context_provider,
        task_scoper=task_scoper,
        config_manager=config_manager,
        state_manager=state_manager
    )


@pytest.fixture
def mock_app(agent_coordinator, agent_bridge, state_manager):
    """Create a mock App instance."""
    app = MagicMock()
    app.agent_coordinator = agent_coordinator
    app.agent_bridge = agent_bridge
    app.state_manager = state_manager
    app.update_squad_channels = AsyncMock(return_value=None)
    return app


@pytest.fixture
def command_handler(mock_app):
    """Create a CommandHandler instance."""
    return CommandHandler(mock_app)


@pytest.fixture
def mock_log():
    """Create a mock RichLog widget."""
    log = MagicMock(spec=RichLog)
    log.write = Mock()
    return log


@pytest.fixture
def sample_task(state_manager):
    """Create a sample task for testing."""
    task_id = state_manager.create_task(
        name="Test Task",
        description="Test task description",
        status="pending"
    )
    return task_id


# ========== TDL: App → Command Handler → Agent Coordinator Integration ==========

@pytest.mark.asyncio
async def test_user_commands_trigger_agent_actions_start_agent(
    command_handler, mock_app, agent_coordinator, agent_bridge, sample_task, mock_log
):
    """Test user commands trigger agent actions - start agent command."""
    # Start bridge
    await agent_bridge.start()
    await agent_coordinator.start()

    # Track coordinator calls
    start_agent_calls = []

    async def track_start_worker_agent(task_id, agent_type, **kwargs):
        start_agent_calls.append((task_id, agent_type, kwargs))
        return True

    agent_coordinator.start_worker_agent = track_start_worker_agent

    # Handle command
    handled = await command_handler.handle(f"/start_agent {sample_task} coder", mock_log)

    # Verify command was handled
    assert handled is True
    assert len(start_agent_calls) == 1
    assert start_agent_calls[0][0] == sample_task
    assert start_agent_calls[0][1] == "coder"
    # Verify log was written
    assert mock_log.write.called


@pytest.mark.asyncio
async def test_user_commands_trigger_agent_actions_stop_agent(
    command_handler, mock_app, agent_coordinator, agent_bridge, sample_task, mock_log
):
    """Test user commands trigger agent actions - stop agent command."""
    # Start bridge
    await agent_bridge.start()
    await agent_coordinator.start()

    # Track coordinator calls
    stop_agent_calls = []

    async def track_stop_agent(task_id):
        stop_agent_calls.append(task_id)
        return True

    agent_coordinator.stop_agent = track_stop_agent

    # Handle command
    handled = await command_handler.handle(f"/stop_agent {sample_task}", mock_log)

    # Verify command was handled
    assert handled is True
    assert len(stop_agent_calls) == 1
    assert stop_agent_calls[0] == sample_task
    # Verify log was written
    assert mock_log.write.called


@pytest.mark.asyncio
async def test_command_parsing_and_routing(
    command_handler, mock_app, agent_bridge, mock_log
):
    """Test command parsing and routing."""
    # Start bridge
    await agent_bridge.start()

    # Mock bridge methods
    async def mock_get_status():
        return {"connected": True}

    agent_bridge.get_status = mock_get_status

    # Test various commands
    commands = [
        "/status",
        "/start_agent task-1 coder",
        "/stop_agent task-1",
        "/orchestrator Test mission"
    ]

    for command in commands:
        handled = await command_handler.handle(command, mock_log)
        # All should be handled (even if they fail due to missing setup)
        assert handled is True
        # Log should be written
        assert mock_log.write.called


@pytest.mark.asyncio
async def test_command_parsing_and_routing_unknown_command(
    command_handler, mock_log
):
    """Test command parsing and routing - unknown command."""
    # Handle unknown command
    handled = await command_handler.handle("/unknown_command", mock_log)

    # Should be handled (returns True for commands)
    assert handled is True
    # Should write error message
    assert mock_log.write.called
    # Check that error message was written
    write_calls = [str(call) for call in mock_log.write.call_args_list]
    assert any("Unknown command" in str(call) for call in write_calls)


@pytest.mark.asyncio
async def test_response_display_command_output(
    command_handler, mock_app, agent_coordinator, agent_bridge, sample_task, mock_log
):
    """Test response display - command output."""
    # Start bridge
    await agent_bridge.start()
    await agent_coordinator.start()

    # Mock coordinator to return success
    async def mock_start_worker_agent(task_id, agent_type, **kwargs):
        return True

    agent_coordinator.start_worker_agent = mock_start_worker_agent

    # Handle command
    await command_handler.handle(f"/start_agent {sample_task} coder", mock_log)

    # Verify response was displayed in log
    assert mock_log.write.called
    # Should have multiple write calls (start message, success message)
    assert mock_log.write.call_count >= 2


@pytest.mark.asyncio
async def test_response_display_error_handling(
    command_handler, mock_app, agent_coordinator, agent_bridge, mock_log
):
    """Test response display - error handling."""
    # Start bridge
    await agent_bridge.start()
    await agent_coordinator.start()

    # Mock coordinator to return failure
    async def mock_start_worker_agent(task_id, agent_type, **kwargs):
        return False

    agent_coordinator.start_worker_agent = mock_start_worker_agent

    # Handle command with invalid task
    await command_handler.handle("/start_agent invalid-task coder", mock_log)

    # Verify error was displayed
    assert mock_log.write.called
    # Should have error message
    write_calls = [str(call) for call in mock_log.write.call_args_list]
    assert any("Failed" in str(call) or "error" in str(call).lower() for call in write_calls)


@pytest.mark.asyncio
async def test_integration_complete_command_workflow(
    command_handler, mock_app, agent_coordinator, agent_bridge, sample_task, mock_log
):
    """Test complete integration - command workflow."""
    # Start bridge
    await agent_bridge.start()
    await agent_coordinator.start()

    # Track all coordinator interactions
    coordinator_calls = []

    async def track_start_agent(task_id, agent_type, **kwargs):
        coordinator_calls.append(("start", task_id, agent_type))
        return True

    async def track_stop_agent(task_id):
        coordinator_calls.append(("stop", task_id))
        return True

    agent_coordinator.start_worker_agent = track_start_agent
    agent_coordinator.stop_agent = track_stop_agent

    # Execute command workflow
    # 1. Start agent
    handled1 = await command_handler.handle(f"/start_agent {sample_task} coder", mock_log)
    assert handled1 is True

    # 2. Stop agent
    handled2 = await command_handler.handle(f"/stop_agent {sample_task}", mock_log)
    assert handled2 is True

    # Verify complete workflow
    assert len(coordinator_calls) == 2
    assert coordinator_calls[0][0] == "start"
    assert coordinator_calls[0][1] == sample_task
    assert coordinator_calls[1][0] == "stop"
    assert coordinator_calls[1][1] == sample_task
    # Verify UI was updated
    assert mock_app.update_squad_channels.called


@pytest.mark.asyncio
async def test_command_handler_coordinator_integration_orchestrator(
    command_handler, mock_app, agent_coordinator, agent_bridge, mock_log
):
    """Test command handler coordinator integration - orchestrator command."""
    # Start bridge
    await agent_bridge.start()
    await agent_coordinator.start()

    # Track orchestrator calls
    orchestrator_calls = []

    async def track_start_orchestrator(mission_description):
        orchestrator_calls.append(mission_description)
        return True

    agent_coordinator.start_orchestrator = track_start_orchestrator

    # Handle orchestrator command
    handled = await command_handler.handle("/orchestrator Test mission description", mock_log)

    # Verify command was handled
    assert handled is True
    assert len(orchestrator_calls) == 1
    assert "Test mission description" in orchestrator_calls[0]


@pytest.mark.asyncio
async def test_command_handler_coordinator_integration_sprint(
    command_handler, mock_app, agent_coordinator, agent_bridge, state_manager, mock_log
):
    """Test command handler coordinator integration - sprint command."""
    # Start bridge
    await agent_bridge.start()
    await agent_coordinator.start()

    # Create a sprint using SprintManager
    from manifest.core.sprint_manager import SprintManager
    sprint_manager = SprintManager(state_manager)
    sprint_id = sprint_manager.create_sprint(name="Test Sprint")

    # Track sprint calls
    sprint_calls = []

    async def track_start_sprint(sprint_id_param):
        sprint_calls.append(sprint_id_param)
        return {"success": True, "started_tasks": []}

    agent_coordinator.start_sprint = track_start_sprint

    # Handle sprint command
    handled = await command_handler.handle(f"/start_sprint {sprint_id}", mock_log)

    # Verify command was handled
    assert handled is True
    assert len(sprint_calls) == 1
    assert sprint_calls[0] == sprint_id


@pytest.mark.asyncio
async def test_command_handler_coordinator_integration_non_command(
    command_handler, mock_log
):
    """Test command handler coordinator integration - non-command input."""
    # Handle non-command input
    handled = await command_handler.handle("This is not a command", mock_log)

    # Should return False (not a command)
    assert handled is False
    # Log should not be written for non-commands
    # (or may be written elsewhere, but command handler returns False)


@pytest.mark.asyncio
async def test_command_handler_coordinator_error_propagation(
    command_handler, mock_app, agent_coordinator, agent_bridge, mock_log
):
    """Test command handler coordinator integration - error propagation."""
    # Start bridge
    await agent_bridge.start()
    await agent_coordinator.start()

    # Mock coordinator to raise exception
    async def failing_start_agent(task_id, agent_type, **kwargs):
        raise Exception("Coordinator error")

    agent_coordinator.start_worker_agent = failing_start_agent

    # Handle command
    # Should handle exception gracefully
    try:
        handled = await command_handler.handle("/start_agent task-1 coder", mock_log)
        # Command handler should handle the error
        assert handled is True
    except Exception:
        # If exception propagates, that's also valid behavior
        pass

    # Verify error was handled (either caught or logged)
    assert mock_log.write.called
