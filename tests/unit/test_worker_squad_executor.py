"""
Unit tests for WorkerSquadExecutor.

Tests workflow execution, stage management, and TDD process.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from manifest.agents.worker_squad_executor import WorkerSquadExecutor


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
