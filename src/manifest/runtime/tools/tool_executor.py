"""
Tool Executor for executing tool calls from LLMs.

Routes tool calls to TerminalRouter (bash) and FileManager (edit, write, read, etc.).
When tool_approval.ask_before_tool_run is True in .manifest/settings.json,
state-changing tools require user approval before execution.

Approval flow: no callback is wired; the caller receives approval_request_id and must
re-invoke the tool with __approved_request_id__ set to that id to proceed.
"""
from pathlib import Path
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from manifest.runtime.tools.file_manager import FileManager
from manifest.core.logger import get_logger

if TYPE_CHECKING:
    from manifest.runtime.router.terminal_router import TerminalRouter
    from manifest.runtime.permissions.permission_approval_manager import PermissionApprovalManager
    from manifest.runtime.tools.tool_execution_auditor import ToolExecutionAuditor

logger = get_logger(__name__)

# State-changing tools that require approval when tool_approval.ask_before_tool_run is True.
STATE_CHANGING_TOOLS = frozenset({
    "bash", "edit", "write",
    "blueprint_sync", "architect", "doc_creation",
})

class ToolExecutor:
    """Executes tool calls from LLMs.

    Routes tool calls to appropriate handlers:
    - bash: TerminalRouter
    - edit, write, read, grep, glob, list: FileManager
    """

    def __init__(
        self,
        terminal_router: Optional["TerminalRouter"] = None,
        file_manager: Optional[FileManager] = None,
        approval_manager: Optional["PermissionApprovalManager"] = None,
        auditor: Optional["ToolExecutionAuditor"] = None,
        agent_type: Optional[str] = None,
        task_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        manifest_dir: Optional[Path] = None,
    ):
        """Initialize tool executor.

        Args:
            terminal_router: TerminalRouter instance for bash commands.
            file_manager: FileManager instance for file operations.
            approval_manager: Optional PermissionApprovalManager for handling "ask" permissions.
            auditor: Optional ToolExecutionAuditor for logging tool executions.
            agent_type: Optional agent type for audit logging.
            task_id: Optional task ID for audit logging.
            agent_id: Optional agent ID for audit logging.
            manifest_dir: Optional path to .manifest for OpenCode tools (blueprint_sync, architect, doc_creation).
        """
        self.terminal_router = terminal_router
        self.file_manager = file_manager
        self.approval_manager = approval_manager
        self.auditor = auditor
        self.agent_type = agent_type
        self.task_id = task_id
        self.agent_id = agent_id
        self.manifest_dir = manifest_dir or Path.cwd() / ".manifest"

    def _check_tool_approval_gate(self, tool_name: str, tool_input: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Require user approval for state-changing tools when tool_approval.ask_before_tool_run is True.

        Returns:
            A result dict to return (permission_required), or None to proceed with execution.
        """
        if tool_name not in STATE_CHANGING_TOOLS:
            return None
        approved_id = tool_input.get("__approved_request_id__")
        if approved_id and self.approval_manager:
            req = self.approval_manager.get_request(approved_id)
            if req and req.get("status") == "approved":
                return None  # Proceed with execution (caller's tool_input unchanged)
        try:
            from manifest.core.config import ConfigManager
            cm = ConfigManager(self.manifest_dir)
            if not cm.get_setting("tool_approval.ask_before_tool_run", False):
                return None
        except Exception as e:
            logger.debug("_check_tool_approval config load failed: %s", e)
            return None
        if not self.approval_manager:
            return None
        resource = tool_input.get("file_path") or tool_input.get("command") or tool_name
        request_id = self.approval_manager.create_approval_request(
            permission_type="tool_run",
            resource=str(resource),
            agent_type=self.agent_type or "agent",
            tool_name=tool_name,
            tool_input=tool_input,
            approval_callback=None,  # No callback; user re-invokes with __approved_request_id__
        )
        return self._tool_result(
            tool_input, tool_name,
            result=None,
            permission_required=True,
            approval_request_id=request_id,
            message="Tool execution pending approval. Approve then re-invoke with __approved_request_id__ set to this request_id.",
        )

    @staticmethod
    def _tool_result(
        tool_input: Dict[str, Any],
        tool_name: str,
        result: Any = None,
        error: Optional[str] = None,
        **extra: Any,
    ) -> Dict[str, Any]:
        """Build a standard tool result dict. Use **extra for permission_required, permission_denied, etc."""
        out: Dict[str, Any] = {
            "tool_call_id": tool_input.get("id", "unknown"),
            "tool_name": tool_name,
            "result": result,
        }
        if error is not None:
            out["error"] = error
        out.update(extra)
        return out

    async def execute_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single tool call.

        Args:
            tool_name: Name of the tool to execute.
            tool_input: Input parameters for the tool.

        Returns:
            Dict with 'tool_call_id', 'tool_name', 'result', and optional 'error'.
            May also include 'permission_denied' or 'permission_required' flags.
        """
        gate_result = self._check_tool_approval_gate(tool_name, tool_input)
        if gate_result is not None:
            return gate_result

        result = None
        try:
            if tool_name == "bash":
                result = await self._execute_bash(tool_input)
            elif tool_name == "edit":
                result = self._execute_edit(tool_input)
            elif tool_name == "write":
                result = self._execute_write(tool_input)
            elif tool_name == "read":
                result = self._execute_read(tool_input)
            elif tool_name == "grep":
                result = self._execute_grep(tool_input)
            elif tool_name == "glob":
                result = self._execute_glob(tool_input)
            elif tool_name == "list":
                result = self._execute_list(tool_input)
            elif tool_name == "blueprint_sync":
                result = self._execute_blueprint_sync(tool_input)
            elif tool_name == "architect":
                result = self._execute_architect(tool_input)
            elif tool_name == "doc_creation":
                result = self._execute_doc_creation(tool_input)
            elif tool_name == "drift_check":
                result = self._execute_drift_check(tool_input)
            else:
                result = {
                    "tool_call_id": tool_input.get("id", "unknown"),
                    "tool_name": tool_name,
                    "error": f"Unknown tool: {tool_name}",
                    "result": None,
                    "error_type": "unknown_tool"
                }
        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}': {e}", exc_info=True)
            # Analyze error type for better error handling
            error_type = "execution_error"
            error_msg = str(e)

            # Categorize common errors
            if "Permission" in error_msg or "permission" in error_msg.lower():
                error_type = "permission_error"
            elif "File not found" in error_msg or "No such file" in error_msg:
                error_type = "file_not_found"
            elif "String not found" in error_msg:
                error_type = "string_not_found"

            result = {
                "tool_call_id": tool_input.get("id", "unknown"),
                "tool_name": tool_name,
                "error": error_msg,
                "error_type": error_type,
                "result": None
            }

        # Log to auditor if available (for all executions, success or error)
        if self.auditor and result:
            await self.auditor.log_tool_execution(
                tool_name=tool_name,
                tool_input=tool_input,
                result=result,
                agent_type=self.agent_type,
                task_id=self.task_id,
                agent_id=self.agent_id
            )

        return result

    async def execute_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Execute multiple tool calls.

        Args:
            tool_calls: List of tool call dicts with 'id', 'name', 'input'.

        Returns:
            List of execution results with validation information.
        """
        results = []
        for tool_call in tool_calls:
            tool_id = tool_call.get("id", "unknown")
            tool_name = tool_call.get("name")
            tool_input = tool_call.get("input", {})
            tool_input["id"] = tool_id  # Include ID in input for result tracking

            result = await self.execute_tool(tool_name, tool_input)

            # Add validation information
            result["validated"] = self._validate_tool_result(result, tool_name, tool_input)

            # Log to auditor if available (for all executions, success or error)
            if self.auditor and result:
                await self.auditor.log_tool_execution(
                    tool_name=tool_name,
                    tool_input=tool_input,
                    result=result,
                    agent_type=self.agent_type,
                    task_id=self.task_id,
                    agent_id=self.agent_id
                )

            results.append(result)

        return results

    def _validate_tool_result(
        self,
        result: Dict[str, Any],
        tool_name: str,
        tool_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate tool execution result.

        Checks if the tool execution was successful and provides
        validation information for downstream processing.

        Args:
            result: Tool execution result dictionary.
            tool_name: Name of the tool that was executed.
            tool_input: Input parameters for the tool.

        Returns:
            Dictionary with validation information:
            {
                "success": bool,
                "validation_errors": List[str],
                "warnings": List[str]
            }
        """
        validation = {
            "success": True,
            "validation_errors": [],
            "warnings": []
        }

        # Check for errors
        if result.get("error"):
            validation["success"] = False
            validation["validation_errors"].append(result.get("error"))
            return validation

        # Tool-specific validation
        if tool_name == "edit":
            tool_result = result.get("result", {})
            if not tool_result.get("success"):
                validation["success"] = False
                validation["validation_errors"].append(
                    tool_result.get("error", "Edit operation failed")
                )
            else:
                file_path = tool_input.get("file_path")
                if file_path:
                    validation["warnings"].append(
                        f"File '{file_path}' was modified. Run tests to verify changes."
                    )

        elif tool_name == "write":
            tool_result = result.get("result", {})
            if not tool_result.get("success"):
                validation["success"] = False
                validation["validation_errors"].append(
                    tool_result.get("error", "Write operation failed")
                )
            else:
                file_path = tool_input.get("file_path")
                if file_path:
                    validation["warnings"].append(
                        f"New file '{file_path}' was created. Run tests to verify."
                    )

        elif tool_name == "bash":
            tool_result = result.get("result", {})
            returncode = tool_result.get("returncode", 0)
            if returncode != 0:
                validation["success"] = False
                stderr = tool_result.get("stderr", "")
                validation["validation_errors"].append(
                    f"Command failed with return code {returncode}: {stderr[:200]}"
                )
            else:
                # Check if command looks like a test command
                command = tool_input.get("command", "")
                if "test" in command.lower() or "pytest" in command.lower():
                    stdout = tool_result.get("stdout", "")
                    if "failed" in stdout.lower() or "error" in stdout.lower():
                        validation["warnings"].append(
                            "Test command executed but some tests may have failed. "
                            "Check output for details."
                        )

        return validation

    async def _execute_bash(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute bash command.

        Args:
            tool_input: Dict with 'command' and optional 'args'.

        Returns:
            Execution result dict.
        """
        if not self.terminal_router:
            return self._tool_result(tool_input, "bash", error="TerminalRouter not available")

        command = tool_input.get("command")
        args = tool_input.get("args", [])

        if not command:
            return self._tool_result(tool_input, "bash", error="Command not provided")

        try:
            result = await self.terminal_router.execute_command(
                command=command,
                args=args,
                stream=False
            )

            # Check for permission denied
            if result.get("permission_denied"):
                return self._tool_result(
                    tool_input, "bash",
                    error=result.get("stderr", "Permission denied"),
                    permission_denied=True,
                )

            # Check for permission required (ask)
            if result.get("permission_required"):
                permission_details = result.get("permission_details", {})

                # Create approval request if approval_manager is available
                if self.approval_manager:
                    request_id = self.approval_manager.create_approval_request(
                        permission_type="bash",
                        resource=permission_details.get("resource", "unknown command"),
                        agent_type=permission_details.get("agent_type", "unknown"),
                        tool_name="bash",
                        tool_input=tool_input,
                        approval_callback=None,  # No callback; user re-invokes with __approved_request_id__
                    )

                    return self._tool_result(
                        tool_input, "bash",
                        error="Permission approval required",
                        permission_required=True,
                        permission_details=permission_details,
                        approval_request_id=request_id,
                    )
                else:
                    return self._tool_result(
                        tool_input, "bash",
                        error="Permission approval required but no approval manager available",
                        permission_required=True,
                        permission_details=permission_details,
                    )

            return self._tool_result(tool_input, "bash", result={
                "stdout": result.get("stdout", ""),
                "stderr": result.get("stderr", ""),
                "returncode": result.get("returncode", -1),
                "command": f"{command} {' '.join(args) if args else ''}".strip()
            })
        except Exception as e:
            logger.error(f"Error executing bash command: {e}")
            return self._tool_result(tool_input, "bash", error=str(e))

    def _execute_edit(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute edit operation.

        Args:
            tool_input: Dict with 'file_path', 'old_string', 'new_string'.

        Returns:
            Execution result dict.
        """
        if not self.file_manager:
            return {
                "tool_call_id": tool_input.get("id", "unknown"),
                "tool_name": "edit",
                "error": "FileManager not available",
                "result": None
            }

        file_path = tool_input.get("file_path")
        old_string = tool_input.get("old_string")
        new_string = tool_input.get("new_string")

        if not all([file_path, old_string, new_string is not None]):
            return {
                "tool_call_id": tool_input.get("id", "unknown"),
                "tool_name": "edit",
                "error": "Missing required parameters: file_path, old_string, new_string",
                "result": None
            }

        result = self.file_manager.edit(file_path, old_string, new_string)

        # Check for permission denied or required
        if not result.get("success"):
            error = result.get("error", "Unknown error")
            permission_required = result.get("permission_required", False)

            # Create approval request if permission_required and approval_manager available
            if permission_required and self.approval_manager:
                request_id = self.approval_manager.create_approval_request(
                    permission_type=result.get("permission_type", "edit"),
                    resource=result.get("resource", tool_input.get("file_path", "unknown")),
                    agent_type=self.file_manager.agent_type if self.file_manager else "unknown",
                    tool_name="edit",
                    tool_input=tool_input,
                    approval_callback=None,  # No callback; user re-invokes with __approved_request_id__
                )

                return {
                    "tool_call_id": tool_input.get("id", "unknown"),
                    "tool_name": "edit",
                    "error": error,
                    "result": None,
                    "permission_denied": error == "Permission denied",
                    "permission_required": True,
                    "permission_details": {
                        "permission_type": result.get("permission_type", "edit"),
                        "resource": result.get("resource", tool_input.get("file_path", "unknown"))
                    },
                    "approval_request_id": request_id
                }

            return {
                "tool_call_id": tool_input.get("id", "unknown"),
                "tool_name": "edit",
                "error": error,
                "result": None,
                "permission_denied": error == "Permission denied",
                "permission_required": permission_required
            }

        return {
            "tool_call_id": tool_input.get("id", "unknown"),
            "tool_name": "edit",
            "result": result
        }

    def _execute_write(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute write operation.

        Args:
            tool_input: Dict with 'file_path', 'content'.

        Returns:
            Execution result dict.
        """
        if not self.file_manager:
            return {
                "tool_call_id": tool_input.get("id", "unknown"),
                "tool_name": "write",
                "error": "FileManager not available",
                "result": None
            }

        file_path = tool_input.get("file_path")
        content = tool_input.get("content")

        if not file_path or content is None:
            return {
                "tool_call_id": tool_input.get("id", "unknown"),
                "tool_name": "write",
                "error": "Missing required parameters: file_path, content",
                "result": None
            }

        result = self.file_manager.write(file_path, content)

        # Check for permission denied or required
        if not result.get("success"):
            error = result.get("error", "Unknown error")
            permission_required = result.get("permission_required", False)

            # Create approval request if permission_required and approval_manager available
            if permission_required and self.approval_manager:
                request_id = self.approval_manager.create_approval_request(
                    permission_type=result.get("permission_type", "write"),
                    resource=result.get("resource", tool_input.get("file_path", "unknown")),
                    agent_type=self.file_manager.agent_type if self.file_manager else "unknown",
                    tool_name="write",
                    tool_input=tool_input,
                    approval_callback=None,  # No callback; user re-invokes with __approved_request_id__
                )

                return {
                    "tool_call_id": tool_input.get("id", "unknown"),
                    "tool_name": "write",
                    "error": error,
                    "result": None,
                    "permission_denied": error == "Permission denied",
                    "permission_required": True,
                    "permission_details": {
                        "permission_type": result.get("permission_type", "write"),
                        "resource": result.get("resource", tool_input.get("file_path", "unknown"))
                    },
                    "approval_request_id": request_id
                }

            return {
                "tool_call_id": tool_input.get("id", "unknown"),
                "tool_name": "write",
                "error": error,
                "result": None,
                "permission_denied": error == "Permission denied",
                "permission_required": permission_required
            }

        return {
            "tool_call_id": tool_input.get("id", "unknown"),
            "tool_name": "write",
            "result": result
        }

    def _execute_read(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute read operation.

        Args:
            tool_input: Dict with 'file_path' and optional 'start_line', 'end_line'.

        Returns:
            Execution result dict.
        """
        if not self.file_manager:
            return {
                "tool_call_id": tool_input.get("id", "unknown"),
                "tool_name": "read",
                "error": "FileManager not available",
                "result": None
            }

        file_path = tool_input.get("file_path")
        if not file_path:
            return {
                "tool_call_id": tool_input.get("id", "unknown"),
                "tool_name": "read",
                "error": "Missing required parameter: file_path",
                "result": None
            }

        start_line = tool_input.get("start_line")
        end_line = tool_input.get("end_line")

        result = self.file_manager.read(file_path, start_line, end_line)

        return {
            "tool_call_id": tool_input.get("id", "unknown"),
            "tool_name": "read",
            "result": result
        }

    def _execute_grep(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute grep operation.

        Args:
            tool_input: Dict with 'pattern', 'file_path'.

        Returns:
            Execution result dict.
        """
        if not self.file_manager:
            return {
                "tool_call_id": tool_input.get("id", "unknown"),
                "tool_name": "grep",
                "error": "FileManager not available",
                "result": None
            }

        pattern = tool_input.get("pattern")
        file_path = tool_input.get("file_path")

        if not pattern or not file_path:
            return {
                "tool_call_id": tool_input.get("id", "unknown"),
                "tool_name": "grep",
                "error": "Missing required parameters: pattern, file_path",
                "result": None
            }

        result = self.file_manager.grep(pattern, file_path)

        return {
            "tool_call_id": tool_input.get("id", "unknown"),
            "tool_name": "grep",
            "result": result
        }

    def _execute_glob(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute glob operation.

        Args:
            tool_input: Dict with 'pattern'.

        Returns:
            Execution result dict.
        """
        if not self.file_manager:
            return {
                "tool_call_id": tool_input.get("id", "unknown"),
                "tool_name": "glob",
                "error": "FileManager not available",
                "result": None
            }

        pattern = tool_input.get("pattern")
        if not pattern:
            return {
                "tool_call_id": tool_input.get("id", "unknown"),
                "tool_name": "glob",
                "error": "Missing required parameter: pattern",
                "result": None
            }

        result = self.file_manager.glob(pattern)

        return {
            "tool_call_id": tool_input.get("id", "unknown"),
            "tool_name": "glob",
            "result": result
        }

    def _execute_list(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute list operation.

        Args:
            tool_input: Dict with optional 'directory'.

        Returns:
            Execution result dict.
        """
        if not self.file_manager:
            return {
                "tool_call_id": tool_input.get("id", "unknown"),
                "tool_name": "list",
                "error": "FileManager not available",
                "result": None
            }

        directory = tool_input.get("directory")

        result = self.file_manager.list(directory)

        return {
            "tool_call_id": tool_input.get("id", "unknown"),
            "tool_name": "list",
            "result": result
        }

    def _execute_blueprint_sync(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute blueprint_sync tool (compare_blueprints, detect_deviation, sync_blueprint, compare_all_docs)."""
        from manifest.runtime.opencode.tools.blueprint_sync import BlueprintSyncTool
        tool = BlueprintSyncTool(self.manifest_dir)
        action = (tool_input.get("action") or "").strip()
        if not action:
            return self._tool_result(tool_input, "blueprint_sync", error="Missing action")
        try:
            if action == "compare_blueprints":
                out = tool.compare_blueprints()
            elif action in ("detect_drift", "detect_deviation"):
                out = tool.detect_deviation()
            elif action == "sync_blueprint":
                mode = (tool_input.get("mode") or "workflow").strip()
                out = tool.sync_blueprint(mode=mode)
            elif action == "compare_all_docs":
                out = tool.compare_all_docs()
            else:
                return self._tool_result(tool_input, "blueprint_sync", error=f"Unknown action: {action}")
            return self._tool_result(tool_input, "blueprint_sync", result=out)
        except Exception as e:
            logger.error(f"blueprint_sync error: {e}", exc_info=True)
            return self._tool_result(tool_input, "blueprint_sync", error=str(e))

    def _execute_architect(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute architect tool (write PRD, architecture, or intent only)."""
        from manifest.runtime.opencode.tools.architect_tool import ArchitectTool
        tool = ArchitectTool(self.manifest_dir)
        action = (tool_input.get("action") or "").strip()
        if not action:
            return self._tool_result(tool_input, "architect", error="Missing action")
        content = tool_input.get("content")
        try:
            out = tool.run(action=action, content=content)
            if out.get("ok"):
                return self._tool_result(tool_input, "architect", result=out)
            return self._tool_result(tool_input, "architect", error=out.get("error", "Unknown error"))
        except Exception as e:
            logger.error(f"architect error: {e}", exc_info=True)
            return self._tool_result(tool_input, "architect", error=str(e))

    def _execute_doc_creation(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute doc_creation tool (hierarchical blueprint from PRD)."""
        from manifest.runtime.opencode.tools.doc_creation_tool import DocCreationTool
        tool = DocCreationTool(self.manifest_dir)
        action = (tool_input.get("action") or "").strip()
        if not action:
            return self._tool_result(tool_input, "doc_creation", error="Missing action")
        try:
            out = tool.run(
                action=action,
                parent_entity_id=tool_input.get("parent_entity_id"),
                child_entities=tool_input.get("child_entities"),
                prd_excerpt=tool_input.get("prd_excerpt"),
                context=tool_input.get("context"),
                depth=tool_input.get("depth"),
            )
            if out.get("ok"):
                return self._tool_result(tool_input, "doc_creation", result=out)
            return self._tool_result(tool_input, "doc_creation", error=out.get("error", "Unknown error"))
        except Exception as e:
            logger.error(f"doc_creation error: {e}", exc_info=True)
            return self._tool_result(tool_input, "doc_creation", error=str(e))

    def _execute_drift_check(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute drift_check tool (returns component statuses: healthy/planned/deviation/extra)."""
        from manifest.runtime.opencode.tools.blueprint_sync import DeviationCheckTool
        tool = DeviationCheckTool(self.manifest_dir)
        try:
            out = tool.check()
            return self._tool_result(tool_input, "drift_check", result=out)
        except Exception as e:
            logger.error(f"drift_check error: {e}", exc_info=True)
            return self._tool_result(tool_input, "drift_check", error=str(e))
