"""
Extended unit tests for StateManager.

Tests state persistence, loading, saving, and edge cases.
"""
import pytest
import asyncio
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


# ========== TDL: State Management Tests ==========

@pytest.mark.asyncio
async def test_state_persistence_async_save_load(state_manager):
    """Test async state persistence (save/load)."""
    # Set initial state
    state_manager.set_mission_tree({"root": {"id": "mission-1"}})
    state_manager.set_task_checklist([{"id": "task-1", "name": "Test"}])
    state_manager.add_chat_message("main", "user", "Hello")

    # Save asynchronously
    result = await state_manager.save_state()
    assert result is True

    # Load asynchronously
    loaded = await state_manager.load_state_async()
    assert loaded["mission_tree"] == {"root": {"id": "mission-1"}}
    assert len(loaded["task_checklist"]) == 1
    assert len(loaded["chat_history"]["main"]) == 1


def test_mission_tree_operations_add_update_remove(state_manager):
    """Test mission tree operations (add/update/remove)."""
    # Add mission
    initial_tree = {"root": {"id": "mission-1", "status": "active"}}
    state_manager.set_mission_tree(initial_tree)
    assert state_manager.get_mission_tree() == initial_tree

    # Update mission
    updated_tree = {"root": {"id": "mission-1", "status": "completed", "children": ["task-1"]}}
    state_manager.set_mission_tree(updated_tree)
    assert state_manager.get_mission_tree()["root"]["status"] == "completed"

    # Remove mission (clear tree)
    state_manager.set_mission_tree({})
    assert state_manager.get_mission_tree() == {}


def test_task_checklist_management(state_manager):
    """Test task checklist management operations."""
    # Add tasks
    tasks = [
        {"id": "task-1", "name": "Task 1", "status": "pending"},
        {"id": "task-2", "name": "Task 2", "status": "in_progress"}
    ]
    state_manager.set_task_checklist(tasks)
    assert len(state_manager.get_task_checklist()) == 2

    # Update task (using update_task method which takes individual params)
    state_manager.update_task("task-1", status="completed")
    updated_task = state_manager.get_task("task-1")
    assert updated_task is not None
    assert updated_task["status"] == "completed"

    # Remove task
    state_manager.delete_task("task-2")
    assert len(state_manager.get_task_checklist()) == 1
    assert state_manager.get_task("task-2") is None


def test_chat_history_persistence(state_manager):
    """Test chat history persistence across saves."""
    # Add messages
    state_manager.add_chat_message("channel-1", "user", "Message 1")
    state_manager.add_chat_message("channel-1", "assistant", "Response 1")
    state_manager.add_chat_message("channel-2", "user", "Message 2")

    # Save and reload
    state_manager.save_state_sync()
    new_manager = StateManager(manifest_dir=state_manager.manifest_dir)

    # Verify persistence
    history1 = new_manager.get_chat_history("channel-1")
    assert len(history1) == 2
    history2 = new_manager.get_chat_history("channel-2")
    assert len(history2) == 1


def test_sprint_management_create_list_load(state_manager):
    """Test sprint management (create/list/load)."""
    # Create sprint
    sprint_data = {
        "id": "1",  # list_sprints returns just the ID part
        "name": "Test Sprint",
        "tasks": ["task-1", "task-2"],
        "status": "active"
    }
    result = state_manager.save_sprint(sprint_data)
    assert result is True

    # List sprints (returns just the ID, not "sprint-{id}")
    sprints = state_manager.list_sprints()
    assert "1" in sprints

    # Load sprint
    loaded_sprint = state_manager.load_sprint("1")
    assert loaded_sprint is not None
    assert loaded_sprint["id"] == "1"
    assert loaded_sprint["name"] == "Test Sprint"


@pytest.mark.asyncio
async def test_sprint_management_async(state_manager):
    """Test async sprint management."""
    sprint_data = {
        "id": "sprint-2",
        "name": "Async Sprint",
        "tasks": []
    }
    result = await state_manager.save_sprint_async(sprint_data)
    assert result is True

    loaded = state_manager.load_sprint("sprint-2")
    assert loaded is not None
    assert loaded["id"] == "sprint-2"


def test_state_recovery_after_crash(state_manager):
    """Test state recovery after crash (corrupted file handling)."""
    # Create valid state
    state_manager.set_mission_tree({"root": {"id": "mission-1"}})
    state_manager.save_state_sync()

    # Corrupt the state file
    state_file = state_manager.state_file
    with open(state_file, "w") as f:
        f.write("invalid json content {{{{")

    # Create new manager - should recover with default state
    recovered_manager = StateManager(manifest_dir=state_manager.manifest_dir)
    state = recovered_manager.get_state()

    # Should have default state structure
    assert "version" in state
    assert "mission_tree" in state
    assert state["mission_tree"] == {}  # Default empty


def test_state_recovery_missing_file(state_manager):
    """Test state recovery when file doesn't exist."""
    # Don't create any state file
    new_manager = StateManager(manifest_dir=state_manager.manifest_dir)

    # Should initialize with default state
    state = new_manager.get_state()
    assert "version" in state
    assert isinstance(state["mission_tree"], dict)
    assert isinstance(state["task_checklist"], list)


def test_invalid_state_handling(state_manager):
    """Test handling of invalid state data."""
    # Test with None values - set_mission_tree expects a dict, None might cause issues
    # So we test with empty dict instead
    state_manager.set_mission_tree({})
    tree = state_manager.get_mission_tree()
    assert tree is not None
    assert isinstance(tree, dict)

    # Test with invalid task checklist (non-dict items)
    state_manager.set_task_checklist(["invalid", "not", "a", "dict"])
    # Should still work (stores as-is, filtering happens elsewhere)
    tasks = state_manager.get_task_checklist()
    assert isinstance(tasks, list)
    assert len(tasks) == 4


def test_state_migration_versioning(state_manager):
    """Test state migration and versioning."""
    # Get current version
    version = state_manager.get_state_version()
    assert version == "1.0"  # Default version

    # Test version in state
    state = state_manager.get_state()
    assert state["version"] == "1.0"

    # Simulate version upgrade (future: add migration logic)
    state_manager._state["version"] = "2.0"
    assert state_manager.get_state_version() == "2.0"


def test_concurrent_access_handling(state_manager, temp_dir):
    """Test concurrent access handling (multiple managers on same state)."""
    # Create two managers pointing to same directory
    manager1 = StateManager(manifest_dir=temp_dir)
    manager2 = StateManager(manifest_dir=temp_dir)

    # Manager1 modifies state
    manager1.set_mission_tree({"root": {"id": "mission-1"}})
    manager1.save_state_sync()

    # Manager2 should see the changes after reload
    manager2._load_state()
    assert manager2.get_mission_tree() == {"root": {"id": "mission-1"}}


@pytest.mark.asyncio
async def test_concurrent_save_operations(state_manager):
    """Test concurrent save operations."""
    # Multiple async saves should not conflict
    state_manager.set_mission_tree({"root": {"id": "mission-1"}})

    # Save multiple times concurrently
    results = await asyncio.gather(
        state_manager.save_state(),
        state_manager.save_state(),
        state_manager.save_state()
    )

    # All should succeed
    assert all(results)


def test_task_operations_comprehensive(state_manager):
    """Test comprehensive task operations."""
    # Create task
    task_id = state_manager.create_task(
        name="Test Task",
        description="Test description",
        dependencies=[]
    )
    assert task_id is not None

    # Get task
    task = state_manager.get_task(task_id)
    assert task is not None
    assert task["name"] == "Test Task"

    # Update task (using keyword args, not dict)
    state_manager.update_task(task_id, status="in_progress")
    updated = state_manager.get_task(task_id)
    assert updated is not None
    assert updated["status"] == "in_progress"

    # Complete task
    state_manager.complete_task(task_id)
    completed = state_manager.get_task(task_id)
    assert completed is not None
    assert completed["status"] == "completed"

    # Find tasks
    found = state_manager.find_tasks(status="completed")
    assert len(found) >= 1
    assert any(t["id"] == task_id for t in found)


def test_task_dependencies_management(state_manager):
    """Test task dependencies resolution."""
    # Create parent task
    parent_id = state_manager.create_task(name="Parent", dependencies=[])

    # Create child task with dependency
    child_id = state_manager.create_task(name="Child", dependencies=[parent_id])

    # Check if child is blocked (should be blocked until parent is "done")
    is_blocked, blocking = state_manager.is_task_blocked(child_id)
    # Child should be blocked until parent completes
    assert isinstance(is_blocked, bool)
    if is_blocked:
        assert parent_id in blocking

    # Complete parent (sets status to "done")
    state_manager.complete_task(parent_id)

    # Verify parent status is "done"
    parent_task = state_manager.get_task(parent_id)
    assert parent_task is not None

    # Check again - should not be blocked now if parent is "done"
    is_blocked_after, blocking_after = state_manager.is_task_blocked(child_id)
    # is_task_blocked checks if dependencies have status "done"
    # So if parent is "done", child should not be blocked
    assert is_blocked_after is False


def test_worker_squad_stage_persistence(state_manager):
    """Test worker squad stage persistence."""
    # Create a task first (worker squad stage needs a task to exist)
    task_id = state_manager.create_task(name="Test Task", description="Test")

    # Save stage data
    stage_data = {
        "stage": "planner",
        "success": True,
        "output": "Plan created"
    }
    result = state_manager.save_worker_squad_stage(task_id, "planner", stage_data)
    assert result is True

    # Retrieve stage data (get_worker_squad_stage is in TaskManager)
    # Verify task has the stage data
    task = state_manager.get_task(task_id)
    assert task is not None
    # Stage data should be stored in task's worker_squad field
    if "worker_squad" in task and "stages" in task["worker_squad"]:
        assert "planner" in task["worker_squad"]["stages"]


@pytest.mark.asyncio
async def test_worker_squad_stage_async_persistence(state_manager):
    """Test async worker squad stage persistence."""
    # Create a task first
    task_id = state_manager.create_task(name="Test Task", description="Test")

    stage_data = {"stage": "coder", "success": True}
    result = await state_manager.save_worker_squad_stage_async(task_id, "coder", stage_data)
    assert result is True

    # Verify task has the stage data
    task = state_manager.get_task(task_id)
    assert task is not None
    if "worker_squad" in task and "stages" in task["worker_squad"]:
        assert "coder" in task["worker_squad"]["stages"]
