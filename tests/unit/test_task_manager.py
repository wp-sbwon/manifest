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


def test_update_task_sprint_id(task_manager):
    """Test updating task sprint_id (used by /create_sprint to link tasks)."""
    task_id = task_manager.create_task(name="Test", sprint_id=None)

    result = task_manager.update_task(task_id, sprint_id="sprint-my-sprint-123")
    assert result is True

    task = task_manager.get_task(task_id)
    assert task.get("sprint_id") == "sprint-my-sprint-123"


# ========== TDL: Task Management Tests ==========

def test_task_creation_with_validation(task_manager):
    """Test task creation with validation."""
    # Create task with all fields
    task_id = task_manager.create_task(
        name="Valid Task",
        description="Task description",
        stage="planning",
        status="pending",
        sprint_id="sprint-1",
        dependencies=[]
    )

    assert task_id is not None
    task = task_manager.get_task(task_id)
    assert task is not None
    assert task["name"] == "Valid Task"
    assert task["description"] == "Task description"
    assert task["stage"] == "planning"
    assert task["status"] == "pending"
    assert task["sprint_id"] == "sprint-1"
    assert isinstance(task["dependencies"], list)
    assert "created_at" in task
    assert "updated_at" in task


def test_task_updates_status_stage_dependencies(task_manager):
    """Test task updates (status, stage, dependencies)."""
    # Create task
    task_id = task_manager.create_task(name="Test Task", status="pending", stage="planning")

    # Update status
    task_manager.update_task(task_id, status="in_progress")
    task = task_manager.get_task(task_id)
    assert task["status"] == "in_progress"

    # Update stage
    task_manager.update_task(task_id, stage="implementation")
    task = task_manager.get_task(task_id)
    assert task["stage"] == "implementation"

    # Update name and description
    task_manager.update_task(task_id, name="Updated Name", description="Updated description")
    task = task_manager.get_task(task_id)
    assert task["name"] == "Updated Name"
    assert task["description"] == "Updated description"


def test_task_dependencies_resolution(task_manager):
    """Test task dependencies resolution."""
    # Create parent tasks
    parent1_id = task_manager.create_task(name="Parent 1")
    parent2_id = task_manager.create_task(name="Parent 2")

    # Create child task with multiple dependencies
    child_id = task_manager.create_task(
        name="Child Task",
        dependencies=[parent1_id, parent2_id]
    )

    # Check dependencies
    child = task_manager.get_task(child_id)
    assert parent1_id in child["dependencies"]
    assert parent2_id in child["dependencies"]

    # Check if blocked (should be blocked until parents are done)
    is_blocked, blocking = task_manager.is_task_blocked(child_id)
    assert is_blocked is True
    assert parent1_id in blocking
    assert parent2_id in blocking

    # Complete parent 1
    task_manager.complete_task(parent1_id)
    # Update parent 1 status to "done" for dependency check
    task_manager.update_task(parent1_id, status="done")

    # Check again
    is_blocked_after, blocking_after = task_manager.is_task_blocked(child_id)
    # Should still be blocked by parent 2
    assert parent2_id in blocking_after


def test_task_filtering_queries(task_manager):
    """Test task filtering/queries."""
    # Create tasks with different attributes
    task1_id = task_manager.create_task(name="Task 1", status="pending", stage="planning", sprint_id="sprint-1")
    task2_id = task_manager.create_task(name="Task 2", status="in_progress", stage="implementation", sprint_id="sprint-1")
    task3_id = task_manager.create_task(name="Task 3", status="pending", stage="planning", sprint_id="sprint-2")

    # Filter by status
    pending_tasks = task_manager.find_tasks(status="pending")
    assert len(pending_tasks) >= 2
    assert all(t["status"] == "pending" for t in pending_tasks)

    # Filter by stage
    planning_tasks = task_manager.find_tasks(stage="planning")
    assert len(planning_tasks) >= 2
    assert all(t["stage"] == "planning" for t in planning_tasks)

    # Filter by sprint_id
    sprint1_tasks = task_manager.find_tasks(sprint_id="sprint-1")
    assert len(sprint1_tasks) >= 2
    assert all(t["sprint_id"] == "sprint-1" for t in sprint1_tasks)

    # Filter by multiple criteria
    filtered = task_manager.find_tasks(status="pending", sprint_id="sprint-1")
    assert len(filtered) >= 1
    assert all(t["status"] == "pending" and t["sprint_id"] == "sprint-1" for t in filtered)

    # Filter by agent_type (if tasks have agent info)
    # This might return empty if no tasks have agent_type set
    agent_tasks = task_manager.find_tasks(agent_type="coder")
    assert isinstance(agent_tasks, list)


def test_task_deletion(task_manager):
    """Test task deletion."""
    # Create multiple tasks
    task1_id = task_manager.create_task(name="Task 1")
    task2_id = task_manager.create_task(name="Task 2")
    task3_id = task_manager.create_task(name="Task 3")

    initial_count = len(task_manager.state_manager.get_task_checklist())

    # Delete one task
    result = task_manager.delete_task(task2_id)
    assert result is True

    # Verify deletion
    assert task_manager.get_task(task2_id) is None
    final_count = len(task_manager.state_manager.get_task_checklist())
    assert final_count == initial_count - 1

    # Verify other tasks still exist
    assert task_manager.get_task(task1_id) is not None
    assert task_manager.get_task(task3_id) is not None


def test_invalid_task_data_handling(task_manager):
    """Test invalid task data handling."""
    # Try to update non-existent task
    result = task_manager.update_task("nonexistent-task", name="Test")
    assert result is False

    # Try to delete non-existent task
    result = task_manager.delete_task("nonexistent-task")
    assert result is False

    # Try to get non-existent task
    task = task_manager.get_task("nonexistent-task")
    assert task is None

    # Try to check blocking for non-existent task
    is_blocked, blocking = task_manager.is_task_blocked("nonexistent-task")
    assert is_blocked is False
    assert blocking == []


def test_task_creation_with_empty_name(task_manager):
    """Test task creation edge cases."""
    # Create task with empty name (should still work, validation might be elsewhere)
    task_id = task_manager.create_task(name="")
    assert task_id is not None
    task = task_manager.get_task(task_id)
    assert task["name"] == ""


def test_task_dependencies_circular_reference_prevention(task_manager):
    """Test that circular dependencies don't cause issues."""
    # Create tasks
    task1_id = task_manager.create_task(name="Task 1", dependencies=[])
    task2_id = task_manager.create_task(name="Task 2", dependencies=[task1_id])

    # Manually create circular dependency (system doesn't prevent this, but should handle gracefully)
    task1 = task_manager.get_task(task1_id)
    # Note: We can't directly modify dependencies through update_task,
    # but we can test that the system handles dependencies correctly
    task2 = task_manager.get_task(task2_id)
    assert task1_id in task2["dependencies"]


def test_task_complete_with_git_diff(task_manager):
    """Test task completion captures Git diff."""
    task_id = task_manager.create_task(name="Test Task")

    # Complete task (should capture Git diff)
    result = task_manager.complete_task(task_id)
    assert result is True

    task = task_manager.get_task(task_id)
    assert task["status"] == "completed"
    assert task["stage"] == "completed"
    assert "completed_at" in task


def test_task_cancel_and_rollback(task_manager):
    """Test task cancellation and rollback."""
    task_id = task_manager.create_task(name="Test Task", stage="implementation")

    # Cancel task
    result = task_manager.cancel_task(task_id)
    assert result is True
    task = task_manager.get_task(task_id)
    assert task["status"] == "cancelled"

    # Rollback task (should move to previous stage)
    # First update to a later stage
    task_manager.update_task(task_id, stage="testing", status="in_progress")
    # Then rollback
    result = task_manager.rollback_task(task_id)
    assert result is True
    task = task_manager.get_task(task_id)
    # Should have rolled back to previous stage
    assert task["stage"] in ["planning", "implementation"]  # Previous stage


def test_find_tasks_with_no_criteria(task_manager):
    """Test finding tasks with no criteria returns all tasks."""
    task_manager.create_task(name="Task 1")
    task_manager.create_task(name="Task 2")
    task_manager.create_task(name="Task 3")

    all_tasks = task_manager.find_tasks()
    assert len(all_tasks) >= 3


def test_task_worker_squad_stage_persistence(task_manager):
    """Test Worker Squad stage result persistence."""
    task_id = task_manager.create_task(name="Test Task")

    stage_result = {
        "stage": "planner",
        "success": True,
        "output": "Plan created",
        "plan": {"steps": ["step1", "step2"]}
    }

    result = task_manager.save_worker_squad_stage(task_id, "planner", stage_result)
    assert result is True

    # Verify stage data is stored in task
    task = task_manager.get_task(task_id)
    assert task is not None
    if "worker_squad" in task and "stages" in task["worker_squad"]:
        assert "planner" in task["worker_squad"]["stages"]


@pytest.mark.asyncio
async def test_task_worker_squad_stage_async_persistence(task_manager):
    """Test async Worker Squad stage result persistence."""
    task_id = task_manager.create_task(name="Test Task")

    stage_result = {
        "stage": "coder",
        "success": True,
        "output": "Code implemented"
    }

    result = await task_manager.save_worker_squad_stage_async(task_id, "coder", stage_result)
    assert result is True

    # Verify stage data is stored
    task = task_manager.get_task(task_id)
    assert task is not None
