"""
Terminal command routing for programmatic use.

Terminal and tool execution for agents are handled by the configured backend (primary: OpenCode).
This router is for programmatic command execution from Manifest code.
"""
import asyncio
import subprocess
from typing import Dict, Any, Optional, AsyncIterator, TYPE_CHECKING
from pathlib import Path
from manifest.core.logger import get_logger

if TYPE_CHECKING:
    from manifest.runtime.permissions.permission_manager import PermissionManager

logger = get_logger(__name__)


class TerminalRouter:
    """Routes and executes terminal commands for agents.

    Provides a unified interface for executing terminal commands using
    standard subprocess execution. Handles command execution, output
    streaming, cancellation, and monitoring.

    Attributes:
        working_dir: Directory where commands are executed.
        active_commands: Dictionary tracking currently running commands.
        watchdog: Optional watchdog instance for monitoring command execution.
        permission_manager: Optional PermissionManager for access control.
        agent_type: Optional agent type for permission checks.
    """

    def __init__(
        self,
        working_dir: Optional[Path] = None,
        watchdog=None,
        use_opencode: Optional[bool] = None,
        permission_manager: Optional["PermissionManager"] = None,
        agent_type: Optional[str] = None
    ):
        """Initialize the terminal router.

        Args:
            working_dir: Directory where commands should be executed.
            watchdog: Optional watchdog for monitoring command execution.
            use_opencode: Unused; kept for compatibility.
            permission_manager: Optional PermissionManager for access control.
            agent_type: Optional agent type for permission checks.
        """
        self.working_dir = working_dir or Path.cwd()
        self.active_commands: Dict[str, subprocess.Popen] = {}
        self.watchdog = watchdog
        self.permission_manager = permission_manager
        self.agent_type = agent_type

    async def execute_command(
        self,
        command: str,
        args: Optional[list] = None,
        timeout: Optional[float] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Execute a terminal command and return results.

        Checks permissions before execution if PermissionManager is configured.
        Delegates to OpenCodeAdapter which handles OpenCode integration
        and fallback. The command is registered with the watchdog if
        available for monitoring.

        Args:
            command: Command name to execute (e.g., "git", "python").
            args: Optional list of command arguments.
            timeout: Optional timeout in seconds. Command will be killed
                if it exceeds this time.
            stream: Whether to stream output in real-time. If True, output
                is yielded as it arrives rather than buffered.

        Returns:
            Dictionary containing:
            - stdout: Standard output text
            - stderr: Standard error text
            - returncode: Exit code of the command
            - command_id: Unique ID for this command execution
            - backend: Always "internal" (subprocess)
            - permission_denied: True if command was denied (only if denied)
        """
        full_command = [command] + (args or [])
        command_id = f"cmd_{id(full_command)}"

        # Check permissions if PermissionManager is configured
        if self.permission_manager and self.agent_type:
            permission = self.permission_manager.check_permission(
                "bash",
                full_command
            )

            if permission == "deny":
                return {
                    "stdout": "",
                    "stderr": f"Permission denied: Command '{' '.join(full_command)}' is not allowed for agent type '{self.agent_type}'",
                    "returncode": -1,
                    "command_id": command_id,
                    "permission_denied": True,
                    "backend": "internal"
                }
            elif permission == "ask":
                # Return permission_required flag for UI approval
                # For now, deny to be safe (can be approved via UI later)
                logger.warning(
                    f"Permission 'ask' for command '{' '.join(full_command)}' "
                    f"by agent '{self.agent_type}' - approval required"
                )
                return {
                    "stdout": "",
                    "stderr": f"Permission approval required: Command '{' '.join(full_command)}' requires approval for agent type '{self.agent_type}'",
                    "returncode": -1,
                    "command_id": command_id,
                    "permission_required": True,
                    "permission_details": {
                        "permission_type": "bash",
                        "resource": ' '.join(full_command),
                        "agent_type": self.agent_type
                    },
                    "backend": "internal"
                }

        # Register with watchdog if available
        if self.watchdog:
            self.watchdog.register_command(command_id)

        # Execute command directly using subprocess
        try:
            if stream:
                result = await self._execute_streaming(full_command, command_id, timeout)
            else:
                result = await self._execute_buffered(full_command, command_id, timeout)

            result["backend"] = "internal"
            result["command_id"] = command_id
            return result
        except asyncio.TimeoutError:
            return {
                "stdout": "",
                "stderr": "Command timed out",
                "returncode": -1,
                "command_id": command_id,
                "timeout": True,
                "backend": "internal"
            }
        except Exception as e:
            logger.error(f"Error executing command: {e}", exc_info=True)
            return {
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
                "command_id": command_id,
                "error": True,
                "backend": "internal"
            }

    async def _execute_buffered(
        self,
        command: list,
        command_id: str,
        timeout: Optional[float]
    ) -> Dict[str, Any]:
        """Execute a command and collect all output before returning.

        Runs the command and waits for it to complete, collecting all
        stdout and stderr output. This is useful when you need the complete
        output before processing it.

        Args:
            command: List containing command and arguments.
            command_id: Unique identifier for this command execution.
            timeout: Optional timeout in seconds. Command is killed if exceeded.

        Returns:
            Dictionary with stdout, stderr, returncode, and command_id.
            Command is removed from active_commands when done.
        """
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.working_dir)
        )

        self.active_commands[command_id] = process

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            return {
                "stdout": stdout.decode('utf-8', errors='replace'),
                "stderr": stderr.decode('utf-8', errors='replace'),
                "returncode": process.returncode,
                "command_id": command_id,
                "backend": "internal"
            }
        finally:
            if command_id in self.active_commands:
                del self.active_commands[command_id]

    async def _execute_streaming(
        self,
        command: list,
        command_id: str,
        timeout: Optional[float]
    ) -> Dict[str, Any]:
        """Execute a command and stream output in real-time.

        Runs the command and reads stdout/stderr as they're produced,
        allowing for real-time output display. Output is still collected
        and returned at the end.

        Args:
            command: List containing command and arguments.
            command_id: Unique identifier for this command execution.
            timeout: Optional timeout in seconds. Command is killed if exceeded.

        Returns:
            Dictionary with stdout, stderr, returncode, command_id, and
            streamed=True flag. Command is removed from active_commands when done.
        """
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.working_dir)
        )

        self.active_commands[command_id] = process

        stdout_lines = []
        stderr_lines = []

        try:
            # Stream stdout and stderr
            async def read_stream(stream, lines_list):
                async for line in stream:
                    decoded = line.decode('utf-8', errors='replace')
                    lines_list.append(decoded)
                    yield decoded

            # Create tasks for reading both streams
            stdout_task = asyncio.create_task(
                self._read_stream(process.stdout, stdout_lines)
            )
            stderr_task = asyncio.create_task(
                self._read_stream(process.stderr, stderr_lines)
            )

            # Wait for process to complete or timeout
            try:
                await asyncio.wait_for(
                    process.wait(),
                    timeout=timeout
                )
            except asyncio.TimeoutExpired:
                process.kill()
                await process.wait()
                raise

            # Wait for streams to finish
            await stdout_task
            await stderr_task

            return {
                "stdout": "".join(stdout_lines),
                "stderr": "".join(stderr_lines),
                "returncode": process.returncode,
                "command_id": command_id,
                "streamed": True,
                "backend": "internal"
            }
        finally:
            if command_id in self.active_commands:
                del self.active_commands[command_id]

    async def _read_stream(self, stream, lines_list):
        """Read lines from a stream and append them to a list.

        Helper method for streaming command output. Reads lines asynchronously
        and decodes them, appending to the provided list for later collection.

        Args:
            stream: Async stream to read from (stdout or stderr).
            lines_list: List to append decoded lines to.
        """
        if stream:
            async for line in stream:
                decoded = line.decode('utf-8', errors='replace')
                lines_list.append(decoded)

    async def stream_command_output(
        self,
        command: str,
        args: Optional[list] = None
    ) -> AsyncIterator[str]:
        """Stream command output line by line as it's produced.

        Output is yielded line by line for real-time display, useful for
        long-running commands where you want to show progress.

        Args:
            command: Command name to execute.
            args: Optional list of command arguments.

        Yields:
            Output lines as strings, one line at a time as they're produced
            by the command.
        """
        full_command = [command] + (args or [])
        process = await asyncio.create_subprocess_exec(
            *full_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(self.working_dir)
        )

        try:
            if process.stdout:
                async for line in process.stdout:
                    yield line.decode('utf-8', errors='replace')

            await process.wait()
        finally:
            if process.returncode is None:
                process.terminate()
                await process.wait()

    def cancel_command(self, command_id: str) -> bool:
        """Cancel a currently running command.

        Sends a termination signal to the command process and removes it
        from the active commands registry. The process may take a moment
        to actually terminate.

        Args:
            command_id: ID of the command to cancel.

        Returns:
            True if command was found and termination signal sent,
            False if command wasn't in active_commands.
        """
        if command_id in self.active_commands:
            process = self.active_commands[command_id]
            process.terminate()
            del self.active_commands[command_id]
            return True
        return False

    def is_command_running(self, command_id: str) -> bool:
        """Check if a command is currently executing.

        Args:
            command_id: ID of the command to check.

        Returns:
            True if command is in active_commands and hasn't finished
            (returncode is None), False otherwise.
        """
        if command_id not in self.active_commands:
            return False

        process = self.active_commands[command_id]
        return process.returncode is None

    def is_opencode_available(self) -> bool:
        """Check if OpenCode is available and configured.

        Returns:
            Always False (OpenCode terminal adapter removed).
        """
        return False
