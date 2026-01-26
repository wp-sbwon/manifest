"""
Unit tests for PermissionApprovalManager.

Tests permission approval workflow and pending requests.
"""
import pytest
from unittest.mock import Mock, AsyncMock
from manifest.runtime.permissions.permission_approval_manager import PermissionApprovalManager


@pytest.fixture
def approval_manager():
    """Create a PermissionApprovalManager instance."""
    return PermissionApprovalManager()


def test_approval_manager_initialization(approval_manager):
    """Test PermissionApprovalManager initialization."""
    assert approval_manager is not None
    assert hasattr(approval_manager, 'pending_requests')
    assert hasattr(approval_manager, 'approval_callbacks')


def test_create_approval_request(approval_manager):
    """Test creating a permission request."""
    request_id = approval_manager.create_approval_request(
        permission_type="write",
        resource="test.py",
        agent_type="coder",
        tool_name="write_file",
        tool_input={"path": "test.py", "content": "test"}
    )

    assert request_id is not None
    assert request_id in approval_manager.pending_requests


def test_get_pending_requests(approval_manager):
    """Test getting pending requests."""
    # Create a request
    request_id = approval_manager.create_approval_request(
        permission_type="write",
        resource="test.py",
        agent_type="coder",
        tool_name="write_file",
        tool_input={"path": "test.py"}
    )

    requests = approval_manager.get_pending_requests()
    assert isinstance(requests, list)
    assert len(requests) == 1
    assert requests[0]["id"] == request_id


@pytest.mark.asyncio
async def test_approve_request(approval_manager):
    """Test approving a request."""
    request_id = approval_manager.create_approval_request(
        permission_type="write",
        resource="test.py",
        agent_type="coder",
        tool_name="write_file",
        tool_input={"path": "test.py"}
    )

    result = await approval_manager.approve_request(request_id)
    assert result is True
    assert approval_manager.pending_requests[request_id]["status"] == "approved"


@pytest.mark.asyncio
async def test_deny_request(approval_manager):
    """Test denying a request."""
    request_id = approval_manager.create_approval_request(
        permission_type="write",
        resource="test.py",
        agent_type="coder",
        tool_name="write_file",
        tool_input={"path": "test.py"}
    )

    result = await approval_manager.deny_request(request_id)
    assert result is True
    assert approval_manager.pending_requests[request_id]["status"] == "denied"


def test_get_request(approval_manager):
    """Test getting a specific request."""
    request_id = approval_manager.create_approval_request(
        permission_type="write",
        resource="test.py",
        agent_type="coder",
        tool_name="write_file",
        tool_input={"path": "test.py"}
    )

    request = approval_manager.get_request(request_id)
    assert request is not None
    assert request["id"] == request_id
    assert request["status"] == "pending"
