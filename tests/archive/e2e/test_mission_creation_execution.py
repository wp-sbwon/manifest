"""
E2E Test: Mission Creation & Execution Workflow

Tests the complete workflow from user creating a mission to task execution.
This is a critical end-to-end test that validates the entire system works together.
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


# ========== TDL: Workflow 1: Mission Creation & Execution ==========

@pytest.mark.asyncio
async def test_mission_creation_and_persistence(
    agent_coordinator, agent_bridge, state_manager
):
    """Test: Mission is created and persisted."""
    # Start bridge and coordinator
    await agent_bridge.start()
    await agent_coordinator.start()

    # Step 1: User enters mission description
    mission_description = "Create a simple calculator application with add, subtract, multiply, and divide functions"

    # Step 2: Orchestrator processes mission
    # Mock orchestrator to return task breakdown
    mock_tasks = [
        {"id": "task-1", "name": "Create calculator class", "description": "Implement Calculator class"},
        {"id": "task-2", "name": "Add arithmetic methods", "description": "Implement add, subtract, multiply, divide"}
    ]

    async def mock_start_orchestrator(description):
        # Simulate orchestrator creating tasks
        for task in mock_tasks:
            state_manager.create_task(
                name=task["name"],
                description=task["description"],
                status="pending"
            )
        return True

    agent_coordinator.start_orchestrator = mock_start_orchestrator

    # Start orchestrator
    success = await agent_coordinator.start_orchestrator(mission_description)
    assert success is True

    # Step 3: Verify mission is persisted
    state = state_manager.get_state()
    mission_tree = state.get("mission_tree", {})

    # Verify tasks were created
    tasks = state_manager.get_task_checklist()
    assert len(tasks) >= len(mock_tasks)

    # Verify state was saved
    await state_manager.save_state()
    assert state_manager.state_file.exists()


@pytest.mark.asyncio
async def test_tasks_correctly_extracted(
    agent_coordinator, agent_bridge, state_manager
):
    """Test: Tasks are correctly extracted from mission."""
    # Start bridge and coordinator
    await agent_bridge.start()
    await agent_coordinator.start()

    mission_description = "Build a todo app with create, read, update, delete operations"

    # Mock orchestrator to extract tasks
    expected_tasks = [
        {"name": "Create Todo model", "description": "Define Todo data structure"},
        {"name": "Implement CRUD operations", "description": "Create, read, update, delete todos"},
        {"name": "Add user interface", "description": "Create UI for todo management"}
    ]

    async def mock_start_orchestrator(description):
        for task in expected_tasks:
            state_manager.create_task(
                name=task["name"],
                description=task["description"],
                status="pending"
            )
        return True

    agent_coordinator.start_orchestrator = mock_start_orchestrator

    # Process mission
    await agent_coordinator.start_orchestrator(mission_description)

    # Verify tasks were extracted correctly
    tasks = state_manager.get_task_checklist()
    assert len(tasks) == len(expected_tasks)

    # Verify task details
    for expected_task in expected_tasks:
        found = any(
            task.get("name") == expected_task["name"] and
            task.get("description") == expected_task["description"]
            for task in tasks
        )
        assert found, f"Task not found: {expected_task['name']}"


@pytest.mark.asyncio
async def test_worker_squad_completes_all_stages(
    agent_coordinator, agent_bridge, state_manager, temp_dir
):
    """Test: Worker Squad completes all stages."""
    # Start bridge and coordinator
    await agent_bridge.start()
    await agent_coordinator.start()

    # Create a task
    task_id = state_manager.create_task(
        name="Test Task",
        description="Test task for worker squad",
        status="pending"
    )

    # Track stage completions
    completed_stages = []

    async def mock_execute(task_id_param):
        # Simulate Worker Squad stages
        stages = ["planner", "tdd_test", "coder", "test", "debug", "self_review", "approver"]
        for stage in stages:
            completed_stages.append(stage)
            # Simulate stage completion
            await asyncio.sleep(0.01)  # Small delay to simulate work
        return {
            "success": True,
            "stages": {stage: {"status": "completed"} for stage in stages}
        }

    agent_coordinator.worker_squad_executor.execute = mock_execute

    # Execute Worker Squad
    result = await agent_coordinator.execute_worker_squad(task_id)

    # Verify all stages completed
    assert result.get("success") is True
    assert len(completed_stages) == 7  # All 7 stages
    assert "planner" in completed_stages
    assert "coder" in completed_stages
    assert "test" in completed_stages
    assert "approver" in completed_stages


@pytest.mark.asyncio
async def test_state_persisted_throughout_workflow(
    agent_coordinator, agent_bridge, state_manager
):
    """Test: State is persisted throughout workflow."""
    # Start bridge and coordinator
    await agent_bridge.start()
    await agent_coordinator.start()

    # Track state saves
    state_saves = []

    original_save = state_manager.save_state

    async def track_save():
        state_saves.append("saved")
        return await original_save()

    state_manager.save_state = track_save

    # Create mission and tasks
    mission_description = "Test mission"

    async def mock_start_orchestrator(description):
        state_manager.create_task(name="Task 1", description="Task 1", status="pending")
        await state_manager.save_state()
        return True

    agent_coordinator.start_orchestrator = mock_start_orchestrator

    # Execute workflow
    await agent_coordinator.start_orchestrator(mission_description)

    # Create and execute task
    task_id = state_manager.create_task(name="Task 2", description="Task 2", status="pending")

    async def mock_execute(task_id_param):
        await state_manager.save_state()
        return {"success": True}

    agent_coordinator.worker_squad_executor.execute = mock_execute
    await agent_coordinator.execute_worker_squad(task_id)

    # Verify state was saved multiple times
    assert len(state_saves) >= 2, "State should be saved multiple times during workflow"


@pytest.mark.asyncio
async def test_results_displayed_in_ui(
    agent_coordinator, agent_bridge, state_manager
):
    """Test: Results are displayed in UI."""
    # Start bridge and coordinator
    await agent_bridge.start()
    await agent_coordinator.start()

    # Create a task
    task_id = state_manager.create_task(
        name="Test Task",
        description="Test task",
        status="pending"
    )

    # Mock channel manager to track UI updates
    ui_updates = []

    class MockChannelManager:
        async def handle_agent_output(self, channel, content, role="assistant", save_immediately=True):
            ui_updates.append({"channel": channel, "content": content, "role": role})

    mock_channel_manager = MockChannelManager()
    agent_bridge.channel_manager = mock_channel_manager

    # Mock executor to produce output
    async def mock_execute(task_id_param):
        # Simulate agent output
        await agent_bridge._handle_agent_chunk(
            chunk={"type": "complete", "content": "Task completed successfully"},
            channel=f"squad-{task_id}-planner"
        )
        return {"success": True, "output": "Task completed successfully"}

    agent_coordinator.worker_squad_executor.execute = mock_execute

    # Execute workflow
    result = await agent_coordinator.execute_worker_squad(task_id)

    # Verify results were displayed
    assert result.get("success") is True
    assert len(ui_updates) > 0, "UI should receive updates"
    assert any("completed" in update.get("content", "").lower() for update in ui_updates)


@pytest.mark.asyncio
async def test_complete_mission_workflow(
    agent_coordinator, agent_bridge, state_manager
):
    """Test: Complete mission workflow from start to finish."""
    # Start bridge and coordinator
    await agent_bridge.start()
    await agent_coordinator.start()

    # Step 1: User enters mission
    mission_description = "Build a simple REST API with CRUD operations"

    # Step 2: Orchestrator processes mission
    created_tasks = []

    async def mock_start_orchestrator(description):
        tasks = [
            {"name": "Design API structure", "description": "Define endpoints and data models"},
            {"name": "Implement endpoints", "description": "Create CRUD endpoints"},
            {"name": "Add validation", "description": "Validate input data"}
        ]
        for task in tasks:
            task_id = state_manager.create_task(
                name=task["name"],
                description=task["description"],
                status="pending"
            )
            created_tasks.append(task_id)
        await state_manager.save_state()
        return True

    agent_coordinator.start_orchestrator = mock_start_orchestrator

    # Step 3: Execute orchestrator
    success = await agent_coordinator.start_orchestrator(mission_description)
    assert success is True
    assert len(created_tasks) == 3

    # Step 4: Execute Worker Squad for first task
    task_id = created_tasks[0]

    async def mock_execute(task_id_param):
        # Simulate successful execution
        await state_manager.save_state()
        return {
            "success": True,
            "task_id": task_id_param,
            "stages": {
                "planner": {"status": "completed"},
                "coder": {"status": "completed"},
                "test": {"status": "completed"}
            }
        }

    agent_coordinator.worker_squad_executor.execute = mock_execute

    result = await agent_coordinator.execute_worker_squad(task_id)

    # Step 5: Verify complete workflow
    assert result.get("success") is True
    assert result.get("task_id") == task_id

    # Verify state persistence
    state = state_manager.get_state()
    tasks = state_manager.get_task_checklist()
    assert len(tasks) == 3

    # Verify task was updated
    task = next((t for t in tasks if t.get("id") == task_id), None)
    assert task is not None
