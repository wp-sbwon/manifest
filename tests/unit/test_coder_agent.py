"""
Unit tests for CoderAgent.

Tests code implementation, tool usage, and task execution.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from manifest.runtime.agent.agents.coder_agent import CoderAgent


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
    state.add_chat_message = Mock()
    return state


@pytest.fixture
def coder_agent(mock_executor, mock_state_manager):
    """Create a CoderAgent instance."""
    return CoderAgent(
        agent_id="coder-1",
        executor=mock_executor,
        state_manager=mock_state_manager
    )


def test_coder_agent_initialization(coder_agent):
    """Test CoderAgent initialization."""
    assert coder_agent.agent_id == "coder-1"
    assert coder_agent.executor is not None
    assert coder_agent.state_manager is not None


@pytest.mark.asyncio
async def test_implement_task(coder_agent):
    """Test implementing a task."""
    task_description = "Implement feature X"
    context = {"task_description": task_description}
    task_scope = {}
    model_config = {"provider": "opencode"}
    
    # Mock executor to return a generator
    async def mock_execute(*args, **kwargs):
        yield {"type": "text", "content": "Implementation started"}
        yield {"type": "complete"}
    
    # Replace the executor's execute_agent method with our async generator
    coder_agent.executor.execute_agent = mock_execute
    
    results = []
    async for chunk in coder_agent.implement(task_description, context, task_scope, model_config):
        results.append(chunk)
    
    assert len(results) > 0
    # Verify we got expected results
    assert any(r.get("type") in ["text", "complete"] for r in results)


@pytest.mark.asyncio
async def test_self_review(coder_agent):
    """Test self review functionality."""
    planner_plan = "Plan to implement feature X"
    implementation_summary = "Implemented feature X with tests"
    context = {"task_description": "Review implementation"}
    model_config = {"provider": "opencode"}
    
    # Mock executor to return a generator
    async def mock_execute(*args, **kwargs):
        yield {"type": "chunk", "content": "Review started"}
        yield {"type": "complete", "content": "Complete"}
    
    coder_agent.executor.execute_agent = mock_execute
    
    results = []
    async for chunk in coder_agent.self_review(planner_plan, implementation_summary, context, model_config):
        results.append(chunk)
    
    assert len(results) > 0
