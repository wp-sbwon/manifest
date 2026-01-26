"""
Unit tests for OrchestratorAgent.

Tests mission orchestration, task breakdown, and coordination.
"""
import pytest
from unittest.mock import Mock, AsyncMock
from manifest.runtime.agent.agents.orchestrator_agent import OrchestratorAgent


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
    state.get_mission_tree = Mock(return_value={})
    return state


@pytest.fixture
def orchestrator_agent(mock_executor, mock_state_manager):
    """Create an OrchestratorAgent instance."""
    agent = OrchestratorAgent(
        agent_id="orchestrator-1",
        executor=mock_executor,
        state_manager=mock_state_manager
    )
    # Initialize message_history
    agent.message_history = []
    return agent


def test_orchestrator_agent_initialization(orchestrator_agent):
    """Test OrchestratorAgent initialization."""
    assert orchestrator_agent.agent_id == "orchestrator-1"
    assert orchestrator_agent.executor is not None
    assert orchestrator_agent.state_manager is not None


@pytest.mark.asyncio
async def test_coordinate_mission(orchestrator_agent):
    """Test coordinating a mission."""
    mission_description = "Build feature X"
    context = {"mission_description": mission_description, "available_agents": ["planner", "coder"]}
    model_config = {"provider": "opencode"}
    
    # Mock executor to return a generator
    async def mock_execute(*args, **kwargs):
        yield {"type": "chunk", "content": "Coordination started"}
        yield {"type": "complete", "content": "Complete"}
    
    # The execute_agent is already an AsyncMock, but we need to make it return a generator
    orchestrator_agent.executor.execute_agent = mock_execute
    orchestrator_agent.state_manager.add_chat_message = Mock()
    orchestrator_agent._save_response = AsyncMock()
    
    results = []
    async for chunk in orchestrator_agent.coordinate(mission_description, context, model_config):
        results.append(chunk)
    
    assert len(results) > 0
