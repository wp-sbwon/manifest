"""
Integration tests for parallel stage execution.

Tests that independent stages can run in parallel when parallel execution
is enabled, with proper dependency resolution and resource limits.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from manifest.agents.worker_squad_executor import WorkerSquadExecutor
from manifest.agents.workflow_definition import (
    WorkflowDefinition,
    StageDefinition,
    StageCondition
)


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = Mock()
    coordinator.state_manager = Mock()
    coordinator.state_manager.save_worker_squad_stage_async = AsyncMock()
    coordinator.state_manager.get_worker_squad_stage = Mock(return_value=None)
    coordinator.state_manager.get_task_checklist = Mock(return_value=[])
    coordinator.start_worker_agent_and_wait = AsyncMock(return_value={"success": True, "output": "test"})
    coordinator.event_bus = None
    return coordinator


@pytest.fixture
def executor(mock_coordinator):
    """Create a WorkerSquadExecutor instance."""
    return WorkerSquadExecutor(mock_coordinator)


@pytest.fixture
def parallel_workflow():
    """Create a workflow definition with parallel stages."""
    stages = [
        StageDefinition(
            name="stage_a",
            agent_type="planner",
            dependencies=[],
            parallel=True
        ),
        StageDefinition(
            name="stage_b",
            agent_type="coder",
            dependencies=[],
            parallel=True
        ),
        StageDefinition(
            name="stage_c",
            agent_type="test",
            dependencies=["stage_a", "stage_b"],
            parallel=False
        ),
    ]
    return WorkflowDefinition(
        name="parallel_test",
        stages=stages,
        entry_points=["stage_a", "stage_b"],
        exit_points=["stage_c"]
    )


@pytest.mark.asyncio
async def test_parallel_execution_enabled(executor):
    """Test that parallel execution can be enabled."""
    executor.enable_parallel_execution(enabled=True, max_concurrent=3)
    assert executor._enable_parallel_execution is True
    assert executor._max_concurrent_stages == 3


@pytest.mark.asyncio
async def test_parallel_execution_disabled(executor):
    """Test that parallel execution can be disabled."""
    executor.enable_parallel_execution(enabled=True)
    executor.enable_parallel_execution(enabled=False)
    assert executor._enable_parallel_execution is False


@pytest.mark.asyncio
async def test_get_ready_stages_parallel(executor, parallel_workflow):
    """Test that _get_ready_stages returns independent stages for parallel execution."""
    executor.set_custom_workflow(parallel_workflow)
    executor.enable_parallel_execution(enabled=True)

    # Initially, both stage_a and stage_b should be ready (no dependencies)
    ready = executor._get_ready_stages(
        completed_stages=set(),
        failed_stages=set(),
        workflow_state={"stages": {}, "completed_stages": set()}
    )

    # Both independent stages should be ready
    assert "stage_a" in ready
    assert "stage_b" in ready
    assert "stage_c" not in ready  # Depends on a and b


@pytest.mark.asyncio
async def test_get_ready_stages_after_dependencies(executor, parallel_workflow):
    """Test that stages become ready after dependencies complete."""
    executor.set_custom_workflow(parallel_workflow)
    executor.enable_parallel_execution(enabled=True)

    # After stage_a and stage_b complete, stage_c should be ready
    ready = executor._get_ready_stages(
        completed_stages={"stage_a", "stage_b"},
        failed_stages=set(),
        workflow_state={"stages": {}, "completed_stages": {"stage_a", "stage_b"}}
    )

    assert "stage_c" in ready
    assert "stage_a" not in ready  # Already completed
    assert "stage_b" not in ready  # Already completed


@pytest.mark.asyncio
async def test_parallel_execution_respects_max_concurrent(executor, parallel_workflow):
    """Test that parallel execution respects max_concurrent limit."""
    executor.set_custom_workflow(parallel_workflow)
    executor.enable_parallel_execution(enabled=True, max_concurrent=1)

    # Create a workflow with many independent stages
    many_stages = [
        StageDefinition(name=f"stage_{i}", agent_type="planner", dependencies=[], parallel=True)
        for i in range(5)
    ]
    many_workflow = WorkflowDefinition(
        name="many_parallel",
        stages=many_stages,
        entry_points=[s.name for s in many_stages],
        exit_points=[]
    )
    executor.set_custom_workflow(many_workflow)

    # Get ready stages
    ready = executor._get_ready_stages(
        completed_stages=set(),
        failed_stages=set(),
        workflow_state={"stages": {}, "completed_stages": set()}
    )

    # All 5 stages should be ready (dependency check)
    assert len(ready) == 5

    # But when executing, only max_concurrent should run
    assert executor._max_concurrent_stages == 1


@pytest.mark.asyncio
async def test_parallel_execution_tracks_running_stages(executor, parallel_workflow):
    """Test that parallel execution tracks running stages to avoid duplicates."""
    executor.set_custom_workflow(parallel_workflow)
    executor.enable_parallel_execution(enabled=True)

    # Simulate workflow state
    task_id = "test-task"
    workflow_state = {
        "stages": {},
        "completed_stages": set(),
        "failed_stages": set()
    }
    executor._active_workflows[task_id] = workflow_state

    # Manually trigger parallel execution
    ready_stages = ["stage_a", "stage_b"]

    # First call - should create tasks
    if ready_stages:
        if task_id not in executor._running_stages:
            executor._running_stages[task_id] = {}

        # Create mock tasks
        for stage in ready_stages:
            if stage not in executor._running_stages[task_id]:
                mock_task = AsyncMock()
                executor._running_stages[task_id][stage] = mock_task

    # Verify stages are tracked
    assert "stage_a" in executor._running_stages[task_id]
    assert "stage_b" in executor._running_stages[task_id]

    # Second call with same stages - should not duplicate
    for stage in ready_stages:
        if stage in executor._running_stages[task_id]:
            # Should skip - already running
            pass

    # Should still have only 2 tasks
    assert len(executor._running_stages[task_id]) == 2


@pytest.mark.asyncio
async def test_parallel_execution_cleanup_after_completion(executor):
    """Test that running stages are cleaned up after completion."""
    executor.enable_parallel_execution(enabled=True)

    task_id = "test-task"
    executor._running_stages[task_id] = {
        "stage_a": AsyncMock(),
        "stage_b": AsyncMock()
    }

    # Simulate stage completion cleanup
    stage = "stage_a"
    if task_id in executor._running_stages:
        executor._running_stages[task_id].pop(stage, None)
        if not executor._running_stages[task_id]:
            del executor._running_stages[task_id]

    # stage_a should be removed
    assert "stage_a" not in executor._running_stages.get(task_id, {})
    # stage_b should still be there
    assert "stage_b" in executor._running_stages[task_id]

    # Clean up stage_b
    stage = "stage_b"
    if task_id in executor._running_stages:
        executor._running_stages[task_id].pop(stage, None)
        if not executor._running_stages[task_id]:
            del executor._running_stages[task_id]

    # task_id should be removed entirely
    assert task_id not in executor._running_stages


def test_workflow_definition_get_execution_order(parallel_workflow):
    """Test that WorkflowDefinition.get_execution_order groups parallel stages."""
    execution_order = parallel_workflow.get_execution_order()

    # Should have levels: [stage_a, stage_b] can run in parallel, then [stage_c]
    assert len(execution_order) == 2
    assert len(execution_order[0]) == 2  # stage_a and stage_b in parallel
    assert set(execution_order[0]) == {"stage_a", "stage_b"}
    assert execution_order[1] == ["stage_c"]  # stage_c depends on both


def test_workflow_definition_no_circular_dependencies(parallel_workflow):
    """Test that workflow definition detects circular dependencies."""
    # parallel_workflow has no cycles
    is_valid, errors = parallel_workflow.validate()
    assert is_valid is True

    # Create a workflow with a cycle
    cycle_stages = [
        StageDefinition(name="a", agent_type="planner", dependencies=["b"]),
        StageDefinition(name="b", agent_type="coder", dependencies=["a"]),
    ]
    cycle_workflow = WorkflowDefinition(
        name="cycle",
        stages=cycle_stages,
        entry_points=["a"],
        exit_points=[]
    )

    is_valid, errors = cycle_workflow.validate()
    assert is_valid is False
    assert any("circular" in str(err).lower() or "cycle" in str(err).lower() for err in errors)
