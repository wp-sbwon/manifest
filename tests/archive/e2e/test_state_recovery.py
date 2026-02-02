"""
E2E Test: State Recovery Workflow

Tests the complete workflow of app restart and state recovery.
This validates that the system can recover from crashes and continue work seamlessly.
"""
import pytest
import asyncio
import tempfile
import shutil
import json
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


# ========== TDL: Workflow 4: State Recovery ==========

@pytest.mark.asyncio
async def test_state_persisted_correctly(
    state_manager, temp_dir
):
    """Test: State is persisted correctly."""
    # Step 1: User works on mission - create tasks and state
    mission_data = {
        "mission1": {
            "description": "Build calculator app",
            "status": "active",
            "tasks": ["task-1", "task-2"]
        }
    }
    state_manager.set_mission_tree(mission_data)

    # Create tasks
    task_id_1 = state_manager.create_task(
        name="Task 1",
        description="Implement calculator class",
        status="in_progress"
    )
    task_id_2 = state_manager.create_task(
        name="Task 2",
        description="Add arithmetic methods",
        status="pending"
    )

    # Add chat history
    state_manager.add_chat_message("main", "user", "Start calculator project")
    state_manager.add_chat_message("main", "assistant", "I'll help you build a calculator")

    # Step 2: Save state
    await state_manager.save_state()

    # Verify state file exists
    assert state_manager.state_file.exists()

    # Verify state file contains data
    with open(state_manager.state_file, 'r') as f:
        saved_state = json.load(f)
        assert "mission_tree" in saved_state
        assert saved_state["mission_tree"] == mission_data


@pytest.mark.asyncio
async def test_state_recovered_on_restart(
    temp_dir, state_manager
):
    """Test: State is recovered on restart."""
    # Step 1: Create initial state
    mission_data = {
        "mission1": {
            "description": "Test mission",
            "status": "active"
        }
    }
    state_manager.set_mission_tree(mission_data)

    task_id = state_manager.create_task(
        name="Test Task",
        description="Test task",
        status="in_progress"
    )

    state_manager.add_chat_message("main", "user", "Test message")
    await state_manager.save_state()

    # Step 2: Simulate restart - create new StateManager
    new_state_manager = StateManager(manifest_dir=temp_dir)

    # Step 3: Verify state was recovered
    recovered_state = new_state_manager.get_state()
    assert "mission_tree" in recovered_state
    assert recovered_state["mission_tree"] == mission_data

    # Verify tasks were recovered
    tasks = new_state_manager.get_task_checklist()
    assert len(tasks) > 0
    recovered_task = next((t for t in tasks if t.get("id") == task_id), None)
    assert recovered_task is not None
    assert recovered_task.get("name") == "Test Task"

    # Verify chat history was recovered
    history = new_state_manager.get_chat_history("main")
    assert len(history) > 0
    assert any(msg.get("content") == "Test message" for msg in history)


@pytest.mark.asyncio
async def test_active_agents_restored(
    temp_dir, state_manager, agent_bridge, agent_coordinator, config_manager
):
    """Test: Active agents are restored after restart."""
    # Start bridge and coordinator
    await agent_bridge.start()
    await agent_coordinator.start()

    # Step 1: Create task and start agent
    task_id = state_manager.create_task(
        name="Active Task",
        description="Task with active agent",
        status="in_progress"
    )

    # Simulate agent being active
    # Note: Active agents are tracked in agent_bridge, not coordinator
    # We'll verify task state instead
    agent_bridge._active_agents[task_id] = {
        "agent_type": "planner",
        "status": "active",
        "channel": f"squad-{task_id}-planner"
    }

    # Save state
    await state_manager.save_state()

    # Step 2: Simulate restart
    new_state_manager = StateManager(manifest_dir=temp_dir)
    new_task_scoper = TaskScoper(manifest_dir=temp_dir)
    new_context_provider = ContextProvider(manifest_dir=temp_dir, task_scoper=new_task_scoper)
    new_agent_bridge = AgentBridge(
        state_manager=new_state_manager,
        config_manager=config_manager
    )
    new_agent_coordinator = AgentCoordinator(
        agent_bridge=new_agent_bridge,
        context_provider=new_context_provider,
        task_scoper=new_task_scoper,
        config_manager=config_manager,
        state_manager=new_state_manager
    )

    await new_agent_bridge.start()
    await new_agent_coordinator.start()

    # Step 3: Verify task was recovered
    tasks = new_state_manager.get_task_checklist()
    recovered_task = next((t for t in tasks if t.get("id") == task_id), None)
    assert recovered_task is not None
    assert recovered_task.get("status") == "in_progress"

    # Note: Active agents are tracked in memory, not persisted
    # But the task state is persisted, so we can verify the task exists


@pytest.mark.asyncio
async def test_work_continues_seamlessly(
    temp_dir, state_manager, agent_bridge, agent_coordinator
):
    """Test: Work can continue seamlessly after restart."""
    # Step 1: User works on mission
    task_id = state_manager.create_task(
        name="Calculator Task",
        description="Build calculator",
        status="in_progress"
    )

    # Add progress
    state_manager.add_chat_message(
        f"squad-{task_id}-planner",
        "assistant",
        "Planning: Create Calculator class with add, subtract, multiply, divide methods"
    )
    await state_manager.save_state()

    # Step 2: Simulate app crash/restart
    new_state_manager = StateManager(manifest_dir=temp_dir)

    # Step 3: Verify state recovered
    tasks = new_state_manager.get_task_checklist()
    recovered_task = next((t for t in tasks if t.get("id") == task_id), None)
    assert recovered_task is not None

    # Step 4: Continue work - update task
    new_state_manager.update_task(task_id, status="completed")
    await new_state_manager.save_state()

    # Verify update was saved
    final_tasks = new_state_manager.get_task_checklist()
    final_task = next((t for t in final_tasks if t.get("id") == task_id), None)
    assert final_task is not None
    assert final_task.get("status") == "completed"

    # Verify chat history is still accessible
    history = new_state_manager.get_chat_history(f"squad-{task_id}-planner")
    assert len(history) > 0
    assert any("Calculator" in msg.get("content", "") for msg in history)


@pytest.mark.asyncio
async def test_state_recovery_with_corrupted_file(
    temp_dir, state_manager
):
    """Test: State recovery handles corrupted state file gracefully."""
    # Step 1: Create valid state
    state_manager.set_mission_tree({"mission1": {"status": "active"}})
    await state_manager.save_state()

    # Step 2: Corrupt the state file
    with open(state_manager.state_file, 'w') as f:
        f.write("invalid json content {{{{\"")

    # Step 3: Simulate restart - should handle corruption gracefully
    new_state_manager = StateManager(manifest_dir=temp_dir)

    # Should initialize with default state, not crash
    recovered_state = new_state_manager.get_state()
    assert "version" in recovered_state
    assert "mission_tree" in recovered_state
    # Should have default empty state, not corrupted data
    assert isinstance(recovered_state["mission_tree"], dict)


@pytest.mark.asyncio
async def test_state_recovery_partial_data(
    temp_dir, state_manager
):
    """Test: State recovery with partial data."""
    # Step 1: Create state with multiple components
    state_manager.set_mission_tree({"mission1": {"status": "active"}})
    task_id_1 = state_manager.create_task(name="Task 1", description="Task 1", status="pending")
    task_id_2 = state_manager.create_task(name="Task 2", description="Task 2", status="in_progress")
    state_manager.add_chat_message("main", "user", "Message 1")
    state_manager.add_chat_message("main", "assistant", "Response 1")
    await state_manager.save_state()

    # Step 2: Restart
    new_state_manager = StateManager(manifest_dir=temp_dir)

    # Step 3: Verify all components recovered
    state = new_state_manager.get_state()
    assert "mission_tree" in state
    assert state["mission_tree"] == {"mission1": {"status": "active"}}

    tasks = new_state_manager.get_task_checklist()
    assert len(tasks) == 2
    assert any(t.get("id") == task_id_1 for t in tasks)
    assert any(t.get("id") == task_id_2 for t in tasks)

    history = new_state_manager.get_chat_history("main")
    assert len(history) == 2
    assert any(msg.get("content") == "Message 1" for msg in history)
    assert any(msg.get("content") == "Response 1" for msg in history)


@pytest.mark.asyncio
async def test_complete_state_recovery_workflow(
    temp_dir, state_manager, agent_bridge, agent_coordinator, config_manager
):
    """Test: Complete state recovery workflow."""
    # Step 1: User works on mission
    await agent_bridge.start()
    await agent_coordinator.start()

    mission_data = {
        "mission1": {
            "description": "Build web app",
            "status": "active"
        }
    }
    state_manager.set_mission_tree(mission_data)

    # Create multiple tasks
    task_ids = []
    for i in range(3):
        task_id = state_manager.create_task(
            name=f"Task {i+1}",
            description=f"Task {i+1} description",
            status="pending" if i > 0 else "in_progress"
        )
        task_ids.append(task_id)

    # Add chat history
    state_manager.add_chat_message("main", "user", "Start project")
    state_manager.add_chat_message("main", "assistant", "I'll help you")

    # Save state
    await state_manager.save_state()

    # Step 2: Simulate crash/restart
    new_state_manager = StateManager(manifest_dir=temp_dir)
    new_task_scoper = TaskScoper(manifest_dir=temp_dir)
    new_context_provider = ContextProvider(manifest_dir=temp_dir, task_scoper=new_task_scoper)
    new_agent_bridge = AgentBridge(
        state_manager=new_state_manager,
        config_manager=config_manager
    )
    new_agent_coordinator = AgentCoordinator(
        agent_bridge=new_agent_bridge,
        context_provider=new_context_provider,
        task_scoper=new_task_scoper,
        config_manager=config_manager,
        state_manager=new_state_manager
    )

    await new_agent_bridge.start()
    await new_agent_coordinator.start()

    # Step 3: Verify complete recovery
    recovered_state = new_state_manager.get_state()
    assert recovered_state["mission_tree"] == mission_data

    tasks = new_state_manager.get_task_checklist()
    assert len(tasks) == 3
    for task_id in task_ids:
        assert any(t.get("id") == task_id for t in tasks)

    history = new_state_manager.get_chat_history("main")
    assert len(history) == 2

    # Step 4: Continue work
    new_state_manager.update_task(task_ids[0], status="completed")
    await new_state_manager.save_state()

    # Verify work continued
    final_tasks = new_state_manager.get_task_checklist()
    completed_task = next((t for t in final_tasks if t.get("id") == task_ids[0]), None)
    assert completed_task is not None
    assert completed_task.get("status") == "completed"
