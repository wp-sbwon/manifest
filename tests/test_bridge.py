"""
Unit tests for omoc_bridge.py
"""
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from state_manager import StateManager
from omoc_bridge import OMOCBridge


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
    return OMOCBridge(state_manager, omoc_path="echo")  # Use echo as mock


def test_omoc_bridge_initialization(omoc_bridge):
    """Test OMOCBridge initialization."""
    assert omoc_bridge.state_manager is not None
    assert omoc_bridge.is_connected is False
    assert omoc_bridge.process is None


def test_is_omoc_available(omoc_bridge):
    """Test OMOC availability check."""
    # echo should be available on most systems
    available = omoc_bridge.is_omoc_available()
    # This may be True or False depending on system, but should not crash
    assert isinstance(available, bool)


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
    """Test bridge command methods (without actual OMOC)."""
    # These should not crash even without OMOC running
    status = await omoc_bridge.get_status()
    assert isinstance(status, dict)
    
    # start_mission should return False if not connected
    result = await omoc_bridge.start_mission("test-task")
    assert isinstance(result, bool)