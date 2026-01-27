"""
Unit tests for OrchestratorAgent.

Tests mission orchestration, task breakdown, and coordination.
"""
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
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


# ========== TDL: Orchestrator Agent Tests ==========

@pytest.mark.asyncio
async def test_mission_breakdown(orchestrator_agent):
    """Test mission breakdown into tasks."""
    mission_description = "Build authentication system with login and logout"
    context = {
        "mission_description": mission_description,
        "available_agents": ["planner", "coder", "test"],
        "tier_0": {"content": "Policy content"},
        "tier_1": {"intent": {"features": []}}
    }
    model_config = {"provider": "opencode", "model": "test-model"}

    # Mock executor to return mission breakdown
    async def mock_execute(*args, **kwargs):
        breakdown = """
        Mission Breakdown:
        1. Task 1: Implement login functionality
        2. Task 2: Implement logout functionality
        3. Task 3: Add authentication tests
        """
        yield {"type": "chunk", "content": breakdown}
        yield {"type": "complete", "content": breakdown}

    orchestrator_agent.executor.execute_agent = mock_execute
    orchestrator_agent.state_manager.add_chat_message = Mock()
    orchestrator_agent._save_response = AsyncMock()

    results = []
    async for chunk in orchestrator_agent.coordinate(mission_description, context, model_config):
        results.append(chunk)

    assert len(results) >= 2
    # Verify mission breakdown content
    complete_chunk = [r for r in results if r.get("type") == "complete"]
    assert len(complete_chunk) > 0
    assert "Task" in complete_chunk[0].get("content", "")


@pytest.mark.asyncio
async def test_task_extraction_from_responses(orchestrator_agent):
    """Test task extraction from orchestrator responses."""
    # Mock a response with structured task data
    task_response = """
    {
        "tasks": [
            {"id": "task-1", "name": "Implement login", "dependencies": []},
            {"id": "task-2", "name": "Implement logout", "dependencies": ["task-1"]},
            {"id": "task-3", "name": "Add tests", "dependencies": ["task-1", "task-2"]}
        ]
    }
    """

    async def mock_execute(*args, **kwargs):
        yield {"type": "chunk", "content": task_response}
        yield {"type": "complete", "content": task_response}

    orchestrator_agent.executor.execute_agent = mock_execute
    orchestrator_agent.state_manager.add_chat_message = Mock()
    orchestrator_agent._save_response = AsyncMock()

    results = []
    async for chunk in orchestrator_agent.coordinate("Test mission", {}, {"provider": "opencode"}):
        results.append(chunk)

    # Verify response contains task data
    complete_chunk = [r for r in results if r.get("type") == "complete"]
    assert len(complete_chunk) > 0
    content = complete_chunk[0].get("content", "")
    # Should contain task information
    assert "task-1" in content or "tasks" in content.lower()


@pytest.mark.asyncio
async def test_task_dependency_analysis(orchestrator_agent):
    """Test task dependency analysis in orchestrator output."""
    # Mock response with dependencies
    dependency_response = """
    Task Dependencies:
    - Task 1: No dependencies
    - Task 2: Depends on Task 1
    - Task 3: Depends on Task 1 and Task 2
    """

    async def mock_execute(*args, **kwargs):
        yield {"type": "chunk", "content": dependency_response}
        yield {"type": "complete", "content": dependency_response}

    orchestrator_agent.executor.execute_agent = mock_execute
    orchestrator_agent.state_manager.add_chat_message = Mock()
    orchestrator_agent._save_response = AsyncMock()

    results = []
    async for chunk in orchestrator_agent.coordinate("Test mission", {}, {"provider": "opencode"}):
        results.append(chunk)

    # Verify dependency information is present
    complete_chunk = [r for r in results if r.get("type") == "complete"]
    assert len(complete_chunk) > 0
    content = complete_chunk[0].get("content", "")
    assert "depend" in content.lower() or "task" in content.lower()


@pytest.mark.asyncio
async def test_mission_state_management(orchestrator_agent):
    """Test mission state management (saving responses)."""
    response_content = "Mission breakdown complete with 3 tasks"

    async def mock_execute(*args, **kwargs):
        yield {"type": "complete", "content": response_content}

    orchestrator_agent.executor.execute_agent = mock_execute
    orchestrator_agent.state_manager.add_chat_message = Mock()
    orchestrator_agent.state_manager.save_state = AsyncMock()

    results = []
    async for chunk in orchestrator_agent.coordinate("Test mission", {}, {"provider": "opencode"}):
        results.append(chunk)

    # Verify state was saved
    orchestrator_agent.state_manager.add_chat_message.assert_called_once()
    orchestrator_agent.state_manager.save_state.assert_called_once()

    # Verify message was added to correct channel
    call_args = orchestrator_agent.state_manager.add_chat_message.call_args
    assert "orchestrator" in call_args[0][0]  # Channel name
    assert call_args[0][1] == "assistant"  # Role
    assert response_content in call_args[0][2]  # Content


@pytest.mark.asyncio
async def test_mission_state_persistence(orchestrator_agent):
    """Test that mission state persists across calls."""
    # First call
    async def mock_execute_1(*args, **kwargs):
        yield {"type": "complete", "content": "First response"}

    orchestrator_agent.executor.execute_agent = mock_execute_1
    orchestrator_agent.state_manager.add_chat_message = Mock()
    orchestrator_agent.state_manager.save_state = AsyncMock()

    async for chunk in orchestrator_agent.coordinate("Mission 1", {}, {"provider": "opencode"}):
        pass

    # Verify state was saved
    assert orchestrator_agent.state_manager.save_state.call_count == 1

    # Second call - should maintain message history
    async def mock_execute_2(*args, **kwargs):
        yield {"type": "complete", "content": "Second response"}

    orchestrator_agent.executor.execute_agent = mock_execute_2

    async for chunk in orchestrator_agent.coordinate("Mission 2", {}, {"provider": "opencode"}):
        pass

    # Verify state was saved again
    assert orchestrator_agent.state_manager.save_state.call_count == 2


@pytest.mark.asyncio
async def test_response_streaming_and_parsing(orchestrator_agent):
    """Test response streaming and parsing (chunk handling)."""
    chunks = [
        {"type": "chunk", "content": "Mission "},
        {"type": "chunk", "content": "breakdown "},
        {"type": "chunk", "content": "in progress"},
        {"type": "complete", "content": "Mission breakdown complete"}
    ]

    async def mock_execute(*args, **kwargs):
        for chunk in chunks:
            yield chunk

    orchestrator_agent.executor.execute_agent = mock_execute
    orchestrator_agent.state_manager.add_chat_message = Mock()
    orchestrator_agent._save_response = AsyncMock()

    results = []
    async for chunk in orchestrator_agent.coordinate("Test mission", {}, {"provider": "opencode"}):
        results.append(chunk)

    # Verify all chunks were received
    assert len(results) == 4

    # Verify chunk types
    chunk_types = [r.get("type") for r in results]
    assert "chunk" in chunk_types
    assert "complete" in chunk_types

    # Verify message history was updated incrementally
    assert len(orchestrator_agent.message_history) > 0
    # Last message should contain accumulated content
    last_message = orchestrator_agent.message_history[-1]
    assert last_message["role"] == "assistant"
    assert "Mission" in last_message["content"]


@pytest.mark.asyncio
async def test_response_parsing_structured_data(orchestrator_agent):
    """Test parsing structured data from orchestrator responses."""
    structured_response = """
    {
        "mission": "Build auth system",
        "tasks": [
            {"name": "Task 1", "priority": "high"},
            {"name": "Task 2", "priority": "medium"}
        ],
        "estimated_sprints": 2
    }
    """

    async def mock_execute(*args, **kwargs):
        yield {"type": "chunk", "content": structured_response}
        yield {"type": "complete", "content": structured_response}

    orchestrator_agent.executor.execute_agent = mock_execute
    orchestrator_agent.state_manager.add_chat_message = Mock()
    orchestrator_agent._save_response = AsyncMock()

    results = []
    async for chunk in orchestrator_agent.coordinate("Test mission", {}, {"provider": "opencode"}):
        results.append(chunk)

    # Verify structured data can be parsed
    complete_chunk = [r for r in results if r.get("type") == "complete"]
    assert len(complete_chunk) > 0
    content = complete_chunk[0].get("content", "")

    # Try to parse as JSON if it looks like JSON
    if content.strip().startswith("{"):
        try:
            parsed = json.loads(content)
            assert "tasks" in parsed or "mission" in parsed
        except json.JSONDecodeError:
            # Not valid JSON, but that's okay - just verify content exists
            assert len(content) > 0


@pytest.mark.asyncio
async def test_start_ideation(orchestrator_agent):
    """Test ideation mode for PRD creation."""
    user_input = "I want to build a task management app"
    context = {"tier_0": {"content": "Policy"}, "tier_1": {"intent": {}}}
    model_config = {"provider": "opencode"}
    ideation_history = [{"role": "user", "content": user_input}]

    async def mock_execute(*args, **kwargs):
        yield {"type": "chunk", "content": "What features do you need?"}
        yield {"type": "complete", "content": "What features do you need?"}

    orchestrator_agent.executor.execute_agent = mock_execute
    orchestrator_agent.state_manager.add_chat_message = Mock()
    orchestrator_agent._save_response = AsyncMock()

    results = []
    async for chunk in orchestrator_agent.start_ideation(
        user_input, context, model_config, ideation_history
    ):
        results.append(chunk)

    assert len(results) > 0
    assert any("features" in r.get("content", "").lower() for r in results)


@pytest.mark.asyncio
async def test_create_sprint_plan(orchestrator_agent):
    """Test sprint plan creation from PRD, architecture, and blueprint."""
    prd_data = {"title": "Auth System PRD", "features": ["login", "logout"]}
    architecture_data = {"components": [{"id": "auth", "name": "Auth Service"}]}
    blueprint_data = {"components": [{"id": "auth", "files": ["auth.py"]}]}
    context = {"tier_0": {"content": "Policy"}}
    model_config = {"provider": "opencode"}

    async def mock_execute(*args, **kwargs):
        yield {"type": "chunk", "content": "Sprint plan:"}
        yield {"type": "complete", "content": "Sprint 1: Task 1, Task 2"}

    orchestrator_agent.executor.execute_agent = mock_execute
    orchestrator_agent.state_manager.add_chat_message = Mock()
    orchestrator_agent._save_response = AsyncMock()

    results = []
    async for chunk in orchestrator_agent.create_sprint_plan(
        prd_data, architecture_data, blueprint_data, context, model_config
    ):
        results.append(chunk)

    assert len(results) > 0
    complete_chunk = [r for r in results if r.get("type") == "complete"]
    assert len(complete_chunk) > 0
    assert "Sprint" in complete_chunk[0].get("content", "")


@pytest.mark.asyncio
async def test_message_history_accumulation(orchestrator_agent):
    """Test that message history accumulates across chunks."""
    async def mock_execute(*args, **kwargs):
        yield {"type": "chunk", "content": "Part 1 "}
        yield {"type": "chunk", "content": "Part 2 "}
        yield {"type": "chunk", "content": "Part 3"}
        yield {"type": "complete", "content": "Part 1 Part 2 Part 3"}

    orchestrator_agent.executor.execute_agent = mock_execute
    orchestrator_agent.state_manager.add_chat_message = Mock()
    orchestrator_agent._save_response = AsyncMock()

    async for chunk in orchestrator_agent.coordinate("Test", {}, {"provider": "opencode"}):
        pass

    # Verify message history has accumulated content
    assert len(orchestrator_agent.message_history) > 0
    last_message = orchestrator_agent.message_history[-1]
    assert "Part 1" in last_message["content"]
    assert "Part 2" in last_message["content"]
    assert "Part 3" in last_message["content"]


@pytest.mark.asyncio
async def test_coordinate_with_terminal_router(orchestrator_agent):
    """Test coordinate with terminal router available."""
    from unittest.mock import Mock
    orchestrator_agent.terminal_router = Mock()

    async def mock_execute(*args, **kwargs):
        yield {"type": "complete", "content": "Mission complete"}

    orchestrator_agent.executor.execute_agent = mock_execute
    orchestrator_agent.state_manager.add_chat_message = Mock()
    orchestrator_agent._save_response = AsyncMock()

    results = []
    async for chunk in orchestrator_agent.coordinate("Test mission", {}, {"provider": "opencode"}):
        results.append(chunk)

    # Should work with or without terminal router
    assert len(results) > 0
