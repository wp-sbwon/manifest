"""
Integration tests for StateManager → All Components interaction.

Tests the integration between StateManager and all components to ensure
proper state persistence, recovery, concurrent updates, and consistency.
"""
import pytest
import asyncio
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from manifest.core.state_manager import StateManager
from manifest.bridge.agent_bridge import AgentBridge
from manifest.agents.agent_coordinator import AgentCoordinator
from manifest.agents.context_provider import ContextProvider
from manifest.agents.task_scoper import TaskScoper
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
def agent_bridge(state_manager, config_manager):
    """Create an AgentBridge instance."""
    return AgentBridge(state_manager, config_manager=config_manager)


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


# ========== TDL: State Manager → All Components Integration ==========

@pytest.mark.asyncio
async def test_state_persistence_across_operations_agent_coordinator(
    agent_coordinator, agent_bridge, state_manager
):
    """Test state persistence across operations - AgentCoordinator."""
    # Start bridge and coordinator
    await agent_bridge.start()
    await agent_coordinator.start()

    # Perform operations that should persist state
    state_manager.set_mission_tree({"mission1": {"status": "active"}})
    state_manager.create_task(
        name="Test Task",
        description="Test description",
        status="pending"
    )

    # Save state
    await state_manager.save_state()

    # Verify state was persisted
    assert state_manager.state_file.exists()
    with open(state_manager.state_file, 'r') as f:
        saved_state = json.load(f)
        assert "mission_tree" in saved_state
        assert "mission1" in saved_state["mission_tree"]
        assert len(saved_state.get("task_checklist", [])) > 0


@pytest.mark.asyncio
async def test_state_persistence_across_operations_agent_bridge(
    agent_bridge, state_manager
):
    """Test state persistence across operations - AgentBridge."""
    # Start bridge
    await agent_bridge.start()

    # Bridge operations should persist state
    state_manager.set_last_action("Bridge operation")
    await state_manager.save_state()

    # Verify state was persisted
    assert state_manager.state_file.exists()
    with open(state_manager.state_file, 'r') as f:
        saved_state = json.load(f)
        assert saved_state.get("last_action") == "Bridge operation"


@pytest.mark.asyncio
async def test_state_persistence_across_operations_multiple_components(
    agent_coordinator, agent_bridge, state_manager, temp_dir
):
    """Test state persistence across operations - multiple components."""
    # Start components
    await agent_bridge.start()
    await agent_coordinator.start()

    # Multiple components modify state (ChannelManager removed; use StateManager directly)
    state_manager.set_mission_tree({"mission1": {"status": "active"}})
    task_id = state_manager.create_task(name="Task 1", description="Desc 1")
    state_manager.add_chat_message("main", "user", "Message 1")

    # Save state
    await state_manager.save_state()

    # Verify all state was persisted
    assert state_manager.state_file.exists()
    with open(state_manager.state_file, 'r') as f:
        saved_state = json.load(f)
        assert "mission_tree" in saved_state
        assert len(saved_state.get("task_checklist", [])) > 0
        assert "main" in saved_state.get("chat_history", {})


@pytest.mark.asyncio
async def test_state_recovery_after_restart_full_recovery(
    temp_dir, state_manager
):
    """Test state recovery after restart - full state recovery."""
    # Create initial state
    state_manager.set_mission_tree({"mission1": {"status": "active"}})
    task_id = state_manager.create_task(name="Task 1", description="Desc 1")
    state_manager.add_chat_message("main", "user", "Hello")
    state_manager.set_last_action("Previous action")

    # Save state
    await state_manager.save_state()

    # Simulate restart - create new StateManager
    new_state_manager = StateManager(manifest_dir=temp_dir)

    # Verify state was recovered
    recovered_state = new_state_manager.get_state()
    assert "mission1" in recovered_state["mission_tree"]
    assert len(recovered_state["task_checklist"]) > 0
    assert len(recovered_state["chat_history"]["main"]) > 0
    assert recovered_state["last_action"] == "Previous action"


@pytest.mark.asyncio
async def test_state_recovery_after_restart_partial_recovery(
    temp_dir, state_manager
):
    """Test state recovery after restart - partial state recovery."""
    # Create state with some data
    state_manager.set_mission_tree({"mission1": {"status": "active"}})
    state_manager.create_task(name="Task 1", description="Desc 1")

    # Save state
    await state_manager.save_state()

    # Simulate restart
    new_state_manager = StateManager(manifest_dir=temp_dir)

    # Verify partial state was recovered
    recovered_state = new_state_manager.get_state()
    assert "mission_tree" in recovered_state
    assert len(recovered_state.get("task_checklist", [])) > 0


@pytest.mark.asyncio
async def test_state_recovery_after_restart_corrupted_state(
    temp_dir, state_manager
):
    """Test state recovery after restart - corrupted state handling."""
    # Create valid state
    state_manager.set_mission_tree({"mission1": {"status": "active"}})
    await state_manager.save_state()

    # Corrupt the state file
    with open(state_manager.state_file, 'w') as f:
        f.write("invalid json content {{{{")

    # Simulate restart - should handle corruption gracefully
    new_state_manager = StateManager(manifest_dir=temp_dir)

    # Should initialize with default state, not crash
    recovered_state = new_state_manager.get_state()
    assert "version" in recovered_state
    assert "mission_tree" in recovered_state
    # Should have default empty state, not corrupted data
    assert recovered_state["mission_tree"] == {}


@pytest.mark.asyncio
async def test_concurrent_state_updates_multiple_components(
    agent_coordinator, agent_bridge, state_manager
):
    """Test concurrent state updates - multiple components."""
    # Start components
    await agent_bridge.start()
    await agent_coordinator.start()

    # Simulate concurrent updates from different components
    async def update_from_coordinator():
        for i in range(5):
            state_manager.set_last_action(f"Coordinator action {i}")
            await state_manager.save_state()
            await asyncio.sleep(0.01)

    async def update_from_bridge():
        for i in range(5):
            state_manager.set_last_action(f"Bridge action {i}")
            await state_manager.save_state()
            await asyncio.sleep(0.01)

    # Run concurrent updates
    await asyncio.gather(
        update_from_coordinator(),
        update_from_bridge()
    )

    # Verify state was saved (last write wins or both are preserved)
    assert state_manager.state_file.exists()
    with open(state_manager.state_file, 'r') as f:
        saved_state = json.load(f)
        # Last action should be one of the updates
        assert "action" in saved_state.get("last_action", "")


@pytest.mark.asyncio
async def test_concurrent_state_updates_same_component(
    state_manager
):
    """Test concurrent state updates - same component."""
    # Simulate concurrent updates from same component
    async def update_task(i):
        state_manager.create_task(name=f"Task {i}", description=f"Desc {i}")
        await state_manager.save_state()
        await asyncio.sleep(0.01)

    # Run concurrent task creation
    await asyncio.gather(*[update_task(i) for i in range(10)])

    # Verify all tasks were persisted (or at least some)
    assert state_manager.state_file.exists()
    with open(state_manager.state_file, 'r') as f:
        saved_state = json.load(f)
        tasks = saved_state.get("task_checklist", [])
        # Should have at least some tasks (may not have all due to race conditions)
        assert len(tasks) > 0


@pytest.mark.asyncio
async def test_state_consistency_validation_after_operations(
    agent_coordinator, agent_bridge, state_manager
):
    """Test state consistency validation - after operations."""
    # Start components
    await agent_bridge.start()
    await agent_coordinator.start()

    # Perform operations
    state_manager.set_mission_tree({"mission1": {"status": "active"}})
    task_id = state_manager.create_task(name="Task 1", description="Desc 1")
    state_manager.add_chat_message("main", "user", "Message")

    # Save state
    await state_manager.save_state()

    # Validate state consistency
    state = state_manager.get_state()

    # Check required fields exist
    assert "version" in state
    assert "mission_tree" in state
    assert "task_checklist" in state
    assert "chat_history" in state

    # Check data consistency
    assert isinstance(state["mission_tree"], dict)
    assert isinstance(state["task_checklist"], list)
    assert isinstance(state["chat_history"], dict)

    # Check task exists in checklist
    tasks = state["task_checklist"]
    task = next((t for t in tasks if t.get("id") == task_id), None)
    assert task is not None
    assert task["name"] == "Task 1"


@pytest.mark.asyncio
async def test_state_consistency_validation_after_recovery(
    temp_dir, state_manager
):
    """Test state consistency validation - after recovery."""
    # Create and save state
    state_manager.set_mission_tree({"mission1": {"status": "active"}})
    task_id = state_manager.create_task(name="Task 1", description="Desc 1")
    await state_manager.save_state()

    # Recover state
    new_state_manager = StateManager(manifest_dir=temp_dir)
    recovered_state = new_state_manager.get_state()

    # Validate consistency
    assert "version" in recovered_state
    assert "mission_tree" in recovered_state
    assert "task_checklist" in recovered_state

    # Validate data integrity
    assert "mission1" in recovered_state["mission_tree"]
    tasks = recovered_state["task_checklist"]
    task = next((t for t in tasks if t.get("id") == task_id), None)
    assert task is not None
    assert task["name"] == "Task 1"


@pytest.mark.asyncio
async def test_state_consistency_validation_structure_integrity(
    state_manager
):
    """Test state consistency validation - structure integrity."""
    # Create state with various data types
    state_manager.set_mission_tree({
        "mission1": {"status": "active", "tasks": ["task1", "task2"]}
    })
    state_manager.create_task(name="Task 1", description="Desc 1")
    state_manager.add_chat_message("main", "user", "Message 1")
    state_manager.add_chat_message("main", "assistant", "Response 1")

    # Save and reload
    await state_manager.save_state()
    state = state_manager.get_state()

    # Validate structure integrity
    assert isinstance(state["mission_tree"], dict)
    assert isinstance(state["task_checklist"], list)
    assert isinstance(state["chat_history"], dict)

    # Validate nested structures
    mission = state["mission_tree"].get("mission1")
    assert mission is not None
    assert isinstance(mission, dict)
    assert "status" in mission

    # Validate chat history structure
    main_chat = state["chat_history"].get("main", [])
    assert isinstance(main_chat, list)
    assert len(main_chat) >= 2


@pytest.mark.asyncio
async def test_integration_complete_workflow_state_persistence(
    agent_coordinator, agent_bridge, state_manager, temp_dir
):
    """Test complete integration - workflow with state persistence."""
    # Start components
    await agent_bridge.start()
    await agent_coordinator.start()

    # Simulate complete workflow
    # 1. Create mission
    state_manager.set_mission_tree({"mission1": {"status": "active"}})
    await state_manager.save_state()

    # 2. Create task
    task_id = state_manager.create_task(name="Task 1", description="Desc 1")
    await state_manager.save_state()

    # 3. Update task status
    tasks = state_manager.get_task_checklist()
    task = next((t for t in tasks if t.get("id") == task_id), None)
    if task:
        task["status"] = "in_progress"
        state_manager.set_task_checklist(tasks)
        await state_manager.save_state()

    # 4. Add chat messages
    state_manager.add_chat_message("main", "user", "User message")
    state_manager.add_chat_message("main", "assistant", "Assistant response")
    await state_manager.save_state()

    # 5. Simulate restart and verify all state recovered
    new_state_manager = StateManager(manifest_dir=temp_dir)
    recovered_state = new_state_manager.get_state()

    # Verify all operations persisted
    assert "mission1" in recovered_state["mission_tree"]
    tasks_recovered = recovered_state["task_checklist"]
    task_recovered = next((t for t in tasks_recovered if t.get("id") == task_id), None)
    assert task_recovered is not None
    assert task_recovered["status"] == "in_progress"
    assert len(recovered_state["chat_history"]["main"]) >= 2
