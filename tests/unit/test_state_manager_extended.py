"""
Extended unit tests for StateManager.

Tests state persistence, loading, saving, and edge cases.
"""
import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from manifest.core.state_manager import StateManager


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing."""
    return tmp_path


@pytest.fixture
def state_manager(temp_dir):
    """Create a StateManager instance."""
    return StateManager(manifest_dir=temp_dir)


def test_state_manager_initialization(state_manager, temp_dir):
    """Test StateManager initialization."""
    assert state_manager.manifest_dir == temp_dir
    assert state_manager is not None


def test_get_task_checklist(state_manager):
    """Test getting task checklist."""
    tasks = state_manager.get_task_checklist()
    assert isinstance(tasks, list)


def test_set_task_checklist(state_manager):
    """Test setting task checklist."""
    tasks = [{"id": "task-1", "name": "Test"}]
    state_manager.set_task_checklist(tasks)
    
    retrieved = state_manager.get_task_checklist()
    assert len(retrieved) >= 1


def test_get_chat_history(state_manager):
    """Test getting chat history."""
    history = state_manager.get_chat_history("main")
    assert isinstance(history, list)


def test_add_chat_message(state_manager):
    """Test adding a chat message."""
    state_manager.add_chat_message("main", "user", "Hello")
    
    history = state_manager.get_chat_history("main")
    assert len(history) >= 1


@pytest.mark.asyncio
async def test_save_state(state_manager):
    """Test saving state."""
    result = await state_manager.save_state()
    assert result is True or result is None


@pytest.mark.asyncio
async def test_load_state_async(state_manager):
    """Test loading state asynchronously."""
    # Save first
    await state_manager.save_state()
    
    # Load
    result = await state_manager.load_state_async()
    assert isinstance(result, dict)


def test_get_mission_tree(state_manager):
    """Test getting mission tree."""
    tree = state_manager.get_mission_tree()
    assert isinstance(tree, dict)


def test_set_mission_tree(state_manager):
    """Test setting mission tree."""
    tree = {"root": {"children": []}}
    state_manager.set_mission_tree(tree)
    
    retrieved = state_manager.get_mission_tree()
    assert retrieved == tree


def test_get_last_action(state_manager):
    """Test getting last action."""
    action = state_manager.get_last_action()
    assert action is None or isinstance(action, str)


def test_set_last_action(state_manager):
    """Test setting last action."""
    state_manager.set_last_action("Test action")
    
    action = state_manager.get_last_action()
    assert action == "Test action"
