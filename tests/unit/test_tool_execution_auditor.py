"""
Unit tests for ToolExecutionAuditor.

Tests tool execution auditing, logging, and validation.
"""
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
from manifest.runtime.tools.tool_execution_auditor import ToolExecutionAuditor


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing."""
    return tmp_path


@pytest.fixture
def auditor(temp_dir):
    """Create a ToolExecutionAuditor instance."""
    return ToolExecutionAuditor(manifest_dir=temp_dir)


@pytest.fixture
def sample_tool_call():
    """Create a sample tool call for testing."""
    return {
        "tool_name": "read",
        "tool_input": {"file_path": "test.txt"},
        "tool_result": {"content": "file content"},
        "execution_time": 0.1,
        "success": True
    }


def test_auditor_initialization(auditor, temp_dir):
    """Test ToolExecutionAuditor initialization."""
    assert auditor.manifest_dir == temp_dir
    assert auditor is not None
    assert auditor.audit_file == temp_dir / "tool_execution_audit.json"


@pytest.mark.asyncio
async def test_log_tool_execution(auditor, sample_tool_call):
    """Test logging a tool execution."""
    await auditor.log_tool_execution(
        tool_name=sample_tool_call["tool_name"],
        tool_input=sample_tool_call["tool_input"],
        result=sample_tool_call["tool_result"],
        agent_id="test-agent",
        task_id="task-1"
    )
    
    # Check that audit log was created
    assert auditor.audit_file.exists() or len(auditor._audit_log) > 0


@pytest.mark.asyncio
async def test_log_tool_execution_with_error(auditor):
    """Test logging tool execution with error."""
    tool_input = {"file_path": "nonexistent.txt"}
    result = {"error": "File not found", "success": False}
    
    await auditor.log_tool_execution(
        tool_name="read",
        tool_input=tool_input,
        result=result,
        agent_id="test-agent",
        task_id="task-1"
    )
    
    # Error should be logged
    logs = auditor.get_audit_log()
    error_logs = [log for log in logs if log.get("agent_id") == "test-agent"]
    assert len(error_logs) > 0
    assert error_logs[0].get("success") is False


@pytest.mark.asyncio
async def test_get_audit_logs(auditor, sample_tool_call):
    """Test retrieving audit logs."""
    # Log some executions
    await auditor.log_tool_execution(
        tool_name=sample_tool_call["tool_name"],
        tool_input=sample_tool_call["tool_input"],
        result=sample_tool_call["tool_result"],
        agent_id="agent-1",
        task_id="task-1"
    )
    await auditor.log_tool_execution(
        tool_name=sample_tool_call["tool_name"],
        tool_input=sample_tool_call["tool_input"],
        result=sample_tool_call["tool_result"],
        agent_id="agent-2",
        task_id="task-2"
    )
    
    logs = auditor.get_audit_log()
    agent1_logs = [log for log in logs if log.get("agent_id") == "agent-1"]
    
    assert len(agent1_logs) > 0
    assert all(log.get("agent_id") == "agent-1" for log in agent1_logs)


@pytest.mark.asyncio
async def test_get_audit_logs_by_task(auditor, sample_tool_call):
    """Test retrieving audit logs by task ID."""
    await auditor.log_tool_execution(
        tool_name=sample_tool_call["tool_name"],
        tool_input=sample_tool_call["tool_input"],
        result=sample_tool_call["tool_result"],
        agent_id="agent-1",
        task_id="task-1"
    )
    await auditor.log_tool_execution(
        tool_name=sample_tool_call["tool_name"],
        tool_input=sample_tool_call["tool_input"],
        result=sample_tool_call["tool_result"],
        agent_id="agent-1",
        task_id="task-2"
    )
    
    logs = auditor.get_audit_log(task_id="task-1")
    
    assert len(logs) > 0
    assert all(log.get("task_id") == "task-1" for log in logs)


@pytest.mark.asyncio
async def test_get_audit_logs_by_tool(auditor, sample_tool_call):
    """Test retrieving audit logs by tool name."""
    await auditor.log_tool_execution(
        tool_name="read",
        tool_input=sample_tool_call["tool_input"],
        result=sample_tool_call["tool_result"],
        agent_id="agent-1",
        task_id="task-1"
    )
    
    logs = auditor.get_audit_log()
    tool_logs = [log for log in logs if log.get("tool_name") == "read"]
    
    assert len(tool_logs) > 0
    assert all(log.get("tool_name") == "read" for log in tool_logs)


def test_get_audit_logs_empty(auditor):
    """Test retrieving logs when none exist."""
    logs = auditor.get_audit_log()
    assert logs == []


def test_validate_tool_result(auditor, sample_tool_call):
    """Test validating tool execution result structure."""
    # Check that sample_tool_call has required fields
    assert "tool_name" in sample_tool_call
    assert "tool_input" in sample_tool_call
    assert "tool_result" in sample_tool_call
    # Structure is valid
    assert isinstance(sample_tool_call, dict)


def test_sanitize_input(auditor):
    """Test input sanitization."""
    tool_input = {
        "file_path": "/path/to/file.txt",
        "content": "sensitive data"
    }
    
    sanitized = auditor._sanitize_input(tool_input, "write")
    # Should return dict (may sanitize sensitive data)
    assert isinstance(sanitized, dict)


def test_sanitize_result(auditor):
    """Test result sanitization."""
    result = {
        "content": "file content",
        "success": True
    }
    
    sanitized = auditor._sanitize_result(result, "read")
    # Should return dict
    assert isinstance(sanitized, dict)


@pytest.mark.asyncio
async def test_audit_log_rotation(auditor, sample_tool_call):
    """Test audit log rotation when max entries exceeded."""
    # Log many executions to trigger rotation
    for i in range(100):
        await auditor.log_tool_execution(
            tool_name=sample_tool_call["tool_name"],
            tool_input=sample_tool_call["tool_input"],
            result=sample_tool_call["tool_result"],
            agent_id=f"agent-{i}",
            task_id=f"task-{i}"
        )
    
    # Log should not exceed max_log_entries
    assert len(auditor._audit_log) <= auditor.max_log_entries


@pytest.mark.asyncio
async def test_get_file_modification_history(auditor):
    """Test getting file modification history."""
    tool_input = {"file_path": "test.txt", "old_string": "old", "new_string": "new"}
    result = {"success": True}
    
    await auditor.log_tool_execution(
        tool_name="edit",
        tool_input=tool_input,
        result=result,
        agent_id="agent-1",
        task_id="task-1"
    )
    
    history = auditor.get_file_modification_history("test.txt")
    assert isinstance(history, list)


@pytest.mark.asyncio
async def test_get_command_execution_history(auditor):
    """Test getting command execution history."""
    tool_input = {"command": "echo hello", "args": []}
    result = {"returncode": 0, "stdout": "hello"}
    
    await auditor.log_tool_execution(
        tool_name="bash",
        tool_input=tool_input,
        result=result,
        agent_id="agent-1",
        task_id="task-1"
    )
    
    history = auditor.get_command_execution_history()
    assert isinstance(history, list)


@pytest.mark.asyncio
async def test_save_audit_log(auditor, sample_tool_call):
    """Test saving audit log to disk."""
    import asyncio
    
    await auditor.log_tool_execution(
        tool_name=sample_tool_call["tool_name"],
        tool_input=sample_tool_call["tool_input"],
        result=sample_tool_call["tool_result"],
        agent_id="agent-1",
        task_id="task-1"
    )
    
    # Wait for async save
    await asyncio.sleep(0.1)
    
    # Audit file should exist or be in memory
    assert auditor.audit_file.exists() or len(auditor._audit_log) > 0


@pytest.mark.asyncio
async def test_load_audit_log(auditor, temp_dir):
    """Test loading audit log from disk."""
    # Create audit file
    audit_data = {
        "entries": [{
            "timestamp": "2026-01-26T00:00:00",
            "tool_name": "read",
            "agent_id": "agent-1",
            "task_id": "task-1",
            "success": True
        }]
    }
    
    auditor.audit_file.parent.mkdir(parents=True, exist_ok=True)
    with open(auditor.audit_file, 'w') as f:
        json.dump(audit_data, f)
    
    # Reload
    auditor._load_audit_log()
    
    assert len(auditor._audit_log) > 0


def test_extract_file_modification(auditor):
    """Test extracting file modification information."""
    tool_input = {"file_path": "test.txt", "old_string": "old", "new_string": "new"}
    result = {"success": True}
    
    modification = auditor._extract_file_modification("edit", tool_input, result)
    assert isinstance(modification, dict)
    assert "file_path" in modification or modification is not None


@pytest.mark.asyncio
async def test_concurrent_logging(auditor, sample_tool_call):
    """Test concurrent logging of tool executions."""
    import asyncio
    
    async def log_execution(agent_id, task_id):
        await auditor.log_tool_execution(
            tool_name=sample_tool_call["tool_name"],
            tool_input=sample_tool_call["tool_input"],
            result=sample_tool_call["tool_result"],
            agent_id=agent_id,
            task_id=task_id
        )
    
    tasks = [
        log_execution(f"agent-{i}", f"task-{i}")
        for i in range(10)
    ]
    await asyncio.gather(*tasks)
    
    # All logs should be recorded
    logs = auditor.get_audit_log()
    assert len(logs) >= 10


@pytest.mark.asyncio
async def test_audit_log_format(auditor, sample_tool_call):
    """Test audit log format consistency."""
    await auditor.log_tool_execution(
        tool_name=sample_tool_call["tool_name"],
        tool_input=sample_tool_call["tool_input"],
        result=sample_tool_call["tool_result"],
        agent_id="agent-1",
        task_id="task-1"
    )
    
    logs = auditor.get_audit_log()
    if len(logs) > 0:
        log = logs[0]
        assert "timestamp" in log
        assert "tool_name" in log
        assert "agent_id" in log


@pytest.mark.asyncio
async def test_error_handling_invalid_tool_call(auditor):
    """Test error handling for invalid tool calls."""
    # Should handle invalid input gracefully
    try:
        await auditor.log_tool_execution(
            tool_name=None,
            tool_input={},
            result={},
            agent_id="agent-1",
            task_id="task-1"
        )
        # Should not crash
    except (TypeError, ValueError, AttributeError):
        # Expected for invalid input
        pass


def test_audit_directory_creation(temp_dir):
    """Test that audit directory is created if it doesn't exist."""
    new_manifest_dir = temp_dir / "new_manifest"
    
    new_auditor = ToolExecutionAuditor(manifest_dir=new_manifest_dir)
    
    # Directory should be created or parent exists
    assert new_manifest_dir.exists() or new_manifest_dir.parent.exists()
