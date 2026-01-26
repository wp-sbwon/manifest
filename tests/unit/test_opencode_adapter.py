"""
Tests for OpenCode adapter integration.
"""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from manifest.runtime.opencode_adapter import OpenCodeAdapter, get_opencode_status, OPENCODE_AVAILABLE


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for tests."""
    return tmp_path


@pytest.mark.asyncio
async def test_opencode_adapter_without_opencode(temp_dir):
    """Test adapter falls back to internal implementation when OpenCode is not available."""
    adapter = OpenCodeAdapter(working_dir=temp_dir, use_opencode=False)

    assert not adapter.is_opencode_available()

    # Test command execution
    result = await adapter.execute_command("echo", ["hello"], timeout=5.0)

    assert result["returncode"] == 0
    assert "hello" in result["stdout"]
    assert result["backend"] == "internal"


@pytest.mark.asyncio
async def test_opencode_adapter_auto_detect(temp_dir):
    """Test adapter auto-detects OpenCode availability."""
    adapter = OpenCodeAdapter(working_dir=temp_dir, use_opencode=None)

    # Should match OPENCODE_AVAILABLE
    assert adapter.use_opencode == OPENCODE_AVAILABLE


@pytest.mark.asyncio
async def test_opencode_adapter_force_internal(temp_dir):
    """Test adapter can be forced to use internal implementation."""
    adapter = OpenCodeAdapter(working_dir=temp_dir, use_opencode=False)

    assert not adapter.is_opencode_available()

    result = await adapter.execute_command("python", ["--version"], timeout=5.0)

    assert result["returncode"] == 0
    assert "Python" in result["stdout"]
    assert result["backend"] == "internal"


@pytest.mark.asyncio
async def test_opencode_adapter_streaming(temp_dir):
    """Test adapter streaming output."""
    adapter = OpenCodeAdapter(working_dir=temp_dir, use_opencode=False)

    lines = []
    async for line in adapter.stream_command_output("echo", ["-e", "line1\nline2"]):
        lines.append(line)

    assert len(lines) > 0
    assert any("line1" in line or "line2" in line for line in lines)


@pytest.mark.asyncio
async def test_opencode_adapter_timeout(temp_dir):
    """Test adapter handles timeouts correctly."""
    adapter = OpenCodeAdapter(working_dir=temp_dir, use_opencode=False)

    # This should timeout quickly
    result = await adapter.execute_command(
        "sleep",
        ["10"],  # Sleep for 10 seconds
        timeout=0.1  # But timeout after 0.1 seconds
    )

    assert result["timeout"] is True
    assert result["returncode"] == -1
    assert "timed out" in result["stderr"]


@pytest.mark.asyncio
async def test_opencode_adapter_error_handling(temp_dir):
    """Test adapter handles command errors correctly."""
    adapter = OpenCodeAdapter(working_dir=temp_dir, use_opencode=False)

    # Non-existent command
    result = await adapter.execute_command("nonexistent_command_xyz", timeout=5.0)

    assert result["returncode"] != 0
    assert result["backend"] == "internal"


@pytest.mark.asyncio
async def test_opencode_adapter_with_mock_opencode(temp_dir):
    """Test adapter with mocked OpenCode."""
    with patch('manifest.runtime.opencode_adapter.opencode', create=True):
        with patch('manifest.runtime.opencode_adapter.OPENCODE_AVAILABLE', True):
            # Re-import to get the mocked value
            import importlib
            import manifest.runtime.opencode_adapter
            importlib.reload(manifest.runtime.opencode_adapter)

            adapter = manifest.runtime.opencode_adapter.OpenCodeAdapter(
                working_dir=temp_dir,
                use_opencode=True
            )

            # Should attempt to use OpenCode but fall back if initialization fails
            # (since we're just mocking the module, not the actual router)
            result = await adapter.execute_command("echo", ["test"], timeout=5.0)

            # Should still work (fallback)
            assert result["returncode"] == 0 or result.get("error") is not None


def test_get_opencode_status():
    """Test OpenCode status detection."""
    status = get_opencode_status()

    assert "available" in status
    assert "version" in status
    assert "module_loaded" in status
    assert isinstance(status["available"], bool)
    assert isinstance(status["module_loaded"], bool)


@pytest.mark.asyncio
async def test_opencode_adapter_working_dir(temp_dir):
    """Test adapter respects working directory."""
    # Create a test file in temp_dir
    test_file = temp_dir / "test_file.txt"
    test_file.write_text("test content")

    adapter = OpenCodeAdapter(working_dir=temp_dir, use_opencode=False)

    # List files in working directory
    result = await adapter.execute_command("ls", ["test_file.txt"], timeout=5.0)

    assert result["returncode"] == 0
    assert "test_file.txt" in result["stdout"]


@pytest.mark.asyncio
async def test_opencode_adapter_streaming_mode(temp_dir):
    """Test adapter streaming mode."""
    adapter = OpenCodeAdapter(working_dir=temp_dir, use_opencode=False)

    result = await adapter.execute_command(
        "echo",
        ["-e", "line1\nline2\nline3"],
        timeout=5.0,
        stream=True
    )

    assert result["returncode"] == 0
    assert result.get("streamed") is True
    assert "line1" in result["stdout"] or "line2" in result["stdout"]
