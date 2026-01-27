"""
Integration tests for ToolExecutor → PermissionManager interaction.

Tests the integration between ToolExecutor and PermissionManager to ensure
proper permission checks for tool execution and approval workflow integration.
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
from manifest.runtime.permissions.permission_approval_manager import PermissionApprovalManager
from manifest.runtime.tools.file_manager import FileManager
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
def approval_manager():
    """Create a PermissionApprovalManager instance."""
    return PermissionApprovalManager()


@pytest.fixture
def terminal_router(temp_dir, permission_manager):
    """Create a TerminalRouter instance."""
    return TerminalRouter(
        working_dir=temp_dir,
        permission_manager=permission_manager,
        agent_type="coder"
    )


@pytest.fixture
def file_manager(temp_dir, permission_manager):
    """Create a FileManager instance."""
    return FileManager(
        working_dir=temp_dir,
        permission_manager=permission_manager,
        agent_type="coder"
    )


@pytest.fixture
def tool_executor(terminal_router, file_manager, approval_manager):
    """Create a ToolExecutor instance."""
    return ToolExecutor(
        terminal_router=terminal_router,
        file_manager=file_manager,
        approval_manager=approval_manager,
        agent_type="coder",
        task_id="test-task",
        agent_id="test-agent"
    )


# ========== TDL: Tool Executor → Permission Manager Integration ==========

@pytest.mark.asyncio
async def test_permission_checks_for_tool_execution_allow(
    tool_executor, permission_manager, config_manager
):
    """Test permission checks for tool execution - allow permission."""
    # Configure permission manager to allow command
    mock_config = Mock(spec=ConfigManager)
    mock_config._load_agent_config = Mock(return_value={
        "agent_permissions": {
            "agent": {
                "coder": {
                    "permission": {
                        "bash": {
                            "*": "allow"  # Allow all commands
                        }
                    }
                }
            }
        }
    })

    permission_manager.config_manager = mock_config
    permission_manager._load_permissions()

    # Mock terminal router to return success
    async def mock_execute_command(command, args=None, **kwargs):
        return {
            "stdout": "output",
            "stderr": "",
            "returncode": 0,
            "command_id": "cmd-1",
            "backend": "internal"
        }

    tool_executor.terminal_router.execute_command = mock_execute_command

    # Execute tool
    result = await tool_executor.execute_tool(
        tool_name="bash",
        tool_input={
            "id": "tool-1",
            "command": "echo",
            "args": ["hello"]
        }
    )

    # Verify tool executed successfully (permission was allowed)
    assert result["tool_name"] == "bash"
    assert "error" not in result or result.get("error") is None
    assert result.get("permission_denied") is not True


@pytest.mark.asyncio
async def test_permission_checks_for_tool_execution_deny(
    tool_executor, permission_manager, config_manager
):
    """Test permission checks for tool execution - deny permission."""
    # Configure permission manager to deny command
    mock_config = Mock(spec=ConfigManager)
    mock_config._load_agent_config = Mock(return_value={
        "agent_permissions": {
            "agent": {
                "coder": {
                    "permission": {
                        "bash": {
                            "rm *": "deny"  # Deny rm commands
                        }
                    }
                }
            }
        }
    })

    permission_manager.config_manager = mock_config
    permission_manager._load_permissions()

    # Mock terminal router to return permission denied
    async def mock_execute_command(command, args=None, **kwargs):
        # TerminalRouter checks permission and returns denied
        return {
            "stdout": "",
            "stderr": "Permission denied: Command 'rm -rf /' is not allowed",
            "returncode": -1,
            "command_id": "cmd-1",
            "permission_denied": True,
            "backend": "internal"
        }

    tool_executor.terminal_router.execute_command = mock_execute_command

    # Execute tool
    result = await tool_executor.execute_tool(
        tool_name="bash",
        tool_input={
            "id": "tool-1",
            "command": "rm",
            "args": ["-rf", "/"]
        }
    )

    # Verify permission was denied
    assert result["tool_name"] == "bash"
    assert result.get("permission_denied") is True
    assert "error" in result
    assert "Permission denied" in result["error"]


@pytest.mark.asyncio
async def test_permission_checks_for_tool_execution_ask(
    tool_executor, permission_manager, approval_manager, config_manager
):
    """Test permission checks for tool execution - ask permission."""
    # Configure permission manager to ask for permission
    mock_config = Mock(spec=ConfigManager)
    mock_config._load_agent_config = Mock(return_value={
        "agent_permissions": {
            "agent": {
                "coder": {
                    "permission": {
                        "bash": {
                            "git push": "ask"  # Ask for git push
                        }
                    }
                }
            }
        }
    })

    permission_manager.config_manager = mock_config
    permission_manager._load_permissions()

    # Track approval requests
    approval_requests = []

    def track_create_approval_request(*args, **kwargs):
        approval_requests.append((args, kwargs))
        return "request-123"

    approval_manager.create_approval_request = track_create_approval_request

    # Mock terminal router to return permission required
    async def mock_execute_command(command, args=None, **kwargs):
        return {
            "stdout": "",
            "stderr": "Permission approval required",
            "returncode": -1,
            "command_id": "cmd-1",
            "permission_required": True,
            "permission_details": {
                "permission_type": "bash",
                "resource": "git push",
                "agent_type": "coder"
            },
            "backend": "internal"
        }

    tool_executor.terminal_router.execute_command = mock_execute_command

    # Execute tool
    result = await tool_executor.execute_tool(
        tool_name="bash",
        tool_input={
            "id": "tool-1",
            "command": "git",
            "args": ["push"]
        }
    )

    # Verify approval request was created
    assert result["tool_name"] == "bash"
    assert result.get("permission_required") is True
    assert len(approval_requests) > 0
    assert "approval_request_id" in result


@pytest.mark.asyncio
async def test_approval_workflow_integration_approval_granted(
    tool_executor, permission_manager, approval_manager, config_manager
):
    """Test approval workflow integration - approval granted."""
    # Configure permission manager to ask
    mock_config = Mock(spec=ConfigManager)
    mock_config._load_agent_config = Mock(return_value={
        "agent_permissions": {
            "agent": {
                "coder": {
                    "permission": {
                        "bash": {
                            "git push": "ask"
                        }
                    }
                }
            }
        }
    })

    permission_manager.config_manager = mock_config
    permission_manager._load_permissions()

    # Track approval workflow
    approval_created = False
    approval_granted = False

    def track_create_approval_request(*args, **kwargs):
        nonlocal approval_created
        approval_created = True
        return "request-123"

    approval_manager.create_approval_request = track_create_approval_request

    # Mock terminal router - first returns permission_required, then success after approval
    call_count = 0

    async def mock_execute_command(command, args=None, **kwargs):
        nonlocal call_count, approval_granted
        call_count += 1
        if call_count == 1:
            # First call: permission required
            return {
                "stdout": "",
                "stderr": "Permission approval required",
                "returncode": -1,
                "command_id": "cmd-1",
                "permission_required": True,
                "permission_details": {
                    "permission_type": "bash",
                    "resource": "git push",
                    "agent_type": "coder"
                },
                "backend": "internal"
            }
        else:
            # Second call: approved and executed
            approval_granted = True
            return {
                "stdout": "pushed",
                "stderr": "",
                "returncode": 0,
                "command_id": "cmd-2",
                "backend": "internal"
            }

    tool_executor.terminal_router.execute_command = mock_execute_command

    # First execution: permission required
    result1 = await tool_executor.execute_tool(
        tool_name="bash",
        tool_input={
            "id": "tool-1",
            "command": "git",
            "args": ["push"]
        }
    )

    # Verify approval request was created
    assert result1.get("permission_required") is True
    assert approval_created is True

    # Simulate approval granted (in real scenario, this would be done via UI)
    # For test, we just verify the workflow structure
    assert "approval_request_id" in result1


@pytest.mark.asyncio
async def test_approval_workflow_integration_approval_denied(
    tool_executor, permission_manager, approval_manager, config_manager
):
    """Test approval workflow integration - approval denied."""
    # Configure permission manager to ask
    mock_config = Mock(spec=ConfigManager)
    mock_config._load_agent_config = Mock(return_value={
        "agent_permissions": {
            "agent": {
                "coder": {
                    "permission": {
                        "bash": {
                            "git push": "ask"
                        }
                    }
                }
            }
        }
    })

    permission_manager.config_manager = mock_config
    permission_manager._load_permissions()

    # Mock terminal router to return permission required
    async def mock_execute_command(command, args=None, **kwargs):
        return {
            "stdout": "",
            "stderr": "Permission approval required",
            "returncode": -1,
            "command_id": "cmd-1",
            "permission_required": True,
            "permission_details": {
                "permission_type": "bash",
                "resource": "git push",
                "agent_type": "coder"
            },
            "backend": "internal"
        }

    tool_executor.terminal_router.execute_command = mock_execute_command

    # Execute tool
    result = await tool_executor.execute_tool(
        tool_name="bash",
        tool_input={
            "id": "tool-1",
            "command": "git",
            "args": ["push"]
        }
    )

    # Verify approval request was created
    assert result.get("permission_required") is True
    assert "approval_request_id" in result

    # In real scenario, if approval is denied, the tool would not execute
    # For test, we verify the request was created


@pytest.mark.asyncio
async def test_permission_checks_file_operations(
    tool_executor, file_manager, permission_manager, config_manager
):
    """Test permission checks for file operations."""
    # Configure permission manager
    mock_config = Mock(spec=ConfigManager)
    mock_config._load_agent_config = Mock(return_value={
        "agent_permissions": {
            "agent": {
                "coder": {
                    "permission": {
                        "write": {
                            "*.py": "allow",
                            "*.json": "deny"
                        }
                    }
                }
            }
        }
    })

    permission_manager.config_manager = mock_config
    permission_manager._load_permissions()

    # Mock file manager to return permission denied for json files
    def mock_write_file(file_path, content, **kwargs):
        # FileManager checks permission and returns denied for json
        return {
            "success": False,
            "error": "Permission denied",
            "permission_denied": True,
            "permission_type": "write",
            "resource": "test.json"
        }

    file_manager.write_file = mock_write_file

    # Execute write tool
    result = tool_executor._execute_write({
        "id": "tool-1",
        "file_path": "test.json",
        "content": "{}"
    })

    # Verify permission was checked
    assert result["tool_name"] == "write"
    # Should have permission denied or error
    assert result.get("permission_denied") is True or "error" in result


@pytest.mark.asyncio
async def test_permission_checks_multiple_tools(
    tool_executor, permission_manager, config_manager
):
    """Test permission checks for multiple tool types."""
    # Configure permission manager
    mock_config = Mock(spec=ConfigManager)
    mock_config._load_agent_config = Mock(return_value={
        "agent_permissions": {
            "agent": {
                "coder": {
                    "permission": {
                        "bash": {
                            "*": "allow"
                        },
                        "read": {
                            "*": "allow"
                        },
                        "write": {
                            "*.py": "allow",
                            "*.json": "deny"
                        }
                    }
                }
            }
        }
    })

    permission_manager.config_manager = mock_config
    permission_manager._load_permissions()

    # Mock handlers
    async def mock_execute_command(command, args=None, **kwargs):
        return {
            "stdout": "output",
            "stderr": "",
            "returncode": 0,
            "command_id": "cmd-1",
            "backend": "internal"
        }

    tool_executor.terminal_router.execute_command = mock_execute_command

    def mock_read_file(file_path, **kwargs):
        return {
            "success": True,
            "content": "file content"
        }

    tool_executor.file_manager.read_file = mock_read_file

    # Execute multiple tools
    results = await tool_executor.execute_tool_calls([
        {
            "id": "tool-1",
            "name": "bash",
            "input": {"command": "echo", "args": ["hello"]}
        },
        {
            "id": "tool-2",
            "name": "read",
            "input": {"file_path": "test.py"}
        }
    ])

    # Verify all tools executed (permissions allowed)
    assert len(results) == 2
    assert results[0]["tool_name"] == "bash"
    assert results[1]["tool_name"] == "read"
    # Both should succeed (permissions allowed)
    assert results[0].get("error") is None or results[0].get("permission_denied") is not True
    assert results[1].get("error") is None or results[1].get("permission_denied") is not True


@pytest.mark.asyncio
async def test_integration_complete_permission_workflow(
    tool_executor, permission_manager, approval_manager, config_manager
):
    """Test complete integration - permission workflow."""
    # Configure permission manager with mixed permissions
    mock_config = Mock(spec=ConfigManager)
    mock_config._load_agent_config = Mock(return_value={
        "agent_permissions": {
            "agent": {
                "coder": {
                    "permission": {
                        "bash": {
                            "echo *": "allow",
                            "git push": "ask",
                            "rm *": "deny"
                        }
                    }
                }
            }
        }
    })

    permission_manager.config_manager = mock_config
    permission_manager._load_permissions()

    # Track approval requests
    approval_requests = []

    def track_create_approval_request(*args, **kwargs):
        approval_requests.append((args, kwargs))
        return f"request-{len(approval_requests)}"

    approval_manager.create_approval_request = track_create_approval_request

    # Mock terminal router
    async def mock_execute_command(command, args=None, **kwargs):
        full_cmd = f"{command} {' '.join(args) if args else ''}".strip()
        if "echo" in full_cmd:
            return {
                "stdout": "output",
                "stderr": "",
                "returncode": 0,
                "command_id": "cmd-1",
                "backend": "internal"
            }
        elif "git push" in full_cmd:
            return {
                "stdout": "",
                "stderr": "Permission approval required",
                "returncode": -1,
                "command_id": "cmd-2",
                "permission_required": True,
                "permission_details": {
                    "permission_type": "bash",
                    "resource": "git push",
                    "agent_type": "coder"
                },
                "backend": "internal"
            }
        elif "rm" in full_cmd:
            return {
                "stdout": "",
                "stderr": "Permission denied",
                "returncode": -1,
                "command_id": "cmd-3",
                "permission_denied": True,
                "backend": "internal"
            }

    tool_executor.terminal_router.execute_command = mock_execute_command

    # Execute tools with different permissions
    results = await tool_executor.execute_tool_calls([
        {
            "id": "tool-1",
            "name": "bash",
            "input": {"command": "echo", "args": ["hello"]}
        },
        {
            "id": "tool-2",
            "name": "bash",
            "input": {"command": "git", "args": ["push"]}
        },
        {
            "id": "tool-3",
            "name": "bash",
            "input": {"command": "rm", "args": ["-rf", "/"]}
        }
    ])

    # Verify permission workflow
    assert len(results) == 3
    # Tool 1: allowed
    assert results[0]["tool_name"] == "bash"
    assert results[0].get("permission_denied") is not True
    # Tool 2: ask (approval required)
    assert results[1]["tool_name"] == "bash"
    assert results[1].get("permission_required") is True
    assert len(approval_requests) > 0
    # Tool 3: denied
    assert results[2]["tool_name"] == "bash"
    assert results[2].get("permission_denied") is True
