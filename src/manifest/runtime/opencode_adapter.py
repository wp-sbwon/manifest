"""
OpenCode adapter for optional OpenCode terminal integration.

This module provides the OpenCodeAdapter class which integrates with OpenCode
(if available) for enhanced terminal command execution. If OpenCode is not
available or initialization fails, it falls back to internal subprocess-based
execution.

The adapter provides a unified interface that abstracts away whether OpenCode
or internal execution is being used, making it transparent to callers.
"""
import asyncio
import subprocess
from typing import Dict, Any, Optional, AsyncIterator
from pathlib import Path

# Try to import OpenCode
try:
    import opencode
    OPENCODE_AVAILABLE = True
    OPENCODE_VERSION = getattr(opencode, '__version__', 'unknown')
except ImportError:
    OPENCODE_AVAILABLE = False
    OPENCODE_VERSION = None
    opencode = None


class OpenCodeAdapter:
    """Adapter for OpenCode terminal functionality with fallback.
    
    Provides a unified interface for terminal command execution that can use
    either OpenCode (if available) or internal subprocess execution. The
    adapter automatically detects OpenCode availability and falls back gracefully
    if OpenCode is not installed or initialization fails.
    
    Attributes:
        working_dir: Directory where commands are executed.
        active_commands: Dictionary tracking active command processes (shared
            with TerminalRouter for unified tracking).
        watchdog: Optional watchdog instance for monitoring command execution.
        use_opencode: Whether OpenCode is being used (True) or internal (False).
        opencode_router: OpenCode router instance if OpenCode is available.
    """
    
    def __init__(
        self,
        working_dir: Optional[Path] = None,
        use_opencode: Optional[bool] = None,
        active_commands: Optional[Dict[str, subprocess.Popen]] = None,
        watchdog=None
    ):
        """Initialize the OpenCode adapter.
        
        Attempts to initialize OpenCode if available and requested. If
        OpenCode is not available or initialization fails, falls back to
        internal execution.
        
        Args:
            working_dir: Directory for command execution. Defaults to current directory.
            use_opencode: Force OpenCode usage. True forces OpenCode, False forces
                internal, None auto-detects based on availability.
            active_commands: Dictionary to share with TerminalRouter for unified
                command tracking.
            watchdog: Optional watchdog for monitoring command execution.
        """
        self.working_dir = working_dir or Path.cwd()
        self.active_commands = active_commands or {}
        self.watchdog = watchdog
        
        # Determine if we should use OpenCode
        if use_opencode is None:
            self.use_opencode = OPENCODE_AVAILABLE
        else:
            self.use_opencode = use_opencode and OPENCODE_AVAILABLE
        
        # Initialize OpenCode router if available and requested
        self.opencode_router = None
        if self.use_opencode and opencode:
            try:
                # Initialize OpenCode router
                # Note: Actual API depends on OpenCode implementation
                # This is a placeholder that should be adapted to actual OpenCode API
                self.opencode_router = self._init_opencode_router()
            except Exception as e:
                # If OpenCode initialization fails, fall back to internal
                self.use_opencode = False
                self.opencode_router = None
    
    def _init_opencode_router(self):
        """
        Initialize OpenCode router.
        This method should be adapted to actual OpenCode API.
        """
        # Placeholder: Adapt to actual OpenCode API when available
        # Example structure (to be updated based on actual OpenCode API):
        # return opencode.TerminalRouter(working_dir=self.working_dir)
        return None
    
    def is_opencode_available(self) -> bool:
        """Check if OpenCode is available and being used."""
        return self.use_opencode and self.opencode_router is not None
    
    async def execute_command(
        self,
        command: str,
        args: Optional[list] = None,
        timeout: Optional[float] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Execute a terminal command.
        Uses OpenCode if available, otherwise falls back to internal implementation.
        
        Args:
            command: Command to execute
            args: Command arguments
            timeout: Command timeout in seconds
            stream: Whether to stream output
            
        Returns:
            Dict with 'stdout', 'stderr', 'returncode', 'command_id', 'backend'
        """
        if self.use_opencode and self.opencode_router:
            return await self._execute_with_opencode(command, args, timeout, stream)
        else:
            return await self._execute_internal(command, args, timeout, stream)
    
    async def _execute_with_opencode(
        self,
        command: str,
        args: Optional[list],
        timeout: Optional[float],
        stream: bool
    ) -> Dict[str, Any]:
        """Execute a command using OpenCode router.
        
        This is a placeholder method that should be adapted to the actual
        OpenCode API when it becomes available. Currently falls back to
        internal execution.
        
        Args:
            command: Command name to execute.
            args: Optional command arguments.
            timeout: Optional timeout in seconds.
            stream: Whether to stream output.
        
        Returns:
            Dictionary with command execution results. Currently falls back
            to internal execution.
        """
        # Placeholder: Adapt to actual OpenCode API
        # Example structure (to be updated):
        # result = await self.opencode_router.execute(command, args, timeout=timeout, stream=stream)
        # return {
        #     "stdout": result.stdout,
        #     "stderr": result.stderr,
        #     "returncode": result.returncode,
        #     "command_id": result.command_id,
        #     "backend": "opencode"
        # }
        
        # For now, fall back to internal if OpenCode API is not yet known
        return await self._execute_internal(command, args, timeout, stream)
    
    async def _execute_internal(
        self,
        command: str,
        args: Optional[list],
        timeout: Optional[float],
        stream: bool
    ) -> Dict[str, Any]:
        """
        Execute command using internal implementation (fallback).
        """
        full_command = [command] + (args or [])
        command_id = f"cmd_{id(full_command)}"
        
        try:
            if stream:
                return await self._execute_streaming_internal(full_command, command_id, timeout)
            else:
                return await self._execute_buffered_internal(full_command, command_id, timeout)
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
            return {
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
                "command_id": command_id,
                "error": True,
                "backend": "internal"
            }
    
    async def _execute_buffered_internal(
        self,
        command: list,
        command_id: str,
        timeout: Optional[float]
    ) -> Dict[str, Any]:
        """Execute a command and collect all output before returning.
        
        Internal implementation for buffered execution. Runs the command
        and waits for completion, collecting all stdout and stderr.
        
        Args:
            command: List containing command and arguments.
            command_id: Unique identifier for this command.
            timeout: Optional timeout in seconds.
        
        Returns:
            Dictionary with stdout, stderr, returncode, command_id, and backend.
        """
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.working_dir)
        )
        
        # Track process in active_commands (same as original TerminalRouter)
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
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise
        finally:
            # Clean up from active_commands (same as original TerminalRouter)
            if command_id in self.active_commands:
                del self.active_commands[command_id]
    
    async def _execute_streaming_internal(
        self,
        command: list,
        command_id: str,
        timeout: Optional[float]
    ) -> Dict[str, Any]:
        """Execute a command and stream output in real-time.
        
        Internal implementation for streaming execution. Reads stdout and
        stderr as they're produced, but still collects them for the final
        result.
        
        Args:
            command: List containing command and arguments.
            command_id: Unique identifier for this command.
            timeout: Optional timeout in seconds.
        
        Returns:
            Dictionary with stdout, stderr, returncode, command_id, backend,
            and streamed=True flag.
        """
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.working_dir)
        )
        
        # Track process in active_commands (same as original TerminalRouter)
        self.active_commands[command_id] = process
        
        stdout_lines = []
        stderr_lines = []
        
        try:
            async def read_stream(stream, lines_list):
                if stream:
                    async for line in stream:
                        decoded = line.decode('utf-8', errors='replace')
                        lines_list.append(decoded)
            
            stdout_task = asyncio.create_task(
                read_stream(process.stdout, stdout_lines)
            )
            stderr_task = asyncio.create_task(
                read_stream(process.stderr, stderr_lines)
            )
            
            try:
                await asyncio.wait_for(
                    process.wait(),
                    timeout=timeout
                )
            except asyncio.TimeoutExpired:
                process.kill()
                await process.wait()
                raise
            
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
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise
        finally:
            # Clean up from active_commands (same as original TerminalRouter)
            if command_id in self.active_commands:
                del self.active_commands[command_id]
    
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
        if self.use_opencode and self.opencode_router:
            # Placeholder: Use OpenCode streaming if available
            # async for line in self.opencode_router.stream(command, args):
            #     yield line
            pass
        
        # Fall back to internal implementation
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


def get_opencode_status() -> Dict[str, Any]:
    """
    Get OpenCode availability status.
    
    Returns:
        Dict with 'available', 'version', 'in_use' status
    """
    return {
        "available": OPENCODE_AVAILABLE,
        "version": OPENCODE_VERSION,
        "module_loaded": opencode is not None
    }
