"""
Unit tests for AgentWatchdog.

Tests agent monitoring, health checks, and timeout handling.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from manifest.agents.watchdog import AgentWatchdog


@pytest.fixture
def mock_state_manager():
    """Create a mock state manager."""
    state_manager = Mock()
    state_manager.get_state = Mock(return_value={"task_checklist": []})
    state_manager.save_state = AsyncMock()
    return state_manager


@pytest.fixture
def mock_terminal_router():
    """Create a mock terminal router."""
    terminal_router = Mock()
    terminal_router.active_commands = {}
    return terminal_router


@pytest.fixture
def watchdog(mock_state_manager, mock_terminal_router):
    """Create an AgentWatchdog instance."""
    return AgentWatchdog(
        state_manager=mock_state_manager,
        terminal_router=mock_terminal_router
    )


def test_watchdog_initialization(watchdog, mock_state_manager, mock_terminal_router):
    """Test AgentWatchdog initialization."""
    assert watchdog.state_manager == mock_state_manager
    assert watchdog.terminal_router == mock_terminal_router
    assert watchdog.monitoring is False
    assert watchdog is not None


@pytest.mark.asyncio
async def test_start_stop(watchdog):
    """Test starting and stopping monitoring."""
    await watchdog.start()
    assert watchdog.monitoring is True

    await watchdog.stop()
    assert watchdog.monitoring is False


def test_register_unregister_command(watchdog):
    """Test registering and unregistering commands."""
    watchdog.register_command("cmd-1")
    assert "cmd-1" in watchdog._command_timestamps

    watchdog.unregister_command("cmd-1")
    assert "cmd-1" not in watchdog._command_timestamps


def test_get_alerts(watchdog):
    """Test getting alerts."""
    alerts = watchdog.get_alerts()
    assert isinstance(alerts, list)


def test_get_status(watchdog):
    """Test getting watchdog status."""
    status = watchdog.get_status()
    assert isinstance(status, dict)
    assert "monitoring" in status
    assert "active_commands" in status
    assert "recent_alerts" in status
    assert "total_alerts" in status


def test_add_alert_callback(watchdog):
    """Test adding alert callback."""
    callback = Mock()
    watchdog.add_alert_callback(callback)
    assert callback in watchdog._alert_callbacks
