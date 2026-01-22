"""
Terminal Router - OpenCode router for terminal command execution.
Routes terminal commands through OpenCode router system.
"""
import asyncio
import subprocess
from typing import Dict, Any, Optional, AsyncIterator
from pathlib import Path


class TerminalRouter:
    """
    Routes terminal commands through OpenCode router system.
    Terminal command execution router.
    """
    
    def __init__(self, working_dir: Optional[Path] = None, watchdog=None):
        """
        Initialize terminal router.
        
        Args:
            working_dir: Working directory for command execution
            watchdog: Optional watchdog instance for monitoring
        """
        self.working_dir = working_dir or Path.cwd()
        self.active_commands: Dict[str, subprocess.Popen] = {}
        self.watchdog = watchdog
    
    async def execute_command(
        self,
        command: str,
        args: Optional[list] = None,
        timeout: Optional[float] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Execute a terminal command through the router.
        
        Args:
            command: Command to execute
            args: Command arguments
            timeout: Command timeout in seconds
            stream: Whether to stream output
            
        Returns:
            Dict with 'stdout', 'stderr', 'returncode', 'command_id'
        """
        full_command = [command] + (args or [])
        command_id = f"cmd_{id(full_command)}"
        
        # Register with watchdog if available
        if self.watchdog:
            self.watchdog.register_command(command_id)
        
        try:
            if stream:
                return await self._execute_streaming(full_command, command_id, timeout)
            else:
                return await self._execute_buffered(full_command, command_id, timeout)
        except asyncio.TimeoutError:
            # Kill the process if timeout
            if command_id in self.active_commands:
                try:
                    self.active_commands[command_id].kill()
                except:
                    pass
                del self.active_commands[command_id]
            
            return {
                "stdout": "",
                "stderr": "Command timed out",
                "returncode": -1,
                "command_id": command_id,
                "timeout": True
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
                "command_id": command_id,
                "error": True
            }
    
    async def _execute_buffered(
        self,
        command: list,
        command_id: str,
        timeout: Optional[float]
    ) -> Dict[str, Any]:
        """Execute command with buffered output."""
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
                "command_id": command_id
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
        """Execute command with streaming output."""
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
                "streamed": True
            }
        finally:
            if command_id in self.active_commands:
                del self.active_commands[command_id]
    
    async def _read_stream(self, stream, lines_list):
        """Read from stream and append to lines list."""
        if stream:
            async for line in stream:
                decoded = line.decode('utf-8', errors='replace')
                lines_list.append(decoded)
    
    async def stream_command_output(
        self,
        command: str,
        args: Optional[list] = None
    ) -> AsyncIterator[str]:
        """
        Stream command output line by line.
        
        Yields:
            Output lines as they are produced
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
        """
        Cancel a running command.
        
        Args:
            command_id: Command ID to cancel
            
        Returns:
            True if command was cancelled, False if not found
        """
        if command_id in self.active_commands:
            process = self.active_commands[command_id]
            process.terminate()
            del self.active_commands[command_id]
            return True
        return False
    
    def is_command_running(self, command_id: str) -> bool:
        """Check if a command is currently running."""
        if command_id not in self.active_commands:
            return False
        
        process = self.active_commands[command_id]
        return process.returncode is None
