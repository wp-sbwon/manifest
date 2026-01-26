"""
Unit tests for TaskManager.

Tests task creation, updates, queries, and lifecycle management.
"""
import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from manifest.core.task_manager import TaskManager
from manifest.core.state_manager import StateManager


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing."""
    return tmp_path


@pytest.fixture
def state_manager(temp_dir):
    """Create a StateManager instance."""
    return StateManager(manifest_dir=temp_dir)


@pytest.fixture
def task_manager(state_manager):
    """Create a TaskManager instance."""
    return TaskManager(state_manager=state_manager)


def test_task_manager_initialization(task_manager, state_manager):
    """Test TaskManager initialization."""
    assert task_manager.state_manager == state_manager
    assert task_manager is not None


def test_create_task(task_manager):
    """Test creating a new task."""
    task_id = task_manager.create_task(
        name="Test Task",
        description="Test description",
        stage="planning",
        status="pending"
    )

    assert task_id is not None
    assert task_id.startswith("task-")

    # Verify task was created
    tasks = task_manager.state_manager.get_task_checklist()
    assert len(tasks) > 0
    assert any(t.get("id") == task_id for t in tasks)


def test_create_task_with_sprint(task_manager):
    """Test creating task with sprint ID."""
    task_id = task_manager.create_task(
        name="Sprint Task",
        sprint_id="sprint-1"
    )

    tasks = task_manager.state_manager.get_task_checklist()
    task = next((t for t in tasks if t.get("id") == task_id), None)
    assert task is not None
    assert task.get("sprint_id") == "sprint-1"


def test_create_task_with_dependencies(task_manager):
    """Test creating task with dependencies."""
    # Create first task
    task1_id = task_manager.create_task(name="Task 1")

    # Create second task with dependency
    task2_id = task_manager.create_task(
        name="Task 2",
        dependencies=[task1_id]
    )

    tasks = task_manager.state_manager.get_task_checklist()
    task2 = next((t for t in tasks if t.get("id") == task2_id), None)
    assert task2 is not None
    assert task1_id in task2.get("dependencies", [])


def test_update_task(task_manager):
    """Test updating a task."""
    # Create task
    task_id = task_manager.create_task(name="Original Name")

    # Update task
    result = task_manager.update_task(
        task_id=task_id,
        name="Updated Name",
        status="in_progress"
    )

    assert result is True

    # Verify update
    task = task_manager.get_task(task_id)
    assert task is not None
    assert task.get("name") == "Updated Name"
    assert task.get("status") == "in_progress"


def test_update_task_not_found(task_manager):
    """Test updating non-existent task."""
    result = task_manager.update_task(
        task_id="nonexistent",
        name="Test"
    )
    assert result is False


def test_get_task(task_manager):
    """Test getting a task by ID."""
    task_id = task_manager.create_task(name="Test Task")

    task = task_manager.get_task(task_id)
    assert task is not None
    assert task.get("id") == task_id
    assert task.get("name") == "Test Task"


def test_get_task_not_found(task_manager):
    """Test getting non-existent task."""
    task = task_manager.get_task("nonexistent")
    assert task is None


def test_delete_task(task_manager):
    """Test deleting a task."""
    task_id = task_manager.create_task(name="To Delete")

    result = task_manager.delete_task(task_id)
    assert result is True

    # Verify deletion
    task = task_manager.get_task(task_id)
    assert task is None


def test_delete_task_not_found(task_manager):
    """Test deleting non-existent task."""
    result = task_manager.delete_task("nonexistent")
    assert result is False


def test_get_all_tasks(task_manager):
    """Test getting all tasks via state manager."""
    task_manager.create_task(name="Task 1")
    task_manager.create_task(name="Task 2")

    tasks = task_manager.state_manager.get_task_checklist()
    assert len(tasks) >= 2


def test_is_task_blocked(task_manager):
    """Test checking if task is blocked."""
    task1_id = task_manager.create_task(name="Task 1")
    task2_id = task_manager.create_task(
        name="Task 2",
        dependencies=[task1_id]
    )

    is_blocked, blocking = task_manager.is_task_blocked(task2_id)
    assert isinstance(is_blocked, bool)
    assert isinstance(blocking, list)


def test_get_tasks_by_status(task_manager):
    """Test getting tasks filtered by status."""
    task_manager.create_task(name="Pending", status="pending")
    task_manager.create_task(name="In Progress", status="in_progress")

    tasks = task_manager.state_manager.get_task_checklist()
    pending_tasks = [t for t in tasks if t.get("status") == "pending"]
    assert len(pending_tasks) >= 1


def test_get_tasks_by_sprint(task_manager):
    """Test getting tasks filtered by sprint."""
    task_manager.create_task(name="Sprint Task", sprint_id="sprint-1")
    task_manager.create_task(name="No Sprint")

    tasks = task_manager.state_manager.get_task_checklist()
    sprint_tasks = [t for t in tasks if t.get("sprint_id") == "sprint-1"]
    assert len(sprint_tasks) >= 1


def test_task_dependencies_in_task(task_manager):
    """Test task dependencies stored in task."""
    task1_id = task_manager.create_task(name="Task 1")
    task2_id = task_manager.create_task(
        name="Task 2",
        dependencies=[task1_id]
    )

    task2 = task_manager.get_task(task2_id)
    assert task2 is not None
    assert task1_id in task2.get("dependencies", [])


def test_update_task_with_status(task_manager):
    """Test updating task with status change."""
    task_id = task_manager.create_task(name="Test", status="pending")

    result = task_manager.update_task(
        task_id=task_id,
        status="in_progress"
    )
    assert result is True

    task = task_manager.get_task(task_id)
    assert task.get("status") == "in_progress"


def test_update_task_with_stage(task_manager):
    """Test updating task with stage change."""
    task_id = task_manager.create_task(name="Test", stage="planning")

    result = task_manager.update_task(
        task_id=task_id,
        stage="implementation"
    )
    assert result is True

    task = task_manager.get_task(task_id)
    assert task.get("stage") == "implementation"
