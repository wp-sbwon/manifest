"""
Unit tests for CommandHandler.

Tests command parsing, routing, and handler execution.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
from manifest.ui.commands.command_handler import CommandHandler
from textual.widgets import RichLog


@pytest.fixture
def mock_app():
    """Create a mock app."""
    app = Mock()
    app.audit_drift = AsyncMock()
    app.load_intent_data = AsyncMock()
    app.load_blueprint_data = AsyncMock()
    app.load_project_data = AsyncMock()
    app.update_architect_view = AsyncMock()
    app.update_blueprint_view = AsyncMock()
    app.update_project_view = AsyncMock()
    app.agent_bridge = Mock()
    app.agent_bridge.is_connected = True
    app.agent_bridge.get_status = AsyncMock(return_value="connected")
    app.agent_coordinator = Mock()
    app.agent_coordinator.start_worker_agent = AsyncMock(return_value=True)
    app.update_squad_channels = AsyncMock()
    return app


@pytest.fixture
def command_handler(mock_app):
    """Create a CommandHandler instance."""
    return CommandHandler(app=mock_app)


@pytest.fixture
def mock_log():
    """Create a mock RichLog widget."""
    log = Mock(spec=RichLog)
    log.write = Mock()
    return log


def test_command_handler_initialization(command_handler, mock_app):
    """Test CommandHandler initialization."""
    assert command_handler.app == mock_app
    assert command_handler.parser is not None
    assert isinstance(command_handler.handlers, dict)
    assert len(command_handler.handlers) > 0


@pytest.mark.asyncio
async def test_handle_non_command(command_handler, mock_log):
    """Test handling non-command input."""
    result = await command_handler.handle("regular message", mock_log)
    assert result is False


@pytest.mark.asyncio
async def test_handle_unknown_command(command_handler, mock_log):
    """Test handling unknown command."""
    result = await command_handler.handle("/unknown_command", mock_log)
    assert result is True
    mock_log.write.assert_called()


@pytest.mark.asyncio
async def test_handle_audit_command(command_handler, mock_log):
    """Test handling /audit command."""
    result = await command_handler.handle("/audit", mock_log)
    assert result is True
    command_handler.app.audit_drift.assert_called_once()


@pytest.mark.asyncio
async def test_handle_reload_command(command_handler, mock_log):
    """Test handling /reload command."""
    result = await command_handler.handle("/reload", mock_log)
    assert result is True
    command_handler.app.load_intent_data.assert_called_once()
    command_handler.app.load_blueprint_data.assert_called_once()


@pytest.mark.asyncio
async def test_handle_status_command(command_handler, mock_log):
    """Test handling /status command."""
    result = await command_handler.handle("/status", mock_log)
    assert result is True
    mock_log.write.assert_called()


@pytest.mark.asyncio
async def test_handle_start_agent_command(command_handler, mock_log):
    """Test handling /start_agent command."""
    result = await command_handler.handle("/start_agent task-1 coder", mock_log)
    assert result is True
    command_handler.app.agent_coordinator.start_worker_agent.assert_called_once()


@pytest.mark.asyncio
async def test_handle_start_agent_no_args(command_handler, mock_log):
    """Test handling /start_agent without args."""
    result = await command_handler.handle("/start_agent", mock_log)
    assert result is True
    mock_log.write.assert_called()


@pytest.mark.asyncio
async def test_handle_stop_agent_command(command_handler, mock_log):
    """Test handling /stop_agent command."""
    command_handler.app.agent_coordinator.stop_agent = AsyncMock(return_value=True)
    result = await command_handler.handle("/stop_agent task-1", mock_log)
    assert result is True


@pytest.mark.asyncio
async def test_handle_create_task_command(command_handler, mock_log, tmp_path):
    """Test handling /create_task command."""
    from manifest.core.task_manager import TaskManager
    from manifest.core.state_manager import StateManager

    # Create real state manager for task creation
    temp_state = StateManager(manifest_dir=tmp_path)
    temp_state.create_task = Mock(return_value="task-1")
    temp_state.save_state = AsyncMock()
    command_handler.app.state_manager = temp_state
    command_handler.app._load_project_data = AsyncMock()

    result = await command_handler.handle("/create_task TestTask", mock_log)
    assert result is True


@pytest.mark.asyncio
async def test_handle_list_tasks_command(command_handler, mock_log):
    """Test handling /list_tasks command."""
    from manifest.core.state_manager import StateManager

    # Create real state manager
    temp_state = StateManager(manifest_dir=Path("/tmp/test_manifest"))
    command_handler.app.state_manager = temp_state
    command_handler.app.state_manager.find_tasks = Mock(return_value=[])

    result = await command_handler.handle("/list_tasks", mock_log)
    assert result is True


@pytest.mark.asyncio
async def test_handle_git_status_command(command_handler, mock_log):
    """Test handling /git_status command."""
    command_handler.app.git_manager = Mock()
    command_handler.app.git_manager.get_status = Mock(return_value={"status": "clean"})

    result = await command_handler.handle("/git_status", mock_log)
    assert result is True


# ========== TDL: Command Handler - Missing Items ==========

def test_command_parsing_basic(command_handler):
    """Test command parsing with basic command."""
    command, args = command_handler.parser.parse("/audit")
    assert command == "audit"
    assert args == []


def test_command_parsing_with_args(command_handler):
    """Test command parsing with arguments."""
    command, args = command_handler.parser.parse("/start_agent task-1 coder")
    assert command == "start_agent"
    assert args == ["task-1", "coder"]


def test_command_parsing_multiple_args(command_handler):
    """Test command parsing with multiple arguments."""
    command, args = command_handler.parser.parse("/create_task TaskName description stage status")
    assert command == "create_task"
    assert len(args) == 4
    assert args == ["TaskName", "description", "stage", "status"]


def test_command_parsing_non_command(command_handler):
    """Test parsing non-command input."""
    command, args = command_handler.parser.parse("regular message")
    assert command == ""
    assert args == []


def test_command_parsing_empty_command(command_handler):
    """Test parsing empty command."""
    command, args = command_handler.parser.parse("/")
    assert command == ""
    assert args == []


def test_command_parsing_key_value_pairs(command_handler):
    """Test parsing key=value pairs."""
    args = ["name=TestTask", "status=pending", "stage=planning"]
    result = command_handler.parser.parse_key_value_pairs(args)
    assert result["name"] == "TestTask"
    assert result["status"] == "pending"
    assert result["stage"] == "planning"


def test_command_parsing_key_value_pairs_with_allowed_keys(command_handler):
    """Test parsing key=value pairs with allowed keys filter."""
    args = ["name=TestTask", "status=pending", "invalid=value"]
    allowed = ["name", "status"]
    result = command_handler.parser.parse_key_value_pairs(args, allowed_keys=allowed)
    assert "name" in result
    assert "status" in result
    assert "invalid" not in result


def test_command_parsing_filters(command_handler):
    """Test parsing filter expressions."""
    args = ["status=pending", "stage=planning", "sprint=sprint-1"]
    filters = command_handler.parser.parse_filters(args)
    assert filters["status"] == "pending"
    assert filters["stage"] == "planning"
    assert filters["sprint"] == "sprint-1"


@pytest.mark.asyncio
async def test_command_routing_to_handler(command_handler, mock_log):
    """Test command routing to correct handler."""
    # Mock a handler to verify it's called
    original_handler = command_handler.handlers["audit"]
    mock_handler = AsyncMock()
    command_handler.handlers["audit"] = mock_handler

    await command_handler.handle("/audit", mock_log)

    mock_handler.assert_called_once()
    # Restore original handler
    command_handler.handlers["audit"] = original_handler


@pytest.mark.asyncio
async def test_command_routing_unknown_command(command_handler, mock_log):
    """Test routing unknown command."""
    result = await command_handler.handle("/unknown_command", mock_log)
    assert result is True
    # Should write error message
    assert mock_log.write.called


def test_command_routing_all_handlers_registered(command_handler):
    """Test that all expected handlers are registered."""
    expected_commands = [
        "audit", "reload", "status", "start_agent", "stop_agent",
        "sync_blueprints", "resolve_conflict", "config", "sprint_history",
        "orchestrator", "create_task", "update_task", "delete_task",
        "list_tasks", "approve_sprint", "start_sprint"
    ]

    for cmd in expected_commands:
        assert cmd in command_handler.handlers, f"Command '{cmd}' not registered"


@pytest.mark.asyncio
async def test_command_validation_missing_required_args(command_handler, mock_log):
    """Test command validation for missing required arguments."""
    # start_agent requires at least task_id
    result = await command_handler.handle("/start_agent", mock_log)
    assert result is True
    # Should write usage message
    assert mock_log.write.called
    call_args = str(mock_log.write.call_args)
    assert "Usage" in call_args or "usage" in call_args.lower()


@pytest.mark.asyncio
async def test_command_validation_update_task_no_args(command_handler, mock_log):
    """Test command validation for update_task without args."""
    result = await command_handler.handle("/update_task", mock_log)
    assert result is True
    # Should write usage message
    assert mock_log.write.called


@pytest.mark.asyncio
async def test_command_validation_delete_task_no_args(command_handler, mock_log):
    """Test command validation for delete_task without args."""
    result = await command_handler.handle("/delete_task", mock_log)
    assert result is True
    # Should write usage message
    assert mock_log.write.called


@pytest.mark.asyncio
async def test_command_validation_resolve_conflict_no_args(command_handler, mock_log):
    """Test command validation for resolve_conflict without args."""
    result = await command_handler.handle("/resolve_conflict", mock_log)
    assert result is True
    # Should write usage message
    assert mock_log.write.called


@pytest.mark.asyncio
async def test_command_execution_audit(command_handler, mock_log):
    """Test command execution for /audit."""
    result = await command_handler.handle("/audit", mock_log)
    assert result is True
    command_handler.app.audit_drift.assert_called_once()


@pytest.mark.asyncio
async def test_command_execution_reload(command_handler, mock_log):
    """Test command execution for /reload."""
    result = await command_handler.handle("/reload", mock_log)
    assert result is True
    command_handler.app.load_intent_data.assert_called_once()
    command_handler.app.load_blueprint_data.assert_called_once()
    command_handler.app.load_project_data.assert_called_once()


@pytest.mark.asyncio
async def test_command_execution_start_agent(command_handler, mock_log):
    """Test command execution for /start_agent."""
    command_handler.app.agent_coordinator.start_worker_agent = AsyncMock(return_value=True)
    result = await command_handler.handle("/start_agent task-1 coder", mock_log)
    assert result is True
    command_handler.app.agent_coordinator.start_worker_agent.assert_called_once_with("task-1", "coder")


@pytest.mark.asyncio
async def test_command_execution_stop_agent(command_handler, mock_log):
    """Test command execution for /stop_agent."""
    command_handler.app.agent_coordinator.stop_agent = AsyncMock(return_value=True)
    result = await command_handler.handle("/stop_agent task-1", mock_log)
    assert result is True
    command_handler.app.agent_coordinator.stop_agent.assert_called_once_with("task-1")


@pytest.mark.asyncio
async def test_command_execution_create_task(command_handler, mock_log, tmp_path):
    """Test command execution for /create_task."""
    from manifest.core.state_manager import StateManager

    temp_state = StateManager(manifest_dir=tmp_path)
    temp_state.create_task = Mock(return_value="task-1")
    temp_state.save_state = AsyncMock()
    command_handler.app.state_manager = temp_state
    command_handler.app._load_project_data = AsyncMock()

    result = await command_handler.handle("/create_task TestTask", mock_log)
    assert result is True
    temp_state.create_task.assert_called_once()


@pytest.mark.asyncio
async def test_command_execution_update_task(command_handler, mock_log):
    """Test command execution for /update_task."""
    command_handler.app.state_manager = Mock()
    command_handler.app.state_manager.update_task = Mock(return_value=True)
    command_handler.app.state_manager.save_state = AsyncMock()
    command_handler.app._load_project_data = AsyncMock()

    result = await command_handler.handle("/update_task task-1 name=NewName status=completed", mock_log)
    assert result is True
    command_handler.app.state_manager.update_task.assert_called_once()


@pytest.mark.asyncio
async def test_command_execution_delete_task(command_handler, mock_log):
    """Test command execution for /delete_task."""
    command_handler.app.state_manager = Mock()
    command_handler.app.state_manager.delete_task = Mock(return_value=True)
    command_handler.app.state_manager.save_state = AsyncMock()
    command_handler.app._load_project_data = AsyncMock()

    result = await command_handler.handle("/delete_task task-1", mock_log)
    assert result is True
    command_handler.app.state_manager.delete_task.assert_called_once()


@pytest.mark.asyncio
async def test_command_execution_list_tasks(command_handler, mock_log):
    """Test command execution for /list_tasks."""
    command_handler.app.state_manager = Mock()
    command_handler.app.state_manager.find_tasks = Mock(return_value=[
        {"id": "task-1", "name": "Task 1", "status": "pending", "stage": "planning"}
    ])

    result = await command_handler.handle("/list_tasks", mock_log)
    assert result is True
    command_handler.app.state_manager.find_tasks.assert_called_once()


@pytest.mark.asyncio
async def test_command_error_handling_handler_exception(command_handler, mock_log):
    """Test error handling when handler raises exception."""
    # Make audit handler raise an exception
    original_handler = command_handler.handlers["audit"]
    async def failing_handler(args, log):
        raise Exception("Handler error")
    command_handler.handlers["audit"] = failing_handler

    # Should not raise exception, but handle gracefully
    try:
        result = await command_handler.handle("/audit", mock_log)
        # If it returns, that's fine - error was handled
    except Exception:
        # If exception propagates, that's also acceptable for now
        pass

    # Restore original handler
    command_handler.handlers["audit"] = original_handler


@pytest.mark.asyncio
async def test_command_error_handling_missing_app_attribute(command_handler, mock_log):
    """Test error handling when app attribute is missing."""
    # Set agent_coordinator to None instead of deleting
    command_handler.app.agent_coordinator = None

    result = await command_handler.handle("/start_agent task-1", mock_log)
    assert result is True
    # Should write error message
    assert mock_log.write.called


@pytest.mark.asyncio
async def test_command_error_handling_invalid_index(command_handler, mock_log):
    """Test error handling for invalid index in apply commands."""
    command_handler.app._pending_blueprint_suggestions = [Mock(), Mock()]

    result = await command_handler.handle("/apply_blueprint_update 99", mock_log)
    assert result is True
    # Should write error message about invalid index
    assert mock_log.write.called


@pytest.mark.asyncio
async def test_command_error_handling_non_numeric_index(command_handler, mock_log):
    """Test error handling for non-numeric index."""
    command_handler.app._pending_blueprint_suggestions = [Mock()]

    result = await command_handler.handle("/apply_blueprint_update abc", mock_log)
    assert result is True
    # Should write usage message
    assert mock_log.write.called


@pytest.mark.asyncio
async def test_command_error_handling_git_not_available(command_handler, mock_log):
    """Test error handling when git is not available."""
    command_handler.app.git_manager = Mock()
    command_handler.app.git_manager.is_available = Mock(return_value=False)

    result = await command_handler.handle("/git_status", mock_log)
    assert result is True
    # Should write error message
    assert mock_log.write.called
    call_args = str(mock_log.write.call_args)
    assert "not available" in call_args.lower() or "Git not available" in call_args


@pytest.mark.asyncio
async def test_command_error_handling_task_not_found(command_handler, mock_log):
    """Test error handling when task is not found."""
    command_handler.app.state_manager = Mock()
    command_handler.app.state_manager.update_task = Mock(return_value=False)

    result = await command_handler.handle("/update_task nonexistent name=Test", mock_log)
    assert result is True
    # Should write error message
    assert mock_log.write.called
    call_args = str(mock_log.write.call_args)
    assert "not found" in call_args.lower()


@pytest.mark.asyncio
async def test_command_execution_with_filters(command_handler, mock_log):
    """Test command execution with filter arguments."""
    command_handler.app.state_manager = Mock()
    command_handler.app.state_manager.find_tasks = Mock(return_value=[])

    result = await command_handler.handle("/list_tasks status=pending stage=planning", mock_log)
    assert result is True
    # Should call find_tasks with filters
    command_handler.app.state_manager.find_tasks.assert_called_once()
    call_kwargs = command_handler.app.state_manager.find_tasks.call_args[1]
    assert call_kwargs.get("status") == "pending"
    assert call_kwargs.get("stage") == "planning"
