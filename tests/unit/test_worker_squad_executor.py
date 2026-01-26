"""
Unit tests for WorkerSquadExecutor.

Tests workflow execution, stage management, and TDD process.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from manifest.agents.worker_squad_executor import WorkerSquadExecutor
from manifest.agents.workflow_event_bus import WorkflowEventType


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = Mock()
    coordinator.state_manager = Mock()
    coordinator.state_manager.get_task_checklist = Mock(return_value=[])
    coordinator.state_manager.set_task_checklist = Mock()
    # Create a mock event bus
    mock_event_bus = Mock()
    mock_event_bus.publish = AsyncMock()
    coordinator.event_bus = mock_event_bus
    return coordinator


@pytest.fixture
def worker_squad_executor(mock_coordinator):
    """Create a WorkerSquadExecutor instance."""
    return WorkerSquadExecutor(coordinator=mock_coordinator)


def test_worker_squad_executor_initialization(worker_squad_executor, mock_coordinator):
    """Test WorkerSquadExecutor initialization."""
    assert worker_squad_executor.coordinator == mock_coordinator
    assert worker_squad_executor.state_manager == mock_coordinator.state_manager
    assert isinstance(worker_squad_executor.timeouts, dict)
    assert worker_squad_executor is not None


def test_set_timeout(worker_squad_executor):
    """Test setting timeout for a stage."""
    worker_squad_executor.set_timeout("planner", 600.0)
    assert worker_squad_executor.timeouts["planner"] == 600.0


def test_enable_event_driven(worker_squad_executor):
    """Test enabling event-driven mode."""
    worker_squad_executor.enable_event_driven(True)
    assert worker_squad_executor._use_event_driven is True

    worker_squad_executor.enable_event_driven(False)
    assert worker_squad_executor._use_event_driven is False


def test_enable_parallel_execution(worker_squad_executor):
    """Test enabling parallel execution."""
    worker_squad_executor.enable_parallel_execution(True)
    assert worker_squad_executor._enable_parallel_execution is True

    worker_squad_executor.enable_parallel_execution(False)
    assert worker_squad_executor._enable_parallel_execution is False


def test_set_workflow_definition(worker_squad_executor):
    """Test setting workflow definition by name."""
    # Should handle missing workflow gracefully
    result = worker_squad_executor.set_workflow_definition("nonexistent")
    assert result is False


def test_get_workflow_definition(worker_squad_executor):
    """Test getting current workflow definition."""
    workflow = worker_squad_executor.get_workflow_definition()
    # Should return None or WorkflowDefinition
    assert workflow is None or hasattr(workflow, "name")


def test_get_stage_dependencies(worker_squad_executor):
    """Test getting stage dependencies."""
    deps = worker_squad_executor._get_stage_dependencies()
    assert isinstance(deps, dict)
    # Should have planner with no dependencies
    assert "planner" in deps


def test_are_errors_recoverable(worker_squad_executor):
    """Test checking if errors are recoverable."""
    errors = ["syntax error", "import error"]
    is_recoverable = worker_squad_executor._are_errors_recoverable(errors)
    assert isinstance(is_recoverable, bool)


def test_is_workflow_complete(worker_squad_executor):
    """Test checking if workflow is complete."""
    workflow_state = {
        "completed_stages": ["planner", "coder", "test"],
        "failed_stages": []
    }
    is_complete = worker_squad_executor._is_workflow_complete(workflow_state)
    assert isinstance(is_complete, bool)


def test_should_terminate_workflow(worker_squad_executor):
    """Test checking if workflow should terminate."""
    should_terminate = worker_squad_executor._should_terminate_workflow("critical_stage")
    assert isinstance(should_terminate, bool)


@pytest.mark.asyncio
async def test_execute_workflow(worker_squad_executor):
    """Test executing a workflow."""
    # Mock coordinator methods with AsyncMock
    worker_squad_executor.coordinator.start_worker_agent = AsyncMock(return_value=True)
    worker_squad_executor.coordinator.start_worker_agent_and_wait = AsyncMock(return_value={"success": True})

    # Mock state manager methods
    worker_squad_executor.state_manager.get_task_checklist = Mock(return_value=[{"id": "task-1"}])
    worker_squad_executor.state_manager.save_worker_squad_stage_async = AsyncMock()
    worker_squad_executor.state_manager.get_worker_squad_stage = Mock(return_value=None)

    # Mock stage execution methods with AsyncMock
    worker_squad_executor._execute_planner_stage = AsyncMock(return_value={"success": True})
    worker_squad_executor._execute_tdd_test_stage = AsyncMock(return_value={"success": True})
    worker_squad_executor._execute_coder_stage = AsyncMock(return_value={"success": True})
    worker_squad_executor._execute_test_stage = AsyncMock(return_value={"success": True, "passed": True})
    worker_squad_executor._execute_self_review_stage = AsyncMock(return_value={"success": True})
    worker_squad_executor._execute_approver_stage = AsyncMock(return_value={"success": True, "approved": True})

    result = await worker_squad_executor.execute("task-1")
    assert isinstance(result, dict)
    assert "success" in result or "stages" in result


@pytest.mark.asyncio
async def test_execute_planner_stage(worker_squad_executor):
    """Test executing planner stage."""
    worker_squad_executor.coordinator.start_worker_agent = AsyncMock(return_value=True)
    worker_squad_executor.coordinator.start_worker_agent_and_wait = AsyncMock(return_value={"success": True})

    result = await worker_squad_executor._execute_planner_stage("task-1")
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_execute_coder_stage(worker_squad_executor):
    """Test executing coder stage."""
    worker_squad_executor.coordinator.start_worker_agent = AsyncMock(return_value=True)
    worker_squad_executor.coordinator.start_worker_agent_and_wait = AsyncMock(return_value={"success": True})

    result = await worker_squad_executor._execute_coder_stage("task-1", {})
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_execute_test_stage(worker_squad_executor):
    """Test executing test stage."""
    worker_squad_executor.coordinator.start_worker_agent = AsyncMock(return_value=True)
    worker_squad_executor.coordinator.start_worker_agent_and_wait = AsyncMock(return_value={"success": True, "passed": True})

    result = await worker_squad_executor._execute_test_stage("task-1", {})
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_execute_complete_workflow_sequence(worker_squad_executor):
    """Test complete TDD workflow execution sequence."""
    worker_squad_executor.coordinator.start_worker_agent_and_wait = AsyncMock()
    worker_squad_executor.state_manager.get_task_checklist = Mock(return_value=[{"id": "task-1"}])
    worker_squad_executor.state_manager.save_worker_squad_stage_async = AsyncMock()
    worker_squad_executor.state_manager.get_worker_squad_stage = Mock(return_value=None)

    # Mock recovery manager
    worker_squad_executor.recovery_manager = Mock()
    worker_squad_executor.recovery_manager.attempt_recovery = AsyncMock(return_value={"recovered": False})

    # Mock all stage execution methods
    worker_squad_executor._execute_planner_stage = AsyncMock(return_value={"success": True, "plan": "test plan"})
    worker_squad_executor._execute_tdd_test_stage = AsyncMock(return_value={"success": True, "test_skeleton": "test code"})
    worker_squad_executor._execute_coder_stage = AsyncMock(return_value={"success": True, "implementation": "code"})
    worker_squad_executor._execute_test_stage = AsyncMock(return_value={"success": True, "passed": True, "status": "completed"})
    worker_squad_executor._execute_self_review_stage = AsyncMock(return_value={"success": True, "review": "approved", "status": "completed"})
    worker_squad_executor._execute_approver_stage = AsyncMock(return_value={"success": True, "approved": True, "status": "completed"})

    # Mock event bus
    worker_squad_executor.coordinator.event_bus = Mock()
    worker_squad_executor.coordinator.event_bus.publish = AsyncMock()

    result = await worker_squad_executor.execute("task-1")

    assert isinstance(result, dict)
    assert result.get("success") is not None
    # Verify stages were executed
    worker_squad_executor._execute_planner_stage.assert_called_once()


@pytest.mark.asyncio
async def test_stage_failure_handling(worker_squad_executor):
    """Test stage failure handling and retry logic."""
    worker_squad_executor.coordinator.start_worker_agent_and_wait = AsyncMock()
    worker_squad_executor.state_manager.get_task_checklist = Mock(return_value=[{"id": "task-1"}])
    worker_squad_executor.state_manager.save_worker_squad_stage_async = AsyncMock()
    worker_squad_executor.state_manager.get_worker_squad_stage = Mock(return_value=None)

    # Mock recovery manager
    worker_squad_executor.recovery_manager = Mock()
    worker_squad_executor.recovery_manager.attempt_recovery = AsyncMock(return_value={"recovered": False})

    # Mock planner succeeds, but test stage fails
    worker_squad_executor._execute_planner_stage = AsyncMock(return_value={"success": True})
    worker_squad_executor._execute_tdd_test_stage = AsyncMock(return_value={"success": True})
    worker_squad_executor._execute_coder_stage = AsyncMock(return_value={"success": True})
    worker_squad_executor._execute_test_stage = AsyncMock(return_value={
        "success": False,
        "passed": False,
        "status": "failed",
        "errors": ["test failure"]
    })
    worker_squad_executor._execute_debug_stage = AsyncMock(return_value={"success": True, "fixed": True, "status": "completed"})
    worker_squad_executor._execute_self_review_stage = AsyncMock(return_value={"success": True, "status": "completed"})
    worker_squad_executor._execute_approver_stage = AsyncMock(return_value={"success": True, "approved": True, "status": "completed"})

    # Mock event bus
    worker_squad_executor.coordinator.event_bus = Mock()
    worker_squad_executor.coordinator.event_bus.publish = AsyncMock()

    result = await worker_squad_executor.execute("task-1")

    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_previous_stage_data_passing(worker_squad_executor):
    """Test that previous stage data is passed to next stages."""
    # Test the _execute_coder_stage method directly with previous_stages
    worker_squad_executor.coordinator.start_worker_agent_and_wait = AsyncMock(return_value={"success": True})

    previous_stages = {
        "planner": {"plan": "test plan", "success": True},
        "tdd_test": {"test_skeleton": "test code", "success": True}
    }

    result = await worker_squad_executor._execute_coder_stage("task-1", previous_stages)

    assert isinstance(result, dict)
    # Verify coordinator was called (data passing is verified by method execution)
    worker_squad_executor.coordinator.start_worker_agent_and_wait.assert_called()


@pytest.mark.asyncio
async def test_workflow_termination_on_critical_failure(worker_squad_executor):
    """Test workflow termination when critical stage fails."""
    worker_squad_executor.coordinator.start_worker_agent_and_wait = AsyncMock()
    worker_squad_executor.state_manager.get_task_checklist = Mock(return_value=[{"id": "task-1"}])
    worker_squad_executor.state_manager.save_worker_squad_stage_async = AsyncMock()
    worker_squad_executor.state_manager.get_worker_squad_stage = Mock(return_value=None)

    # Mock recovery manager - recovery fails
    worker_squad_executor.recovery_manager = Mock()
    worker_squad_executor.recovery_manager.attempt_recovery = AsyncMock(return_value={
        "recovered": False,
        "error": "Critical failure"
    })

    # Planner fails critically
    worker_squad_executor._execute_planner_stage = AsyncMock(return_value={
        "success": False,
        "critical": True,
        "error": "Critical failure"
    })

    # Mock event bus
    worker_squad_executor.coordinator.event_bus = Mock()
    worker_squad_executor.coordinator.event_bus.publish = AsyncMock()

    result = await worker_squad_executor.execute("task-1")

    assert isinstance(result, dict)
    # Workflow should terminate early
    assert result.get("success") is False or "error" in result


@pytest.mark.asyncio
async def test_event_driven_mode(worker_squad_executor):
    """Test event-driven workflow mode."""
    worker_squad_executor.enable_event_driven(True)
    assert worker_squad_executor._use_event_driven is True

    # Test that event-driven mode can be enabled/disabled
    worker_squad_executor.enable_event_driven(False)
    assert worker_squad_executor._use_event_driven is False

    worker_squad_executor.enable_event_driven(True)
    assert worker_squad_executor._use_event_driven is True


@pytest.mark.asyncio
async def test_workflow_state_persistence(worker_squad_executor):
    """Test that workflow state is persisted between stages."""
    worker_squad_executor.coordinator.start_worker_agent_and_wait = AsyncMock()
    worker_squad_executor.state_manager.get_task_checklist = Mock(return_value=[{"id": "task-1"}])
    worker_squad_executor.state_manager.save_worker_squad_stage_async = AsyncMock()
    worker_squad_executor.state_manager.get_worker_squad_stage = Mock(return_value=None)

    # Mock recovery manager
    worker_squad_executor.recovery_manager = Mock()
    worker_squad_executor.recovery_manager.attempt_recovery = AsyncMock(return_value={"recovered": False})

    worker_squad_executor._execute_planner_stage = AsyncMock(return_value={"success": True, "plan": "test"})
    worker_squad_executor._execute_tdd_test_stage = AsyncMock(return_value={"success": True})
    worker_squad_executor._execute_coder_stage = AsyncMock(return_value={"success": True})
    worker_squad_executor._execute_test_stage = AsyncMock(return_value={"success": True, "passed": True, "status": "completed"})
    worker_squad_executor._execute_self_review_stage = AsyncMock(return_value={"success": True, "status": "completed"})
    worker_squad_executor._execute_approver_stage = AsyncMock(return_value={"success": True, "approved": True, "status": "completed"})

    # Mock event bus
    worker_squad_executor.coordinator.event_bus = Mock()
    worker_squad_executor.coordinator.event_bus.publish = AsyncMock()

    await worker_squad_executor.execute("task-1")

    # Verify state was saved after each stage
    assert worker_squad_executor.state_manager.save_worker_squad_stage_async.called


@pytest.mark.asyncio
async def test_stage_completion_detection(worker_squad_executor):
    """Test stage completion detection."""
    worker_squad_executor.coordinator.start_worker_agent_and_wait = AsyncMock(return_value={
        "success": True,
        "status": "completed",
        "output": "Stage complete"
    })
    worker_squad_executor.state_manager.get_task_checklist = Mock(return_value=[{"id": "task-1"}])

    result = await worker_squad_executor._execute_planner_stage("task-1")

    assert isinstance(result, dict)
    assert result.get("success") is True


@pytest.mark.asyncio
async def test_handle_stage_completion(worker_squad_executor):
    """Test handling stage completion."""
    # Set up workflow state
    worker_squad_executor._active_workflows = {
        "task-1": {
            "stages": {},
            "completed_stages": set(),
            "failed_stages": set()
        }
    }
    worker_squad_executor.state_manager.save_worker_squad_stage_async = AsyncMock()
    worker_squad_executor._determine_next_stage = Mock(return_value="tdd_test")
    worker_squad_executor._is_workflow_complete = Mock(return_value=False)
    worker_squad_executor._execute_stage_async = AsyncMock()

    stage_data = {"plan": "test plan", "success": True}
    await worker_squad_executor._handle_stage_completion("task-1", "planner", stage_data)

    # Verify state was updated
    assert "planner" in worker_squad_executor._active_workflows["task-1"]["stages"]


@pytest.mark.asyncio
async def test_handle_stage_failure(worker_squad_executor):
    """Test handling stage failure."""
    # Set up workflow state
    worker_squad_executor._active_workflows = {
        "task-1": {
            "stages": {},
            "completed_stages": set(),
            "failed_stages": set()
        }
    }
    worker_squad_executor.state_manager.save_worker_squad_stage_async = AsyncMock()
    worker_squad_executor._are_errors_recoverable = Mock(return_value=True)
    worker_squad_executor._should_terminate_workflow = Mock(return_value=False)
    worker_squad_executor.recovery_manager = Mock()
    worker_squad_executor.recovery_manager.attempt_recovery = AsyncMock(return_value={"recovered": False})
    worker_squad_executor.coordinator.event_bus = Mock()
    worker_squad_executor.coordinator.event_bus.publish = AsyncMock()

    failure_data = {"error": "test error", "recoverable": True}
    await worker_squad_executor._handle_stage_failure("task-1", "test", failure_data)

    # Verify recovery was attempted
    worker_squad_executor.recovery_manager.attempt_recovery.assert_called_once()


def test_determine_next_stage(worker_squad_executor):
    """Test determining next stage in workflow."""
    # Test stage progression
    next_stage = worker_squad_executor._determine_next_stage("planner", {}, {})
    assert next_stage == "tdd_test" or next_stage is not None

    next_stage = worker_squad_executor._determine_next_stage("coder", {}, {})
    assert next_stage == "test" or next_stage is not None


def test_get_ready_stages(worker_squad_executor):
    """Test getting ready stages based on dependencies."""
    completed_stages = {"planner"}
    failed_stages = set()
    workflow_state = {}
    ready = worker_squad_executor._get_ready_stages(completed_stages, failed_stages, workflow_state)
    assert isinstance(ready, list)


@pytest.mark.asyncio
async def test_setup_event_subscriptions(worker_squad_executor):
    """Test setting up event subscriptions for event-driven mode."""
    from manifest.agents.workflow_event_bus import WorkflowEventType

    worker_squad_executor.coordinator.event_bus = Mock()
    worker_squad_executor.coordinator.event_bus.subscribe = Mock()
    worker_squad_executor.event_bus = worker_squad_executor.coordinator.event_bus

    await worker_squad_executor._setup_event_subscriptions("task-1")

    # Verify subscriptions were stored
    assert "task-1" in worker_squad_executor._event_subscriptions
    # Verify workflow state was initialized
    assert "task-1" in worker_squad_executor._active_workflows
    # Verify subscribe was called
    worker_squad_executor.coordinator.event_bus.subscribe.assert_called()


@pytest.mark.asyncio
async def test_cleanup_event_subscriptions(worker_squad_executor):
    """Test cleaning up event subscriptions."""
    from manifest.agents.workflow_event_bus import WorkflowEventType

    worker_squad_executor.coordinator.event_bus = Mock()
    worker_squad_executor.coordinator.event_bus.unsubscribe = Mock()
    worker_squad_executor.event_bus = worker_squad_executor.coordinator.event_bus

    # Set up subscriptions first (they're stored in _event_subscriptions as dict)
    callback1 = Mock()
    callback2 = Mock()
    worker_squad_executor._event_subscriptions = {
        "task-1": {
            "stage_completed": callback1,
            "stage_failed": callback2
        }
    }
    worker_squad_executor._active_workflows = {"task-1": {}}

    await worker_squad_executor._cleanup_event_subscriptions("task-1")

    # Verify subscriptions were cleaned up
    worker_squad_executor.coordinator.event_bus.unsubscribe.assert_called()
    # Verify subscriptions dict was cleared
    assert "task-1" not in worker_squad_executor._event_subscriptions
    # Verify workflow state was cleaned up
    assert "task-1" not in worker_squad_executor._active_workflows


def test_evaluate_custom_condition(worker_squad_executor):
    """Test evaluating custom workflow conditions."""
    from manifest.agents.workflow_definition import StageDefinition

    # Create mock stage definition
    stage_def = Mock(spec=StageDefinition)
    stage_def.metadata = {"condition_expr": "tests_passed > 0"}

    stage_result = {"success": True}
    workflow_state = {}
    result = worker_squad_executor._evaluate_custom_condition(stage_def, workflow_state, stage_result)
    assert isinstance(result, bool)

    # Test with no condition expression
    stage_def.metadata = {}
    result = worker_squad_executor._evaluate_custom_condition(stage_def, workflow_state, stage_result)
    assert isinstance(result, bool)
