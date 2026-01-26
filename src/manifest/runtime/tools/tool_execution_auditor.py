"""
Tool Execution Auditor for logging and auditing tool executions.

This module provides comprehensive logging and auditing of all tool executions,
including file modifications, command executions, and errors. The auditor tracks
detailed information for security, debugging, and compliance purposes.
"""
import json
import asyncio
import aiofiles
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class ToolExecutionAuditor:
    """Audits and logs all tool executions for security and debugging.

    Tracks detailed information about every tool execution including:
    - Tool name and input parameters
    - Execution results and errors
    - File modifications (with diffs)
    - Command executions
    - Timestamps and agent context

    All audit logs are persisted to disk in JSON format for later analysis.

    Attributes:
        manifest_dir: Directory where audit logs are stored.
        audit_file: Path to the audit log file.
        max_log_entries: Maximum number of log entries to keep (for rotation).
    """

    def __init__(
        self,
        manifest_dir: Optional[Path] = None,
        max_log_entries: int = 10000
    ):
        """Initialize the tool execution auditor.

        Args:
            manifest_dir: Directory where audit logs are stored. Defaults to .manifest.
            max_log_entries: Maximum number of log entries before rotation. Default: 10000.
        """
        self.manifest_dir = manifest_dir or Path(".manifest")
        self.audit_file = self.manifest_dir / "tool_execution_audit.json"
        self.max_log_entries = max_log_entries
        self._audit_log: List[Dict[str, Any]] = []
        self._load_audit_log()

    def _load_audit_log(self) -> None:
        """Load existing audit log from disk.

        If the file doesn't exist or loading fails, starts with an empty log.
        """
        if self.audit_file.exists():
            try:
                with open(self.audit_file, "r") as f:
                    data = json.load(f)
                    self._audit_log = data.get("entries", [])
                    # Keep only recent entries if over limit
                    if len(self._audit_log) > self.max_log_entries:
                        self._audit_log = self._audit_log[-self.max_log_entries:]
            except Exception as e:
                logger.warning(f"Failed to load audit log: {e}. Starting with empty log.")
                self._audit_log = []
        else:
            self._audit_log = []

    async def log_tool_execution(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        result: Dict[str, Any],
        agent_type: Optional[str] = None,
        task_id: Optional[str] = None,
        agent_id: Optional[str] = None
    ) -> None:
        """Log a tool execution to the audit log.

        Records comprehensive information about the tool execution including
        input parameters, results, errors, and context.

        Args:
            tool_name: Name of the tool that was executed.
            tool_input: Input parameters for the tool.
            result: Execution result dictionary.
            agent_type: Type of agent that executed the tool.
            task_id: Optional task ID associated with this execution.
            agent_id: Optional agent ID that executed the tool.
        """
        try:
            # Extract relevant information
            tool_call_id = tool_input.get("id", "unknown")
            error = result.get("error")
            success = error is None and not result.get("permission_denied", False)

            # Create audit entry
            audit_entry = {
                "timestamp": datetime.now().isoformat(),
                "tool_name": tool_name,
                "tool_call_id": tool_call_id,
                "agent_type": agent_type,
                "agent_id": agent_id,
                "task_id": task_id,
                "success": success,
                "input": self._sanitize_input(tool_input, tool_name),
                "result": self._sanitize_result(result, tool_name),
                "error": error,
                "error_type": result.get("error_type"),
                "permission_denied": result.get("permission_denied", False),
                "permission_required": result.get("permission_required", False)
            }

            # Add tool-specific details
            if tool_name in ["edit", "write"]:
                audit_entry["file_modification"] = self._extract_file_modification(
                    tool_name, tool_input, result
                )
            elif tool_name == "bash":
                audit_entry["command_execution"] = self._extract_command_execution(
                    tool_input, result
                )
            elif tool_name == "read":
                audit_entry["file_read"] = {
                    "file_path": tool_input.get("file_path"),
                    "success": success
                }

            # Add to log
            self._audit_log.append(audit_entry)

            # Rotate if needed
            if len(self._audit_log) > self.max_log_entries:
                self._audit_log = self._audit_log[-self.max_log_entries:]

            # Save asynchronously (non-blocking)
            asyncio.create_task(self._save_audit_log())

        except Exception as e:
            logger.error(f"Error logging tool execution: {e}", exc_info=True)

    def _sanitize_input(
        self,
        tool_input: Dict[str, Any],
        tool_name: str
    ) -> Dict[str, Any]:
        """Sanitize tool input for logging.

        Removes sensitive information and truncates large values.

        Args:
            tool_input: Original tool input dictionary.
            tool_name: Name of the tool.

        Returns:
            Sanitized input dictionary.
        """
        sanitized = tool_input.copy()

        # Remove internal fields
        sanitized.pop("id", None)

        # Truncate large strings (e.g., file content)
        max_length = 1000
        for key, value in sanitized.items():
            if isinstance(value, str) and len(value) > max_length:
                sanitized[key] = value[:max_length] + f"... (truncated, {len(value)} chars)"

        return sanitized

    def _sanitize_result(
        self,
        result: Dict[str, Any],
        tool_name: str
    ) -> Dict[str, Any]:
        """Sanitize tool result for logging.

        Removes sensitive information and truncates large values.

        Args:
            result: Original result dictionary.
            tool_name: Name of the tool.

        Returns:
            Sanitized result dictionary.
        """
        sanitized = result.copy()

        # Remove internal tracking fields
        sanitized.pop("tool_call_id", None)
        sanitized.pop("tool_name", None)

        # Truncate large result values
        max_length = 2000
        if "result" in sanitized and isinstance(sanitized["result"], dict):
            result_dict = sanitized["result"]
            for key, value in result_dict.items():
                if isinstance(value, str) and len(value) > max_length:
                    result_dict[key] = value[:max_length] + f"... (truncated, {len(value)} chars)"

        return sanitized

    def _extract_file_modification(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract file modification details for audit log.

        Args:
            tool_name: Name of the tool (edit or write).
            tool_input: Tool input parameters.
            result: Tool execution result.

        Returns:
            Dictionary with file modification details.
        """
        file_path = tool_input.get("file_path", "unknown")
        success = result.get("success", False)

        modification = {
            "file_path": file_path,
            "operation": tool_name,
            "success": success
        }

        if tool_name == "edit":
            # For edit, we can track what was changed
            old_string = tool_input.get("old_string", "")
            new_string = tool_input.get("new_string", "")
            modification["change_type"] = "edit"
            modification["old_string_preview"] = old_string[:200] if old_string else ""
            modification["new_string_preview"] = new_string[:200] if new_string else ""
        elif tool_name == "write":
            # For write, track if file was created or overwritten
            content = tool_input.get("content", "")
            modification["change_type"] = "write"
            modification["content_preview"] = content[:200] if content else ""
            modification["content_length"] = len(content)

        return modification

    def _extract_command_execution(
        self,
        tool_input: Dict[str, Any],
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract command execution details for audit log.

        Args:
            tool_input: Tool input parameters.
            result: Tool execution result.

        Returns:
            Dictionary with command execution details.
        """
        command = tool_input.get("command", "unknown")
        args = tool_input.get("args", [])
        full_command = f"{command} {' '.join(args) if args else ''}".strip()

        result_data = result.get("result", {})
        stdout = result_data.get("stdout", "") if isinstance(result_data, dict) else ""
        stderr = result_data.get("stderr", "") if isinstance(result_data, dict) else ""
        returncode = result_data.get("returncode", -1) if isinstance(result_data, dict) else -1

        return {
            "command": full_command,
            "returncode": returncode,
            "stdout_preview": stdout[:500] if stdout else "",
            "stderr_preview": stderr[:500] if stderr else "",
            "stdout_length": len(stdout),
            "stderr_length": len(stderr),
            "success": returncode == 0
        }

    async def _save_audit_log(self) -> None:
        """Save audit log to disk asynchronously.

        Creates the manifest directory if it doesn't exist and writes the
        audit log in JSON format.
        """
        try:
            self.manifest_dir.mkdir(parents=True, exist_ok=True)
            audit_data = {
                "version": "1.0",
                "last_updated": datetime.now().isoformat(),
                "total_entries": len(self._audit_log),
                "entries": self._audit_log
            }
            async with aiofiles.open(self.audit_file, "w") as f:
                await f.write(json.dumps(audit_data, indent=2))
        except Exception as e:
            logger.error(f"Error saving audit log: {e}", exc_info=True)

    def get_audit_log(
        self,
        agent_type: Optional[str] = None,
        task_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get filtered audit log entries.

        Args:
            agent_type: Filter by agent type.
            task_id: Filter by task ID.
            tool_name: Filter by tool name.
            limit: Maximum number of entries to return.

        Returns:
            List of audit log entries matching the filters.
        """
        filtered = self._audit_log

        if agent_type:
            filtered = [e for e in filtered if e.get("agent_type") == agent_type]
        if task_id:
            filtered = [e for e in filtered if e.get("task_id") == task_id]
        if tool_name:
            filtered = [e for e in filtered if e.get("tool_name") == tool_name]

        if limit:
            filtered = filtered[-limit:]

        return filtered

    def get_file_modification_history(
        self,
        file_path: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get modification history for a specific file.

        Args:
            file_path: Path to the file.
            limit: Maximum number of entries to return.

        Returns:
            List of modification entries for the file.
        """
        modifications = []
        for entry in self._audit_log:
            mod = entry.get("file_modification")
            if mod and mod.get("file_path") == file_path:
                modifications.append(entry)

        if limit:
            modifications = modifications[-limit:]

        return modifications

    def get_command_execution_history(
        self,
        command_pattern: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get command execution history.

        Args:
            command_pattern: Optional pattern to filter commands (substring match).
            limit: Maximum number of entries to return.

        Returns:
            List of command execution entries.
        """
        commands = []
        for entry in self._audit_log:
            cmd = entry.get("command_execution")
            if cmd:
                if not command_pattern or command_pattern in cmd.get("command", ""):
                    commands.append(entry)

        if limit:
            commands = commands[-limit:]

        return commands
