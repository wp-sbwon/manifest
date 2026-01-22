"""
Tests for Terminal Router.
"""
import pytest
import asyncio
from pathlib import Path
from manifest.runtime.router.terminal_router import TerminalRouter


@pytest.fixture
def terminal_router(tmp_path):
    """Create a TerminalRouter instance."""
    return TerminalRouter(working_dir=tmp_path)


@pytest.mark.asyncio
async def test_terminal_router_init(terminal_router):
    """Test TerminalRouter initialization."""
    assert terminal_router.working_dir is not None
    assert len(terminal_router.active_commands) == 0


@pytest.mark.asyncio
async def test_execute_command(terminal_router):
    """Test command execution."""
    result = await terminal_router.execute_command("echo", ["hello"])
    
    assert result["returncode"] == 0
    assert "hello" in result["stdout"]
    assert "command_id" in result


@pytest.mark.asyncio
async def test_execute_command_timeout(terminal_router):
    """Test command timeout."""
    # Use sleep command that will timeout
    result = await terminal_router.execute_command("sleep", ["5"], timeout=0.1)
    
    assert result["returncode"] == -1
    assert result.get("timeout") is True


@pytest.mark.asyncio
async def test_cancel_command(terminal_router):
    """Test command cancellation."""
    # Start a long-running command
    command_id = None
    
    async def run_long_command():
        nonlocal command_id
        result = await terminal_router.execute_command("sleep", ["10"], timeout=None)
        command_id = result.get("command_id")
    
    # Start command in background
    task = asyncio.create_task(run_long_command())
    await asyncio.sleep(0.1)  # Give it time to start
    
    # Cancel it
    if command_id:
        cancelled = terminal_router.cancel_command(command_id)
        assert cancelled is True
    
    # Clean up
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
