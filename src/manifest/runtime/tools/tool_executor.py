"""
Tool Executor for executing tool calls.

This module provides the ToolExecutor class which takes tool calls from LLMs
and executes them using the appropriate handlers (TerminalRouter, FileManager).
"""
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from manifest.runtime.tools.file_manager import FileManager
from manifest.core.logger import get_logger

if TYPE_CHECKING:
    from manifest.runtime.router.terminal_router import TerminalRouter

logger = get_logger(__name__)


class ToolExecutor:
    """Executes tool calls from LLMs.
    
    Routes tool calls to appropriate handlers:
    - bash: TerminalRouter
    - edit, write, read, grep, glob, list: FileManager
    """
    
    def __init__(
        self,
        terminal_router: Optional["TerminalRouter"] = None,
        file_manager: Optional[FileManager] = None
    ):
        """Initialize tool executor.
        
        Args:
            terminal_router: TerminalRouter instance for bash commands.
            file_manager: FileManager instance for file operations.
        """
        self.terminal_router = terminal_router
        self.file_manager = file_manager
    
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
        """
        try:
            if tool_name == "bash":
                return await self._execute_bash(tool_input)
            elif tool_name == "edit":
                return self._execute_edit(tool_input)
            elif tool_name == "write":
                return self._execute_write(tool_input)
            elif tool_name == "read":
                return self._execute_read(tool_input)
            elif tool_name == "grep":
                return self._execute_grep(tool_input)
            elif tool_name == "glob":
                return self._execute_glob(tool_input)
            elif tool_name == "list":
                return self._execute_list(tool_input)
            else:
                return {
                    "tool_call_id": tool_input.get("id", "unknown"),
                    "tool_name": tool_name,
                    "error": f"Unknown tool: {tool_name}",
                    "result": None
                }
        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}': {e}")
            return {
                "tool_call_id": tool_input.get("id", "unknown"),
                "tool_name": tool_name,
                "error": str(e),
                "result": None
            }
    
    async def execute_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Execute multiple tool calls.
        
        Args:
            tool_calls: List of tool call dicts with 'id', 'name', 'input'.
            
        Returns:
            List of execution results.
        """
        results = []
        for tool_call in tool_calls:
            tool_id = tool_call.get("id", "unknown")
            tool_name = tool_call.get("name")
            tool_input = tool_call.get("input", {})
            tool_input["id"] = tool_id  # Include ID in input for result tracking
            
            result = await self.execute_tool(tool_name, tool_input)
            results.append(result)
        
        return results
    
    async def _execute_bash(self, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute bash command.
        
        Args:
            tool_input: Dict with 'command' and optional 'args'.
            
        Returns:
            Execution result dict.
        """
        if not self.terminal_router:
            return {
                "tool_call_id": tool_input.get("id", "unknown"),
                "tool_name": "bash",
                "error": "TerminalRouter not available",
                "result": None
            }
        
        command = tool_input.get("command")
        args = tool_input.get("args", [])
        
        if not command:
            return {
                "tool_call_id": tool_input.get("id", "unknown"),
                "tool_name": "bash",
                "error": "Command not provided",
                "result": None
            }
        
        try:
            result = await self.terminal_router.execute_command(
                command=command,
                args=args,
                stream=False
            )
            
            return {
                "tool_call_id": tool_input.get("id", "unknown"),
                "tool_name": "bash",
                "result": {
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", ""),
                    "returncode": result.get("returncode", -1),
                    "command": f"{command} {' '.join(args) if args else ''}".strip()
                }
            }
        except Exception as e:
            logger.error(f"Error executing bash command: {e}")
            return {
                "tool_call_id": tool_input.get("id", "unknown"),
                "tool_name": "bash",
                "error": str(e),
                "result": None
            }
    
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
