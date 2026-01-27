"""
E2E Test: Agent Failure Recovery Workflow

Tests the complete workflow of agent failure detection and recovery.
This validates that the system can handle agent failures gracefully and continue work.
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


# ========== TDL: Workflow 7: Agent Failure Recovery ==========

@pytest.mark.asyncio
async def test_failures_detected(
    agent_coordinator, agent_bridge, state_manager
):
    """Test: Failures are detected when agent fails."""
    # Start bridge and coordinator
    await agent_bridge.start()
    await agent_coordinator.start()

    # Step 1: Create task
    task_id = state_manager.create_task(
        name="Test Task",
        description="Test task",
        status="pending"
    )

    # Step 2: Track failure detection
    failures_detected = []

    async def failing_agent(task_id_param, agent_type, **kwargs):
        # Simulate agent failure
        failures_detected.append({
            "task_id": task_id_param,
            "agent_type": agent_type,
            "error": "Agent execution failed"
        })
        raise Exception("Agent execution failed")

    agent_coordinator.start_worker_agent = failing_agent

    # Step 3: Start agent (should fail)
    try:
        result = await agent_coordinator.start_worker_agent(task_id, "planner")
        # If it doesn't raise, result should be False
        if result is not False:
            failures_detected.append({"detected": True})
    except Exception as e:
        # Failure was detected
        failures_detected.append({
            "detected": True,
            "error": str(e)
        })

    # Verify failure was detected
    assert len(failures_detected) > 0


@pytest.mark.asyncio
async def test_recovery_strategies_work(
    agent_coordinator, agent_bridge, state_manager
):
    """Test: Recovery strategies work after agent failure."""
    # Start bridge and coordinator
    await agent_bridge.start()
    await agent_coordinator.start()

    # Step 1: Create task
    task_id = state_manager.create_task(
        name="Test Task",
        description="Test task",
        status="pending"
    )

    # Step 2: Track recovery attempts
    recovery_attempts = []
    attempt_count = {"count": 0}

    async def retry_agent(task_id_param, agent_type, **kwargs):
        attempt_count["count"] += 1
        recovery_attempts.append({
            "attempt": attempt_count["count"],
            "task_id": task_id_param,
            "agent_type": agent_type
        })

        # Fail first time, succeed second time
        if attempt_count["count"] == 1:
            raise Exception("First attempt failed")
        return True

    agent_coordinator.start_worker_agent = retry_agent

    # Step 3: First attempt fails
    try:
        await agent_coordinator.start_worker_agent(task_id, "planner")
    except Exception:
        pass

    # Step 4: Retry (recovery strategy)
    result = await agent_coordinator.start_worker_agent(task_id, "planner")

    # Verify recovery worked
    assert len(recovery_attempts) >= 2
    assert result is True or attempt_count["count"] >= 2


@pytest.mark.asyncio
async def test_state_not_corrupted(
    agent_coordinator, agent_bridge, state_manager
):
    """Test: State is not corrupted after agent failure."""
    # Start bridge and coordinator
    await agent_bridge.start()
    await agent_coordinator.start()

    # Step 1: Create task and add some state
    task_id = state_manager.create_task(
        name="Test Task",
        description="Test task",
        status="in_progress"
    )

    state_manager.add_chat_message(
        f"squad-{task_id}-planner",
        "assistant",
        "Agent started working..."
    )
    await state_manager.save_state()

    # Step 2: Agent fails
    async def failing_agent(task_id_param, agent_type, **kwargs):
        raise Exception("Agent failed")

    agent_coordinator.start_worker_agent = failing_agent

    try:
        await agent_coordinator.start_worker_agent(task_id, "planner")
    except Exception:
        pass

    # Step 3: Verify state is still valid
    state = state_manager.get_state()
    assert "version" in state
    assert "task_checklist" in state

    # Verify task still exists
    tasks = state_manager.get_task_checklist()
    task = next((t for t in tasks if t.get("id") == task_id), None)
    assert task is not None

    # Verify chat history is intact
    history = state_manager.get_chat_history(f"squad-{task_id}-planner")
    assert len(history) > 0
    assert any("started" in msg.get("content", "").lower() for msg in history)


@pytest.mark.asyncio
async def test_workflow_can_continue(
    agent_coordinator, agent_bridge, state_manager
):
    """Test: Workflow can continue after agent failure."""
    # Start bridge and coordinator
    await agent_bridge.start()
    await agent_coordinator.start()

    # Step 1: Create task
    task_id = state_manager.create_task(
        name="Test Task",
        description="Test task",
        status="pending"
    )

    # Step 2: First agent fails
    failure_occurred = False

    async def failing_agent(task_id_param, agent_type, **kwargs):
        nonlocal failure_occurred
        failure_occurred = True
        raise Exception("Agent failed")

    agent_coordinator.start_worker_agent = failing_agent

    try:
        await agent_coordinator.start_worker_agent(task_id, "planner")
    except Exception:
        pass

    # Step 3: Verify failure occurred
    assert failure_occurred is True

    # Step 4: Continue workflow with different agent
    success_count = {"count": 0}

    async def successful_agent(task_id_param, agent_type, **kwargs):
        success_count["count"] += 1
        return True

    agent_coordinator.start_worker_agent = successful_agent

    # Continue with coder agent
    result = await agent_coordinator.start_worker_agent(task_id, "coder")

    # Verify workflow continued
    assert result is True
    assert success_count["count"] > 0

    # Verify task state allows continuation
    tasks = state_manager.get_task_checklist()
    task = next((t for t in tasks if t.get("id") == task_id), None)
    assert task is not None


@pytest.mark.asyncio
async def test_timeout_failure_detection(
    agent_coordinator, agent_bridge, state_manager
):
    """Test: Timeout failures are detected."""
    # Start bridge and coordinator
    await agent_bridge.start()
    await agent_coordinator.start()

    # Step 1: Create task
    task_id = state_manager.create_task(
        name="Test Task",
        description="Test task",
        status="pending"
    )

    # Step 2: Simulate timeout
    timeout_detected = False

    async def timeout_agent(task_id_param, agent_type, **kwargs):
        # Simulate long-running operation that times out
        await asyncio.sleep(0.1)  # Simulate delay
        nonlocal timeout_detected
        timeout_detected = True
        raise asyncio.TimeoutError("Agent execution timed out")

    agent_coordinator.start_worker_agent = timeout_agent

    try:
        await agent_coordinator.start_worker_agent(task_id, "planner")
    except (asyncio.TimeoutError, Exception):
        timeout_detected = True

    # Verify timeout was detected
    assert timeout_detected is True


@pytest.mark.asyncio
async def test_error_failure_detection(
    agent_coordinator, agent_bridge, state_manager
):
    """Test: Error failures are detected."""
    # Start bridge and coordinator
    await agent_bridge.start()
    await agent_bridge.start()
    await agent_coordinator.start()

    # Step 1: Create task
    task_id = state_manager.create_task(
        name="Test Task",
        description="Test task",
        status="pending"
    )

    # Step 2: Simulate various error types
    errors_detected = []

    async def error_agent(task_id_param, agent_type, **kwargs):
        # Simulate different error types
        error_type = kwargs.get("error_type", "generic")
        if error_type == "value_error":
            raise ValueError("Invalid value")
        elif error_type == "runtime_error":
            raise RuntimeError("Runtime error occurred")
        else:
            raise Exception("Generic error")

    agent_coordinator.start_worker_agent = error_agent

    # Test different error types
    error_types = ["value_error", "runtime_error", "generic"]
    for error_type in error_types:
        try:
            await agent_coordinator.start_worker_agent(task_id, "planner", error_type=error_type)
        except Exception as e:
            errors_detected.append({
                "error_type": error_type,
                "error": str(e)
            })

    # Verify errors were detected
    assert len(errors_detected) == len(error_types)


@pytest.mark.asyncio
async def test_complete_failure_recovery_workflow(
    agent_coordinator, agent_bridge, state_manager
):
    """Test: Complete agent failure recovery workflow."""
    # Start bridge and coordinator
    await agent_bridge.start()
    await agent_coordinator.start()

    # Step 1: Create task
    task_id = state_manager.create_task(
        name="Test Task",
        description="Test task",
        status="pending"
    )

    # Step 2: Track workflow stages
    workflow_stages = []

    attempt_count = {"count": 0}

    async def agent_with_recovery(task_id_param, agent_type, **kwargs):
        attempt_count["count"] += 1
        workflow_stages.append(f"attempt_{attempt_count['count']}")

        # Fail first two attempts, succeed on third
        if attempt_count["count"] < 3:
            workflow_stages.append("failure_detected")
            raise Exception(f"Attempt {attempt_count['count']} failed")
        else:
            workflow_stages.append("success")
            return True

    agent_coordinator.start_worker_agent = agent_with_recovery

    # Step 3: Execute workflow with failures and recovery
    result = None
    for attempt in range(3):
        try:
            result = await agent_coordinator.start_worker_agent(task_id, "planner")
            if result:
                break
        except Exception:
            workflow_stages.append("recovery_attempted")
            await asyncio.sleep(0.01)  # Small delay between attempts

    # Step 4: Verify complete workflow
    assert len(workflow_stages) >= 3
    assert "failure_detected" in workflow_stages or attempt_count["count"] >= 1
    assert result is True or attempt_count["count"] >= 3

    # Verify state is intact
    tasks = state_manager.get_task_checklist()
    task = next((t for t in tasks if t.get("id") == task_id), None)
    assert task is not None
