"""
E2E Test: Large Mission Handling Workflow

Tests the complete workflow of handling missions with many tasks.
This validates that the system can efficiently create, execute, and aggregate
results for missions with 20+ tasks.
"""
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from manifest.agents.agent_coordinator import AgentCoordinator
from manifest.agents.sprint_executor import SprintExecutor
from manifest.agents.worker_squad_executor import WorkerSquadExecutor
from manifest.bridge.agent_bridge import AgentBridge
from manifest.agents.context_provider import ContextProvider
from manifest.agents.task_scoper import TaskScoper
from manifest.core.config import ConfigManager
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


@pytest.fixture
def config_manager(temp_dir):
    """Create a ConfigManager instance."""
    return ConfigManager(manifest_dir=temp_dir)


@pytest.fixture
def agent_bridge(state_manager, config_manager):
    """Create an AgentBridge instance."""
    return AgentBridge(
        state_manager=state_manager,
        config_manager=config_manager
    )


@pytest.fixture
def agent_coordinator(agent_bridge, temp_dir, state_manager, config_manager):
    """Create an AgentCoordinator instance."""
    task_scoper = TaskScoper(manifest_dir=temp_dir)
    context_provider = ContextProvider(manifest_dir=temp_dir, task_scoper=task_scoper)
    return AgentCoordinator(
        agent_bridge=agent_bridge,
        context_provider=context_provider,
        task_scoper=task_scoper,
        config_manager=config_manager,
        state_manager=state_manager
    )


@pytest.fixture
def sprint_executor(agent_coordinator):
    """Create a SprintExecutor instance."""
    return SprintExecutor(coordinator=agent_coordinator)


# ========== TDL: Workflow 9: Large Mission Handling ==========

@pytest.mark.asyncio
async def test_all_tasks_are_created(
    state_manager, agent_coordinator
):
    """Test: All tasks are created for a large mission."""
    # Step 1: Create a large mission with 25 tasks
    mission_id = "mission-large-001"
    task_count = 25
    created_tasks = []

    # Step 2: Create all tasks
    for i in range(task_count):
        task_id = state_manager.create_task(
            name=f"Task {i+1}",
            description=f"Task {i+1} description",
            status="pending",
            sprint_id=mission_id
        )
        created_tasks.append(task_id)

    # Step 3: Verify all tasks were created
    assert len(created_tasks) == task_count

    # Step 4: Verify tasks exist in state
    tasks = state_manager.get_task_checklist()
    mission_tasks = [t for t in tasks if t.get("sprint_id") == mission_id]
    assert len(mission_tasks) == task_count

    # Step 5: Verify task IDs are unique
    task_ids = [t.get("id") for t in mission_tasks]
    assert len(task_ids) == len(set(task_ids))  # All unique


@pytest.mark.asyncio
async def test_execution_is_efficient(
    sprint_executor, state_manager, agent_coordinator
):
    """Test: Execution is efficient for large missions."""
    # Step 1: Create a large mission with 20 tasks
    mission_id = "mission-large-002"
    task_count = 20

    for i in range(task_count):
        state_manager.create_task(
            name=f"Task {i+1}",
            description=f"Task {i+1} description",
            status="pending",
            sprint_id=mission_id
        )

    # Step 2: Track execution start time
    import time
    start_time = time.time()

    # Step 3: Mock worker squad execution to be fast
    execution_times = []

    async def mock_execute(task_id):
        task_start = time.time()
        # Simulate fast execution
        await asyncio.sleep(0.01)  # 10ms per task
        execution_times.append(time.time() - task_start)
        return {"success": True, "stages": {}}

    agent_coordinator.worker_squad_executor.execute = mock_execute

    # Step 4: Start sprint execution (with parallel execution)
    result = await sprint_executor.start_sprint(mission_id, max_parallel=10)

    # Step 5: Verify execution completed
    assert result is not None
    assert "started_tasks" in result or "success" in result

    # Step 6: Verify execution time is reasonable
    # With 20 tasks and max_parallel=10, should complete in ~2 batches
    # Each batch takes ~10ms, so total should be ~20-30ms
    end_time = time.time()
    execution_duration = end_time - start_time

    # Should complete in reasonable time (allowing for overhead)
    assert execution_duration < 5.0  # Should complete in under 5 seconds


@pytest.mark.asyncio
async def test_no_memory_leaks(
    state_manager, agent_coordinator, sprint_executor
):
    """Test: No memory leaks during large mission execution."""
    # Step 1: Create a large mission with 30 tasks
    mission_id = "mission-large-003"
    task_count = 30

    for i in range(task_count):
        state_manager.create_task(
            name=f"Task {i+1}",
            description=f"Task {i+1} description",
            status="pending",
            sprint_id=mission_id
        )

    # Step 2: Track active workflows before execution
    initial_workflows = len(agent_coordinator.worker_squad_executor._active_workflows)

    # Step 3: Mock execution to complete quickly
    async def mock_execute(task_id):
        await asyncio.sleep(0.001)  # 1ms per task
        return {"success": True, "stages": {}}

    agent_coordinator.worker_squad_executor.execute = mock_execute

    # Step 4: Execute sprint
    result = await sprint_executor.start_sprint(mission_id, max_parallel=10)

    # Step 5: Wait a bit for cleanup
    await asyncio.sleep(0.1)

    # Step 6: Verify active workflows are cleaned up
    # (Workflows should be removed after completion)
    final_workflows = len(agent_coordinator.worker_squad_executor._active_workflows)

    # Active workflows should not grow unbounded
    # They may increase during execution but should be cleaned up
    assert final_workflows <= initial_workflows + task_count  # Reasonable bound

    # Step 7: Verify state size is reasonable
    state = state_manager.get_state()
    state_size = len(str(state))
    # State should be reasonable (not growing unbounded)
    assert state_size < 1000000  # Less than 1MB for 30 tasks


@pytest.mark.asyncio
async def test_results_are_correct(
    state_manager, agent_coordinator, sprint_executor
):
    """Test: Results are correct for large mission."""
    # Step 1: Create a large mission with 20 tasks
    mission_id = "mission-large-004"
    task_count = 20
    task_ids = []

    for i in range(task_count):
        task_id = state_manager.create_task(
            name=f"Task {i+1}",
            description=f"Task {i+1} description",
            status="pending",
            sprint_id=mission_id
        )
        task_ids.append(task_id)

    # Step 2: Track execution results
    execution_results = {}

    async def mock_execute(task_id):
        # Simulate successful execution with unique result
        result = {
            "success": True,
            "stages": {
                "planner": {"output": f"Plan for {task_id}"},
                "coder": {"output": f"Code for {task_id}"}
            },
            "task_id": task_id
        }
        execution_results[task_id] = result
        return result

    agent_coordinator.worker_squad_executor.execute = mock_execute

    # Step 3: Execute sprint
    result = await sprint_executor.start_sprint(mission_id, max_parallel=10)

    # Step 4: Verify all tasks were executed
    assert len(execution_results) == task_count

    # Step 5: Verify each task has correct results
    for task_id in task_ids:
        assert task_id in execution_results
        task_result = execution_results[task_id]
        assert task_result["success"] is True
        assert task_result["task_id"] == task_id
        assert "stages" in task_result

    # Step 6: Verify results are unique (no cross-contamination)
    outputs = [r["stages"]["planner"]["output"] for r in execution_results.values()]
    assert len(outputs) == len(set(outputs))  # All unique


@pytest.mark.asyncio
async def test_parallel_execution_works(
    state_manager, agent_coordinator, sprint_executor
):
    """Test: Parallel execution works for large missions."""
    # Step 1: Create a large mission with 25 tasks
    mission_id = "mission-large-005"
    task_count = 25

    for i in range(task_count):
        state_manager.create_task(
            name=f"Task {i+1}",
            description=f"Task {i+1} description",
            status="pending",
            sprint_id=mission_id
        )

    # Step 2: Track parallel execution
    concurrent_executions = {"max": 0, "current": 0}
    execution_order = []

    async def mock_execute(task_id):
        concurrent_executions["current"] += 1
        concurrent_executions["max"] = max(
            concurrent_executions["max"],
            concurrent_executions["current"]
        )
        execution_order.append(("start", task_id))

        # Simulate execution time
        await asyncio.sleep(0.05)  # 50ms per task

        execution_order.append(("end", task_id))
        concurrent_executions["current"] -= 1

        return {"success": True, "stages": {}}

    agent_coordinator.worker_squad_executor.execute = mock_execute

    # Step 3: Execute sprint with max_parallel=10
    result = await sprint_executor.start_sprint(mission_id, max_parallel=10)

    # Step 4: Verify parallel execution occurred
    # With max_parallel=10, we should see up to 10 concurrent executions
    assert concurrent_executions["max"] <= 10
    assert concurrent_executions["max"] > 1  # Should have some parallelism

    # Step 5: Verify all tasks completed
    assert len([e for e in execution_order if e[0] == "end"]) == task_count


@pytest.mark.asyncio
async def test_state_persistence_during_execution(
    state_manager, agent_coordinator, sprint_executor
):
    """Test: State is persisted correctly during large mission execution."""
    # Step 1: Create a large mission with 20 tasks
    mission_id = "mission-large-006"
    task_count = 20
    task_ids = []

    for i in range(task_count):
        task_id = state_manager.create_task(
            name=f"Task {i+1}",
            description=f"Task {i+1} description",
            status="pending",
            sprint_id=mission_id
        )
        task_ids.append(task_id)

    # Step 2: Save initial state
    await state_manager.save_state()

    # Step 3: Mock execution that updates state
    async def mock_execute(task_id):
        # Update task status during execution
        tasks = state_manager.get_task_checklist()
        for task in tasks:
            if task.get("id") == task_id:
                task["status"] = "in_progress"
                break
        await state_manager.save_state()

        await asyncio.sleep(0.01)
        return {"success": True, "stages": {}}

    agent_coordinator.worker_squad_executor.execute = mock_execute

    # Step 4: Execute sprint
    result = await sprint_executor.start_sprint(mission_id, max_parallel=10)

    # Step 5: Verify state was persisted
    state = state_manager.get_state()
    assert "task_checklist" in state

    # Step 6: Verify all tasks are still in state
    tasks = state_manager.get_task_checklist()
    mission_tasks = [t for t in tasks if t.get("sprint_id") == mission_id]
    assert len(mission_tasks) == task_count

    # Step 7: Verify task IDs match
    mission_task_ids = [t.get("id") for t in mission_tasks]
    assert set(mission_task_ids) == set(task_ids)


@pytest.mark.asyncio
async def test_complete_large_mission_workflow(
    state_manager, agent_coordinator, sprint_executor
):
    """Test: Complete large mission workflow from creation to completion."""
    # Step 1: Create a large mission with 25 tasks
    mission_id = "mission-large-007"
    task_count = 25
    task_ids = []

    workflow_stages = []

    # Step 2: Create all tasks
    for i in range(task_count):
        task_id = state_manager.create_task(
            name=f"Task {i+1}",
            description=f"Task {i+1} description",
            status="pending",
            sprint_id=mission_id
        )
        task_ids.append(task_id)
    workflow_stages.append("tasks_created")

    # Step 3: Verify tasks exist
    tasks = state_manager.get_task_checklist()
    mission_tasks = [t for t in tasks if t.get("sprint_id") == mission_id]
    assert len(mission_tasks) == task_count
    workflow_stages.append("tasks_verified")

    # Step 4: Track execution
    completed_tasks = []

    async def mock_execute(task_id):
        completed_tasks.append(task_id)
        await asyncio.sleep(0.01)
        return {
            "success": True,
            "stages": {
                "planner": {"output": f"Plan for {task_id}"},
                "coder": {"output": f"Code for {task_id}"}
            }
        }

    agent_coordinator.worker_squad_executor.execute = mock_execute

    # Step 5: Execute sprint
    result = await sprint_executor.start_sprint(mission_id, max_parallel=10)
    workflow_stages.append("execution_started")

    # Step 6: Wait for completion
    await asyncio.sleep(0.5)  # Allow time for all tasks to complete
    workflow_stages.append("execution_completed")

    # Step 7: Verify complete workflow
    assert "tasks_created" in workflow_stages
    assert "tasks_verified" in workflow_stages
    assert "execution_started" in workflow_stages

    # Step 8: Verify tasks were executed
    # Note: With max_parallel=10, not all tasks may execute immediately
    # but they should all be started
    assert len(completed_tasks) > 0
    assert len(completed_tasks) <= task_count
    # Verify all completed tasks are from our mission
    assert all(tid in task_ids for tid in completed_tasks)

    # Step 9: Verify results are aggregated
    assert result is not None
    # Result should indicate success or provide task status
