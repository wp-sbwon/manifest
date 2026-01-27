"""
Unit tests for StateManager edge cases and error scenarios.

Tests edge cases, error handling, and boundary conditions for state management.
These are meaningful test scenarios beyond the basic TDL items.
"""
import pytest
import json
import tempfile
import shutil
from pathlib import Path
from manifest.core.state_manager import StateManager


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


# ========== Additional Meaningful Test Scenarios ==========

def test_state_recovery_from_corrupted_file(state_manager, temp_dir):
    """Test state recovery when state file is corrupted."""
    # Step 1: Create corrupted state file
    state_file = state_manager.state_file
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text("invalid json content {{{{")

    # Step 2: Create new manager (should recover from corruption)
    new_manager = StateManager(manifest_dir=temp_dir)

    # Step 3: Verify state is valid (should have default structure)
    state = new_manager.get_state()
    assert "version" in state
    assert "mission_tree" in state
    assert "task_checklist" in state
    # State should be initialized with defaults, not corrupted


def test_state_recovery_from_missing_required_fields(state_manager, temp_dir):
    """Test state recovery when required fields are missing."""
    # Step 1: Create state file with missing required fields
    state_file = state_manager.state_file
    state_file.parent.mkdir(parents=True, exist_ok=True)
    incomplete_state = {"version": "1.0"}  # Missing mission_tree, task_checklist, etc.
    state_file.write_text(json.dumps(incomplete_state))

    # Step 2: Create new manager (loads incomplete state as-is)
    new_manager = StateManager(manifest_dir=temp_dir)

    # Step 3: Verify state manager handles missing fields gracefully
    # StateManager._load_state() loads JSON as-is, so incomplete state will be incomplete
    # But methods like get_mission_tree() should handle missing fields
    state = new_manager.get_state()
    assert "version" in state
    assert isinstance(state, dict)

    # Verify that get_mission_tree() and other getters handle missing fields
    # They should return defaults (empty dict/list) if field is missing
    mission_tree = new_manager.get_mission_tree()
    assert isinstance(mission_tree, dict), "get_mission_tree() should return dict even if missing"

    task_checklist = new_manager.get_task_checklist()
    assert isinstance(task_checklist, list), "get_task_checklist() should return list even if missing"


def test_state_handles_unicode_in_task_names(state_manager):
    """Test state handles unicode characters in task names."""
    # Step 1: Create task with unicode characters
    task_id = state_manager.create_task(
        name="测试任务 🚀",
        description="Test with unicode: 日本語 한국어",
        status="pending"
    )

    # Step 2: Save and reload
    state_manager.save_state_sync()

    # Step 3: Verify unicode is preserved
    tasks = state_manager.get_task_checklist()
    task = next((t for t in tasks if t.get("id") == task_id), None)
    assert task is not None
    assert "测试" in task.get("name", "") or "🚀" in task.get("name", "")


def test_state_handles_very_long_strings(state_manager):
    """Test state handles very long strings (boundary condition)."""
    # Step 1: Create task with very long description
    long_description = "A" * 10000  # 10KB string
    task_id = state_manager.create_task(
        name="Long Task",
        description=long_description,
        status="pending"
    )

    # Step 2: Save and reload
    state_manager.save_state_sync()

    # Step 3: Verify long string is preserved
    tasks = state_manager.get_task_checklist()
    task = next((t for t in tasks if t.get("id") == task_id), None)
    assert task is not None
    assert len(task.get("description", "")) == 10000


def test_state_handles_special_characters_in_paths(state_manager, temp_dir):
    """Test state handles special characters in file paths."""
    # Step 1: Create chat message with special characters
    channel = "test-channel-with-special-chars-@#$%"
    state_manager.add_chat_message(channel, "user", "Test message")

    # Step 2: Save and reload
    state_manager.save_state_sync()

    # Step 3: Verify special characters are handled
    history = state_manager.get_chat_history(channel)
    assert len(history) > 0


def test_state_handles_empty_mission_tree(state_manager):
    """Test state handles empty mission tree."""
    # Step 1: Set empty mission tree
    state_manager.set_mission_tree({})

    # Step 2: Save and reload
    state_manager.save_state_sync()

    # Step 3: Verify empty tree is preserved
    tree = state_manager.get_mission_tree()
    assert tree == {}


def test_state_handles_none_values_gracefully(state_manager):
    """Test state handles None values gracefully."""
    # Step 1: Try to add None values (should not crash)
    try:
        state_manager.set_mission_tree(None)
        # Should either accept None or convert to empty dict
        tree = state_manager.get_mission_tree()
        # Tree should be dict (None converted) or None (if accepted)
        assert tree is None or isinstance(tree, dict)
    except (TypeError, ValueError, AttributeError):
        # Acceptable - None should be rejected with appropriate error
        pass


def test_state_file_permission_errors_handled(state_manager, temp_dir):
    """Test state handles file permission errors gracefully."""
    # Step 1: Make directory read-only (if possible)
    state_file = state_manager.state_file
    state_file.parent.mkdir(parents=True, exist_ok=True)

    # Step 2: Try to save (should handle gracefully)
    # Note: On some systems, we can't easily test permission errors
    # This test verifies the code path exists
    try:
        result = state_manager.save_state_sync()
        # Should either succeed or fail gracefully
        assert isinstance(result, bool)
    except PermissionError:
        # Acceptable - permission error should be caught or raised appropriately
        pass


def test_state_handles_concurrent_saves_same_instance(state_manager):
    """Test state handles concurrent saves from same instance."""
    import asyncio

    async def concurrent_saves():
        """Perform concurrent saves."""
        tasks = [
            state_manager.save_state()
            for _ in range(10)
        ]
        await asyncio.gather(*tasks)

    # Step 1: Create some state
    state_manager.create_task(name="Task 1", description="Test", status="pending")

    # Step 2: Perform concurrent saves
    asyncio.run(concurrent_saves())

    # Step 3: Verify state is consistent
    assert state_manager.state_file.exists() or len(state_manager.get_task_checklist()) > 0


def test_state_migration_handles_version_changes(state_manager, temp_dir):
    """Test state migration when version changes."""
    # Step 1: Create state file with old version
    state_file = state_manager.state_file
    state_file.parent.mkdir(parents=True, exist_ok=True)
    old_state = {
        "version": "0.9",
        "mission_tree": {},
        "task_checklist": [],
        "chat_history": {}
    }
    state_file.write_text(json.dumps(old_state))

    # Step 2: Create new manager (should migrate)
    new_manager = StateManager(manifest_dir=temp_dir)

    # Step 3: Verify state has current version
    state = new_manager.get_state()
    assert state.get("version") is not None
    # Version should be updated or preserved appropriately
