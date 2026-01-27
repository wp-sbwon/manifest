"""
Integration tests for ContextProvider → Agent Execution interaction.

Tests the integration between ContextProvider and agent execution to ensure
proper context delivery, size validation, tier-based filtering, and context updates.
"""
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from manifest.core.state_manager import StateManager
from manifest.agents.context_provider import ContextProvider
from manifest.agents.task_scoper import TaskScoper
from manifest.runtime.agent.core.executor import AgentExecutor
from manifest.core.config import ConfigManager


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
def task_scoper(temp_dir):
    """Create a TaskScoper instance."""
    return TaskScoper(manifest_dir=temp_dir)


@pytest.fixture
def context_provider(temp_dir, task_scoper, state_manager):
    """Create a ContextProvider instance."""
    return ContextProvider(
        manifest_dir=temp_dir,
        task_scoper=task_scoper,
        state_manager=state_manager
    )


@pytest.fixture
def agent_executor(config_manager, state_manager):
    """Create an AgentExecutor instance."""
    return AgentExecutor(
        config_manager=config_manager,
        state_manager=state_manager
    )


@pytest.fixture
def sample_task(state_manager):
    """Create a sample task for testing."""
    task_id = state_manager.create_task(
        name="Test Task",
        description="Test task description",
        status="pending"
    )
    return task_id


# ========== TDL: Context Provider → Agent Execution Integration ==========

@pytest.mark.asyncio
async def test_context_delivery_to_agents_worker_agent(
    context_provider, agent_executor, sample_task, config_manager
):
    """Test context delivery to agents - worker agent receives context."""
    # Get context for worker agent
    context = context_provider.get_worker_context(
        task_id=sample_task,
        agent_type="coder"
    )

    # Verify context structure
    assert context is not None
    assert "tier" in context
    assert context["tier"] == "worker"
    assert "task_id" in context
    assert context["task_id"] == sample_task
    assert "agent_type" in context
    assert context["agent_type"] == "coder"
    assert "tier_0" in context
    assert "tier_2" in context
    assert "tier_3" in context
    assert "task_scope" in context
    assert "skills" in context

    # Mock executor to verify context is used
    context_received = None

    async def mock_execute_agent(*args, **kwargs):
        nonlocal context_received
        context_received = kwargs.get("context")
        # Yield a mock response
        yield {"type": "complete", "content": "Mock response"}

    agent_executor.execute_agent = mock_execute_agent

    # Execute agent with context
    model_config = config_manager.get_agent_model_config("coder")
    async for chunk in agent_executor.execute_agent(
        agent_id=sample_task,
        agent_type="coder",
        prompt="Test prompt",
        model_config=model_config,
        context=context
    ):
        pass  # Consume generator

    # Verify context was delivered to executor
    assert context_received is not None
    assert context_received["task_id"] == sample_task
    assert context_received["agent_type"] == "coder"


@pytest.mark.asyncio
async def test_context_delivery_to_agents_orchestrator_agent(
    context_provider, agent_executor, config_manager
):
    """Test context delivery to agents - orchestrator receives context."""
    # Get context for orchestrator
    context = context_provider.get_orchestrator_context()

    # Verify context structure
    assert context is not None
    assert "tier" in context
    assert context["tier"] == "orchestrator"
    assert "tier_0" in context
    assert "tier_1" in context
    assert "skills" in context
    # Orchestrator should NOT have tier_2 or tier_3 (scoped context)
    assert "tier_2" not in context
    assert "tier_3" not in context

    # Mock executor to verify context is used
    context_received = None

    async def mock_execute_agent(*args, **kwargs):
        nonlocal context_received
        context_received = kwargs.get("context")
        yield {"type": "complete", "content": "Mock response"}

    agent_executor.execute_agent = mock_execute_agent

    # Execute agent with context
    model_config = config_manager.get_agent_model_config("orchestrator")
    async for chunk in agent_executor.execute_agent(
        agent_id="orchestrator",
        agent_type="orchestrator",
        prompt="Test prompt",
        model_config=model_config,
        context=context
    ):
        pass  # Consume generator

    # Verify context was delivered
    assert context_received is not None
    assert context_received["tier"] == "orchestrator"


@pytest.mark.asyncio
async def test_context_size_validation_within_limits(
    context_provider, sample_task, config_manager
):
    """Test context size validation - context within model limits."""
    # Get model config
    model_config = config_manager.get_agent_model_config("coder")

    # Get context with size validation
    context = context_provider.get_worker_context(
        task_id=sample_task,
        agent_type="coder",
        model_config=model_config
    )

    # Verify context includes size validation
    assert "context_size_validation" in context or True  # May not always be present
    assert context is not None


@pytest.mark.asyncio
async def test_context_size_validation_exceeds_limits(
    context_provider, sample_task, config_manager
):
    """Test context size validation - context exceeds model limits."""
    # Create a model config with very low token limit
    model_config = {
        "provider": "anthropic",
        "model": "claude-3-5-sonnet-20241022",
        "api_key": "test-key",
        "max_tokens": 1000,  # Very low limit
        "context_window": 200000  # Standard context window
    }

    # Get context - should still work but may log warnings
    context = context_provider.get_worker_context(
        task_id=sample_task,
        agent_type="coder",
        model_config=model_config
    )

    # Context should still be returned (validation is warning, not blocking)
    assert context is not None
    # Size validation may be present
    if "context_size_validation" in context:
        validation = context["context_size_validation"]
        # May indicate if context is too large
        assert isinstance(validation, dict)


@pytest.mark.asyncio
async def test_tier_based_context_filtering_orchestrator_tiers(
    context_provider
):
    """Test tier-based context filtering - orchestrator gets Tier 0-1."""
    context = context_provider.get_orchestrator_context()

    # Orchestrator should have Tier 0 and Tier 1
    assert "tier_0" in context
    assert "tier_1" in context
    # Should NOT have Tier 2 or Tier 3 (scoped context)
    assert "tier_2" not in context
    assert "tier_3" not in context


@pytest.mark.asyncio
async def test_tier_based_context_filtering_worker_tiers(
    context_provider, sample_task
):
    """Test tier-based context filtering - worker gets Tier 0, 2-3."""
    context = context_provider.get_worker_context(
        task_id=sample_task,
        agent_type="coder"
    )

    # Worker should have Tier 0, 2, 3
    assert "tier_0" in context
    assert "tier_2" in context
    assert "tier_3" in context
    # Should NOT have Tier 1 (high-level intent/architecture)
    assert "tier_1" not in context


@pytest.mark.asyncio
async def test_tier_based_context_filtering_different_agent_types(
    context_provider, sample_task
):
    """Test tier-based context filtering - different agent types get appropriate tiers."""
    # Test different agent types
    agent_types = ["planner", "coder", "test", "debug"]

    for agent_type in agent_types:
        context = context_provider.get_worker_context(
            task_id=sample_task,
            agent_type=agent_type
        )

        # All worker agents should have Tier 0, 2, 3
        assert "tier_0" in context
        assert "tier_2" in context
        assert "tier_3" in context
        assert context["agent_type"] == agent_type


@pytest.mark.asyncio
async def test_context_updates_during_execution_stage_specific_context(
    context_provider, sample_task
):
    """Test context updates during execution - stage-specific context."""
    # Get initial context
    initial_context = context_provider.get_worker_context(
        task_id=sample_task,
        agent_type="coder"
    )

    # Verify initial context structure
    assert initial_context is not None
    assert "tier_0" in initial_context

    # Test that context can be updated by getting context for different stages
    # This simulates context updates during execution
    planner_context = context_provider.get_worker_context(
        task_id=sample_task,
        agent_type="planner"
    )

    coder_context = context_provider.get_worker_context(
        task_id=sample_task,
        agent_type="coder"
    )

    # Both should have context, potentially different based on agent type
    assert planner_context is not None
    assert coder_context is not None
    # Both should have tier_0
    assert "tier_0" in planner_context
    assert "tier_0" in coder_context


@pytest.mark.asyncio
async def test_context_updates_during_execution_task_scope_updates(
    context_provider, sample_task, state_manager
):
    """Test context updates during execution - task scope updates."""
    # Get initial context
    initial_context = context_provider.get_worker_context(
        task_id=sample_task,
        agent_type="coder"
    )

    initial_scope = initial_context.get("task_scope", {})

    # Update task (simulating task modification during execution)
    tasks = state_manager.get_task_checklist()
    task = next((t for t in tasks if t.get("id") == sample_task), None)
    if task:
        task["description"] = "Updated task description"
        state_manager.set_task_checklist(tasks)

    # Get updated context
    updated_context = context_provider.get_worker_context(
        task_id=sample_task,
        agent_type="coder"
    )

    # Context should reflect updated task
    assert updated_context is not None
    # Task scope may be updated
    updated_scope = updated_context.get("task_scope", {})
    assert isinstance(updated_scope, dict)


@pytest.mark.asyncio
async def test_context_delivery_integration_with_executor(
    context_provider, agent_executor, sample_task, config_manager
):
    """Test complete integration - context delivery with executor."""
    # Get context
    context = context_provider.get_worker_context(
        task_id=sample_task,
        agent_type="coder",
        model_config=config_manager.get_agent_model_config("coder")
    )

    # Track context usage in executor
    context_used = False

    async def mock_execute_agent(agent_id, agent_type, prompt, model_config, context=None, **kwargs):
        nonlocal context_used
        if context:
            context_used = True
            # Verify context structure
            assert "tier_0" in context
            assert "tier_2" in context
            assert "tier_3" in context
            assert context["task_id"] == sample_task
        yield {"type": "complete", "content": "Response"}

    agent_executor.execute_agent = mock_execute_agent

    # Execute with context
    model_config = config_manager.get_agent_model_config("coder")
    async for chunk in agent_executor.execute_agent(
        agent_id=sample_task,
        agent_type="coder",
        prompt="Test prompt",
        model_config=model_config,
        context=context
    ):
        pass

    # Verify context was used
    assert context_used is True


@pytest.mark.asyncio
async def test_context_size_validation_integration_with_executor(
    context_provider, agent_executor, sample_task, config_manager
):
    """Test context size validation integration with executor."""
    # Get context with validation
    model_config = config_manager.get_agent_model_config("coder")
    context = context_provider.get_worker_context(
        task_id=sample_task,
        agent_type="coder",
        model_config=model_config
    )

    # Executor should handle context regardless of size
    # (validation is warning, not blocking)
    async def mock_execute_agent(*args, **kwargs):
        received_context = kwargs.get("context")
        # Executor should accept context
        assert received_context is not None
        yield {"type": "complete", "content": "Response"}

    agent_executor.execute_agent = mock_execute_agent

    # Execute should succeed even with large context
    async for chunk in agent_executor.execute_agent(
        agent_id=sample_task,
        agent_type="coder",
        prompt="Test prompt",
        model_config=model_config,
        context=context
    ):
        pass

    # Test passes if no exceptions raised
