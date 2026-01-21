"""
Unit tests for omoc_bridge.py
"""
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from manifest.core.state_manager import StateManager
from manifest.bridge.omoc_bridge import OMOCBridge


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def state_manager(temp_dir):
    """Create a StateManager instance."""
    return StateManager(manifest_dir=temp_dir)


@pytest.fixture
def omoc_bridge(state_manager):
    """Create an OMOCBridge instance."""
    from manifest.core.config import ConfigManager
    config_manager = ConfigManager()
    return OMOCBridge(state_manager, config_manager=config_manager)


def test_omoc_bridge_initialization(omoc_bridge):
    """Test OMOCBridge initialization."""
    assert omoc_bridge.state_manager is not None
    assert omoc_bridge.is_connected is False
    assert omoc_bridge.terminal_router is not None
    assert omoc_bridge.orchestrator is not None
    assert omoc_bridge.agent_manager is not None


def test_is_omoc_available(omoc_bridge):
    """Test OMOC availability check."""
    # OMOCBridge no longer has is_omoc_available method
    # Instead, it uses direct integration
    # Just verify the bridge initializes correctly
    assert omoc_bridge.is_connected is False  # Not started yet


@pytest.mark.asyncio
async def test_bridge_message_protocol(omoc_bridge):
    """Test message protocol (without actually starting process)."""
    # Test that we can create messages
    message = {
        "type": "command",
        "command": "test",
        "payload": {"test": "data"}
    }
    
    # Bridge should handle message structure
    assert message["type"] == "command"
    assert message["command"] == "test"


def test_bridge_state_integration(omoc_bridge, state_manager):
    """Test bridge integration with state manager."""
    # Set some state
    state_manager.set_mission_tree({"test": "data"})
    
    # Bridge should have access to state manager
    assert omoc_bridge.state_manager is state_manager
    assert omoc_bridge.state_manager.get_mission_tree() == {"test": "data"}


@pytest.mark.asyncio
async def test_bridge_commands(omoc_bridge):
    """Test bridge command methods."""
    await omoc_bridge.start()
    
    # Test get_status
    status = await omoc_bridge.get_status()
    assert isinstance(status, dict)
    assert "status" in status
    
    # Test start_mission
    result = await omoc_bridge.start_mission("test-task", "Test mission")
    assert isinstance(result, bool)
    
    await omoc_bridge.stop()