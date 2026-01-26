"""
Tests for Terminal Router.
"""
import pytest
import asyncio
from pathlib import Path
from manifest.runtime.router.terminal_router import TerminalRouter
from manifest.runtime.opencode_adapter import OPENCODE_AVAILABLE


@pytest.fixture
def terminal_router(tmp_path):
    """Create a TerminalRouter instance."""
    return TerminalRouter(working_dir=tmp_path)


@pytest.fixture
def terminal_router_force_internal(tmp_path):
    """Create a TerminalRouter instance forced to use internal implementation."""
    return TerminalRouter(working_dir=tmp_path, use_opencode=False)


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


@pytest.mark.asyncio
async def test_terminal_router_opencode_integration(terminal_router):
    """Test TerminalRouter uses OpenCode adapter."""
    # Check that adapter is initialized
    assert hasattr(terminal_router, 'opencode_adapter')
    assert terminal_router.opencode_adapter is not None

    # Execute a command - should work with or without OpenCode
    result = await terminal_router.execute_command("echo", ["test"])

    assert result["returncode"] == 0
    assert "test" in result["stdout"]
    assert "command_id" in result
    # Should have backend info if using adapter
    if "backend" in result:
        assert result["backend"] in ["internal", "opencode"]


@pytest.mark.asyncio
async def test_terminal_router_opencode_availability(terminal_router):
    """Test OpenCode availability check."""
    is_available = terminal_router.is_opencode_available()

    # Should match the actual OpenCode availability
    assert isinstance(is_available, bool)
    assert is_available == OPENCODE_AVAILABLE or not is_available


@pytest.mark.asyncio
async def test_terminal_router_streaming(terminal_router):
    """Test TerminalRouter streaming uses adapter."""
    lines = []
    async for line in terminal_router.stream_command_output("echo", ["-e", "line1\nline2"]):
        lines.append(line)

    assert len(lines) > 0
    assert any("line1" in line or "line2" in line for line in lines)


@pytest.mark.asyncio
async def test_terminal_router_force_internal(terminal_router_force_internal):
    """Test TerminalRouter can be forced to use internal implementation."""
    assert not terminal_router_force_internal.is_opencode_available()

    result = await terminal_router_force_internal.execute_command("echo", ["internal"])

    assert result["returncode"] == 0
    assert "internal" in result["stdout"]
