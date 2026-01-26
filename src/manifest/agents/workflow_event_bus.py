"""
Event bus for multi-agent workflow automation.

This module provides an event-driven system for coordinating agents in the
Worker Squad workflow. Agents can emit events (e.g., completion, errors)
and other agents or the workflow executor can subscribe to these events
to automatically trigger next stages.
"""
import asyncio
from typing import Dict, Any, Optional, Callable, List, Set
from enum import Enum
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class WorkflowEventType(Enum):
    """Types of workflow events."""
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    STAGE_COMPLETED = "stage_completed"
    STAGE_FAILED = "stage_failed"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    TRIGGER_NEXT_STAGE = "trigger_next_stage"
    RETRY_STAGE = "retry_stage"


class WorkflowEvent:
    """Represents a workflow event.

    Attributes:
        event_type: Type of event (WorkflowEventType).
        task_id: ID of the task this event relates to.
        stage: Stage name (e.g., "planner", "coder").
        agent_type: Type of agent that emitted the event.
        data: Additional event data.
        timestamp: When the event occurred.
    """

    def __init__(
        self,
        event_type: WorkflowEventType,
        task_id: str,
        stage: Optional[str] = None,
        agent_type: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ):
        """Initialize a workflow event.

        Args:
            event_type: Type of event.
            task_id: Task ID.
            stage: Optional stage name.
            agent_type: Optional agent type.
            data: Optional additional data.
        """
        import time
        self.event_type = event_type
        self.task_id = task_id
        self.stage = stage
        self.agent_type = agent_type
        self.data = data or {}
        self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_type": self.event_type.value,
            "task_id": self.task_id,
            "stage": self.stage,
            "agent_type": self.agent_type,
            "data": self.data,
            "timestamp": self.timestamp
        }


class WorkflowEventBus:
    """Event bus for workflow automation.

    Provides publish-subscribe pattern for workflow events. Agents can
    emit events, and subscribers (e.g., Worker Squad Executor) can
    listen to events and automatically trigger next stages.

    Attributes:
        _subscribers: Dictionary mapping event types to list of callbacks.
        _event_history: List of recent events for debugging.
    """

    def __init__(self):
        """Initialize the event bus."""
        self._subscribers: Dict[WorkflowEventType, List[Callable]] = {}
        self._event_history: List[WorkflowEvent] = []
        self._max_history = 1000  # Keep last 1000 events

    async def publish(self, event: WorkflowEvent) -> None:
        """Publish an event to all subscribers.

        Args:
            event: The event to publish.
        """
        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        # Notify subscribers
        subscribers = self._subscribers.get(event.event_type, [])
        if subscribers:
            logger.debug(
                f"Publishing event {event.event_type.value} for task {event.task_id} "
                f"to {len(subscribers)} subscribers"
            )

            # Call all subscribers
            for callback in subscribers:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    logger.error(
                        f"Error in event subscriber for {event.event_type.value}: {e}",
                        exc_info=True
                    )

    def subscribe(
        self,
        event_type: WorkflowEventType,
        callback: Callable[[WorkflowEvent], Any]
    ) -> None:
        """Subscribe to events of a specific type.

        Args:
            event_type: Type of event to subscribe to.
            callback: Callback function that receives WorkflowEvent.
                Can be async or sync.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        logger.debug(f"Subscribed to {event_type.value}")

    def unsubscribe(
        self,
        event_type: WorkflowEventType,
        callback: Callable[[WorkflowEvent], Any]
    ) -> None:
        """Unsubscribe from events.

        Args:
            event_type: Type of event to unsubscribe from.
            callback: Callback function to remove.
        """
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
                logger.debug(f"Unsubscribed from {event_type.value}")
            except ValueError:
                pass  # Callback not in list

    def get_event_history(
        self,
        task_id: Optional[str] = None,
        event_type: Optional[WorkflowEventType] = None,
        limit: int = 100
    ) -> List[WorkflowEvent]:
        """Get event history with optional filtering.

        Args:
            task_id: Optional task ID to filter by.
            event_type: Optional event type to filter by.
            limit: Maximum number of events to return.

        Returns:
            List of matching events, most recent first.
        """
        events = self._event_history

        if task_id:
            events = [e for e in events if e.task_id == task_id]

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        # Return most recent first
        return list(reversed(events[-limit:]))

    def get_latest_event(
        self,
        task_id: str,
        event_type: Optional[WorkflowEventType] = None
    ) -> Optional[WorkflowEvent]:
        """Get the latest event for a task.

        Args:
            task_id: Task ID to get event for.
            event_type: Optional event type to filter by.

        Returns:
            Latest matching event, or None if not found.
        """
        events = self.get_event_history(task_id=task_id, event_type=event_type, limit=1)
        return events[0] if events else None
