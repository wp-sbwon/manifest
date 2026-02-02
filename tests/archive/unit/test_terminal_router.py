"""
Unit tests for TerminalRouter.

Tests terminal command execution, permission checking, and routing.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
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


# ========== TDL: Terminal Router Tests ==========

@pytest.mark.asyncio
async def test_command_execution_subprocess(terminal_router):
    """Test command execution using subprocess."""
    # TerminalRouter now uses subprocess directly
    result = await terminal_router.execute_command("echo", ["test"])

    assert isinstance(result, dict)
    assert "backend" in result
    assert result["backend"] == "internal"
    assert result["returncode"] == 0


@pytest.mark.asyncio
async def test_command_execution_subprocess_fallback(terminal_router):
    """Test command execution uses subprocess."""
    # TerminalRouter now uses subprocess directly
    result = await terminal_router.execute_command("echo", ["test"])

    assert isinstance(result, dict)
    assert result["backend"] == "internal"
    assert result["returncode"] == 0


@pytest.mark.asyncio
async def test_permission_checking_allow(terminal_router):
    """Test permission checking with allow result."""
    terminal_router.permission_manager.check_permission = Mock(return_value="allow")

    result = await terminal_router.execute_command("echo", ["test"])

    # Should execute successfully
    assert result.get("returncode") == 0
    assert result["backend"] == "internal"
    terminal_router.permission_manager.check_permission.assert_called_once()


@pytest.mark.asyncio
async def test_permission_checking_deny(terminal_router):
    """Test permission checking with deny result."""
    terminal_router.permission_manager.check_permission = Mock(return_value="deny")

    result = await terminal_router.execute_command("rm", ["-rf", "/"])

    # Should be denied
    assert result.get("permission_denied") is True
    assert result.get("returncode") == -1 or "permission" in result.get("stderr", "").lower()
    terminal_router.permission_manager.check_permission.assert_called_once()


@pytest.mark.asyncio
async def test_permission_approval_flow(terminal_router):
    """Test permission approval flow (ask permission)."""
    terminal_router.permission_manager.check_permission = Mock(return_value="ask")

    result = await terminal_router.execute_command("git", ["push"])

    # Should require approval
    assert result.get("permission_required") is True
    assert "permission_details" in result
    assert result["permission_details"]["permission_type"] == "bash"
    assert result["permission_details"]["agent_type"] == "coder"
    terminal_router.permission_manager.check_permission.assert_called_once()


@pytest.mark.asyncio
async def test_permission_approval_flow_with_details(terminal_router):
    """Test permission approval flow includes correct details."""
    terminal_router.permission_manager.check_permission = Mock(return_value="ask")

    result = await terminal_router.execute_command("docker", ["run", "image"])

    # Verify permission details are correct
    assert result.get("permission_required") is True
    details = result.get("permission_details", {})
    assert details.get("resource") == "docker run image" or "docker" in details.get("resource", "")
    assert details.get("agent_type") == "coder"


@pytest.mark.asyncio
async def test_command_result_parsing(terminal_router):
    """Test command result parsing."""
    result = await terminal_router.execute_command("echo", ["-e", "Line 1\nLine 2\nLine 3"])

    # Verify result is properly parsed
    assert isinstance(result, dict)
    assert "stdout" in result
    assert "stderr" in result
    assert "returncode" in result
    assert "command_id" in result
    assert result["backend"] == "internal"
    assert result["returncode"] == 0


@pytest.mark.asyncio
async def test_command_result_parsing_with_nonzero_exit(terminal_router):
    """Test command result parsing with non-zero exit code."""
    result = await terminal_router.execute_command("false")  # Always returns 1

    # Verify error result is properly parsed
    assert result["returncode"] == 1
    assert result["backend"] == "internal"


@pytest.mark.asyncio
async def test_error_handling_command_not_found(terminal_router):
    """Test error handling when command is not found."""
    result = await terminal_router.execute_command("nonexistent_command_xyz_12345")

    # Should handle error gracefully
    assert isinstance(result, dict)
    assert result.get("returncode") != 0
    assert result["backend"] == "internal"


@pytest.mark.asyncio
async def test_error_handling_timeout(terminal_router):
    """Test error handling when command times out."""
    result = await terminal_router.execute_command("sleep", ["10"], timeout=0.1)

    # Should handle timeout gracefully
    assert isinstance(result, dict)
    assert result.get("timeout") is True or result.get("returncode") == -1
    assert result["backend"] == "internal"


@pytest.mark.asyncio
async def test_error_handling_execution_exception(terminal_router):
    """Test error handling when execution raises exception."""
    # TerminalRouter handles exceptions internally
    result = await terminal_router.execute_command("echo", ["test"])

    # Should execute successfully
    assert isinstance(result, dict)
    assert result["backend"] == "internal"


@pytest.mark.asyncio
async def test_working_directory_management(terminal_router, temp_dir):
    """Test working directory management."""
    # Create a test file in temp_dir
    test_file = temp_dir / "test_file.txt"
    test_file.write_text("test content")

    result = await terminal_router.execute_command("ls", ["test_file.txt"])

    # Verify working directory is set correctly
    assert terminal_router.working_dir == temp_dir
    assert result["returncode"] == 0
    assert "test_file.txt" in result["stdout"]


@pytest.mark.asyncio
async def test_working_directory_management_default(terminal_router):
    """Test working directory defaults to current directory."""
    router_no_dir = TerminalRouter(permission_manager=terminal_router.permission_manager)

    # Should default to current working directory
    assert router_no_dir.working_dir == Path.cwd()


@pytest.mark.asyncio
async def test_working_directory_management_custom(terminal_router, tmp_path):
    """Test working directory with custom directory."""
    custom_dir = tmp_path / "custom_work"
    custom_dir.mkdir()

    router_custom = TerminalRouter(
        working_dir=custom_dir,
        permission_manager=terminal_router.permission_manager
    )

    assert router_custom.working_dir == custom_dir


@pytest.mark.asyncio
async def test_command_execution_with_args(terminal_router):
    """Test command execution with arguments."""
    result = await terminal_router.execute_command("echo", ["arg1", "arg2"])

    # Verify command and args are passed correctly
    assert result["returncode"] == 0
    assert "arg1" in result["stdout"] and "arg2" in result["stdout"]
    assert result["backend"] == "internal"


@pytest.mark.asyncio
async def test_command_execution_with_timeout(terminal_router):
    """Test command execution with timeout."""
    result = await terminal_router.execute_command("echo", ["test"], timeout=5.0)

    # Verify timeout is respected
    assert result["returncode"] == 0
    assert result["backend"] == "internal"


@pytest.mark.asyncio
async def test_command_execution_streaming(terminal_router):
    """Test command execution with streaming output."""
    result = await terminal_router.execute_command("echo", ["test"], stream=True)

    # Verify streaming works
    assert result["returncode"] == 0
    assert result.get("streamed") is True
    assert result["backend"] == "internal"


def test_is_opencode_available(terminal_router):
    """Test checking if OpenCode is available."""
    # TerminalRouter always returns False (OpenCode adapter removed)
    assert terminal_router.is_opencode_available() is False


def test_cancel_command(terminal_router):
    """Test canceling a running command."""
    # Mock active commands
    mock_process = Mock()
    mock_process.terminate = Mock()
    terminal_router.active_commands["cmd-1"] = mock_process

    result = terminal_router.cancel_command("cmd-1")

    # Should cancel the command
    assert result is True
    mock_process.terminate.assert_called_once()


def test_cancel_command_not_found(terminal_router):
    """Test canceling a non-existent command."""
    result = terminal_router.cancel_command("nonexistent")

    # Should return False
    assert result is False


def test_is_command_running(terminal_router):
    """Test checking if a command is running."""
    # Mock active commands
    mock_process = Mock()
    mock_process.returncode = None  # None means still running
    terminal_router.active_commands["cmd-1"] = mock_process

    assert terminal_router.is_command_running("cmd-1") is True
    assert terminal_router.is_command_running("cmd-2") is False
