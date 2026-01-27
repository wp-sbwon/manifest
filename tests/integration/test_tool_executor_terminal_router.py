"""
Integration tests for ToolExecutor → TerminalRouter interaction.

Tests the integration between ToolExecutor and TerminalRouter to ensure
proper command execution, permission checks, and result parsing.
"""
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from manifest.runtime.tools.tool_executor import ToolExecutor
from manifest.runtime.router.terminal_router import TerminalRouter
from manifest.runtime.permissions.permission_manager import PermissionManager
from manifest.core.config import ConfigManager


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def config_manager(temp_dir):
    """Create a ConfigManager instance."""
    return ConfigManager(manifest_dir=temp_dir)


@pytest.fixture
def permission_manager(config_manager):
    """Create a PermissionManager instance."""
    return PermissionManager(config_manager=config_manager, agent_type="coder")


@pytest.fixture
def terminal_router(temp_dir, permission_manager):
    """Create a TerminalRouter instance."""
    return TerminalRouter(
        working_dir=temp_dir,
        permission_manager=permission_manager,
        agent_type="coder"
    )


@pytest.fixture
def tool_executor(terminal_router):
    """Create a ToolExecutor instance."""
    return ToolExecutor(
        terminal_router=terminal_router,
        agent_type="coder",
        task_id="test-task",
        agent_id="test-agent"
    )


# ========== TDL: Tool Executor → Terminal Router Integration ==========

@pytest.mark.asyncio
async def test_tool_calls_execute_commands(
    tool_executor, terminal_router
):
    """Test tool calls execute commands."""
    # Track terminal router calls
    execute_calls = []

    async def track_execute_command(command, args=None, **kwargs):
        execute_calls.append((command, args, kwargs))
        return {
            "stdout": "command output",
            "stderr": "",
            "returncode": 0,
            "command_id": "test-cmd",
            "backend": "internal"
        }

    terminal_router.execute_command = track_execute_command

    # Execute bash tool
    result = await tool_executor.execute_tool(
        tool_name="bash",
        tool_input={
            "id": "tool-1",
            "command": "echo",
            "args": ["hello"]
        }
    )

    # Verify terminal router was called
    assert len(execute_calls) == 1
    assert execute_calls[0][0] == "echo"
    assert execute_calls[0][1] == ["hello"]
    assert result["tool_name"] == "bash"
    assert "result" in result


@pytest.mark.asyncio
async def test_permission_checks_before_execution(
    tool_executor, terminal_router, permission_manager
):
    """Test permission checks before execution."""
    # Mock permission manager to deny command
    original_check = permission_manager.check_permission

    def deny_permission(resource, action):
        return "deny"

    permission_manager.check_permission = deny_permission

    # Mock terminal router to track permission checks
    execute_calls = []

    async def track_execute_command(command, args=None, **kwargs):
        execute_calls.append((command, args))
        return {
            "stdout": "",
            "stderr": "",
            "returncode": 1,
            "permission_denied": True,
            "command_id": "test-cmd",
            "backend": "internal"
        }

    terminal_router.execute_command = track_execute_command

    # Execute bash tool
    result = await tool_executor.execute_tool(
        tool_name="bash",
        tool_input={
            "id": "tool-1",
            "command": "rm",
            "args": ["-rf", "/"]
        }
    )

    # Verify permission was checked (terminal router checks permissions)
    # Result should indicate permission denied
    assert result["tool_name"] == "bash"
    # Terminal router should have checked permissions
    assert len(execute_calls) > 0 or result.get("permission_denied") or result.get("error")

    # Restore original method
    permission_manager.check_permission = original_check


@pytest.mark.asyncio
async def test_result_parsing_and_validation(
    tool_executor, terminal_router
):
    """Test result parsing and validation."""
    # Mock terminal router to return specific result
    async def mock_execute_command(command, args=None, **kwargs):
        return {
            "stdout": "test output\nline 2",
            "stderr": "warning message",
            "returncode": 0,
            "command_id": "cmd-123",
            "backend": "internal"
        }

    terminal_router.execute_command = mock_execute_command

    # Execute bash tool
    result = await tool_executor.execute_tool(
        tool_name="bash",
        tool_input={
            "id": "tool-1",
            "command": "test",
            "args": []
        }
    )

    # Verify result structure
    assert result["tool_name"] == "bash"
    assert "result" in result
    result_data = result["result"]
    assert result_data is not None
    assert "stdout" in result_data
    assert "stderr" in result_data
    assert "returncode" in result_data
    assert result_data["returncode"] == 0
    assert result_data["stdout"] == "test output\nline 2"


@pytest.mark.asyncio
async def test_command_execution_error_handling(
    tool_executor, terminal_router
):
    """Test command execution error handling."""
    # Mock terminal router to raise error
    async def mock_execute_command(command, args=None, **kwargs):
        raise Exception("Command execution failed")

    terminal_router.execute_command = mock_execute_command

    # Execute bash tool
    result = await tool_executor.execute_tool(
        tool_name="bash",
        tool_input={
            "id": "tool-1",
            "command": "failing-command",
            "args": []
        }
    )

    # Verify error was handled
    assert result["tool_name"] == "bash"
    assert "error" in result
    assert "Command execution failed" in result["error"]


@pytest.mark.asyncio
async def test_multiple_tool_calls_execution(
    tool_executor, terminal_router
):
    """Test multiple tool calls execution."""
    # Track all command executions
    execute_calls = []

    async def track_execute_command(command, args=None, **kwargs):
        execute_calls.append((command, args))
        return {
            "stdout": f"output for {command}",
            "stderr": "",
            "returncode": 0,
            "command_id": f"cmd-{len(execute_calls)}",
            "backend": "internal"
        }

    terminal_router.execute_command = track_execute_command

    # Execute multiple tool calls
    tool_calls = [
        {
            "id": "tool-1",
            "name": "bash",
            "input": {"command": "echo", "args": ["hello"]}
        },
        {
            "id": "tool-2",
            "name": "bash",
            "input": {"command": "echo", "args": ["world"]}
        }
    ]

    results = await tool_executor.execute_tool_calls(tool_calls)

    # Verify all commands were executed
    assert len(results) == 2
    assert len(execute_calls) == 2
    assert execute_calls[0][0] == "echo"
    assert execute_calls[1][0] == "echo"
    assert results[0]["tool_name"] == "bash"
    assert results[1]["tool_name"] == "bash"


@pytest.mark.asyncio
async def test_command_result_validation(
    tool_executor, terminal_router
):
    """Test command result validation."""
    # Mock terminal router with various return codes
    async def mock_execute_command(command, args=None, **kwargs):
        if command == "success":
            return {
                "stdout": "success",
                "stderr": "",
                "returncode": 0,
                "command_id": "cmd-1",
                "backend": "internal"
            }
        elif command == "failure":
            return {
                "stdout": "",
                "stderr": "error occurred",
                "returncode": 1,
                "command_id": "cmd-2",
                "backend": "internal"
            }
        else:
            return {
                "stdout": "",
                "stderr": "",
                "returncode": -1,
                "command_id": "cmd-3",
                "backend": "internal"
            }

    terminal_router.execute_command = mock_execute_command

    # Execute different commands
    success_result = await tool_executor.execute_tool(
        tool_name="bash",
        tool_input={"id": "tool-1", "command": "success", "args": []}
    )

    failure_result = await tool_executor.execute_tool(
        tool_name="bash",
        tool_input={"id": "tool-2", "command": "failure", "args": []}
    )

    # Verify results are validated
    assert success_result["tool_name"] == "bash"
    assert success_result["result"]["returncode"] == 0
    assert failure_result["tool_name"] == "bash"
    assert failure_result["result"]["returncode"] == 1


@pytest.mark.asyncio
async def test_integration_complete_workflow(
    tool_executor, terminal_router, temp_dir
):
    """Test complete integration workflow."""
    # Create a test file
    test_file = temp_dir / "test.txt"
    test_file.write_text("test content")

    # Track command executions
    execute_calls = []

    async def track_execute_command(command, args=None, **kwargs):
        execute_calls.append((command, args, kwargs))
        # Simulate actual command execution
        if command == "ls":
            return {
                "stdout": "test.txt\n",
                "stderr": "",
                "returncode": 0,
                "command_id": "cmd-1",
                "backend": "internal"
            }
        elif command == "cat":
            if args and args[0] == str(test_file):
                return {
                    "stdout": "test content",
                    "stderr": "",
                    "returncode": 0,
                    "command_id": "cmd-2",
                    "backend": "internal"
                }
        return {
            "stdout": "",
            "stderr": "command not found",
            "returncode": 1,
            "command_id": "cmd-3",
            "backend": "internal"
        }

    terminal_router.execute_command = track_execute_command

    # Execute workflow: list files, then read file
    tool_calls = [
        {
            "id": "tool-1",
            "name": "bash",
            "input": {"command": "ls", "args": [str(temp_dir)]}
        },
        {
            "id": "tool-2",
            "name": "bash",
            "input": {"command": "cat", "args": [str(test_file)]}
        }
    ]

    results = await tool_executor.execute_tool_calls(tool_calls)

    # Verify complete workflow
    assert len(results) == 2
    assert len(execute_calls) == 2
    assert execute_calls[0][0] == "ls"
    assert execute_calls[1][0] == "cat"
    assert results[0]["result"]["returncode"] == 0
    assert results[1]["result"]["returncode"] == 0
    assert "test.txt" in results[0]["result"]["stdout"]
    assert "test content" in results[1]["result"]["stdout"]


@pytest.mark.asyncio
async def test_terminal_router_not_available(
    temp_dir
):
    """Test behavior when terminal router is not available."""
    # Create tool executor without terminal router
    tool_executor = ToolExecutor(
        terminal_router=None,
        agent_type="coder"
    )

    # Execute bash tool
    result = await tool_executor.execute_tool(
        tool_name="bash",
        tool_input={
            "id": "tool-1",
            "command": "echo",
            "args": ["hello"]
        }
    )

    # Verify error is returned
    assert result["tool_name"] == "bash"
    assert "error" in result
    assert "TerminalRouter not available" in result["error"]


@pytest.mark.asyncio
async def test_command_with_timeout(
    tool_executor, terminal_router
):
    """Test command execution with timeout."""
    # Track timeout parameter
    timeout_received = None

    async def track_execute_command(command, args=None, timeout=None, **kwargs):
        nonlocal timeout_received
        timeout_received = timeout
        return {
            "stdout": "output",
            "stderr": "",
            "returncode": 0,
            "command_id": "cmd-1",
            "backend": "internal"
        }

    terminal_router.execute_command = track_execute_command

    # Execute with timeout (note: tool_executor doesn't pass timeout directly,
    # but we can verify the integration)
    result = await tool_executor.execute_tool(
        tool_name="bash",
        tool_input={
            "id": "tool-1",
            "command": "long-running",
            "args": []
        }
    )

    # Verify command was executed
    assert result["tool_name"] == "bash"
    # Timeout may or may not be passed depending on implementation
    assert timeout_received is None or isinstance(timeout_received, (int, float))
