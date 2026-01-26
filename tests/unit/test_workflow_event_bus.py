"""
Unit tests for WorkflowEventBus.

Tests event publishing, subscription, and workflow event handling.
"""
import pytest
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
