"""
Terminal Router - OpenCode router for terminal command execution.
Routes terminal commands through OpenCode router system.
"""
import asyncio
import subprocess
from typing import Dict, Any, Optional, AsyncIterator
from pathlib import Path
from manifest.runtime.opencode_adapter import OpenCodeAdapter


class TerminalRouter:
    """
    Routes terminal commands through OpenCode router system.
    Terminal command execution router.
    Uses OpenCodeAdapter for OpenCode integration with fallback.
    """
    
    def __init__(
        self,
        working_dir: Optional[Path] = None,
        watchdog=None,
        use_opencode: Optional[bool] = None
    ):
        """
        Initialize terminal router.
        
        Args:
            working_dir: Working directory for command execution
            watchdog: Optional watchdog instance for monitoring
            use_opencode: Force use of OpenCode (True) or internal (False).
                         If None, auto-detect based on availability.
        """
        self.working_dir = working_dir or Path.cwd()
        self.active_commands: Dict[str, subprocess.Popen] = {}
        self.watchdog = watchdog
        
        # Initialize OpenCode adapter with shared active_commands and watchdog
        self.opencode_adapter = OpenCodeAdapter(
            working_dir=working_dir,
            use_opencode=use_opencode,
            active_commands=self.active_commands,  # Share active_commands
            watchdog=watchdog  # Share watchdog
        )
    
    async def execute_command(
        self,
        command: str,
        args: Optional[list] = None,
        timeout: Optional[float] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Execute a terminal command through the router.
        Uses OpenCodeAdapter which handles OpenCode integration with fallback.
        
        Args:
            command: Command to execute
            args: Command arguments
            timeout: Command timeout in seconds
            stream: Whether to stream output
            
        Returns:
            Dict with 'stdout', 'stderr', 'returncode', 'command_id', 'backend'
        """
        full_command = [command] + (args or [])
        command_id = f"cmd_{id(full_command)}"
        
        # Register with watchdog if available
        if self.watchdog:
            self.watchdog.register_command(command_id)
        
        # Use OpenCode adapter (handles OpenCode integration and fallback)
        result = await self.opencode_adapter.execute_command(
            command=command,
            args=args,
            timeout=timeout,
            stream=stream
        )
        
        # Ensure command_id is set
        result["command_id"] = command_id
        
        return result
    
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
        Uses OpenCode adapter if available.
        
        Yields:
            Output lines as they are produced
        """
        async for line in self.opencode_adapter.stream_command_output(command, args):
            yield line
    
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
    
    def is_opencode_available(self) -> bool:
        """Check if OpenCode is available and being used."""
        return self.opencode_adapter.is_opencode_available()