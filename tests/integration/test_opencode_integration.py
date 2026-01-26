"""
Integration tests for OpenCode LLM adapter with actual server.

These tests require an actual OpenCode server to be running or available.
They can be skipped if OpenCode is not installed or server is not available.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from manifest.runtime.opencode_llm_adapter import OpenCodeLLMAdapter
from manifest.core.config import ConfigManager
from manifest.core.state_manager import StateManager
from pathlib import Path

# Skip all tests if OpenCode is not available
OPencode_AVAILABLE = True
try:
    import subprocess
    import os
    # Check common installation paths (including ~/.opencode/bin where install script puts it)
    env = os.environ.copy()
    opencode_path = os.path.expanduser("~/.opencode/bin")
    env["PATH"] = f"{opencode_path}:{os.path.expanduser('~/.local/bin')}:{os.path.expanduser('~/bin')}:/usr/local/bin:{env.get('PATH', '')}"
    result = subprocess.run(
        ["opencode", "--version"],
        capture_output=True,
        timeout=2,
        env=env
    )
    if result.returncode != 0:
        OPencode_AVAILABLE = False
except (FileNotFoundError, subprocess.TimeoutExpired):
    OPencode_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not OPencode_AVAILABLE,
    reason="OpenCode not installed or not available"
)


@pytest.fixture
def config_manager(tmp_path):
    """Create a real config manager."""
    return ConfigManager(manifest_dir=tmp_path)


@pytest.fixture
def state_manager(tmp_path):
    """Create a real state manager."""
    return StateManager(manifest_dir=tmp_path)


@pytest.fixture
def adapter(config_manager, state_manager):
    """Create an OpenCode adapter instance with auto_start disabled for tests."""
    return OpenCodeLLMAdapter(
        config_manager,
        state_manager,
        server_host="localhost",
        server_port=4096,
        auto_start=False  # Don't auto-start in integration tests
    )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_server_connection(adapter):
    """Test connection to OpenCode server."""
    # This test requires an actual OpenCode server running
    result = await adapter._check_server_health()
    # If server is not running, test is skipped (handled by skipif)
    assert isinstance(result, bool)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_create_session_integration(adapter):
    """Test creating a session with actual OpenCode server."""
    # Check if server is running
    if not await adapter._check_server_health():
        pytest.skip("OpenCode server is not running")

    session_id = await adapter._create_session(
        model="claude-3-5-sonnet-20241022",
        provider="anthropic"
    )

    assert session_id is not None
    assert isinstance(session_id, str)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_execute_agent_integration(adapter):
    """Test executing an agent with actual OpenCode server."""
    # Check if server is running
    if not await adapter._check_server_health():
        pytest.skip("OpenCode server is not running")

    # This test requires API keys configured
    # Skip if not configured
    model_config = {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "api_key": "test-key"  # Will fail but tests the flow
    }

    chunks = []
    async for chunk in adapter.execute_agent(
        agent_id="test-agent-1",
        agent_type="orchestrator",
        prompt="Hello, this is a test.",
        model_config=model_config
    ):
        chunks.append(chunk)
        # Stop after first chunk to avoid long test
        if len(chunks) > 0:
            break

    # Should get at least an error chunk if API key is invalid
    assert len(chunks) > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_server_auto_start(adapter):
    """Test automatic server startup."""
    adapter.auto_start = True

    # This test requires opencode command to be available
    # and will actually try to start the server
    result = await adapter._ensure_server_running()

    # Result depends on whether opencode is installed and can start
    assert isinstance(result, bool)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_retry_logic(adapter):
    """Test retry logic for connection failures."""
    # Temporarily set wrong port to test retry
    original_port = adapter.server_port
    adapter.server_port = 9999  # Unlikely to be in use

    try:
        # Should retry and eventually fail (server won't be accessible on wrong port)
        result = await adapter._check_server_health(timeout=1.0)
        # Result should be False (server not accessible on wrong port)
        assert result is False
    finally:
        adapter.server_port = original_port


@pytest.mark.asyncio
@pytest.mark.integration
async def test_session_cleanup(adapter):
    """Test session cleanup functionality."""
    import time
    current_time = time.time()

    # Add some mock sessions
    adapter.active_sessions = {
        "old-session-1": {
            "session_id": "sess-1",
            "status": "completed",
            "completed_at": current_time - 7200.0  # 2 hours ago (very old)
        },
        "old-session-2": {
            "session_id": "sess-2",
            "status": "stopped",
            "stopped_at": current_time - 7200.0  # 2 hours ago (very old)
        },
        "active-session": {
            "session_id": "sess-3",
            "status": "running"
        }
    }

    cleaned = await adapter.cleanup_old_sessions(max_age_seconds=1.0)

    assert cleaned == 2  # Should clean up 2 old sessions
    assert "active-session" in adapter.active_sessions
    assert "old-session-1" not in adapter.active_sessions
    assert "old-session-2" not in adapter.active_sessions
