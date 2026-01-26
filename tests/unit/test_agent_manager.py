"""
Unit tests for AgentManager.

Tests agent lifecycle management, task assignment, state synchronization,
and error recovery.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from manifest.runtime.agent.core.manager import AgentManager
from manifest.runtime.agent.core.executor_factory import ExecutorFactory
from manifest.core.config import ConfigManager
from manifest.core.state_manager import StateManager
from pathlib import Path


@pytest.fixture
def mock_config_manager(tmp_path):
    """Create a mock config manager."""
    config = Mock(spec=ConfigManager)
    config.get_setting = Mock(return_value="opencode")
    config.get_api_keys = Mock(return_value={})
    return config


@pytest.fixture
def mock_state_manager(tmp_path):
    """Create a mock state manager."""
    state = Mock(spec=StateManager)
    state.get_mission_tree = Mock(return_value={})
    state.set_mission_tree = AsyncMock()
    state.get_task_checklist = Mock(return_value=[])
    state.set_task_checklist = AsyncMock()
    state.add_chat_message = Mock()
    state.get_chat_history = Mock(return_value=[])
    state.save_state = AsyncMock()
    state.load_state = AsyncMock(return_value={})
    return state


@pytest.fixture
def mock_executor():
    """Create a mock executor."""
    executor = AsyncMock()
    executor.execute_agent = AsyncMock()
    executor.get_session_status = AsyncMock(return_value={"status": "idle"})
    executor.stop_session = AsyncMock(return_value=True)
    return executor


@pytest.fixture
def agent_manager(mock_state_manager, mock_executor):
    """Create an AgentManager instance for testing."""
    manager = AgentManager(
        state_manager=mock_state_manager,
        executor=mock_executor
    )
    return manager


def test_agent_manager_initialization(agent_manager):
    """Test AgentManager initialization."""
    assert agent_manager is not None
    assert agent_manager.state_manager is not None
    assert agent_manager.agents == {}
    assert agent_manager.executor is not None


@pytest.mark.asyncio
async def test_create_agent(agent_manager):
    """Test creating a new agent."""
    agent_type = "coder"
    context = {
        "task_description": "Test task",
        "task_scope": {},
        "available_tools": []
    }
    model_config = {"provider": "anthropic", "model": "claude-3-sonnet"}
    
    agent = await agent_manager.create_agent(
        agent_type=agent_type,
        context=context,
        model_config=model_config,
        task_id="test-task-1",
        terminal_router=None,
        tool_executor=None
    )
    
    assert agent is not None
    assert agent["type"] == agent_type
    assert agent["id"] == "test-task-1"
    assert agent["id"] in agent_manager.agents


@pytest.mark.asyncio
async def test_create_agent_duplicate_id(agent_manager):
    """Test creating agent with duplicate ID."""
    agent_type = "coder"
    context = {"task_description": "Test task", "task_scope": {}}
    model_config = {"provider": "anthropic", "model": "claude-3-sonnet"}
    task_id = "duplicate-task"
    
    # Create first agent
    agent1 = await agent_manager.create_agent(
        agent_type=agent_type,
        context=context,
        model_config=model_config,
        task_id=task_id,
        terminal_router=None,
        tool_executor=None
    )
    
    # Create second agent with same task_id (will overwrite or create new)
    agent2 = await agent_manager.create_agent(
        agent_type=agent_type,
        context=context,
        model_config=model_config,
        task_id=task_id,
        terminal_router=None,
        tool_executor=None
    )
    
    # Both should succeed (implementation allows overwriting)
    assert agent1 is not None
    assert agent2 is not None


@pytest.mark.asyncio
async def test_get_agent(agent_manager):
    """Test getting an agent by ID."""
    agent_type = "coder"
    context = {"task_description": "Test task", "task_scope": {}}
    model_config = {"provider": "anthropic", "model": "claude-3-sonnet"}
    task_id = "test-task-1"
    
    await agent_manager.create_agent(
        agent_type=agent_type,
        context=context,
        model_config=model_config,
        task_id=task_id,
        terminal_router=None,
        tool_executor=None
    )
    
    agent = agent_manager.get_agent(task_id)
    assert agent is not None
    assert agent["id"] == task_id
    assert agent["type"] == agent_type


@pytest.mark.asyncio
async def test_get_agent_not_found(agent_manager):
    """Test getting non-existent agent returns None."""
    agent = agent_manager.get_agent("non-existent")
    assert agent is None


@pytest.mark.asyncio
async def test_stop_agent(agent_manager):
    """Test stopping an agent."""
    agent_type = "coder"
    context = {"task_description": "Test task", "task_scope": {}}
    model_config = {"provider": "anthropic", "model": "claude-3-sonnet"}
    task_id = "test-task-1"
    
    await agent_manager.create_agent(
        agent_type=agent_type,
        context=context,
        model_config=model_config,
        task_id=task_id,
        terminal_router=None,
        tool_executor=None
    )
    
    result = await agent_manager.stop_agent(task_id)
    
    assert result is True
    assert agent_manager.agents[task_id]["status"] == "stopped"


@pytest.mark.asyncio
async def test_stop_agent_not_found(agent_manager):
    """Test stopping non-existent agent returns False."""
    result = await agent_manager.stop_agent("non-existent")
    assert result is False


@pytest.mark.asyncio
async def test_list_agents(agent_manager):
    """Test listing all active agents."""
    context = {"task_description": "Test task", "task_scope": {}}
    model_config = {"provider": "anthropic", "model": "claude-3-sonnet"}
    
    # Create agents without tool_executor to avoid errors
    await agent_manager.create_agent("coder", context, model_config, task_id="task-1", terminal_router=None, tool_executor=None)
    await agent_manager.create_agent("test", context, model_config, task_id="task-2", terminal_router=None, tool_executor=None)
    
    agents = agent_manager.list_agents()
    
    assert len(agents) == 2
    assert "task-1" in agents
    assert "task-2" in agents


def test_list_agents_empty(agent_manager):
    """Test listing agents when none exist."""
    agents = agent_manager.list_agents()
    assert agents == []


@pytest.mark.asyncio
async def test_start_agent(agent_manager):
    """Test starting an agent."""
    agent_type = "coder"
    context = {"task_description": "Test task", "task_scope": {}}
    model_config = {"provider": "anthropic", "model": "claude-3-sonnet"}
    task_id = "test-task-1"
    
    await agent_manager.create_agent(
        agent_type=agent_type,
        context=context,
        model_config=model_config,
        task_id=task_id,
        terminal_router=None,
        tool_executor=None
    )
    
    result = await agent_manager.start_agent(task_id)
    
    assert result is True
    assert agent_manager.agents[task_id]["status"] == "active"


@pytest.mark.asyncio
async def test_start_agent_not_found(agent_manager):
    """Test starting non-existent agent."""
    result = await agent_manager.start_agent("non-existent")
    assert result is False


@pytest.mark.asyncio
async def test_get_agent_status(agent_manager):
    """Test getting agent status via get_agent."""
    agent_type = "coder"
    context = {"task_description": "Test task", "task_scope": {}}
    model_config = {"provider": "anthropic", "model": "claude-3-sonnet"}
    task_id = "test-task-1"
    
    await agent_manager.create_agent(
        agent_type=agent_type,
        context=context,
        model_config=model_config,
        task_id=task_id,
        terminal_router=None,
        tool_executor=None
    )
    
    agent = agent_manager.get_agent(task_id)
    
    assert agent is not None
    assert "type" in agent
    assert "status" in agent
    assert agent["type"] == agent_type
    assert agent["status"] == "created"


def test_get_agent_status_not_found(agent_manager):
    """Test getting status for non-existent agent."""
    agent = agent_manager.get_agent("non-existent")
    assert agent is None


@pytest.mark.asyncio
async def test_shutdown(agent_manager):
    """Test shutting down all agents."""
    context = {"task_description": "Test task", "task_scope": {}}
    model_config = {"provider": "anthropic", "model": "claude-3-sonnet"}
    
    # Use agent types that don't require tool_executor
    await agent_manager.create_agent("test", context, model_config, task_id="task-1", terminal_router=None, tool_executor=None)
    await agent_manager.create_agent("debug", context, model_config, task_id="task-2", terminal_router=None, tool_executor=None)
    
    await agent_manager.shutdown()
    
    # All agents should be stopped
    assert agent_manager.agents["task-1"]["status"] == "stopped"
    assert agent_manager.agents["task-2"]["status"] == "stopped"


@pytest.mark.asyncio
async def test_generate_prompt(agent_manager):
    """Test prompt generation for different agent types."""
    context = {"task_description": "Test task", "task_scope": {}}
    
    # Test coder prompt
    prompt = agent_manager._generate_agent_prompt("coder", context, "task-1")
    assert prompt is not None
    assert isinstance(prompt, str)
    
    # Test planner prompt
    prompt = agent_manager._generate_agent_prompt("planner", context, "task-1")
    assert prompt is not None
    
    # Test orchestrator prompt
    context["mission_description"] = "Test mission"
    prompt = agent_manager._generate_agent_prompt("orchestrator", context, "task-1")
    assert prompt is not None


@pytest.mark.asyncio
async def test_concurrent_agent_creation(agent_manager):
    """Test creating multiple agents concurrently."""
    context = {"task_description": "Test task", "task_scope": {}}
    model_config = {"provider": "anthropic", "model": "claude-3-sonnet"}
    
    tasks = [
        agent_manager.create_agent("coder", context, model_config, task_id=f"task-{i}", terminal_router=None, tool_executor=None)
        for i in range(5)
    ]
    
    await asyncio.gather(*tasks)
    
    agents = agent_manager.list_agents()
    assert len(agents) == 5


@pytest.mark.asyncio
async def test_agent_prompts(agent_manager):
    """Test that agent prompts are loaded correctly."""
    assert "orchestrator" in agent_manager.agent_prompts
    assert "planner" in agent_manager.agent_prompts
    assert "coder" in agent_manager.agent_prompts
    assert "test" in agent_manager.agent_prompts


@pytest.mark.asyncio
async def test_agent_type_validation(agent_manager):
    """Test that invalid agent types are handled gracefully."""
    invalid_type = "invalid-type"
    context = {"task_description": "Test task", "task_scope": {}}
    model_config = {"provider": "anthropic", "model": "claude-3-sonnet"}
    
    # Should handle invalid type gracefully (uses default prompt)
    agent = await agent_manager.create_agent(
        agent_type=invalid_type,
        context=context,
        model_config=model_config,
        task_id="test-task",
        terminal_router=None,
        tool_executor=None
    )
    
    assert agent is not None
    assert agent["type"] == invalid_type
