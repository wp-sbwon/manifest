"""
E2E Test: Manual Task Creation & Execution Workflow

Tests the complete workflow from user manually creating a task to agent execution.
This validates the manual task creation and agent execution path.
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
from manifest.ui.commands.command_handler import CommandHandler


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


@pytest.fixture
def mock_app(agent_coordinator, agent_bridge, state_manager):
    """Create a mock App instance."""
    app = MagicMock()
    app.agent_coordinator = agent_coordinator
    app.agent_bridge = agent_bridge
    app.state_manager = state_manager
    app.update_squad_channels = AsyncMock(return_value=None)
    app._load_project_data = AsyncMock(return_value=None)
    return app


@pytest.fixture
def command_handler(mock_app):
    """Create a CommandHandler instance."""
    return CommandHandler(mock_app)


@pytest.fixture
def mock_log():
    """Create a mock RichLog widget."""
    log = MagicMock()
    log.write = Mock()
    return log


# ========== TDL: Workflow 2: Manual Task Creation & Execution ==========

@pytest.mark.asyncio
async def test_task_created_correctly(
    command_handler, state_manager, mock_log
):
    """Test: Task is created correctly via command."""
    # Step 1: User creates task via command
    task_name = "Implement user authentication"
    task_description = "Add login and logout functionality"

    # Simulate command: /create_task "Implement user authentication" "Add login and logout functionality"
    # The command handler will parse this and create the task
    handled = await command_handler.handle(
        f'/create_task "{task_name}" "{task_description}"',
        mock_log
    )

    # Verify command was handled
    assert handled is True

    # Verify task was created
    tasks = state_manager.get_task_checklist()
    assert len(tasks) > 0

    # Find the created task
    created_task = next(
        (t for t in tasks if task_name in t.get("name", "")),
        None
    )
    assert created_task is not None, f"Task '{task_name}' not found in tasks"
    assert created_task.get("description") == task_description
    assert created_task.get("status") == "pending"


@pytest.mark.asyncio
async def test_agent_starts_and_completes_planner(
    command_handler, agent_coordinator, agent_bridge, state_manager, mock_log
):
    """Test: Agent starts and completes - planner agent."""
    # Start bridge and coordinator
    await agent_bridge.start()
    await agent_coordinator.start()

    # Step 1: Create task
    task_id = state_manager.create_task(
        name="Test Task",
        description="Test task description",
        status="pending"
    )

    # Step 2: Track agent execution
    agent_started = []
    agent_completed = []

    async def track_start_agent(task_id_param, agent_type, **kwargs):
        agent_started.append({"task_id": task_id_param, "agent_type": agent_type})
        # Simulate agent completion
        await asyncio.sleep(0.01)
        agent_completed.append({"task_id": task_id_param, "agent_type": agent_type})
        return True

    agent_coordinator.start_worker_agent = track_start_agent

    # Step 3: User starts planner agent via command
    handled = await command_handler.handle(
        f"/start_agent {task_id} planner",
        mock_log
    )

    # Verify agent started and completed
    assert handled is True
    assert len(agent_started) == 1
    assert agent_started[0]["agent_type"] == "planner"
    assert agent_started[0]["task_id"] == task_id
    assert len(agent_completed) == 1


@pytest.mark.asyncio
async def test_agent_starts_and_completes_coder(
    command_handler, agent_coordinator, agent_bridge, state_manager, mock_log
):
    """Test: Agent starts and completes - coder agent."""
    # Start bridge and coordinator
    await agent_bridge.start()
    await agent_coordinator.start()

    # Step 1: Create task
    task_id = state_manager.create_task(
        name="Code Implementation Task",
        description="Implement the planned features",
        status="pending"
    )

    # Step 2: Track agent execution
    agent_calls = []

    async def track_start_agent(task_id_param, agent_type, **kwargs):
        agent_calls.append({
            "action": "start",
            "task_id": task_id_param,
            "agent_type": agent_type
        })
        # Simulate agent work
        await asyncio.sleep(0.01)
        agent_calls.append({
            "action": "complete",
            "task_id": task_id_param,
            "agent_type": agent_type
        })
        return True

    agent_coordinator.start_worker_agent = track_start_agent

    # Step 3: User starts coder agent
    handled = await command_handler.handle(
        f"/start_agent {task_id} coder",
        mock_log
    )

    # Verify agent execution
    assert handled is True
    assert len(agent_calls) >= 2
    assert agent_calls[0]["action"] == "start"
    assert agent_calls[0]["agent_type"] == "coder"
    assert agent_calls[1]["action"] == "complete"


@pytest.mark.asyncio
async def test_results_saved(
    command_handler, agent_coordinator, agent_bridge, state_manager, mock_log
):
    """Test: Results are saved after agent execution."""
    # Start bridge and coordinator
    await agent_bridge.start()
    await agent_coordinator.start()

    # Create task
    task_id = state_manager.create_task(
        name="Test Task",
        description="Test task",
        status="pending"
    )

    # Track state saves
    state_saves = []

    original_save = state_manager.save_state

    async def track_save():
        state_saves.append("saved")
        return await original_save()

    state_manager.save_state = track_save

    # Mock agent to produce results
    async def mock_start_agent(task_id_param, agent_type, **kwargs):
        # Simulate agent producing results
        channel = f"squad-{task_id_param}-{agent_type}"
        state_manager.add_chat_message(channel, "assistant", "Agent completed successfully")
        await state_manager.save_state()
        return True

    agent_coordinator.start_worker_agent = mock_start_agent

    # Start agent
    handled = await command_handler.handle(
        f"/start_agent {task_id} planner",
        mock_log
    )

    # Verify results were saved
    assert handled is True
    assert len(state_saves) > 0, "State should be saved after agent execution"

    # Verify chat history was saved
    channel = f"squad-{task_id}-planner"
    history = state_manager.get_chat_history(channel)
    assert len(history) > 0
    assert any("completed" in msg.get("content", "").lower() for msg in history)


@pytest.mark.asyncio
async def test_state_updated(
    command_handler, agent_coordinator, agent_bridge, state_manager, mock_log
):
    """Test: State is updated after agent execution."""
    # Start bridge and coordinator
    await agent_bridge.start()
    await agent_coordinator.start()

    # Create task
    task_id = state_manager.create_task(
        name="Test Task",
        description="Test task",
        status="pending"
    )

    # Get initial state
    initial_tasks = state_manager.get_task_checklist()
    initial_task = next((t for t in initial_tasks if t.get("id") == task_id), None)
    assert initial_task is not None
    assert initial_task.get("status") == "pending"

    # Mock agent to update task status
    async def mock_start_agent(task_id_param, agent_type, **kwargs):
        # Update task status
        state_manager.update_task(task_id_param, status="in_progress")
        await state_manager.save_state()
        return True

    agent_coordinator.start_worker_agent = mock_start_agent

    # Start agent
    handled = await command_handler.handle(
        f"/start_agent {task_id} planner",
        mock_log
    )

    # Verify state was updated
    assert handled is True

    # Reload state and verify update
    tasks = state_manager.get_task_checklist()
    updated_task = next((t for t in tasks if t.get("id") == task_id), None)
    assert updated_task is not None
    assert updated_task.get("status") == "in_progress"


@pytest.mark.asyncio
async def test_complete_manual_task_workflow(
    command_handler, agent_coordinator, agent_bridge, state_manager, mock_log
):
    """Test: Complete manual task creation and execution workflow."""
    # Start bridge and coordinator
    await agent_bridge.start()
    await agent_coordinator.start()

    # Step 1: User creates task via command
    task_name = "Build REST API endpoint"
    task_description = "Create POST /api/users endpoint"

    handled = await command_handler.handle(
        f'/create_task "{task_name}" "{task_description}"',
        mock_log
    )
    assert handled is True

    # Find created task
    tasks = state_manager.get_task_checklist()
    created_task = next((t for t in tasks if task_name in t.get("name", "")), None)
    assert created_task is not None
    task_id = created_task.get("id")

    # Step 2: Track agent executions
    agent_executions = []

    async def track_agent(task_id_param, agent_type, **kwargs):
        agent_executions.append({
            "task_id": task_id_param,
            "agent_type": agent_type,
            "stage": kwargs.get("stage")
        })
        # Simulate agent work
        await asyncio.sleep(0.01)
        return True

    agent_coordinator.start_worker_agent = track_agent

    # Step 3: User starts planner agent
    handled = await command_handler.handle(
        f"/start_agent {task_id} planner",
        mock_log
    )
    assert handled is True

    # Step 4: User starts coder agent
    handled = await command_handler.handle(
        f"/start_agent {task_id} coder",
        mock_log
    )
    assert handled is True

    # Step 5: Verify complete workflow
    assert len(agent_executions) == 2
    assert agent_executions[0]["agent_type"] == "planner"
    assert agent_executions[1]["agent_type"] == "coder"
    assert agent_executions[0]["task_id"] == task_id
    assert agent_executions[1]["task_id"] == task_id

    # Verify task still exists
    tasks = state_manager.get_task_checklist()
    task = next((t for t in tasks if t.get("id") == task_id), None)
    assert task is not None
    assert task.get("name") == task_name
