"""
Unit tests for WorkflowEventBus.

Tests event publishing, subscription, and workflow event handling.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from manifest.agents.workflow_event_bus import (
    WorkflowEventBus,
    WorkflowEvent,
    WorkflowEventType
)


@pytest.fixture
def event_bus():
    """Create a WorkflowEventBus instance."""
    return WorkflowEventBus()


def test_event_bus_initialization(event_bus):
    """Test WorkflowEventBus initialization."""
    assert hasattr(event_bus, '_subscribers')
    assert isinstance(event_bus._subscribers, dict)
    assert hasattr(event_bus, '_event_history')
    assert event_bus._max_history == 1000


def test_workflow_event_creation():
    """Test creating a WorkflowEvent."""
    # WorkflowEventType doesn't have STAGE_STARTED, check available types
    event = WorkflowEvent(
        event_type=WorkflowEventType.STAGE_COMPLETED,
        task_id="task-1",
        data={"stage": "planner"}
    )
    assert event.event_type == WorkflowEventType.STAGE_COMPLETED
    assert event.task_id == "task-1"
    assert event.data == {"stage": "planner"}


@pytest.mark.asyncio
async def test_publish_event(event_bus):
    """Test publishing an event."""
    event = WorkflowEvent(
        event_type=WorkflowEventType.WORKFLOW_STARTED,
        task_id="task-1",
        data={}
    )

    initial_history_len = len(event_bus._event_history)
    await event_bus.publish(event)

    # Verify event was added to history
    assert len(event_bus._event_history) == initial_history_len + 1
    assert event_bus._event_history[-1] == event


@pytest.mark.asyncio
async def test_subscribe_to_event(event_bus):
    """Test subscribing to an event type."""
    callback = Mock()  # Can be sync or async

    # subscribe doesn't return a subscription_id, it's void
    event_bus.subscribe(
        event_type=WorkflowEventType.STAGE_COMPLETED,
        callback=callback
    )

    # Verify subscription was added
    assert WorkflowEventType.STAGE_COMPLETED in event_bus._subscribers
    assert callback in event_bus._subscribers[WorkflowEventType.STAGE_COMPLETED]


@pytest.mark.asyncio
async def test_unsubscribe_from_event(event_bus):
    """Test unsubscribing from an event."""
    callback = Mock()

    # Subscribe first
    event_bus.subscribe(
        event_type=WorkflowEventType.STAGE_COMPLETED,
        callback=callback
    )

    # unsubscribe takes event_type and callback, not subscription_id
    event_bus.unsubscribe(
        event_type=WorkflowEventType.STAGE_COMPLETED,
        callback=callback
    )

    # Verify subscription was removed
    assert callback not in event_bus._subscribers.get(WorkflowEventType.STAGE_COMPLETED, [])


@pytest.mark.asyncio
async def test_event_delivery(event_bus):
    """Test event delivery to subscribers."""
    callback = AsyncMock()

    # subscribe is not async
    event_bus.subscribe(
        event_type=WorkflowEventType.STAGE_COMPLETED,
        callback=callback
    )

    event = WorkflowEvent(
        event_type=WorkflowEventType.STAGE_COMPLETED,
        task_id="task-1",
        data={"stage": "planner"}
    )

    await event_bus.publish(event)

    # Callback should be called
    callback.assert_called_once()


def test_workflow_event_to_dict():
    """Test converting WorkflowEvent to dictionary."""
    event = WorkflowEvent(
        event_type=WorkflowEventType.AGENT_COMPLETED,
        task_id="task-1",
        stage="planner",
        agent_type="planner",
        data={"result": "success"}
    )

    event_dict = event.to_dict()

    assert event_dict["event_type"] == "agent_completed"
    assert event_dict["task_id"] == "task-1"
    assert event_dict["stage"] == "planner"
    assert event_dict["agent_type"] == "planner"
    assert event_dict["data"] == {"result": "success"}
    assert "timestamp" in event_dict


@pytest.mark.asyncio
async def test_publish_with_sync_callback(event_bus):
    """Test publishing event to synchronous callback."""
    sync_callback = Mock()

    event_bus.subscribe(
        event_type=WorkflowEventType.AGENT_STARTED,
        callback=sync_callback
    )

    event = WorkflowEvent(
        event_type=WorkflowEventType.AGENT_STARTED,
        task_id="task-1"
    )

    await event_bus.publish(event)

    # Sync callback should be called
    sync_callback.assert_called_once_with(event)


@pytest.mark.asyncio
async def test_publish_with_callback_error(event_bus):
    """Test that callback errors don't stop event publishing."""
    error_callback = Mock(side_effect=Exception("Callback error"))
    good_callback = Mock()

    event_bus.subscribe(
        event_type=WorkflowEventType.AGENT_FAILED,
        callback=error_callback
    )
    event_bus.subscribe(
        event_type=WorkflowEventType.AGENT_FAILED,
        callback=good_callback
    )

    event = WorkflowEvent(
        event_type=WorkflowEventType.AGENT_FAILED,
        task_id="task-1"
    )

    # Should not raise exception
    await event_bus.publish(event)

    # Both callbacks should be called
    error_callback.assert_called_once()
    good_callback.assert_called_once()
    # Event should still be in history
    assert len(event_bus._event_history) == 1




def test_get_event_history_no_filters(event_bus):
    """Test getting event history without filters."""
    event1 = WorkflowEvent(
        event_type=WorkflowEventType.WORKFLOW_STARTED,
        task_id="task-1"
    )
    event2 = WorkflowEvent(
        event_type=WorkflowEventType.STAGE_COMPLETED,
        task_id="task-2"
    )

    event_bus._event_history = [event1, event2]

    history = event_bus.get_event_history()

    # Should return most recent first
    assert len(history) == 2
    assert history[0] == event2
    assert history[1] == event1


def test_get_event_history_with_task_filter(event_bus):
    """Test getting event history filtered by task_id."""
    event1 = WorkflowEvent(
        event_type=WorkflowEventType.STAGE_COMPLETED,
        task_id="task-1"
    )
    event2 = WorkflowEvent(
        event_type=WorkflowEventType.STAGE_COMPLETED,
        task_id="task-2"
    )
    event3 = WorkflowEvent(
        event_type=WorkflowEventType.STAGE_COMPLETED,
        task_id="task-1"
    )

    event_bus._event_history = [event1, event2, event3]

    history = event_bus.get_event_history(task_id="task-1")

    assert len(history) == 2
    assert all(e.task_id == "task-1" for e in history)


def test_get_event_history_with_type_filter(event_bus):
    """Test getting event history filtered by event_type."""
    event1 = WorkflowEvent(
        event_type=WorkflowEventType.AGENT_STARTED,
        task_id="task-1"
    )
    event2 = WorkflowEvent(
        event_type=WorkflowEventType.AGENT_COMPLETED,
        task_id="task-1"
    )
    event3 = WorkflowEvent(
        event_type=WorkflowEventType.AGENT_STARTED,
        task_id="task-2"
    )

    event_bus._event_history = [event1, event2, event3]

    history = event_bus.get_event_history(event_type=WorkflowEventType.AGENT_STARTED)

    assert len(history) == 2
    assert all(e.event_type == WorkflowEventType.AGENT_STARTED for e in history)


def test_get_event_history_with_limit(event_bus):
    """Test getting event history with limit."""
    events = [
        WorkflowEvent(event_type=WorkflowEventType.STAGE_COMPLETED, task_id=f"task-{i}")
        for i in range(10)
    ]
    event_bus._event_history = events

    history = event_bus.get_event_history(limit=3)

    assert len(history) == 3
    # Most recent first
    assert history[0].task_id == "task-9"


def test_get_latest_event(event_bus):
    """Test getting latest event for a task."""
    event1 = WorkflowEvent(
        event_type=WorkflowEventType.STAGE_COMPLETED,
        task_id="task-1"
    )
    event2 = WorkflowEvent(
        event_type=WorkflowEventType.AGENT_COMPLETED,
        task_id="task-1"
    )
    event3 = WorkflowEvent(
        event_type=WorkflowEventType.STAGE_COMPLETED,
        task_id="task-2"
    )

    event_bus._event_history = [event1, event2, event3]

    latest = event_bus.get_latest_event("task-1")

    assert latest == event2  # Most recent for task-1


def test_get_latest_event_with_type_filter(event_bus):
    """Test getting latest event with type filter."""
    event1 = WorkflowEvent(
        event_type=WorkflowEventType.STAGE_COMPLETED,
        task_id="task-1"
    )
    event2 = WorkflowEvent(
        event_type=WorkflowEventType.AGENT_COMPLETED,
        task_id="task-1"
    )
    event3 = WorkflowEvent(
        event_type=WorkflowEventType.STAGE_COMPLETED,
        task_id="task-1"
    )

    event_bus._event_history = [event1, event2, event3]

    latest = event_bus.get_latest_event("task-1", event_type=WorkflowEventType.STAGE_COMPLETED)

    assert latest == event3  # Most recent STAGE_COMPLETED for task-1


def test_get_latest_event_not_found(event_bus):
    """Test getting latest event when none exists."""
    latest = event_bus.get_latest_event("nonexistent-task")

    assert latest is None


@pytest.mark.asyncio
async def test_event_history_limit(event_bus):
    """Test that event history is limited to max_history."""
    # Add more events than max_history using publish (which enforces limit)
    for i in range(event_bus._max_history + 10):
        event = WorkflowEvent(
            event_type=WorkflowEventType.STAGE_COMPLETED,
            task_id=f"task-{i}"
        )
        await event_bus.publish(event)

    # History should be capped at max_history
    assert len(event_bus._event_history) == event_bus._max_history


@pytest.mark.asyncio
async def test_publish_with_no_subscribers(event_bus):
    """Test publishing event when no subscribers exist."""
    event = WorkflowEvent(
        event_type=WorkflowEventType.WORKFLOW_COMPLETED,
        task_id="task-1"
    )

    # Should not raise error even with no subscribers
    await event_bus.publish(event)

    # Event should still be in history
    assert len(event_bus._event_history) == 1
    assert event_bus._event_history[0] == event


def test_workflow_event_optional_fields():
    """Test WorkflowEvent with optional fields and serialization."""
    # Test with None values
    event = WorkflowEvent(
        event_type=WorkflowEventType.AGENT_STARTED,
        task_id="task-1",
        stage=None,
        agent_type=None,
        data=None
    )
    assert event.data == {}  # Should default to empty dict

    # Test serialization preserves None values
    event_dict = event.to_dict()
    assert event_dict["stage"] is None
    assert event_dict["agent_type"] is None


def test_get_event_history_with_both_filters(event_bus):
    """Test getting event history with both task_id and event_type filters."""
    event1 = WorkflowEvent(
        event_type=WorkflowEventType.AGENT_STARTED,
        task_id="task-1"
    )
    event2 = WorkflowEvent(
        event_type=WorkflowEventType.AGENT_STARTED,
        task_id="task-2"
    )
    event3 = WorkflowEvent(
        event_type=WorkflowEventType.AGENT_COMPLETED,
        task_id="task-1"
    )

    event_bus._event_history = [event1, event2, event3]

    history = event_bus.get_event_history(
        task_id="task-1",
        event_type=WorkflowEventType.AGENT_STARTED
    )

    assert len(history) == 1
    assert history[0] == event1






@pytest.mark.asyncio
async def test_publish_with_multiple_subscribers(event_bus):
    """Test publishing event to multiple subscribers."""
    callback1 = AsyncMock()
    callback2 = AsyncMock()
    callback3 = Mock()  # Sync callback

    event_bus.subscribe(WorkflowEventType.TRIGGER_NEXT_STAGE, callback1)
    event_bus.subscribe(WorkflowEventType.TRIGGER_NEXT_STAGE, callback2)
    event_bus.subscribe(WorkflowEventType.TRIGGER_NEXT_STAGE, callback3)

    event = WorkflowEvent(
        event_type=WorkflowEventType.TRIGGER_NEXT_STAGE,
        task_id="task-1"
    )

    await event_bus.publish(event)

    # All callbacks should be called
    callback1.assert_called_once_with(event)
    callback2.assert_called_once_with(event)
    callback3.assert_called_once_with(event)


# ========== TDL: Workflow Event Bus - Missing Item ==========

@pytest.mark.asyncio
async def test_event_driven_workflow_trigger_stage_completion(event_bus):
    """Test event-driven workflow trigger on stage completion."""
    trigger_callback = AsyncMock()

    # Subscribe to TRIGGER_NEXT_STAGE events
    event_bus.subscribe(WorkflowEventType.TRIGGER_NEXT_STAGE, trigger_callback)

    # Publish stage completion event (which should trigger next stage)
    stage_completed_event = WorkflowEvent(
        event_type=WorkflowEventType.STAGE_COMPLETED,
        task_id="task-1",
        stage="planner",
        agent_type="planner",
        data={"result": "plan created"}
    )

    await event_bus.publish(stage_completed_event)

    # Publish trigger next stage event
    trigger_event = WorkflowEvent(
        event_type=WorkflowEventType.TRIGGER_NEXT_STAGE,
        task_id="task-1",
        stage="planner",
        agent_type="planner",
        data={"completed_stage": "planner", "next_stage": "coder"}
    )

    await event_bus.publish(trigger_event)

    # Trigger callback should be called
    trigger_callback.assert_called_once_with(trigger_event)
    # Verify event data contains next stage information
    call_args = trigger_callback.call_args[0][0]
    assert call_args.data["completed_stage"] == "planner"
    assert call_args.data["next_stage"] == "coder"


@pytest.mark.asyncio
async def test_event_driven_workflow_trigger_chain(event_bus):
    """Test event-driven workflow trigger chain (multiple stages)."""
    triggered_stages = []

    async def stage_trigger_handler(event):
        """Handler that simulates triggering next stage."""
        if event.event_type == WorkflowEventType.TRIGGER_NEXT_STAGE:
            triggered_stages.append({
                "task_id": event.task_id,
                "completed": event.data.get("completed_stage"),
                "next": event.data.get("next_stage")
            })

    # Subscribe to trigger events
    event_bus.subscribe(WorkflowEventType.TRIGGER_NEXT_STAGE, stage_trigger_handler)

    # Simulate workflow progression: planner -> coder -> test
    events = [
        WorkflowEvent(
            event_type=WorkflowEventType.STAGE_COMPLETED,
            task_id="task-1",
            stage="planner",
            data={"result": "plan"}
        ),
        WorkflowEvent(
            event_type=WorkflowEventType.TRIGGER_NEXT_STAGE,
            task_id="task-1",
            stage="planner",
            data={"completed_stage": "planner", "next_stage": "coder"}
        ),
        WorkflowEvent(
            event_type=WorkflowEventType.STAGE_COMPLETED,
            task_id="task-1",
            stage="coder",
            data={"result": "code"}
        ),
        WorkflowEvent(
            event_type=WorkflowEventType.TRIGGER_NEXT_STAGE,
            task_id="task-1",
            stage="coder",
            data={"completed_stage": "coder", "next_stage": "test"}
        )
    ]

    for event in events:
        await event_bus.publish(event)

    # Should have triggered 2 stages
    assert len(triggered_stages) == 2
    assert triggered_stages[0]["completed"] == "planner"
    assert triggered_stages[0]["next"] == "coder"
    assert triggered_stages[1]["completed"] == "coder"
    assert triggered_stages[1]["next"] == "test"


@pytest.mark.asyncio
async def test_event_driven_workflow_trigger_with_workflow_executor(event_bus):
    """Test event-driven workflow trigger simulating workflow executor subscription."""
    workflow_state = {"current_stage": None, "next_stage": None}

    async def workflow_executor_handler(event):
        """Simulate workflow executor handling trigger events."""
        if event.event_type == WorkflowEventType.TRIGGER_NEXT_STAGE:
            workflow_state["current_stage"] = event.data.get("completed_stage")
            workflow_state["next_stage"] = event.data.get("next_stage")

    # Workflow executor subscribes to trigger events
    event_bus.subscribe(WorkflowEventType.TRIGGER_NEXT_STAGE, workflow_executor_handler)

    # Publish trigger event
    trigger_event = WorkflowEvent(
        event_type=WorkflowEventType.TRIGGER_NEXT_STAGE,
        task_id="task-1",
        stage="planner",
        data={"completed_stage": "planner", "next_stage": "coder"}
    )

    await event_bus.publish(trigger_event)

    # Workflow executor should have updated state
    assert workflow_state["current_stage"] == "planner"
    assert workflow_state["next_stage"] == "coder"


@pytest.mark.asyncio
async def test_event_driven_workflow_trigger_conditional_execution(event_bus):
    """Test event-driven workflow trigger with conditional execution."""
    execution_path = []

    async def conditional_handler(event):
        """Handler that conditionally triggers next stage based on event data."""
        if event.event_type == WorkflowEventType.TRIGGER_NEXT_STAGE:
            completed = event.data.get("completed_stage")
            next_stage = event.data.get("next_stage")
            # Simulate conditional logic: if test fails, go to debug
            if completed == "test" and event.data.get("test_passed", True) is False:
                execution_path.append("test -> debug")
            else:
                execution_path.append(f"{completed} -> {next_stage}")

    event_bus.subscribe(WorkflowEventType.TRIGGER_NEXT_STAGE, conditional_handler)

    # Test successful path
    await event_bus.publish(WorkflowEvent(
        event_type=WorkflowEventType.TRIGGER_NEXT_STAGE,
        task_id="task-1",
        stage="planner",
        data={"completed_stage": "planner", "next_stage": "coder", "test_passed": True}
    ))

    # Test failure path
    await event_bus.publish(WorkflowEvent(
        event_type=WorkflowEventType.TRIGGER_NEXT_STAGE,
        task_id="task-1",
        stage="test",
        data={"completed_stage": "test", "next_stage": "self_review", "test_passed": False}
    ))

    assert len(execution_path) == 2
    assert "planner -> coder" in execution_path
    assert "test -> debug" in execution_path


@pytest.mark.asyncio
async def test_event_driven_workflow_trigger_parallel_stages(event_bus):
    """Test event-driven workflow trigger for parallel stage execution."""
    triggered_tasks = []

    async def parallel_handler(event):
        """Handler that can trigger multiple parallel stages."""
        if event.event_type == WorkflowEventType.TRIGGER_NEXT_STAGE:
            triggered_tasks.append({
                "task_id": event.task_id,
                "stage": event.data.get("next_stage")
            })

    event_bus.subscribe(WorkflowEventType.TRIGGER_NEXT_STAGE, parallel_handler)

    # Simulate multiple tasks completing and triggering next stages in parallel
    events = [
        WorkflowEvent(
            event_type=WorkflowEventType.TRIGGER_NEXT_STAGE,
            task_id="task-1",
            stage="planner",
            data={"completed_stage": "planner", "next_stage": "coder"}
        ),
        WorkflowEvent(
            event_type=WorkflowEventType.TRIGGER_NEXT_STAGE,
            task_id="task-2",
            stage="planner",
            data={"completed_stage": "planner", "next_stage": "coder"}
        ),
        WorkflowEvent(
            event_type=WorkflowEventType.TRIGGER_NEXT_STAGE,
            task_id="task-3",
            stage="planner",
            data={"completed_stage": "planner", "next_stage": "coder"}
        )
    ]

    # Publish all events (simulating parallel completion)
    await asyncio.gather(*[event_bus.publish(event) for event in events])

    # All tasks should have triggered their next stages
    assert len(triggered_tasks) == 3
    assert all(t["stage"] == "coder" for t in triggered_tasks)
    assert len(set(t["task_id"] for t in triggered_tasks)) == 3  # All unique task IDs


@pytest.mark.asyncio
async def test_event_driven_workflow_trigger_retry_stage(event_bus):
    """Test event-driven workflow trigger for retry stage events."""
    retry_handler = AsyncMock()

    event_bus.subscribe(WorkflowEventType.RETRY_STAGE, retry_handler)

    # Publish retry stage event
    retry_event = WorkflowEvent(
        event_type=WorkflowEventType.RETRY_STAGE,
        task_id="task-1",
        stage="coder",
        data={"retry_count": 1, "reason": "test_failure"}
    )

    await event_bus.publish(retry_event)

    # Retry handler should be called
    retry_handler.assert_called_once_with(retry_event)
    assert retry_handler.call_args[0][0].data["retry_count"] == 1


@pytest.mark.asyncio
async def test_event_driven_workflow_trigger_workflow_completion(event_bus):
    """Test event-driven workflow trigger on workflow completion."""
    completion_handlers = []

    async def completion_handler(event):
        """Handler for workflow completion."""
        if event.event_type == WorkflowEventType.WORKFLOW_COMPLETED:
            completion_handlers.append({
                "task_id": event.task_id,
                "stages": event.data.get("completed_stages", [])
            })

    event_bus.subscribe(WorkflowEventType.WORKFLOW_COMPLETED, completion_handler)

    # Publish workflow completion event
    completion_event = WorkflowEvent(
        event_type=WorkflowEventType.WORKFLOW_COMPLETED,
        task_id="task-1",
        data={"completed_stages": ["planner", "coder", "test"]}
    )

    await event_bus.publish(completion_event)

    # Completion handler should be called
    assert len(completion_handlers) == 1
    assert completion_handlers[0]["task_id"] == "task-1"
    assert len(completion_handlers[0]["stages"]) == 3


@pytest.mark.asyncio
async def test_event_driven_workflow_trigger_error_handling(event_bus):
    """Test event-driven workflow trigger with error handling."""
    error_handler = Mock(side_effect=Exception("Handler error"))
    good_handler = AsyncMock()

    # Subscribe both error and good handlers
    event_bus.subscribe(WorkflowEventType.TRIGGER_NEXT_STAGE, error_handler)
    event_bus.subscribe(WorkflowEventType.TRIGGER_NEXT_STAGE, good_handler)

    # Publish trigger event
    trigger_event = WorkflowEvent(
        event_type=WorkflowEventType.TRIGGER_NEXT_STAGE,
        task_id="task-1",
        stage="planner",
        data={"completed_stage": "planner", "next_stage": "coder"}
    )

    # Should not raise exception, both handlers should be called
    await event_bus.publish(trigger_event)

    error_handler.assert_called_once()
    good_handler.assert_called_once()
    # Event should still be in history
    assert len(event_bus._event_history) == 1
