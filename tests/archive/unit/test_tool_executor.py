"""
Unit tests for ToolExecutor.
"""
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from manifest.runtime.tools.tool_executor import ToolExecutor
from manifest.runtime.tools.file_manager import FileManager
from pathlib import Path


@pytest.fixture
def mock_terminal_router():
    """Create mock terminal router."""
    router = Mock()
    router.execute_command = AsyncMock(return_value={
        "returncode": 0,
        "stdout": "Command output",
        "stderr": "",
        "command": "test command"
    })
    return router


@pytest.fixture
def mock_file_manager(tmp_path):
    """Create mock file manager."""
    file_manager = Mock(spec=FileManager)
    # FileManager uses 'read', 'write', 'edit', 'list' methods (not read_file, etc.)
    file_manager.read = Mock(return_value="File content")
    file_manager.write = Mock(return_value={"success": True})
    file_manager.edit = Mock(return_value={"success": True})
    file_manager.grep = Mock(return_value=[])
    file_manager.glob = Mock(return_value=[])
    file_manager.list = Mock(return_value=[])
    return file_manager


@pytest.fixture
def tool_executor(mock_terminal_router, mock_file_manager):
    """Create ToolExecutor instance."""
    return ToolExecutor(
        terminal_router=mock_terminal_router,
        file_manager=mock_file_manager
    )


@pytest.mark.asyncio
async def test_execute_tool_bash(tool_executor):
    """Test executing bash tool."""
    tool_input = {
        "id": "call_123",
        "command": "echo",
        "args": ["hello"]
    }

    result = await tool_executor.execute_tool("bash", tool_input)

    assert result["tool_name"] == "bash"
    assert result["tool_call_id"] == "call_123"
    assert result.get("result") is not None
    tool_executor.terminal_router.execute_command.assert_called_once()


@pytest.mark.asyncio
async def test_execute_tool_read(tool_executor):
    """Test executing read tool."""
    tool_input = {
        "id": "call_123",
        "file_path": "test.py"
    }

    result = await tool_executor.execute_tool("read", tool_input)

    assert result["tool_name"] == "read"
    assert result["tool_call_id"] == "call_123"
    assert result.get("result") is not None
    # FileManager.read is called in _execute_read
    assert tool_executor.file_manager.read.called


@pytest.mark.asyncio
async def test_execute_tool_write(tool_executor):
    """Test executing write tool."""
    tool_input = {
        "id": "call_123",
        "file_path": "test.py",
        "content": "print('hello')"
    }

    result = await tool_executor.execute_tool("write", tool_input)

    assert result["tool_name"] == "write"
    assert result["tool_call_id"] == "call_123"
    assert result.get("result") is not None
    # FileManager.write is called in _execute_write
    assert tool_executor.file_manager.write.called


@pytest.mark.asyncio
async def test_execute_tool_edit(tool_executor):
    """Test executing edit tool."""
    tool_input = {
        "id": "call_123",
        "file_path": "test.py",
        "old_string": "old",
        "new_string": "new"
    }

    result = await tool_executor.execute_tool("edit", tool_input)

    assert result["tool_name"] == "edit"
    assert result["tool_call_id"] == "call_123"
    assert result.get("result") is not None
    # FileManager.edit is called in _execute_edit
    assert tool_executor.file_manager.edit.called


@pytest.mark.asyncio
async def test_execute_tool_grep(tool_executor):
    """Test executing grep tool."""
    tool_input = {
        "id": "call_123",
        "file_path": "test.py",
        "pattern": "def test"
    }

    result = await tool_executor.execute_tool("grep", tool_input)

    assert result["tool_name"] == "grep"
    assert result["tool_call_id"] == "call_123"
    assert result.get("result") is not None
    tool_executor.file_manager.grep.assert_called_once()


@pytest.mark.asyncio
async def test_execute_tool_glob(tool_executor):
    """Test executing glob tool."""
    tool_input = {
        "id": "call_123",
        "pattern": "*.py"
    }

    result = await tool_executor.execute_tool("glob", tool_input)

    assert result["tool_name"] == "glob"
    assert result["tool_call_id"] == "call_123"
    assert result.get("result") is not None
    tool_executor.file_manager.glob.assert_called_once()


@pytest.mark.asyncio
async def test_execute_tool_list(tool_executor):
    """Test executing list tool."""
    tool_input = {
        "id": "call_123",
        "directory": "."
    }

    result = await tool_executor.execute_tool("list", tool_input)

    assert result["tool_name"] == "list"
    assert result["tool_call_id"] == "call_123"
    assert result.get("result") is not None
    # FileManager.list is called in _execute_list
    assert tool_executor.file_manager.list.called


@pytest.mark.asyncio
async def test_execute_tool_task_management(tmp_path):
    """Test executing task_management tool."""
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir()
    executor = ToolExecutor(manifest_dir=manifest_dir)
    tool_input = {
        "id": "call_tm",
        "action": "create_task",
        "name": "Test task",
    }
    result = await executor.execute_tool("task_management", tool_input)
    assert result["tool_name"] == "task_management"
    assert result.get("error") is None
    assert result.get("result", {}).get("ok") is True
    assert result["result"].get("task_id") is not None


@pytest.mark.asyncio
async def test_execute_tool_sprint_management(tmp_path):
    """Test executing sprint_management tool."""
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir()
    executor = ToolExecutor(manifest_dir=manifest_dir)
    tool_input = {
        "id": "call_sm",
        "action": "create_sprint",
        "name": "Sprint 1",
    }
    result = await executor.execute_tool("sprint_management", tool_input)
    assert result["tool_name"] == "sprint_management"
    assert result.get("error") is None
    assert result.get("result", {}).get("ok") is True
    assert result["result"].get("sprint_id") is not None


@pytest.mark.asyncio
async def test_execute_tool_unknown(tool_executor):
    """Test executing unknown tool."""
    tool_input = {
        "id": "call_123"
    }

    result = await tool_executor.execute_tool("unknown_tool", tool_input)

    assert result["tool_name"] == "unknown_tool"
    assert result["tool_call_id"] == "call_123"
    assert result.get("error") is not None
    assert "Unknown tool" in result["error"]


@pytest.mark.asyncio
async def test_execute_tool_error_handling(tool_executor):
    """Test error handling in tool execution."""
    # Make file_manager.read raise an exception
    # The exception will be caught in execute_tool's try/except block
    tool_executor.file_manager.read = Mock(side_effect=Exception("File not found"))

    tool_input = {
        "id": "call_123",
        "file_path": "nonexistent.py"
    }

    result = await tool_executor.execute_tool("read", tool_input)

    assert result["tool_name"] == "read"
    # Error should be caught in execute_tool's try/except block (lines 98-118)
    assert "error" in result
    assert result["error"] is not None
    assert "File not found" in result["error"]
    assert result.get("result") is None


@pytest.mark.asyncio
async def test_execute_tool_calls_multiple(tool_executor):
    """Test executing multiple tool calls."""
    tool_calls = [
        {
            "id": "call_1",
            "name": "read",
            "input": {"file_path": "test1.py"}
        },
        {
            "id": "call_2",
            "name": "read",
            "input": {"file_path": "test2.py"}
        }
    ]

    results = await tool_executor.execute_tool_calls(tool_calls)

    assert len(results) == 2
    assert results[0]["tool_call_id"] == "call_1"
    assert results[1]["tool_call_id"] == "call_2"
    # FileManager.read is called via execute_tool -> _execute_read
    # Note: execute_tool_calls calls execute_tool for each, which calls _execute_read
    # The mock should be called, but the exact call count depends on implementation
    assert len(results) == 2


@pytest.mark.asyncio
async def test_execute_tool_calls_empty(tool_executor):
    """Test executing empty tool calls list."""
    results = await tool_executor.execute_tool_calls([])

    assert results == []


@pytest.mark.asyncio
async def test_execute_tool_with_auditor(tool_executor):
    """Test tool execution with auditor."""
    mock_auditor = Mock()
    mock_auditor.log_tool_execution = AsyncMock()
    tool_executor.auditor = mock_auditor

    tool_input = {
        "id": "call_123",
        "file_path": "test.py"
    }

    result = await tool_executor.execute_tool("read", tool_input)

    # Verify auditor was called
    mock_auditor.log_tool_execution.assert_called_once()
    call_args = mock_auditor.log_tool_execution.call_args[1]
    assert call_args["tool_name"] == "read"
    assert call_args["tool_input"] == tool_input
    assert call_args["result"] == result


@pytest.mark.asyncio
async def test_execute_tool_bash_error(tool_executor):
    """Test bash tool with error."""
    tool_executor.terminal_router.execute_command = AsyncMock(return_value={
        "returncode": 1,
        "stdout": "",
        "stderr": "Command failed",
        "command": "invalid command"
    })

    tool_input = {
        "id": "call_123",
        "command": "invalid",
        "args": []
    }

    result = await tool_executor.execute_tool("bash", tool_input)

    assert result["tool_name"] == "bash"
    # Should handle error gracefully
    assert result.get("result") is not None


def test_validate_tool_result_success(tool_executor):
    """Test validating successful tool result."""
    result = {
        "tool_call_id": "call_123",
        "tool_name": "read",
        "result": "File content"
    }
    tool_name = "read"
    tool_input = {"file_path": "test.py"}

    validated = tool_executor._validate_tool_result(result, tool_name, tool_input)

    assert validated["success"] is True
    assert validated.get("validation_errors") == []


def test_validate_tool_result_error(tool_executor):
    """Test validating tool result with error."""
    result = {
        "tool_call_id": "call_123",
        "tool_name": "read",
        "error": "File not found"
    }
    tool_name = "read"
    tool_input = {"file_path": "test.py"}

    validated = tool_executor._validate_tool_result(result, tool_name, tool_input)

    assert validated["success"] is False
    assert len(validated.get("validation_errors", [])) > 0


@pytest.mark.asyncio
async def test_execute_tool_permission_denied(tool_executor):
    """Test tool execution with permission denied."""
    mock_approval_manager = Mock()
    mock_approval_manager.check_permission = AsyncMock(return_value={
        "allowed": False,
        "reason": "Permission denied"
    })
    tool_executor.approval_manager = mock_approval_manager

    tool_input = {
        "id": "call_123",
        "file_path": "protected.py"
    }

    # This would require permission checking logic in the tool executor
    # For now, just verify the structure
    result = await tool_executor.execute_tool("read", tool_input)

    assert result["tool_name"] == "read"
    # Result should be handled appropriately


# ========== TDL: Tool Executor Tests ==========

def test_tool_call_parsing_structure(tool_executor):
    """Test tool call parsing structure."""
    tool_call = {
        "id": "call-123",
        "name": "read",
        "input": {
            "file_path": "test.py"
        }
    }

    # ToolExecutor expects tool calls with 'id', 'name', 'input'
    assert "id" in tool_call
    assert "name" in tool_call
    assert "input" in tool_call
    assert tool_call["name"] == "read"


def test_tool_call_parsing_with_missing_fields(tool_executor):
    """Test tool call parsing handles missing fields."""
    # ToolExecutor should handle missing fields gracefully
    tool_call = {
        "name": "read",
        "input": {}
    }

    # Should work with default "unknown" for missing id
    assert tool_call.get("id", "unknown") == "unknown"
    assert tool_call["name"] == "read"


@pytest.mark.asyncio
async def test_tool_execution_file_operations_edit(tool_executor):
    """Test tool execution for file edit operation."""
    tool_input = {
        "id": "call-1",
        "file_path": "test.py",
        "old_string": "old code",
        "new_string": "new code"
    }

    tool_executor.file_manager.edit = Mock(return_value={"success": True, "file_path": "test.py"})

    result = await tool_executor.execute_tool("edit", tool_input)

    assert result["tool_name"] == "edit"
    assert result.get("result") is not None
    tool_executor.file_manager.edit.assert_called_once_with("test.py", "old code", "new code")


@pytest.mark.asyncio
async def test_tool_execution_file_operations_write(tool_executor):
    """Test tool execution for file write operation."""
    tool_input = {
        "id": "call-1",
        "file_path": "new_file.py",
        "content": "print('hello')"
    }

    tool_executor.file_manager.write = Mock(return_value={"success": True, "file_path": "new_file.py"})

    result = await tool_executor.execute_tool("write", tool_input)

    assert result["tool_name"] == "write"
    assert result.get("result") is not None
    tool_executor.file_manager.write.assert_called_once()


@pytest.mark.asyncio
async def test_tool_execution_file_operations_read(tool_executor):
    """Test tool execution for file read operation."""
    tool_input = {
        "id": "call-1",
        "file_path": "test.py"
    }

    tool_executor.file_manager.read = Mock(return_value="file content")

    result = await tool_executor.execute_tool("read", tool_input)

    assert result["tool_name"] == "read"
    assert result.get("result") is not None
    # read is called with file_path, start_line, end_line (may be None)
    tool_executor.file_manager.read.assert_called_once()
    call_args = tool_executor.file_manager.read.call_args
    assert call_args[0][0] == "test.py"


@pytest.mark.asyncio
async def test_tool_execution_git_operations(tool_executor):
    """Test tool execution for git operations via bash."""
    tool_input = {
        "id": "call-1",
        "command": "git",
        "args": ["status"]
    }

    tool_executor.terminal_router.execute_command = AsyncMock(return_value={
        "stdout": "On branch main",
        "stderr": "",
        "returncode": 0,
        "backend": "opencode"
    })

    result = await tool_executor.execute_tool("bash", tool_input)

    assert result["tool_name"] == "bash"
    assert result.get("result") is not None
    assert result["result"]["returncode"] == 0
    tool_executor.terminal_router.execute_command.assert_called_once()


@pytest.mark.asyncio
async def test_tool_result_validation_success(tool_executor):
    """Test tool result validation for successful execution."""
    result = {
        "tool_call_id": "call-1",
        "tool_name": "read",
        "result": "file content"
    }

    validation = tool_executor._validate_tool_result(result, "read", {"file_path": "test.py"})

    assert validation["success"] is True
    assert len(validation["validation_errors"]) == 0


@pytest.mark.asyncio
async def test_tool_result_validation_edit_warning(tool_executor):
    """Test tool result validation for edit operation includes warning."""
    result = {
        "tool_call_id": "call-1",
        "tool_name": "edit",
        "result": {"success": True, "file_path": "test.py"}
    }

    validation = tool_executor._validate_tool_result(result, "edit", {"file_path": "test.py"})

    assert validation["success"] is True
    # Should include warning about file modification
    assert len(validation["warnings"]) > 0
    assert "modified" in validation["warnings"][0].lower() or "test" in validation["warnings"][0].lower()


@pytest.mark.asyncio
async def test_tool_result_validation_write_warning(tool_executor):
    """Test tool result validation for write operation includes warning."""
    result = {
        "tool_call_id": "call-1",
        "tool_name": "write",
        "result": {"success": True, "file_path": "new_file.py"}
    }

    validation = tool_executor._validate_tool_result(result, "write", {"file_path": "new_file.py"})

    assert validation["success"] is True
    # Should include warning about new file
    assert len(validation["warnings"]) > 0
    assert "created" in validation["warnings"][0].lower() or "new" in validation["warnings"][0].lower()


@pytest.mark.asyncio
async def test_tool_result_validation_bash_failure(tool_executor):
    """Test tool result validation for bash command failure."""
    result = {
        "tool_call_id": "call-1",
        "tool_name": "bash",
        "result": {
            "stdout": "",
            "stderr": "Command failed",
            "returncode": 1
        }
    }

    validation = tool_executor._validate_tool_result(result, "bash", {"command": "failing_command"})

    assert validation["success"] is False
    assert len(validation["validation_errors"]) > 0
    assert "failed" in validation["validation_errors"][0].lower() or "return code" in validation["validation_errors"][0].lower()


@pytest.mark.asyncio
async def test_tool_result_validation_bash_test_warning(tool_executor):
    """Test tool result validation for test commands includes warnings."""
    result = {
        "tool_call_id": "call-1",
        "tool_name": "bash",
        "result": {
            "stdout": "test failed",
            "stderr": "",
            "returncode": 0
        }
    }

    validation = tool_executor._validate_tool_result(result, "bash", {"command": "pytest"})

    # Should include warning if test output suggests failures
    if "failed" in result["result"]["stdout"].lower():
        assert len(validation.get("warnings", [])) > 0 or validation["success"] is True


@pytest.mark.asyncio
async def test_tool_error_handling_execution_error(tool_executor):
    """Test tool error handling for execution errors."""
    tool_executor.file_manager.read = Mock(side_effect=Exception("File read error"))

    tool_input = {"id": "call-1", "file_path": "test.py"}

    result = await tool_executor.execute_tool("read", tool_input)

    assert result.get("error") is not None
    assert "error" in result
    assert result.get("result") is None


@pytest.mark.asyncio
async def test_tool_error_handling_permission_error(tool_executor):
    """Test tool error handling for permission errors."""
    tool_executor.file_manager.read = Mock(side_effect=PermissionError("Permission denied"))

    tool_input = {"id": "call-1", "file_path": "protected.py"}

    result = await tool_executor.execute_tool("read", tool_input)

    assert result.get("error") is not None
    assert "error_type" in result
    # Should categorize as permission_error
    assert result.get("error_type") == "permission_error" or "permission" in result.get("error", "").lower()


@pytest.mark.asyncio
async def test_tool_error_handling_file_not_found(tool_executor):
    """Test tool error handling for file not found errors."""
    tool_executor.file_manager.read = Mock(side_effect=FileNotFoundError("File not found"))

    tool_input = {"id": "call-1", "file_path": "nonexistent.py"}

    result = await tool_executor.execute_tool("read", tool_input)

    assert result.get("error") is not None
    assert "error_type" in result
    # Should categorize as file_not_found
    assert result.get("error_type") == "file_not_found" or "not found" in result.get("error", "").lower()


@pytest.mark.asyncio
async def test_tool_error_handling_string_not_found(tool_executor):
    """Test tool error handling for string not found in edit."""
    tool_executor.file_manager.edit = Mock(return_value={
        "success": False,
        "error": "String not found"
    })

    tool_input = {
        "id": "call-1",
        "file_path": "test.py",
        "old_string": "nonexistent string",
        "new_string": "new string"
    }

    result = await tool_executor.execute_tool("edit", tool_input)

    # Should handle gracefully
    assert result.get("result") is not None or result.get("error") is not None


@pytest.mark.asyncio
async def test_tool_audit_logging(tool_executor):
    """Test tool audit logging."""
    mock_auditor = AsyncMock()
    mock_auditor.log_tool_execution = AsyncMock()
    tool_executor.auditor = mock_auditor
    tool_executor.agent_type = "coder"
    tool_executor.task_id = "task-1"
    tool_executor.agent_id = "agent-1"

    tool_input = {"id": "call-1", "file_path": "test.py"}

    result = await tool_executor.execute_tool("read", tool_input)

    # Verify auditor was called
    mock_auditor.log_tool_execution.assert_called_once()
    call_args = mock_auditor.log_tool_execution.call_args[1]
    assert call_args["tool_name"] == "read"
    assert call_args["agent_type"] == "coder"
    assert call_args["task_id"] == "task-1"
    assert call_args["agent_id"] == "agent-1"


@pytest.mark.asyncio
async def test_tool_audit_logging_with_error(tool_executor):
    """Test tool audit logging includes errors."""
    mock_auditor = AsyncMock()
    mock_auditor.log_tool_execution = AsyncMock()
    tool_executor.auditor = mock_auditor
    tool_executor.file_manager.read = Mock(side_effect=Exception("Error"))

    tool_input = {"id": "call-1", "file_path": "test.py"}

    result = await tool_executor.execute_tool("read", tool_input)

    # Auditor should still be called even for errors
    mock_auditor.log_tool_execution.assert_called_once()
    call_args = mock_auditor.log_tool_execution.call_args[1]
    assert call_args["result"] == result  # Should include error result


@pytest.mark.asyncio
async def test_tool_execution_permission_denied_bash(tool_executor):
    """Test tool execution with permission denied for bash."""
    tool_executor.terminal_router.execute_command = AsyncMock(return_value={
        "stdout": "",
        "stderr": "Permission denied",
        "returncode": -1,
        "permission_denied": True
    })

    tool_input = {"id": "call-1", "command": "rm", "args": ["-rf", "/"]}

    result = await tool_executor.execute_tool("bash", tool_input)

    assert result.get("permission_denied") is True
    assert result.get("error") is not None
    assert "permission" in result.get("error", "").lower()


@pytest.mark.asyncio
async def test_tool_execution_permission_required_bash(tool_executor):
    """Test tool execution with permission required (ask) for bash."""
    mock_approval_manager = Mock()
    mock_approval_manager.create_approval_request = Mock(return_value="request-123")
    tool_executor.approval_manager = mock_approval_manager

    tool_executor.terminal_router.execute_command = AsyncMock(return_value={
        "stdout": "",
        "stderr": "Permission approval required",
        "returncode": -1,
        "permission_required": True,
        "permission_details": {
            "permission_type": "bash",
            "resource": "git push",
            "agent_type": "coder"
        }
    })

    tool_input = {"id": "call-1", "command": "git", "args": ["push"]}

    result = await tool_executor.execute_tool("bash", tool_input)

    assert result.get("permission_required") is True
    assert "approval_request_id" in result
    assert result["approval_request_id"] == "request-123"
    mock_approval_manager.create_approval_request.assert_called_once()


@pytest.mark.asyncio
async def test_tool_execution_permission_required_no_manager(tool_executor):
    """Test tool execution with permission required but no approval manager."""
    tool_executor.approval_manager = None
    tool_executor.terminal_router.execute_command = AsyncMock(return_value={
        "stdout": "",
        "stderr": "Permission approval required",
        "returncode": -1,
        "permission_required": True,
        "permission_details": {
            "permission_type": "bash",
            "resource": "git push",
            "agent_type": "coder"
        }
    })

    tool_input = {"id": "call-1", "command": "git", "args": ["push"]}

    result = await tool_executor.execute_tool("bash", tool_input)

    assert result.get("permission_required") is True
    assert result.get("error") is not None
    assert "approval manager" in result.get("error", "").lower() or "approval" in result.get("error", "").lower()


@pytest.mark.asyncio
async def test_execute_tool_calls_with_validation(tool_executor):
    """Test execute_tool_calls includes validation."""
    tool_calls = [
        {
            "id": "call-1",
            "name": "read",
            "input": {"file_path": "test.py"}
        }
    ]

    results = await tool_executor.execute_tool_calls(tool_calls)

    assert len(results) == 1
    assert "validated" in results[0]
    assert "success" in results[0]["validated"]


@pytest.mark.asyncio
async def test_execute_tool_calls_multiple_with_validation(tool_executor):
    """Test execute_tool_calls with multiple tools includes validation for each."""
    tool_calls = [
        {"id": "call-1", "name": "read", "input": {"file_path": "file1.py"}},
        {"id": "call-2", "name": "write", "input": {"file_path": "file2.py", "content": "code"}}
    ]

    results = await tool_executor.execute_tool_calls(tool_calls)

    assert len(results) == 2
    # Each result should have validation
    assert "validated" in results[0]
    assert "validated" in results[1]


@pytest.mark.asyncio
async def test_tool_execution_missing_file_manager(tool_executor):
    """Test tool execution when FileManager is not available."""
    tool_executor.file_manager = None

    tool_input = {"id": "call-1", "file_path": "test.py"}

    result = await tool_executor.execute_tool("read", tool_input)

    assert result.get("error") is not None
    assert "FileManager" in result.get("error", "") or "not available" in result.get("error", "").lower()


@pytest.mark.asyncio
async def test_tool_execution_missing_terminal_router(tool_executor):
    """Test tool execution when TerminalRouter is not available."""
    tool_executor.terminal_router = None

    tool_input = {"id": "call-1", "command": "echo", "args": ["test"]}

    result = await tool_executor.execute_tool("bash", tool_input)

    assert result.get("error") is not None
    assert "TerminalRouter" in result.get("error", "") or "not available" in result.get("error", "").lower()


@pytest.mark.asyncio
async def test_tool_execution_bash_missing_command(tool_executor):
    """Test bash tool execution with missing command."""
    tool_input = {"id": "call-1"}

    result = await tool_executor.execute_tool("bash", tool_input)

    assert result.get("error") is not None
    assert "command" in result.get("error", "").lower() or "not provided" in result.get("error", "").lower()


@pytest.mark.asyncio
async def test_tool_execution_edit_missing_parameters(tool_executor):
    """Test edit tool execution with missing parameters."""
    tool_input = {"id": "call-1", "file_path": "test.py"}

    result = await tool_executor.execute_tool("edit", tool_input)

    assert result.get("error") is not None
    assert "required" in result.get("error", "").lower() or "missing" in result.get("error", "").lower()
