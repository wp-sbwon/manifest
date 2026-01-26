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
