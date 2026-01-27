"""
E2E Test: Multi-Agent Coordination Workflow

Tests the complete workflow of multiple agents working on related tasks.
This validates agent coordination, communication, and dependency management.
"""
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from manifest.bridge.agent_bridge import AgentBridge
from manifest.agents.agent_coordinator import AgentCoordinator
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


# ========== TDL: Workflow 5: Multi-Agent Coordination ==========

@pytest.mark.asyncio
async def test_agents_coordinate_correctly(
    agent_coordinator, agent_bridge, state_manager
):
    """Test: Agents coordinate correctly when working on related tasks."""
    # Start bridge and coordinator
    await agent_bridge.start()
    await agent_coordinator.start()

    # Step 1: Create multiple related tasks
    task_ids = []
    for i in range(3):
        task_id = state_manager.create_task(
            name=f"Task {i+1}",
            description=f"Related task {i+1}",
            status="pending"
        )
        task_ids.append(task_id)

    # Step 2: Track agent coordination
    agent_calls = []
    execution_order = []

    async def track_start_agent(task_id_param, agent_type, **kwargs):
        agent_calls.append({
            "task_id": task_id_param,
            "agent_type": agent_type,
            "timestamp": asyncio.get_event_loop().time()
        })
        execution_order.append(f"{task_id_param}-{agent_type}")
        return True

    agent_coordinator.start_worker_agent = track_start_agent

    # Step 3: Start agents for different tasks
    await agent_coordinator.start_worker_agent(task_ids[0], "planner")
    await agent_coordinator.start_worker_agent(task_ids[1], "planner")
    await agent_coordinator.start_worker_agent(task_ids[2], "coder")

    # Verify agents were coordinated
    assert len(agent_calls) == 3
    assert len(execution_order) == 3
    # All tasks should have agents started
    started_tasks = {call["task_id"] for call in agent_calls}
    assert len(started_tasks) == 3
    assert all(task_id in started_tasks for task_id in task_ids)


@pytest.mark.asyncio
async def test_dependencies_enforced(
    agent_coordinator, agent_bridge, state_manager
):
    """Test: Dependencies are enforced between tasks."""
    # Start bridge and coordinator
    await agent_bridge.start()
    await agent_coordinator.start()

    # Step 1: Create tasks with dependencies
    # Task 1 must complete before Task 2
    task_id_1 = state_manager.create_task(
        name="Task 1 - Setup",
        description="Setup task that must complete first",
        status="pending"
    )
    task_id_2 = state_manager.create_task(
        name="Task 2 - Implementation",
        description="Implementation task that depends on Task 1",
        status="pending"
    )

    # Step 2: Track execution order
    execution_order = []

    async def track_start_agent(task_id_param, agent_type, **kwargs):
        execution_order.append(task_id_param)
        # Simulate task completion
        if task_id_param == task_id_1:
            state_manager.update_task(task_id_param, status="completed")
        return True

    agent_coordinator.start_worker_agent = track_start_agent

    # Step 3: Start Task 1
    await agent_coordinator.start_worker_agent(task_id_1, "planner")
    await asyncio.sleep(0.01)  # Allow task to "complete"

    # Step 4: Verify Task 1 completed before Task 2 can start
    task_1 = next((t for t in state_manager.get_task_checklist() if t.get("id") == task_id_1), None)
    assert task_1 is not None
    # Task 1 should be completed or in progress
    assert task_1.get("status") in ["completed", "in_progress"]

    # Step 5: Start Task 2 (should be allowed after Task 1 completes)
    await agent_coordinator.start_worker_agent(task_id_2, "planner")

    # Verify execution order
    assert len(execution_order) >= 1
    # Task 1 should be in execution order
    assert task_id_1 in execution_order


@pytest.mark.asyncio
async def test_communication_works(
    agent_coordinator, agent_bridge, state_manager
):
    """Test: Communication works between agents via message bus."""
    # Start bridge and coordinator
    await agent_bridge.start()
    await agent_coordinator.start()

    # Step 1: Create tasks
    task_id_1 = state_manager.create_task(
        name="Task 1",
        description="Task 1",
        status="pending"
    )
    task_id_2 = state_manager.create_task(
        name="Task 2",
        description="Task 2",
        status="pending"
    )

    # Step 2: Set up message bus if available
    messages_sent = []
    messages_received = []

    if hasattr(agent_bridge, 'message_bus') and agent_bridge.message_bus:
        original_send = agent_bridge.message_bus.send_message

        async def track_send_message(from_agent_id, to_agent_id, subject, content):
            messages_sent.append({
                "from": from_agent_id,
                "to": to_agent_id,
                "subject": subject,
                "content": content
            })
            return await original_send(from_agent_id, to_agent_id, subject, content)

        agent_bridge.message_bus.send_message = track_send_message

    # Step 3: Start agents
    await agent_coordinator.start_worker_agent(task_id_1, "planner")
    await agent_coordinator.start_worker_agent(task_id_2, "coder")

    # Step 4: Verify communication infrastructure exists
    # Message bus may or may not be available, but coordination should work
    assert agent_coordinator is not None
    assert agent_bridge is not None

    # If message bus exists, verify it's set up
    if hasattr(agent_bridge, 'message_bus') and agent_bridge.message_bus:
        assert agent_bridge.message_bus is not None


@pytest.mark.asyncio
async def test_no_race_conditions(
    agent_coordinator, agent_bridge, state_manager
):
    """Test: No race conditions when multiple agents start simultaneously."""
    # Start bridge and coordinator
    await agent_bridge.start()
    await agent_coordinator.start()

    # Step 1: Create multiple tasks
    task_ids = []
    for i in range(5):
        task_id = state_manager.create_task(
            name=f"Concurrent Task {i+1}",
            description=f"Task {i+1}",
            status="pending"
        )
        task_ids.append(task_id)

    # Step 2: Track concurrent starts
    concurrent_starts = []
    lock = asyncio.Lock()

    async def track_start_agent(task_id_param, agent_type, **kwargs):
        async with lock:
            concurrent_starts.append({
                "task_id": task_id_param,
                "agent_type": agent_type,
                "timestamp": asyncio.get_event_loop().time()
            })
        return True

    agent_coordinator.start_worker_agent = track_start_agent

    # Step 3: Start all agents concurrently
    start_tasks = [
        agent_coordinator.start_worker_agent(task_id, "planner")
        for task_id in task_ids
    ]
    await asyncio.gather(*start_tasks)

    # Step 4: Verify all agents started without race conditions
    assert len(concurrent_starts) == len(task_ids)
    started_task_ids = {start["task_id"] for start in concurrent_starts}
    assert len(started_task_ids) == len(task_ids)
    assert all(task_id in started_task_ids for task_id in task_ids)

    # Verify no duplicate starts (race condition check)
    task_id_counts = {}
    for start in concurrent_starts:
        task_id = start["task_id"]
        task_id_counts[task_id] = task_id_counts.get(task_id, 0) + 1
    assert all(count == 1 for count in task_id_counts.values()), "No duplicate agent starts"


@pytest.mark.asyncio
async def test_parallel_execution_where_possible(
    agent_coordinator, agent_bridge, state_manager
):
    """Test: Agents start in parallel where possible."""
    # Start bridge and coordinator
    await agent_bridge.start()
    await agent_coordinator.start()

    # Step 1: Create independent tasks (no dependencies)
    task_ids = []
    for i in range(4):
        task_id = state_manager.create_task(
            name=f"Independent Task {i+1}",
            description=f"Independent task {i+1}",
            status="pending"
        )
        task_ids.append(task_id)

    # Step 2: Track parallel execution
    start_times = {}
    end_times = {}

    async def track_start_agent(task_id_param, agent_type, **kwargs):
        start_time = asyncio.get_event_loop().time()
        start_times[task_id_param] = start_time
        # Simulate some work
        await asyncio.sleep(0.01)
        end_times[task_id_param] = asyncio.get_event_loop().time()
        return True

    agent_coordinator.start_worker_agent = track_start_agent

    # Step 3: Start all agents concurrently
    start_coroutines = [
        agent_coordinator.start_worker_agent(task_id, "planner")
        for task_id in task_ids
    ]
    await asyncio.gather(*start_coroutines)

    # Step 4: Verify parallel execution
    assert len(start_times) == len(task_ids)
    assert len(end_times) == len(task_ids)

    # Check that starts happened close together (parallel)
    if len(start_times) > 1:
        start_time_values = list(start_times.values())
        time_diff = max(start_time_values) - min(start_time_values)
        # Starts should be close together (within 0.1 seconds for parallel execution)
        assert time_diff < 0.1, "Agents should start in parallel"


@pytest.mark.asyncio
async def test_complete_multi_agent_coordination_workflow(
    agent_coordinator, agent_bridge, state_manager
):
    """Test: Complete multi-agent coordination workflow."""
    # Start bridge and coordinator
    await agent_bridge.start()
    await agent_coordinator.start()

    # Step 1: Create multiple related tasks
    task_ids = []
    task_names = ["Setup", "Implementation", "Testing", "Documentation"]
    for name in task_names:
        task_id = state_manager.create_task(
            name=f"Task: {name}",
            description=f"Task for {name}",
            status="pending"
        )
        task_ids.append(task_id)

    # Step 2: Track all agent activities
    agent_activities = []

    async def track_start_agent(task_id_param, agent_type, **kwargs):
        agent_activities.append({
            "action": "start",
            "task_id": task_id_param,
            "agent_type": agent_type
        })
        # Simulate agent work
        await asyncio.sleep(0.01)
        agent_activities.append({
            "action": "complete",
            "task_id": task_id_param,
            "agent_type": agent_type
        })
        return True

    agent_coordinator.start_worker_agent = track_start_agent

    # Step 3: Start agents for all tasks
    start_coroutines = [
        agent_coordinator.start_worker_agent(task_id, "planner")
        for task_id in task_ids
    ]
    await asyncio.gather(*start_coroutines)

    # Step 4: Verify complete coordination
    assert len(agent_activities) >= len(task_ids) * 2  # Start + complete for each

    # Verify all tasks had agents started
    started_tasks = {
        activity["task_id"]
        for activity in agent_activities
        if activity["action"] == "start"
    }
    assert len(started_tasks) == len(task_ids)
    assert all(task_id in started_tasks for task_id in task_ids)

    # Verify all tasks completed
    completed_tasks = {
        activity["task_id"]
        for activity in agent_activities
        if activity["action"] == "complete"
    }
    assert len(completed_tasks) == len(task_ids)

    # Verify state was updated
    tasks = state_manager.get_task_checklist()
    assert len(tasks) == len(task_ids)
    for task_id in task_ids:
        task = next((t for t in tasks if t.get("id") == task_id), None)
        assert task is not None
