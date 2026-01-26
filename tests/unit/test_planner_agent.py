"""
Unit tests for PlannerAgent.

Tests planning, task breakdown, and plan generation.
"""
import pytest
from unittest.mock import Mock, AsyncMock
from manifest.runtime.agent.agents.planner_agent import PlannerAgent


@pytest.fixture
def mock_executor():
    """Create a mock executor."""
    executor = AsyncMock()
    executor.execute_agent = AsyncMock()
    return executor


@pytest.fixture
def mock_state_manager():
    """Create a mock state manager."""
    state = Mock()
    state.get_task_checklist = Mock(return_value=[])
    return state


@pytest.fixture
def planner_agent(mock_executor, mock_state_manager):
    """Create a PlannerAgent instance."""
    return PlannerAgent(
        agent_id="planner-1",
        executor=mock_executor,
        state_manager=mock_state_manager
    )


def test_planner_agent_initialization(planner_agent):
    """Test PlannerAgent initialization."""
    assert planner_agent.agent_id == "planner-1"
    assert planner_agent.executor is not None
    assert planner_agent.state_manager is not None


@pytest.mark.asyncio
async def test_plan_task(planner_agent):
    """Test planning a task."""
    task_description = "Plan feature X"
    context = {"task_description": task_description}
    model_config = {"provider": "opencode"}

    # Mock executor to return a generator
    async def mock_execute(*args, **kwargs):
        yield {"type": "text", "content": "Planning started"}
        yield {"type": "complete"}

    planner_agent.executor.execute_agent = mock_execute

    results = []
    async for chunk in planner_agent.plan(task_description, context, model_config):
        results.append(chunk)

    assert len(results) > 0
