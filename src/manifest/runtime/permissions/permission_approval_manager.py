"""
Permission Approval Manager for handling "ask" permission requests.

This module provides a centralized manager for permission approval requests.
When a tool execution requires user approval (permission="ask"), the request
is queued and can be approved or denied by the user through the UI.
"""
import asyncio
from typing import Dict, Any, Optional, Callable, Awaitable, List
from datetime import datetime
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class PermissionApprovalManager:
    """Manages permission approval requests for "ask" permissions.

    When a tool execution requires approval, the request is queued here
    and can be approved or denied by the user through the UI. The manager
    tracks pending requests and provides callbacks for approval/denial.

    Attributes:
        pending_requests: Dictionary mapping request_id to request details.
        approval_callbacks: Dictionary mapping request_id to approval callbacks.
    """

    def __init__(self):
        """Initialize the permission approval manager."""
        self.pending_requests: Dict[str, Dict[str, Any]] = {}
        self.approval_callbacks: Dict[str, Callable[[bool], Awaitable[None]]] = {}
        self._request_counter = 0
        self._lock = asyncio.Lock()

    def create_approval_request(
        self,
        permission_type: str,
        resource: str,
        agent_type: str,
        tool_name: str,
        tool_input: Dict[str, Any],
        approval_callback: Optional[Callable[[bool], Awaitable[None]]] = None
    ) -> str:
        """Create a new permission approval request.

        Args:
            permission_type: Type of permission (edit, write, bash, etc.).
            resource: Resource being accessed (file path, command, etc.).
            agent_type: Type of agent requesting permission.
            tool_name: Name of the tool being executed.
            tool_input: Input parameters for the tool.
            approval_callback: Optional callback to call when approved/denied.

        Returns:
            Request ID for tracking this approval request.
        """
        request_id = f"perm_req_{self._request_counter}_{datetime.now().timestamp()}"
        self._request_counter += 1

        request = {
            "id": request_id,
            "permission_type": permission_type,
            "resource": resource,
            "agent_type": agent_type,
            "tool_name": tool_name,
            "tool_input": tool_input,
            "created_at": datetime.now().isoformat(),
            "status": "pending"
        }

        self.pending_requests[request_id] = request

        if approval_callback:
            self.approval_callbacks[request_id] = approval_callback

        logger.info(
            f"Created permission approval request {request_id}: "
            f"{agent_type} wants to {permission_type} {resource}"
        )

        return request_id

    async def approve_request(self, request_id: str) -> bool:
        """Approve a pending permission request.

        Args:
            request_id: ID of the request to approve.

        Returns:
            True if request was found and approved, False otherwise.
        """
        async with self._lock:
            if request_id not in self.pending_requests:
                logger.warning(f"Approval request {request_id} not found")
                return False

            request = self.pending_requests[request_id]
            if request["status"] != "pending":
                logger.warning(f"Request {request_id} already processed (status: {request['status']})")
                return False

            request["status"] = "approved"
            request["approved_at"] = datetime.now().isoformat()

            # Call approval callback if available
            callback = self.approval_callbacks.get(request_id)
            if callback:
                try:
                    await callback(True)
                except Exception as e:
                    logger.error(f"Error in approval callback for {request_id}: {e}")
                finally:
                    # Clean up callback
                    self.approval_callbacks.pop(request_id, None)

            logger.info(f"Permission request {request_id} approved")
            return True

    async def deny_request(self, request_id: str) -> bool:
        """Deny a pending permission request.

        Args:
            request_id: ID of the request to deny.

        Returns:
            True if request was found and denied, False otherwise.
        """
        async with self._lock:
            if request_id not in self.pending_requests:
                logger.warning(f"Denial request {request_id} not found")
                return False

            request = self.pending_requests[request_id]
            if request["status"] != "pending":
                logger.warning(f"Request {request_id} already processed (status: {request['status']})")
                return False

            request["status"] = "denied"
            request["denied_at"] = datetime.now().isoformat()

            # Call approval callback if available
            callback = self.approval_callbacks.get(request_id)
            if callback:
                try:
                    await callback(False)
                except Exception as e:
                    logger.error(f"Error in denial callback for {request_id}: {e}")
                finally:
                    # Clean up callback
                    self.approval_callbacks.pop(request_id, None)

            logger.info(f"Permission request {request_id} denied")
            return True

    def get_pending_requests(self) -> List[Dict[str, Any]]:
        """Get all pending approval requests.

        Returns:
            List of pending request dictionaries.
        """
        return [
            req for req in self.pending_requests.values()
            if req["status"] == "pending"
        ]

    def get_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific approval request.

        Args:
            request_id: ID of the request to get.

        Returns:
            Request dictionary if found, None otherwise.
        """
        return self.pending_requests.get(request_id)

    def remove_request(self, request_id: str) -> bool:
        """Remove a request from tracking (after processing).

        Args:
            request_id: ID of the request to remove.

        Returns:
            True if request was found and removed, False otherwise.
        """
        if request_id in self.pending_requests:
            del self.pending_requests[request_id]
            self.approval_callbacks.pop(request_id, None)
            return True
        return False
