"""
Unit tests for state_manager.py
"""
import pytest
import json
import tempfile
import shutil
from pathlib import Path
from state_manager import StateManager


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def state_manager(temp_dir):
    """Create a StateManager instance with temp directory."""
    return StateManager(manifest_dir=temp_dir)


def test_state_manager_initialization(state_manager):
    """Test StateManager initialization."""
    state = state_manager.get_state()
    assert "version" in state
    assert "mission_tree" in state
    assert "task_checklist" in state
    assert "chat_history" in state


def test_state_persistence(state_manager):
    """Test state save and load."""
    # Set some state
    state_manager.set_mission_tree({"task1": {"status": "pending"}})
    state_manager.set_task_checklist([{"id": "task1", "name": "Test Task"}])
    state_manager.add_chat_message("main", "user", "Hello")
    
    # Save
    assert state_manager.save_state_sync() is True
    
    # Create new manager and load
    new_manager = StateManager(manifest_dir=state_manager.manifest_dir)
    loaded_state = new_manager.get_state()
    
    assert loaded_state["mission_tree"] == {"task1": {"status": "pending"}}
    assert len(loaded_state["task_checklist"]) == 1
    assert len(loaded_state["chat_history"]["main"]) == 1


def test_chat_history(state_manager):
    """Test chat history management."""
    state_manager.add_chat_message("main", "user", "Hello")
    state_manager.add_chat_message("main", "assistant", "Hi there")
    state_manager.add_chat_message("squad-auth", "assistant", "Auth message")
    
    main_history = state_manager.get_chat_history("main")
    assert len(main_history) == 2
    
    squad_history = state_manager.get_chat_history("squad-auth")
    assert len(squad_history) == 1
    assert squad_history[0]["content"] == "Auth message"


def test_last_action(state_manager):
    """Test last action tracking."""
    state_manager.set_last_action("test_action")
    assert state_manager.get_last_action() == "test_action"
    
    prompt = state_manager.get_next_action_prompt()
    assert prompt == "Resuming from: test_action"


def test_clear_state(state_manager):
    """Test state clearing."""
    state_manager.set_mission_tree({"task1": {}})
    state_manager.clear_state()
    
    state = state_manager.get_state()
    assert state["mission_tree"] == {}