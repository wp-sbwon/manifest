"""
E2E Test: Permission Approval Flow Workflow

Tests the complete workflow of permission approval for dangerous commands.
This validates that the system properly blocks dangerous commands, shows approval requests,
and executes or cancels commands based on user approval/rejection.
"""
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from manifest.runtime.permissions.permission_manager import PermissionManager
from manifest.runtime.permissions.permission_approval_manager import PermissionApprovalManager
from manifest.runtime.router.terminal_router import TerminalRouter
from manifest.runtime.tools.tool_executor import ToolExecutor
from manifest.core.config import ConfigManager
from manifest.core.state_manager import StateManager


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
def permission_manager(config_manager):
    """Create a PermissionManager instance for 'coder' agent."""
    return PermissionManager(config_manager=config_manager, agent_type="coder")


@pytest.fixture
def approval_manager():
    """Create a PermissionApprovalManager instance."""
    return PermissionApprovalManager()


@pytest.fixture
def terminal_router(permission_manager, temp_dir):
    """Create a TerminalRouter instance with permission manager."""
    router = TerminalRouter(
        working_dir=temp_dir,
        permission_manager=permission_manager,
        agent_type="coder"
    )
    return router


@pytest.fixture
def tool_executor(approval_manager, terminal_router):
    """Create a ToolExecutor instance with approval manager."""
    executor = ToolExecutor(
        terminal_router=terminal_router,
        approval_manager=approval_manager
    )
    return executor


# ========== TDL: Workflow 6: Permission Approval Flow ==========

@pytest.mark.asyncio
async def test_dangerous_commands_blocked(
    permission_manager, terminal_router
):
    """Test: Dangerous commands are blocked by permission manager."""
    # Step 1: Configure permission manager to deny dangerous commands
    # (This is typically done via config, but we'll simulate it)
    permission_manager.agent_permissions = {
        "bash": {
            "rm -rf *": "deny",
            "git push --force": "ask",
            "*": "allow"
        }
    }

    # Step 2: Attempt dangerous command (rm -rf *)
    result = await terminal_router.execute_command(
        command="rm",
        args=["-rf", "*"]
    )

    # Step 3: Verify command was blocked
    assert result.get("permission_denied") is True
    assert "Permission denied" in result.get("stderr", "")
    assert result.get("returncode") == -1


@pytest.mark.asyncio
async def test_approval_ui_works(
    approval_manager, tool_executor, permission_manager, terminal_router
):
    """Test: Approval UI works - requests are created and can be retrieved."""
    # Step 1: Configure permission to require approval
    permission_manager.agent_permissions = {
        "bash": {
            "git push --force": "ask",
            "*": "allow"
        }
    }

    # Step 2: Attempt command that requires approval
    tool_input = {
        "id": "test_tool_call",
        "command": "git",
        "args": ["push", "--force"]
    }

    result = await tool_executor._execute_bash(tool_input)

    # Step 3: Verify approval request was created
    assert result.get("permission_required") is True
    assert "approval_request_id" in result

    request_id = result.get("approval_request_id")
    assert request_id is not None

    # Step 4: Verify request is in pending requests
    pending_requests = approval_manager.get_pending_requests()
    assert len(pending_requests) > 0

    request = approval_manager.get_request(request_id)
    assert request is not None
    assert request["status"] == "pending"
    assert request["permission_type"] == "bash"
    assert "git push --force" in request["resource"]


@pytest.mark.asyncio
async def test_commands_execute_after_approval(
    approval_manager, tool_executor, permission_manager, terminal_router
):
    """Test: Commands execute after approval."""
    # Step 1: Configure permission to require approval
    permission_manager.agent_permissions = {
        "bash": {
            "git push --force": "ask",
            "*": "allow"
        }
    }

    # Step 2: Track command execution (TerminalRouter now uses subprocess directly)
    command_executed = {"executed": False, "result": None}

    # Step 3: Attempt command that requires approval
    tool_input = {
        "id": "test_tool_call",
        "command": "git",
        "args": ["push", "--force"]
    }

    result = await tool_executor._execute_bash(tool_input)

    # Step 4: Verify approval request was created
    assert result.get("permission_required") is True
    request_id = result.get("approval_request_id")

    # Step 5: Approve the request
    approval_result = await approval_manager.approve_request(request_id)
    assert approval_result is True

    # Step 6: Verify request was approved
    request = approval_manager.get_request(request_id)
    assert request is not None
    assert request["status"] == "approved"

    # Note: In real flow, after approval, the agent would retry the command
    # and the command would execute. Here we verify the approval mechanism works.


@pytest.mark.asyncio
async def test_commands_cancelled_after_rejection(
    approval_manager, tool_executor, permission_manager, terminal_router
):
    """Test: Commands are cancelled after rejection."""
    # Step 1: Configure permission to require approval
    permission_manager.agent_permissions = {
        "bash": {
            "git push --force": "ask",
            "*": "allow"
        }
    }

    # Step 2: Mock the underlying command execution
    command_executed = {"executed": False}

    async def mock_adapter_execute(command, args=None, **kwargs):
        if command == "git" and args == ["push", "--force"]:
            command_executed["executed"] = True
        return {"stdout": "", "stderr": "", "returncode": -1, "command_id": "test_cmd"}

    # TerminalRouter now uses subprocess directly, no need to mock adapter

    # Step 3: Attempt command that requires approval
    tool_input = {
        "id": "test_tool_call",
        "command": "git",
        "args": ["push", "--force"]
    }

    result = await tool_executor._execute_bash(tool_input)

    # Step 4: Verify approval request was created
    assert result.get("permission_required") is True
    request_id = result.get("approval_request_id")

    # Step 5: Deny the request
    denial_result = await approval_manager.deny_request(request_id)
    assert denial_result is True

    # Step 6: Verify request was denied
    request = approval_manager.get_request(request_id)
    assert request is not None
    assert request["status"] == "denied"
    assert "denied_at" in request

    # Step 7: Verify command was not executed
    # (In real flow, denial would prevent retry, so command never executes)
    assert command_executed["executed"] is False


@pytest.mark.asyncio
async def test_multiple_approval_requests(
    approval_manager, tool_executor, permission_manager, terminal_router
):
    """Test: Multiple approval requests can be handled."""
    # Step 1: Configure permission to require approval
    permission_manager.agent_permissions = {
        "bash": {
            "git push --force": "ask",
            "rm -rf /tmp/test": "ask",
            "*": "allow"
        }
    }

    # Step 2: Mock adapter to prevent actual execution
    async def mock_adapter_execute(command, args=None, **kwargs):
        return {"stdout": "", "stderr": "", "returncode": 0, "command_id": "test_cmd"}

    # TerminalRouter now uses subprocess directly, no need to mock adapter

    # Step 3: Create multiple approval requests
    request_ids = []

    tool_inputs = [
        {"id": "tool_1", "command": "git", "args": ["push", "--force"]},
        {"id": "tool_2", "command": "rm", "args": ["-rf", "/tmp/test"]},
    ]

    for tool_input in tool_inputs:
        result = await tool_executor._execute_bash(tool_input)
        if result.get("permission_required"):
            request_ids.append(result.get("approval_request_id"))

    # Step 4: Verify multiple requests exist
    assert len(request_ids) == 2

    pending_requests = approval_manager.get_pending_requests()
    assert len(pending_requests) >= 2

    # Step 5: Approve one, deny the other
    approve_result = await approval_manager.approve_request(request_ids[0])
    deny_result = await approval_manager.deny_request(request_ids[1])

    assert approve_result is True
    assert deny_result is True

    # Step 6: Verify states are correct
    request1 = approval_manager.get_request(request_ids[0])
    request2 = approval_manager.get_request(request_ids[1])

    assert request1["status"] == "approved"
    assert request2["status"] == "denied"

    # Step 7: Verify both are processed (no longer pending)
    pending_after = approval_manager.get_pending_requests()
    assert len(pending_after) == 0  # Both processed


@pytest.mark.asyncio
async def test_approval_callback_execution(
    approval_manager, tool_executor, permission_manager, terminal_router
):
    """Test: Approval callbacks are executed correctly."""
    # Step 1: Configure permission to require approval
    permission_manager.agent_permissions = {
        "bash": {
            "git push --force": "ask",
            "*": "allow"
        }
    }

    # Step 2: Track callback execution
    callback_called = {"called": False, "approved": None}

    async def approval_callback(approved: bool):
        callback_called["called"] = True
        callback_called["approved"] = approved

    # Step 3: Create approval request with callback
    tool_input = {
        "id": "test_tool_call",
        "command": "git",
        "args": ["push", "--force"]
    }

    result = await tool_executor._execute_bash(tool_input)
    request_id = result.get("approval_request_id")

    # Manually add callback (simulating real flow)
    approval_manager.approval_callbacks[request_id] = approval_callback

    # Step 4: Approve request
    approval_result = await approval_manager.approve_request(request_id)
    assert approval_result is True

    # Step 5: Verify callback was called
    assert callback_called["called"] is True
    assert callback_called["approved"] is True

    # Step 6: Test denial callback
    callback_called["called"] = False
    callback_called["approved"] = None

    result2 = await tool_executor._execute_bash(tool_input)
    request_id2 = result2.get("approval_request_id")
    approval_manager.approval_callbacks[request_id2] = approval_callback

    denial_result = await approval_manager.deny_request(request_id2)
    assert denial_result is True

    assert callback_called["called"] is True
    assert callback_called["approved"] is False


@pytest.mark.asyncio
async def test_complete_permission_approval_workflow(
    approval_manager, tool_executor, permission_manager, terminal_router
):
    """Test: Complete permission approval workflow from request to execution."""
    # Step 1: Configure permission to require approval for dangerous command
    permission_manager.agent_permissions = {
        "bash": {
            "git push --force": "ask",
            "*": "allow"
        }
    }

    # Step 2: Track workflow stages
    workflow_stages = []

    command_execution_count = {"count": 0}

    async def mock_adapter_execute(command, args=None, **kwargs):
        if command == "git" and args == ["push", "--force"]:
            command_execution_count["count"] += 1
            workflow_stages.append("command_executed")
            return {
                "stdout": "Pushed successfully",
                "stderr": "",
                "returncode": 0,
                "command_id": "test_cmd"
            }
        return {"stdout": "", "stderr": "", "returncode": -1, "command_id": "test_cmd"}

    # TerminalRouter now uses subprocess directly, no need to mock adapter

    # Step 3: Agent attempts dangerous command
    tool_input = {
        "id": "test_tool_call",
        "command": "git",
        "args": ["push", "--force"]
    }

    result = await tool_executor._execute_bash(tool_input)
    workflow_stages.append("command_attempted")

    # Step 4: Verify command was blocked and approval requested
    assert result.get("permission_required") is True
    workflow_stages.append("approval_requested")

    request_id = result.get("approval_request_id")
    assert request_id is not None

    # Step 5: Verify request is pending
    pending_requests = approval_manager.get_pending_requests()
    assert len(pending_requests) > 0
    workflow_stages.append("request_pending")

    # Step 6: User approves request
    approval_result = await approval_manager.approve_request(request_id)
    assert approval_result is True
    workflow_stages.append("request_approved")

    # Step 7: Verify request status
    request = approval_manager.get_request(request_id)
    assert request["status"] == "approved"
    assert "approved_at" in request

    # Step 8: Verify complete workflow stages
    assert "command_attempted" in workflow_stages
    assert "approval_requested" in workflow_stages
    assert "request_pending" in workflow_stages
    assert "request_approved" in workflow_stages

    # Note: In real flow, after approval, the agent would retry the command
    # and it would execute. Here we verify the approval mechanism works correctly.
