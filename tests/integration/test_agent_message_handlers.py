"""
Integration tests for agent handle_message + request/response.

Verifies that Planner, Coder, and Test agents correctly handle REQUEST
messages and respond via the message bus so that request() returns
the response content.
"""
import pytest
from unittest.mock import Mock, AsyncMock
from manifest.agents.agent_message_bus import AgentMessageBus
from manifest.runtime.agent.agents.planner_agent import PlannerAgent
from manifest.runtime.agent.agents.coder_agent import CoderAgent
from manifest.runtime.agent.agents.test_agent import TestAgent


@pytest.fixture
def message_bus():
    """Create an AgentMessageBus instance."""
    return AgentMessageBus()


@pytest.fixture
def mock_executor():
    """Minimal mock executor (not used by handle_message)."""
    return AsyncMock()


@pytest.fixture
def mock_state_manager():
    """Minimal mock state manager (used for task checklist in some agents)."""
    state = Mock()
    state.get_task_checklist = Mock(return_value=[])
    return state


@pytest.fixture
def planner_agent(mock_executor, mock_state_manager):
    """Create a PlannerAgent with mocks."""
    return PlannerAgent(
        agent_id="planner-1",
        executor=mock_executor,
        state_manager=mock_state_manager,
    )


@pytest.fixture
def coder_agent(mock_executor, mock_state_manager):
    """Create a CoderAgent with mocks."""
    return CoderAgent(
        agent_id="coder-1",
        executor=mock_executor,
        state_manager=mock_state_manager,
    )


@pytest.fixture
def test_agent(mock_executor, mock_state_manager):
    """Create a TestAgent with mocks."""
    return TestAgent(
        agent_id="test-1",
        executor=mock_executor,
        state_manager=mock_state_manager,
    )


@pytest.mark.asyncio
async def test_planner_responds_to_plan_details(message_bus, planner_agent):
    """Planner responds to plan_details request with _last_plan."""
    planner_agent.message_bus = message_bus
    planner_agent._last_plan = {"content": "Step 1. Do X. Step 2. Do Y."}

    async def handler(msg):
        await planner_agent.handle_message(msg)

    message_bus.register_agent("client", "client")
    message_bus.register_agent("planner-1", "planner", message_handler=handler)

    response = await message_bus.request(
        from_agent_id="client",
        to_agent_id="planner-1",
        subject="plan_details",
        content={},
        timeout=2.0,
    )

    assert response is not None
    assert response.get("success") is True
    content = response.get("content", {})
    assert "plan" in content
    assert content["plan"] == {"content": "Step 1. Do X. Step 2. Do Y."}
    assert content.get("agent_id") == "planner-1"


@pytest.mark.asyncio
async def test_planner_responds_to_plan_status(message_bus, planner_agent):
    """Planner responds to plan_status / is_plan_ready with has_plan."""
    planner_agent.message_bus = message_bus
    planner_agent._last_plan = {"content": "Plan here"}

    async def handler(msg):
        await planner_agent.handle_message(msg)

    message_bus.register_agent("client", "client")
    message_bus.register_agent("planner-1", "planner", message_handler=handler)

    response = await message_bus.request(
        from_agent_id="client",
        to_agent_id="planner-1",
        subject="plan_status",
        content={},
        timeout=2.0,
    )

    assert response is not None
    assert response.get("success") is True
    assert response.get("content", {}).get("has_plan") is True


@pytest.mark.asyncio
async def test_planner_plan_status_no_plan_yet(message_bus, planner_agent):
    """Planner reports has_plan False when _last_plan is None."""
    planner_agent.message_bus = message_bus
    planner_agent._last_plan = None

    async def handler(msg):
        await planner_agent.handle_message(msg)

    message_bus.register_agent("client", "client")
    message_bus.register_agent("planner-1", "planner", message_handler=handler)

    response = await message_bus.request(
        from_agent_id="client",
        to_agent_id="planner-1",
        subject="is_plan_ready",
        content={},
        timeout=2.0,
    )

    assert response is not None
    assert response.get("success") is True
    assert response.get("content", {}).get("has_plan") is False


@pytest.mark.asyncio
async def test_coder_responds_to_implementation_status(message_bus, coder_agent):
    """Coder responds to implementation_status with status / has_implementation."""
    coder_agent.message_bus = message_bus
    coder_agent._implementation_status = {"modified_files": ["a.py"], "done": True}

    async def handler(msg):
        await coder_agent.handle_message(msg)

    message_bus.register_agent("client", "client")
    message_bus.register_agent("coder-1", "coder", message_handler=handler)

    response = await message_bus.request(
        from_agent_id="client",
        to_agent_id="coder-1",
        subject="implementation_status",
        content={},
        timeout=2.0,
    )

    assert response is not None
    assert response.get("success") is True
    content = response.get("content", {})
    assert content.get("status") == {"modified_files": ["a.py"], "done": True}
    assert content.get("has_implementation") is True
    assert content.get("agent_id") == "coder-1"


@pytest.mark.asyncio
async def test_test_agent_responds_to_test_results(message_bus, test_agent):
    """Test agent responds to test_results / get_test_results with _test_results."""
    test_agent.message_bus = message_bus
    test_agent._test_results = {"content": "3 passed, 0 failed", "task_id": "t1"}

    async def handler(msg):
        await test_agent.handle_message(msg)

    message_bus.register_agent("client", "client")
    message_bus.register_agent("test-1", "test", message_handler=handler)

    response = await message_bus.request(
        from_agent_id="client",
        to_agent_id="test-1",
        subject="test_results",
        content={},
        timeout=2.0,
    )

    assert response is not None
    assert response.get("success") is True
    content = response.get("content", {})
    assert content.get("test_results") == {"content": "3 passed, 0 failed", "task_id": "t1"}
    assert content.get("has_results") is True
    assert content.get("agent_id") == "test-1"


@pytest.mark.asyncio
async def test_test_agent_responds_to_test_status(message_bus, test_agent):
    """Test agent responds to test_status with has_results."""
    test_agent.message_bus = message_bus
    test_agent._test_results = None

    async def handler(msg):
        await test_agent.handle_message(msg)

    message_bus.register_agent("client", "client")
    message_bus.register_agent("test-1", "test", message_handler=handler)

    response = await message_bus.request(
        from_agent_id="client",
        to_agent_id="test-1",
        subject="test_status",
        content={},
        timeout=2.0,
    )

    assert response is not None
    assert response.get("success") is True
    assert response.get("content", {}).get("has_results") is False
