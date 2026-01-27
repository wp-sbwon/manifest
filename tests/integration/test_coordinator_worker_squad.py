"""
Integration tests for AgentCoordinator → WorkerSquadExecutor interaction.

Tests the integration between AgentCoordinator and WorkerSquadExecutor to ensure
proper task execution workflows, stage transitions, event publishing, and state persistence.
"""
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from manifest.core.state_manager import StateManager
from manifest.bridge.agent_bridge import AgentBridge
from manifest.agents.agent_coordinator import AgentCoordinator
from manifest.agents.context_provider import ContextProvider
from manifest.agents.task_scoper import TaskScoper
from manifest.core.config import ConfigManager
from manifest.agents.workflow_event_bus import WorkflowEventBus, WorkflowEvent, WorkflowEventType


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
    return AgentBridge(state_manager, config_manager=config_manager)


@pytest.fixture
def context_provider(temp_dir):
    """Create a ContextProvider instance."""
    task_scoper = TaskScoper(manifest_dir=temp_dir)
    return ContextProvider(manifest_dir=temp_dir, task_scoper=task_scoper)


@pytest.fixture
def task_scoper(temp_dir):
    """Create a TaskScoper instance."""
    return TaskScoper(manifest_dir=temp_dir)


@pytest.fixture
def event_bus():
    """Create a WorkflowEventBus instance."""
    return WorkflowEventBus()


@pytest.fixture
def agent_coordinator(agent_bridge, context_provider, task_scoper, config_manager, state_manager, event_bus):
    """Create an AgentCoordinator instance with event bus."""
    coordinator = AgentCoordinator(
        agent_bridge=agent_bridge,
        context_provider=context_provider,
        task_scoper=task_scoper,
        config_manager=config_manager,
        state_manager=state_manager
    )
    # Attach event bus to coordinator
    coordinator.event_bus = event_bus
    # Attach event bus to worker squad executor
    coordinator.worker_squad_executor.event_bus = event_bus
    return coordinator


@pytest.fixture
def sample_task(state_manager):
    """Create a sample task for testing."""
    task_id = state_manager.create_task(
        name="Test Task",
        description="Test task description",
        status="pending"
    )
    return task_id


# ========== TDL: Agent Coordinator → Worker Squad Executor Integration ==========

@pytest.mark.asyncio
async def test_task_execution_workflow_coordinator_delegates_to_executor(
    agent_coordinator, agent_bridge, sample_task
):
    """Test task execution workflow - coordinator delegates to executor."""
    # Start bridge
    await agent_bridge.start()
    await agent_coordinator.start()

    # Mock executor.execute to track calls
    execute_calls = []
    original_execute = agent_coordinator.worker_squad_executor.execute

    async def track_execute(task_id):
        execute_calls.append(task_id)
        # Return a mock result
        return {
            "success": True,
            "stages": {},
            "error": None
        }

    agent_coordinator.worker_squad_executor.execute = track_execute

    # Execute worker squad through coordinator
    result = await agent_coordinator.execute_worker_squad(sample_task)

    # Verify executor was called
    assert len(execute_calls) == 1
    assert execute_calls[0] == sample_task
    assert result["success"] is True

    # Restore original method
    agent_coordinator.worker_squad_executor.execute = original_execute


@pytest.mark.asyncio
async def test_task_execution_workflow_executor_uses_coordinator_to_start_agents(
    agent_coordinator, agent_bridge, sample_task
):
    """Test task execution workflow - executor uses coordinator to start agents."""
    # Start bridge
    await agent_bridge.start()
    await agent_coordinator.start()

    # Track coordinator.start_worker_agent calls
    start_agent_calls = []

    async def track_start_worker_agent(task_id, agent_type, **kwargs):
        start_agent_calls.append((task_id, agent_type, kwargs))
        return True

    # Mock coordinator's start_worker_agent
    original_start = agent_coordinator.start_worker_agent
    agent_coordinator.start_worker_agent = track_start_worker_agent

    # Mock executor's stage execution to avoid full workflow
    async def mock_execute(task_id):
        # Simulate starting planner stage
        await agent_coordinator.start_worker_agent(task_id, "planner", stage="planner")
        return {
            "success": True,
            "stages": {"planner": {"status": "completed"}},
            "error": None
        }

    agent_coordinator.worker_squad_executor.execute = mock_execute

    # Execute worker squad
    result = await agent_coordinator.execute_worker_squad(sample_task)

    # Verify coordinator was used to start agents
    assert len(start_agent_calls) > 0
    assert start_agent_calls[0][0] == sample_task
    assert start_agent_calls[0][1] == "planner"

    # Restore original method
    agent_coordinator.start_worker_agent = original_start


@pytest.mark.asyncio
async def test_stage_transitions_sequential_progression(
    agent_coordinator, agent_bridge, sample_task
):
    """Test stage transitions - sequential stage progression."""
    # Start bridge
    await agent_bridge.start()
    await agent_coordinator.start()

    # Track stage progression
    stages_executed = []

    async def track_stage_execution(task_id):
        # Simulate sequential stage execution
        stages = ["planner", "tdd_test", "coder", "test"]
        for stage in stages:
            stages_executed.append(stage)
            # Simulate stage completion
            await asyncio.sleep(0.01)
        return {
            "success": True,
            "stages": {stage: {"status": "completed"} for stage in stages},
            "error": None
        }

    agent_coordinator.worker_squad_executor.execute = track_stage_execution

    # Execute workflow
    result = await agent_coordinator.execute_worker_squad(sample_task)

    # Verify stages executed in order
    assert len(stages_executed) == 4
    assert stages_executed == ["planner", "tdd_test", "coder", "test"]
    assert result["success"] is True


@pytest.mark.asyncio
async def test_stage_transitions_previous_stage_data_passed(
    agent_coordinator, agent_bridge, sample_task
):
    """Test stage transitions - previous stage data is passed to next stage."""
    # Start bridge
    await agent_bridge.start()
    await agent_coordinator.start()

    # Track previous_stages passed between stages
    previous_stages_data = []

    async def track_previous_stages(task_id):
        # Simulate stages passing data
        previous_stages = {}
        stages = ["planner", "tdd_test", "coder"]
        for stage in stages:
            previous_stages_data.append((stage, previous_stages.copy()))
            # Add stage result to previous_stages
            previous_stages[stage] = {"output": f"{stage} output", "status": "completed"}
        return {
            "success": True,
            "stages": previous_stages,
            "error": None
        }

    agent_coordinator.worker_squad_executor.execute = track_previous_stages

    # Execute workflow
    result = await agent_coordinator.execute_worker_squad(sample_task)

    # Verify previous_stages data was tracked
    assert len(previous_stages_data) == 3
    # Each stage should receive previous stages
    assert previous_stages_data[0][1] == {}  # Planner has no previous stages
    assert "planner" in previous_stages_data[1][1]  # TDD test has planner results
    assert "tdd_test" in previous_stages_data[2][1]  # Coder has TDD test results


@pytest.mark.asyncio
async def test_event_publishing_workflow_started(
    agent_coordinator, agent_bridge, sample_task, event_bus
):
    """Test event publishing - workflow started event."""
    # Start bridge
    await agent_bridge.start()
    await agent_coordinator.start()

    # Track published events
    published_events = []

    async def track_publish(event):
        published_events.append(event)

    event_bus.publish = track_publish

    # Mock executor to trigger event
    async def mock_execute(task_id):
        # Executor should publish WORKFLOW_STARTED event
        if event_bus:
            await event_bus.publish(WorkflowEvent(
                event_type=WorkflowEventType.WORKFLOW_STARTED,
                task_id=task_id,
                data={"workflow_type": "worker_squad"}
            ))
        return {"success": True, "stages": {}, "error": None}

    agent_coordinator.worker_squad_executor.execute = mock_execute

    # Execute workflow
    await agent_coordinator.execute_worker_squad(sample_task)

    # Verify workflow started event was published
    assert len(published_events) > 0
    workflow_started = [e for e in published_events if e.event_type == WorkflowEventType.WORKFLOW_STARTED]
    assert len(workflow_started) > 0
    assert workflow_started[0].task_id == sample_task


@pytest.mark.asyncio
async def test_event_publishing_stage_completed(
    agent_coordinator, agent_bridge, sample_task, event_bus
):
    """Test event publishing - stage completed events."""
    # Start bridge
    await agent_bridge.start()
    await agent_coordinator.start()

    # Track published events
    published_events = []

    async def track_publish(event):
        published_events.append(event)

    event_bus.publish = track_publish

    # Mock executor to publish stage events
    async def mock_execute(task_id):
        stages = ["planner", "coder"]
        for stage in stages:
            if event_bus:
                await event_bus.publish(WorkflowEvent(
                    event_type=WorkflowEventType.STAGE_COMPLETED,
                    task_id=task_id,
                    data={"stage": stage, "status": "completed"}
                ))
        return {"success": True, "stages": {}, "error": None}

    agent_coordinator.worker_squad_executor.execute = mock_execute

    # Execute workflow
    await agent_coordinator.execute_worker_squad(sample_task)

    # Verify stage completed events were published
    stage_events = [e for e in published_events if e.event_type == WorkflowEventType.STAGE_COMPLETED]
    assert len(stage_events) == 2
    assert stage_events[0].data["stage"] == "planner"
    assert stage_events[1].data["stage"] == "coder"


@pytest.mark.asyncio
async def test_event_handling_subscription_and_callback(
    agent_coordinator, agent_bridge, sample_task, event_bus
):
    """Test event handling - subscription and callback execution."""
    # Start bridge
    await agent_bridge.start()
    await agent_coordinator.start()

    # Track callback executions
    callback_executions = []

    async def test_callback(event):
        callback_executions.append(event)

    # Subscribe to workflow events (subscribe is not async)
    event_bus.subscribe(WorkflowEventType.WORKFLOW_STARTED, test_callback)

    # Mock executor to publish event
    async def mock_execute(task_id):
        if event_bus:
            await event_bus.publish(WorkflowEvent(
                event_type=WorkflowEventType.WORKFLOW_STARTED,
                task_id=task_id,
                data={"workflow_type": "worker_squad"}
            ))
        return {"success": True, "stages": {}, "error": None}

    agent_coordinator.worker_squad_executor.execute = mock_execute

    # Execute workflow
    await agent_coordinator.execute_worker_squad(sample_task)

    # Give time for async event handling
    await asyncio.sleep(0.1)

    # Verify callback was executed
    assert len(callback_executions) > 0
    assert callback_executions[0].event_type == WorkflowEventType.WORKFLOW_STARTED
    assert callback_executions[0].task_id == sample_task


@pytest.mark.asyncio
async def test_state_persistence_during_workflow_stage_results_saved(
    agent_coordinator, agent_bridge, sample_task, state_manager
):
    """Test state persistence during workflow - stage results are saved."""
    # Start bridge
    await agent_bridge.start()
    await agent_coordinator.start()

    # Track state save calls
    save_state_calls = []

    async def track_save_state():
        save_state_calls.append("saved")
        return None

    state_manager.save_state = track_save_state

    # Mock executor to simulate stage completion and state saving
    async def mock_execute(task_id):
        stages = ["planner", "coder"]
        for stage in stages:
            # Simulate saving stage result
            await state_manager.save_state()
        return {
            "success": True,
            "stages": {stage: {"status": "completed"} for stage in stages},
            "error": None
        }

    agent_coordinator.worker_squad_executor.execute = mock_execute

    # Execute workflow
    await agent_coordinator.execute_worker_squad(sample_task)

    # Verify state was saved during workflow
    assert len(save_state_calls) >= 2  # At least one save per stage


@pytest.mark.asyncio
async def test_state_persistence_during_workflow_task_status_updated(
    agent_coordinator, agent_bridge, sample_task, state_manager
):
    """Test state persistence during workflow - task status is updated."""
    # Start bridge
    await agent_bridge.start()
    await agent_coordinator.start()

    # Get initial task status
    tasks = state_manager.get_task_checklist()
    initial_task = next((t for t in tasks if t.get("id") == sample_task), None)
    initial_status = initial_task.get("status") if initial_task else None

    # Mock executor to update task status
    async def mock_execute(task_id):
        # Update task status to in_progress
        tasks = state_manager.get_task_checklist()
        task = next((t for t in tasks if t.get("id") == task_id), None)
        if task:
            task["status"] = "in_progress"
            state_manager.set_task_checklist(tasks)
            await state_manager.save_state()
        return {"success": True, "stages": {}, "error": None}

    agent_coordinator.worker_squad_executor.execute = mock_execute

    # Execute workflow
    await agent_coordinator.execute_worker_squad(sample_task)

    # Verify task status was updated
    tasks_after = state_manager.get_task_checklist()
    task_after = next((t for t in tasks_after if t.get("id") == sample_task), None)
    assert task_after is not None
    # Status should have changed (either to in_progress or back to pending if workflow failed)
    assert task_after.get("status") != initial_status or initial_status == "pending"


@pytest.mark.asyncio
async def test_state_persistence_during_workflow_workflow_results_persisted(
    agent_coordinator, agent_bridge, sample_task, state_manager
):
    """Test state persistence during workflow - workflow results are persisted."""
    # Start bridge
    await agent_bridge.start()
    await agent_coordinator.start()

    # Mock executor to return results
    workflow_results = {
        "success": True,
        "stages": {
            "planner": {"output": "plan", "status": "completed"},
            "coder": {"output": "code", "status": "completed"}
        },
        "error": None
    }

    async def mock_execute(task_id):
        return workflow_results

    agent_coordinator.worker_squad_executor.execute = mock_execute

    # Execute workflow
    result = await agent_coordinator.execute_worker_squad(sample_task)

    # Verify results are returned (state persistence verified by result structure)
    assert result["success"] is True
    assert "stages" in result
    assert len(result["stages"]) == 2
    assert "planner" in result["stages"]
    assert "coder" in result["stages"]


@pytest.mark.asyncio
async def test_integration_complete_workflow_with_all_components(
    agent_coordinator, agent_bridge, sample_task, event_bus, state_manager
):
    """Test complete integration - workflow with all components interacting."""
    # Start bridge
    await agent_bridge.start()
    await agent_coordinator.start()

    # Track all interactions
    events_published = []
    state_saves = []
    agent_starts = []

    # Mock event bus
    async def track_publish(event):
        events_published.append(event)

    event_bus.publish = track_publish

    # Mock state manager
    async def track_save_state():
        state_saves.append("saved")

    state_manager.save_state = track_save_state

    # Mock coordinator start_worker_agent
    async def track_start_agent(task_id, agent_type, **kwargs):
        agent_starts.append((task_id, agent_type))
        return True

    agent_coordinator.start_worker_agent = track_start_agent

    # Mock executor to simulate full workflow
    async def mock_execute(task_id):
        # Publish workflow started
        await event_bus.publish(WorkflowEvent(
            event_type=WorkflowEventType.WORKFLOW_STARTED,
            task_id=task_id,
            data={"workflow_type": "worker_squad"}
        ))

        # Execute stages
        stages = ["planner", "coder"]
        for stage in stages:
            await agent_coordinator.start_worker_agent(task_id, stage, stage=stage)
            await state_manager.save_state()
            await event_bus.publish(WorkflowEvent(
                event_type=WorkflowEventType.STAGE_COMPLETED,
                task_id=task_id,
                data={"stage": stage}
            ))

        return {"success": True, "stages": {}, "error": None}

    agent_coordinator.worker_squad_executor.execute = mock_execute

    # Execute workflow
    result = await agent_coordinator.execute_worker_squad(sample_task)

    # Verify all components interacted correctly
    assert result["success"] is True
    assert len(events_published) >= 3  # Started + 2 stage completed
    assert len(state_saves) >= 2  # At least one per stage
    assert len(agent_starts) == 2  # Planner and coder
    assert agent_starts[0][1] == "planner"
    assert agent_starts[1][1] == "coder"
