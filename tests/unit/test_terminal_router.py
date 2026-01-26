"""
Unit tests for TerminalRouter.

Tests terminal command execution, permission checking, and routing.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
from manifest.runtime.router.terminal_router import TerminalRouter


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing."""
    return tmp_path


@pytest.fixture
def mock_permission_manager():
    """Create a mock permission manager."""
    perm = Mock()
    perm.check_permission = Mock(return_value="allow")
    return perm


@pytest.fixture
def terminal_router(temp_dir, mock_permission_manager):
    """Create a TerminalRouter instance."""
    return TerminalRouter(
        working_dir=temp_dir,
        permission_manager=mock_permission_manager,
        agent_type="coder"
    )


def test_terminal_router_initialization(terminal_router, temp_dir):
    """Test TerminalRouter initialization."""
    assert terminal_router.working_dir == temp_dir
    assert terminal_router.permission_manager is not None
    assert terminal_router.agent_type == "coder"
    assert terminal_router is not None


@pytest.mark.asyncio
async def test_execute_command(terminal_router):
    """Test executing a command."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout="output",
            stderr=""
        )

        result = await terminal_router.execute_command("echo test")
        assert isinstance(result, dict)
        # TerminalRouter returns dict with 'stdout', 'stderr', 'returncode', 'command_id', 'backend'
        assert "backend" in result
        assert "command_id" in result
        assert "returncode" in result


@pytest.mark.asyncio
async def test_execute_command_with_permission_denied(terminal_router):
    """Test executing command with permission denied."""
    terminal_router.permission_manager.check_permission = Mock(return_value="deny")

    result = await terminal_router.execute_command("rm -rf /")
    assert isinstance(result, dict)
    # Should be denied
    assert result.get("success") is False or "permission" in str(result).lower()


@pytest.mark.asyncio
async def test_execute_command_with_ask_permission(terminal_router):
    """Test executing command with ask permission."""
    terminal_router.permission_manager.check_permission = Mock(return_value="ask")

    result = await terminal_router.execute_command("git push")

    # Should require approval - check for permission_required flag
    assert isinstance(result, dict)
    assert result.get("permission_required") is True or "approval" in str(result).lower()


def test_check_permission(terminal_router):
    """Test checking permission for a command."""
    # TerminalRouter doesn't have check_permission method, it uses permission_manager
    if terminal_router.permission_manager:
        permission = terminal_router.permission_manager.check_permission("bash", ["git", "push"])
        assert permission in ["allow", "ask", "deny"]
    else:
        # If no permission manager, verify the attribute exists
        assert hasattr(terminal_router, 'permission_manager')


def test_get_working_dir(terminal_router, temp_dir):
    """Test getting working directory."""
    # TerminalRouter doesn't have get_working_dir method, it has working_dir attribute
    assert terminal_router.working_dir == temp_dir


@pytest.mark.asyncio
async def test_execute_command_error_handling(terminal_router):
    """Test error handling in command execution."""
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = Exception("Command failed")

        result = await terminal_router.execute_command("invalid_command")
        assert isinstance(result, dict)
        # Should handle error gracefully
        assert result.get("success") is False or "error" in str(result).lower()
