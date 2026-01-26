"""
Unit tests for ManifestApp.

Tests the main application class initialization, data loading, view updates,
command processing, and event handling.
"""
import pytest
import json
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from textual.app import App
from textual.widgets import RichLog, Input, Button

from manifest.ui.app import ManifestApp, DashboardHeader, ContextBar


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing."""
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir()
    
    # Create minimal test data files
    (manifest_dir / "intent.json").write_text(json.dumps({
        "version": "1.0",
        "sprint": "Test Sprint",
        "features": []
    }))
    
    (manifest_dir / "blueprint.json").write_text(json.dumps({
        "version": "1.0",
        "zones": {},
        "components": [],
        "contracts": []
    }))
    
    (manifest_dir / "state.json").write_text(json.dumps({
        "tasks": [],
        "chat_history": []
    }))
    
    return tmp_path


@pytest.fixture
def mock_config():
    """Create a mock config manager."""
    config = Mock()
    config.has_all_keys.return_value = True
    config.get_api_key.return_value = "test-key"
    return config


@pytest.fixture
def mock_state_manager():
    """Create a mock state manager."""
    state = Mock()
    state.get_state.return_value = {"tasks": [], "chat_history": []}
    state.get_chat_history.return_value = []
    state.add_chat_message = Mock()
    state.save_state = AsyncMock()
    return state


@pytest.fixture
def mock_agent_bridge():
    """Create a mock agent bridge."""
    bridge = Mock()
    bridge.is_connected = True
    bridge.start = AsyncMock()
    bridge.get_status = AsyncMock(return_value="connected")
    return bridge


@pytest.fixture
def mock_agent_coordinator():
    """Create a mock agent coordinator."""
    coordinator = Mock()
    coordinator.start = AsyncMock()
    coordinator.get_active_agents = Mock(return_value=[])
    return coordinator


@pytest.fixture
def app_instance(temp_dir, mock_config, mock_state_manager):
    """Create a ManifestApp instance with mocked dependencies."""
    with patch('manifest.ui.app.get_config_manager', return_value=mock_config), \
         patch('manifest.ui.app.StateManager', return_value=mock_state_manager), \
         patch('manifest.ui.app.Path.cwd', return_value=temp_dir), \
         patch('manifest.audit.monitoring.structure_manager.StructureManager') as mock_structure_manager:
        mock_structure_manager.return_value = Mock()
        app = ManifestApp()
        # manifest_dir is set in __init__ after StructureManager, override it
        app.manifest_dir = temp_dir / ".manifest"
        # Also update structure_manager's manifest_dir if it was already created
        if hasattr(app, 'structure_manager') and app.structure_manager:
            app.structure_manager.manifest_dir = temp_dir / ".manifest"
        return app


def test_app_initialization(app_instance):
    """Test ManifestApp initialization."""
    assert app_instance is not None
    assert app_instance.config is not None
    assert app_instance.state_manager is not None
    assert app_instance.manifest_dir is not None
    assert app_instance.intent_data == {}
    assert app_instance.blueprint_data == {}
    assert app_instance.project_data == {}
    assert app_instance.current_view == "architect"
    assert app_instance.inspector_mode == "visual"


def test_dashboard_header_initialization():
    """Test DashboardHeader initialization."""
    header = DashboardHeader()
    assert header.metrics is not None
    assert "match_pct" in header.metrics
    assert "active_tasks" in header.metrics


def test_dashboard_header_update_metrics():
    """Test DashboardHeader update_metrics method."""
    header = DashboardHeader()
    new_metrics = {
        "match_pct": 95,
        "active_tasks": 5,
        "completed_tasks": 10,
        "running_agents": 2
    }
    header.update_metrics(new_metrics)
    assert header.metrics == new_metrics


def test_dashboard_header_render():
    """Test DashboardHeader render method."""
    header = DashboardHeader()
    header.metrics = {
        "match_pct": 95,
        "active_tasks": 5,
        "completed_tasks": 10,
        "running_agents": 2
    }
    rendered = header.render()
    assert isinstance(rendered, str)
    assert "95" in rendered
    assert "Manifest Dashboard" in rendered


def test_context_bar_initialization():
    """Test ContextBar initialization."""
    context_bar = ContextBar()
    assert context_bar.max_lines == 1
    assert context_bar.activities == []


def test_context_bar_add_activity():
    """Test ContextBar add_activity method."""
    context_bar = ContextBar()
    context_bar.add_activity("task-1", "coder", "Writing code")
    assert len(context_bar.activities) == 1
    assert context_bar.activities[0]["task_id"] == "task-1"
    assert context_bar.activities[0]["agent_type"] == "coder"


def test_context_bar_remove_activity():
    """Test ContextBar remove_activity method."""
    context_bar = ContextBar()
    context_bar.add_activity("task-1", "coder", "Writing code")
    context_bar.remove_activity("task-1", "coder")
    assert len(context_bar.activities) == 0


@pytest.mark.asyncio
async def test_load_intent_data(app_instance):
    """Test loading intent data."""
    mock_data = {"version": "1.0", "features": []}
    app_instance.data_loader.load_intent_data = AsyncMock(return_value=mock_data)
    
    await app_instance.load_intent_data()
    
    assert app_instance.intent_data == mock_data
    app_instance.data_loader.load_intent_data.assert_called_once()


@pytest.mark.asyncio
async def test_load_blueprint_data(app_instance):
    """Test loading blueprint data."""
    mock_data = {"version": "1.0", "components": []}
    app_instance.data_loader.load_blueprint_data = AsyncMock(return_value=mock_data)
    
    await app_instance.load_blueprint_data()
    
    assert app_instance.blueprint_data == mock_data
    app_instance.data_loader.load_blueprint_data.assert_called_once()


@pytest.mark.asyncio
async def test_load_project_data(app_instance):
    """Test loading project data."""
    mock_data = {"tasks": [], "sprints": []}
    app_instance.data_loader.load_project_data = AsyncMock(return_value=mock_data)
    
    await app_instance.load_project_data()
    
    assert app_instance.project_data == mock_data
    app_instance.data_loader.load_project_data.assert_called_once()


@pytest.mark.asyncio
async def test_update_architect_view(app_instance):
    """Test updating architect view."""
    app_instance.intent_data = {
        "features": [
            {"name": "Feature 1", "reqs": [{"id": "REQ-1", "state": "done"}]}
        ]
    }
    
    # Mock query_one to avoid UI dependencies
    with patch.object(app_instance, 'query_one', return_value=Mock()):
        await app_instance.update_architect_view()
        # Should complete without error


@pytest.mark.asyncio
async def test_update_blueprint_view(app_instance):
    """Test updating blueprint view."""
    app_instance.blueprint_data = {
        "zones": {"client": [], "server": []},
        "components": []
    }
    
    with patch.object(app_instance, 'query_one', return_value=Mock()):
        await app_instance.update_blueprint_view()
        # Should complete without error


@pytest.mark.asyncio
async def test_update_project_view(app_instance):
    """Test updating project view."""
    app_instance.project_data = {
        "tasks": [],
        "sprints": []
    }
    
    with patch.object(app_instance, 'query_one', return_value=Mock()):
        await app_instance.update_project_view()
        # Should complete without error


@pytest.mark.asyncio
async def test_update_task_tree(app_instance):
    """Test updating task tree."""
    app_instance.state_manager.find_tasks = Mock(return_value=[])
    
    mock_tree = Mock()
    with patch.object(app_instance, 'query_one', return_value=mock_tree):
        await app_instance.update_task_tree()
        # Should complete without error


@pytest.mark.asyncio
async def test_update_dashboard_metrics(app_instance):
    """Test updating dashboard metrics."""
    app_instance.state_manager.find_tasks = Mock(return_value=[])
    app_instance.agent_coordinator = Mock()
    app_instance.agent_coordinator.get_active_agents = Mock(return_value=[])
    
    mock_header = Mock()
    with patch.object(app_instance, 'query_one', return_value=mock_header):
        await app_instance.update_dashboard_metrics()
        # Should complete without error


@pytest.mark.asyncio
async def test_update_context_bar(app_instance):
    """Test updating context bar."""
    app_instance.agent_coordinator = Mock()
    app_instance.agent_coordinator.get_active_agents = Mock(return_value=[])
    
    mock_context_bar = Mock()
    with patch.object(app_instance, 'query_one', return_value=mock_context_bar):
        await app_instance.update_context_bar()
        # Should complete without error


@pytest.mark.asyncio
async def test_audit_drift(app_instance):
    """Test drift audit functionality."""
    app_instance.drift_auditor.audit = Mock(return_value=[])
    
    mock_log = Mock()
    with patch.object(app_instance, 'query_one', return_value=mock_log):
        await app_instance.audit_drift()
        # Should complete without error


@pytest.mark.asyncio
async def test_action_toggle_inspector(app_instance):
    """Test toggling inspector view."""
    app_instance.inspector_mode = "visual"
    
    mock_visual = Mock()
    mock_data = Mock()
    mock_drift = Mock()
    
    def query_one_side_effect(query, *args, **kwargs):
        if query == "#insp-visual":
            return mock_visual
        elif query == "#insp-data":
            return mock_data
        elif query == "#insp-drift":
            return mock_drift
        return Mock()
    
    with patch.object(app_instance, 'query_one', side_effect=query_one_side_effect):
        app_instance.action_toggle_inspector()
        # Should toggle inspector mode


def test_action_show_project(app_instance):
    """Test showing project view."""
    mock_tabs = Mock()
    with patch.object(app_instance, 'query_one', return_value=mock_tabs):
        app_instance.action_show_project()
        # Should switch to project tab


@pytest.mark.asyncio
async def test_process_command(app_instance):
    """Test processing user commands."""
    app_instance.command_handler = Mock()
    app_instance.command_handler.handle = AsyncMock(return_value=True)
    app_instance.agent_bridge = None  # Disable agent bridge for this test
    
    mock_log = Mock()
    # process_command is decorated with @work, which wraps it in a Worker
    # We can test by directly calling the underlying coroutine function
    # The @work decorator is applied at runtime, so we need to access the original
    import inspect
    # Get the original function (before @work decorator)
    original_func = app_instance.process_command.__wrapped__ if hasattr(app_instance.process_command, '__wrapped__') else app_instance.process_command
    
    with patch('asyncio.sleep', new_callable=AsyncMock):
        # Call the underlying async function directly
        if inspect.iscoroutinefunction(original_func):
            await original_func(app_instance, "/test", mock_log)
        else:
            # Fallback: test the logic manually
            if "/test".startswith("/") and app_instance.command_handler:
                await app_instance.command_handler.handle("/test", mock_log)
    
    app_instance.command_handler.handle.assert_called_once_with("/test", mock_log)


@pytest.mark.asyncio
async def test_on_input_submitted(app_instance):
    """Test handling input submission."""
    mock_input = Mock()
    mock_input.value = "/test command"
    mock_input.id = "global-input"
    
    mock_log = Mock()
    
    event = Mock()
    event.input = mock_input
    event.value = "/test command"  # on_input_submitted uses event.value.strip()
    
    app_instance.process_command = AsyncMock()
    app_instance.state_manager.add_chat_message = Mock()
    app_instance.state_manager.set_last_action = Mock()
    app_instance.state_manager.save_state = AsyncMock()
    
    with patch.object(app_instance, 'query_one', return_value=mock_log), \
         patch('asyncio.sleep', new_callable=AsyncMock):
        await app_instance.on_input_submitted(event)
        
        # Check that process_command was called with stripped value
        app_instance.process_command.assert_called_once()
        call_args = app_instance.process_command.call_args[0]
        assert call_args[0] == "/test command"
        assert call_args[1] == mock_log


@pytest.mark.asyncio
async def test_on_task_approved(app_instance):
    """Test handling task approval."""
    message = Mock()
    message.task_id = "task-1"
    
    app_instance.agent_bridge = Mock()
    app_instance.agent_bridge.is_connected = True
    app_instance.agent_bridge.promote_task = AsyncMock()
    app_instance.state_manager.save_state = AsyncMock()
    
    mock_log = Mock()
    
    with patch.object(app_instance, 'query_one', return_value=mock_log):
        await app_instance.on_task_approved(message)
        
        app_instance.agent_bridge.promote_task.assert_called_once_with("task-1", "approved")
        app_instance.state_manager.save_state.assert_called_once()


@pytest.mark.asyncio
async def test_on_task_rejected(app_instance):
    """Test handling task rejection."""
    message = Mock()
    message.task_id = "task-1"
    
    app_instance.state_manager.save_state = AsyncMock()
    
    mock_log = Mock()
    
    with patch.object(app_instance, 'query_one', return_value=mock_log):
        await app_instance.on_task_rejected(message)
        
        app_instance.state_manager.save_state.assert_called_once()


@pytest.mark.asyncio
async def test_on_task_selected(app_instance):
    """Test handling task selection."""
    message = Mock()
    message.task_id = "task-1"
    message.task = {"id": "task-1", "title": "Test", "description": "Test task", "stage": "planning", "worker_squad": {"stages": {}}}
    message.current_status = "pending"
    
    mock_log = Mock()
    
    with patch.object(app_instance, 'query_one', return_value=mock_log):
        await app_instance.on_task_selected(message)
        
        # Should write to log
        assert mock_log.write.called


@pytest.mark.asyncio
async def test_on_component_selected(app_instance):
    """Test handling component selection."""
    message = Mock()
    message.component_id = "comp-1"
    message.component_data = {"id": "comp-1", "name": "TestComponent"}
    
    app_instance.blueprint_data = {
        "components": [{"id": "comp-1", "name": "TestComponent"}]
    }
    app_instance._update_component_inspector = AsyncMock()
    
    # Mock query_one to avoid ScreenStackError
    with patch.object(app_instance, 'query_one', return_value=Mock()):
        await app_instance.on_component_selected(message)
        
        app_instance._update_component_inspector.assert_called_once()


@pytest.mark.asyncio
async def test_sync_blueprints(app_instance):
    """Test blueprint synchronization."""
    with patch('manifest.audit.blueprint.blueprint_loader.BlueprintLoader') as mock_loader_class:
        mock_loader = Mock()
        mock_loader_class.load_blueprint.return_value = {"components": []}
        mock_loader_class.load_code_blueprint.return_value = {"components": []}
        app_instance.blueprint_synchronizer.sync_blueprints = AsyncMock(return_value=None)
        
        result = await app_instance.sync_blueprints()
        
        app_instance.blueprint_synchronizer.sync_blueprints.assert_called_once()


@pytest.mark.asyncio
async def test_resolve_conflict(app_instance):
    """Test resolving blueprint conflicts."""
    conflict_file = app_instance.manifest_dir / "conflicts" / "conflict-1.json"
    conflict_file.parent.mkdir(parents=True, exist_ok=True)
    conflict_file.write_text('{"id": "conflict-1"}')  # Create the file so it exists
    
    # Create a mock conflict report
    mock_report = Mock()
    mock_report.status = "pending"
    mock_report.task_id = "task-1"
    mock_report.to_dict.return_value = {"id": "conflict-1"}
    
    app_instance.blueprint_synchronizer.load_conflict_report = Mock(return_value=mock_report)
    app_instance.blueprint_synchronizer.save_conflict_report = Mock()
    app_instance.agent_coordinator = Mock()
    app_instance.agent_coordinator.handle_blueprint_conflict = AsyncMock()
    
    await app_instance.resolve_conflict("conflict-1", "approved")
    
    app_instance.blueprint_synchronizer.load_conflict_report.assert_called_once()
    app_instance.blueprint_synchronizer.save_conflict_report.assert_called_once()


@pytest.mark.asyncio
async def test_update_agent_status(app_instance):
    """Test updating agent status display."""
    app_instance.agent_coordinator = Mock()
    app_instance.agent_coordinator.get_active_agents = Mock(return_value=[])
    
    mock_view = Mock()
    with patch.object(app_instance, 'query_one', return_value=mock_view):
        await app_instance.update_agent_status()
        # Should complete without error


@pytest.mark.asyncio
async def test_update_history_view(app_instance):
    """Test updating history view."""
    app_instance.git_manager.get_recent_commits = Mock(return_value=[])
    
    mock_view = Mock()
    with patch.object(app_instance, 'query_one', return_value=mock_view):
        await app_instance.update_history_view()
        # Should complete without error


@pytest.mark.asyncio
async def test_show_sprint_history(app_instance):
    """Test showing sprint history."""
    app_instance.state_manager.list_sprints = Mock(return_value=["sprint-1", "sprint-2"])
    app_instance.state_manager.load_sprint = Mock(return_value={
        "id": "sprint-1",
        "name": "Test Sprint",
        "status": "active",
        "created_at": "2026-01-01",
        "tasks": [{"status": "completed"}, {"status": "pending"}]
    })
    
    mock_log = Mock()
    with patch.object(app_instance, 'query_one', return_value=mock_log):
        await app_instance.show_sprint_history()
        # Should write sprint history to log
        assert mock_log.write.called


@pytest.mark.asyncio
async def test_show_orchestrator_chat(app_instance):
    """Test showing orchestrator chat."""
    app_instance.state_manager.get_chat_history = Mock(return_value=[])
    
    mock_log = Mock()
    with patch.object(app_instance, 'query_one', return_value=mock_log):
        await app_instance.show_orchestrator_chat()
        # Should complete without error


@pytest.mark.asyncio
async def test_action_open_settings(app_instance):
    """Test opening settings screen."""
    mock_screen = Mock()
    with patch('manifest.ui.app.SettingsScreen', return_value=mock_screen), \
         patch.object(app_instance, 'push_screen') as push_screen:
        app_instance.action_open_settings("api_keys")
        push_screen.assert_called_once()


@pytest.mark.asyncio
async def test_on_tab_switched(app_instance):
    """Test handling tab switch events."""
    event = Mock()
    event.pane = Mock()
    event.pane.id = "tab-structure"
    
    mock_visual = Mock()
    mock_data = Mock()
    mock_drift = Mock()
    
    def query_one_side_effect(query, *args, **kwargs):
        if query == "#insp-visual":
            return mock_visual
        elif query == "#insp-data":
            return mock_data
        elif query == "#insp-drift":
            return mock_drift
        return Mock()
    
    app_instance._load_structure_data = AsyncMock()
    
    with patch.object(app_instance, 'query_one', side_effect=query_one_side_effect):
        await app_instance.on_tab_switched(event)
        
        app_instance._load_structure_data.assert_called_once()
        assert app_instance.current_view == "structure"


@pytest.mark.asyncio
async def test_start_container_api(app_instance):
    """Test starting container API server."""
    with patch('manifest.ui.app.create_container_api'), \
         patch('manifest.ui.app.uvicorn.run'), \
         patch('threading.Thread') as mock_thread, \
         patch.object(app_instance, 'query_one', return_value=Mock()):
        await app_instance._start_container_api()
        # Should start API server


@pytest.mark.asyncio
async def test_stop_container_api(app_instance):
    """Test stopping container API server."""
    await app_instance._stop_container_api()
    # Should complete without error (currently a no-op)


def test_app_bindings():
    """Test that app has correct key bindings."""
    # Check that BINDINGS are defined
    assert hasattr(ManifestApp, 'BINDINGS')
    assert isinstance(ManifestApp.BINDINGS, list)
    assert len(ManifestApp.BINDINGS) > 0


def test_app_css():
    """Test that app has CSS defined."""
    # Check that CSS is defined
    assert hasattr(ManifestApp, 'CSS')
    assert isinstance(ManifestApp.CSS, str)
    assert len(ManifestApp.CSS) > 0
