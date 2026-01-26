"""
Unit tests for agent_bridge.py
"""
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from manifest.core.state_manager import StateManager
from manifest.bridge.agent_bridge import AgentBridge


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
def agent_bridge(state_manager):
    """Create an AgentBridge instance."""
    from manifest.core.config import ConfigManager
    config_manager = ConfigManager(manifest_dir=state_manager.manifest_dir)
    return AgentBridge(state_manager, config_manager=config_manager)


def test_agent_bridge_initialization(agent_bridge):
    """Test AgentBridge initialization."""
    assert agent_bridge.state_manager is not None
    assert agent_bridge.is_connected is False
    assert agent_bridge.terminal_router is not None
    assert agent_bridge.orchestrator is not None
    assert agent_bridge.agent_manager is not None


def test_agent_bridge_availability(agent_bridge):
    """Test agent bridge availability check."""
    # This test verifies the bridge is initialized but not started
    assert agent_bridge.is_connected is False  # Not started yet


@pytest.mark.asyncio
async def test_bridge_message_protocol(agent_bridge):
    """Test bridge message protocol."""
    await agent_bridge.start()
    assert agent_bridge.is_connected is True
    await agent_bridge.stop()


def test_bridge_state_integration(agent_bridge, state_manager):
    """Test bridge state integration."""
    state_manager.set_mission_tree({"test": "data"})
    assert agent_bridge.state_manager is state_manager
    assert agent_bridge.state_manager.get_mission_tree() == {"test": "data"}


@pytest.mark.asyncio
async def test_bridge_commands(agent_bridge):
    """Test bridge commands."""
    await agent_bridge.start()
    assert agent_bridge.is_connected is True

    status = await agent_bridge.get_status()
    assert status is not None

    result = await agent_bridge.start_mission("test-task", "Test mission")
    assert result is True

    await agent_bridge.stop()
