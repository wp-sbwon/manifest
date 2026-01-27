"""
Agent-to-Agent messaging system for direct communication.

This module provides a message bus for agents to communicate directly with
each other, enabling request-response patterns and event-based communication
without going through the workflow executor.

Agents can:
- Send messages to specific agents
- Send messages to agent types
- Subscribe to message types
- Request information from other agents
- Respond to requests
"""
import asyncio
from typing import Dict, Any, Optional, Callable, List, Set
from enum import Enum
from dataclasses import dataclass, field
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class MessageType(Enum):
    """Types of agent messages."""
    REQUEST = "request"  # Request information or action
    RESPONSE = "response"  # Response to a request
    NOTIFICATION = "notification"  # One-way notification
    EVENT = "event"  # Event notification
    BROADCAST = "broadcast"  # Broadcast to all agents


@dataclass
class AgentMessage:
    """Represents a message between agents.

    Attributes:
        message_id: Unique identifier for this message.
        message_type: Type of message (request, response, notification, etc.).
        from_agent_id: ID of the sending agent.
        from_agent_type: Type of the sending agent.
        to_agent_id: ID of the target agent (None for broadcast/type-based).
        to_agent_type: Type of the target agent (None for specific agent).
        subject: Message subject/topic.
        content: Message content/data.
        correlation_id: ID for request-response correlation (for responses).
        metadata: Additional metadata.
        timestamp: When the message was created.
    """
    message_id: str
    message_type: MessageType
    from_agent_id: str
    from_agent_type: str
    to_agent_id: Optional[str] = None
    to_agent_type: Optional[str] = None
    subject: str = ""
    content: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: __import__("time").time())

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "from_agent_id": self.from_agent_id,
            "from_agent_type": self.from_agent_type,
            "to_agent_id": self.to_agent_id,
            "to_agent_type": self.to_agent_type,
            "subject": self.subject,
            "content": self.content,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }


class AgentMessageBus:
    """Message bus for agent-to-agent communication.

    Provides publish-subscribe and request-response patterns for agents
    to communicate directly with each other. Supports:
    - Direct messaging (agent to agent)
    - Type-based messaging (agent to agent type)
    - Broadcast messaging (agent to all)
    - Request-response pattern with correlation
    - Message routing and delivery

    Attributes:
        _registered_agents: Dictionary mapping agent_id to agent info.
        _type_subscriptions: Dictionary mapping agent_type to list of agent_ids.
        _subject_subscriptions: Dictionary mapping subject to list of callbacks.
        _pending_requests: Dictionary mapping correlation_id to response future.
        _message_history: List of recent messages for debugging.
    """

    def __init__(self):
        """Initialize the agent message bus."""
        self._registered_agents: Dict[str, Dict[str, Any]] = {}  # agent_id -> agent info
        self._type_subscriptions: Dict[str, Set[str]] = {}  # agent_type -> set of agent_ids
        self._subject_subscriptions: Dict[str, List[Callable]] = {}  # subject -> callbacks
        self._pending_requests: Dict[str, asyncio.Future] = {}  # correlation_id -> future
        self._message_history: List[AgentMessage] = []
        self._max_history = 1000
        self._message_id_counter = 0
        self._lock = asyncio.Lock()

    def register_agent(
        self,
        agent_id: str,
        agent_type: str,
        message_handler: Optional[Callable[[AgentMessage], Any]] = None
    ) -> None:
        """Register an agent with the message bus.

        Args:
            agent_id: Unique identifier for the agent.
            agent_type: Type of the agent (e.g., "planner", "coder").
            message_handler: Optional callback function to handle incoming messages.
                Should be async and accept AgentMessage.
        """
        self._registered_agents[agent_id] = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "message_handler": message_handler,
            "registered_at": __import__("time").time()
        }

        # Add to type subscriptions
        if agent_type not in self._type_subscriptions:
            self._type_subscriptions[agent_type] = set()
        self._type_subscriptions[agent_type].add(agent_id)

        logger.debug(f"Agent {agent_id} ({agent_type}) registered with message bus")

    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent from the message bus.

        Args:
            agent_id: ID of the agent to unregister.
        """
        if agent_id in self._registered_agents:
            agent_info = self._registered_agents[agent_id]
            agent_type = agent_info["agent_type"]

            # Remove from type subscriptions
            if agent_type in self._type_subscriptions:
                self._type_subscriptions[agent_type].discard(agent_id)
                if not self._type_subscriptions[agent_type]:
                    del self._type_subscriptions[agent_type]

            del self._registered_agents[agent_id]
            logger.debug(f"Agent {agent_id} unregistered from message bus")

    def subscribe_to_subject(
        self,
        subject: str,
        callback: Callable[[AgentMessage], Any]
    ) -> None:
        """Subscribe to messages with a specific subject.

        Args:
            subject: Subject/topic to subscribe to.
            callback: Callback function to handle messages.
                Should be async and accept AgentMessage.
        """
        if subject not in self._subject_subscriptions:
            self._subject_subscriptions[subject] = []
        self._subject_subscriptions[subject].append(callback)
        logger.debug(f"Subscribed to subject: {subject}")

    def unsubscribe_from_subject(
        self,
        subject: str,
        callback: Callable[[AgentMessage], Any]
    ) -> None:
        """Unsubscribe from a subject.

        Args:
            subject: Subject to unsubscribe from.
            callback: Callback function to remove.
        """
        if subject in self._subject_subscriptions:
            try:
                self._subject_subscriptions[subject].remove(callback)
                if not self._subject_subscriptions[subject]:
                    del self._subject_subscriptions[subject]
                logger.debug(f"Unsubscribed from subject: {subject}")
            except ValueError:
                pass

    async def send_message(
        self,
        from_agent_id: str,
        to_agent_id: Optional[str] = None,
        to_agent_type: Optional[str] = None,
        subject: str = "",
        content: Dict[str, Any] = None,
        message_type: MessageType = MessageType.NOTIFICATION,
        correlation_id: Optional[str] = None
    ) -> Optional[str]:
        """Send a message to an agent or agent type.

        Args:
            from_agent_id: ID of the sending agent.
            to_agent_id: ID of the target agent (for direct messaging).
            to_agent_type: Type of the target agent (for type-based messaging).
            subject: Message subject/topic.
            content: Message content/data.
            message_type: Type of message.
            correlation_id: Optional correlation ID for request-response (set by request()).

        Returns:
            Message ID if message was sent, None otherwise.
        """
        if from_agent_id not in self._registered_agents:
            logger.warning(f"Agent {from_agent_id} not registered, cannot send message")
            return None

        from_agent_info = self._registered_agents[from_agent_id]
        from_agent_type = from_agent_info["agent_type"]

        # Generate message ID
        async with self._lock:
            self._message_id_counter += 1
            message_id = f"msg_{self._message_id_counter}_{from_agent_id}"

        message = AgentMessage(
            message_id=message_id,
            message_type=message_type,
            from_agent_id=from_agent_id,
            from_agent_type=from_agent_type,
            to_agent_id=to_agent_id,
            to_agent_type=to_agent_type,
            subject=subject,
            content=content or {},
            correlation_id=correlation_id,
            timestamp=__import__("time").time()
        )

        # Add to history
        self._message_history.append(message)
        if len(self._message_history) > self._max_history:
            self._message_history.pop(0)

        # Route message
        await self._route_message(message)

        return message_id

    async def request(
        self,
        from_agent_id: str,
        to_agent_id: Optional[str] = None,
        to_agent_type: Optional[str] = None,
        subject: str = "",
        content: Dict[str, Any] = None,
        timeout: float = 30.0
    ) -> Optional[Dict[str, Any]]:
        """Send a request and wait for response (request-response pattern).

        Args:
            from_agent_id: ID of the requesting agent.
            to_agent_id: ID of the target agent.
            to_agent_type: Type of the target agent.
            subject: Request subject.
            content: Request content/data.
            timeout: Timeout in seconds for response.

        Returns:
            Response content dictionary, or None if timeout or error.
        """
        # Generate correlation ID
        correlation_id = f"req_{from_agent_id}_{__import__('time').time()}"

        # Create future for response
        response_future = asyncio.Future()
        self._pending_requests[correlation_id] = response_future

        # Send request message (pass correlation_id so handler can respond with it)
        message_id = await self.send_message(
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            to_agent_type=to_agent_type,
            subject=subject,
            content=content or {},
            message_type=MessageType.REQUEST,
            correlation_id=correlation_id
        )

        if not message_id:
            self._pending_requests.pop(correlation_id, None)
            return None

        try:
            # Wait for response with timeout
            response = await asyncio.wait_for(response_future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            logger.warning(f"Request {correlation_id} timed out after {timeout}s")
            self._pending_requests.pop(correlation_id, None)
            return None
        except Exception as e:
            logger.error(f"Error waiting for response to {correlation_id}: {e}")
            self._pending_requests.pop(correlation_id, None)
            return None

    async def respond(
        self,
        from_agent_id: str,
        correlation_id: str,
        content: Dict[str, Any] = None,
        success: bool = True
    ) -> bool:
        """Respond to a request.

        Args:
            from_agent_id: ID of the responding agent.
            correlation_id: Correlation ID from the original request.
            content: Response content/data.
            success: Whether the request was successful.

        Returns:
            True if response was delivered, False otherwise.
        """
        if correlation_id not in self._pending_requests:
            logger.warning(f"Correlation ID {correlation_id} not found in pending requests")
            return False

        response_future = self._pending_requests[correlation_id]

        response_data = {
            "success": success,
            "content": content or {},
            "correlation_id": correlation_id
        }

        # Set response future result
        if not response_future.done():
            response_future.set_result(response_data)
            self._pending_requests.pop(correlation_id, None)
            return True

        return False

    async def _route_message(self, message: AgentMessage) -> None:
        """Route a message to appropriate recipients.

        Args:
            message: Message to route.
        """
        recipients = []

        # Determine recipients based on message type and target
        if message.to_agent_id:
            # Direct message to specific agent
            if message.to_agent_id in self._registered_agents:
                recipients.append(message.to_agent_id)
        elif message.to_agent_type:
            # Message to agent type
            if message.to_agent_type in self._type_subscriptions:
                recipients.extend(self._type_subscriptions[message.to_agent_type])
        elif message.message_type == MessageType.BROADCAST:
            # Broadcast to all agents
            recipients.extend(self._registered_agents.keys())

        # Also check subject subscriptions
        if message.subject and message.subject in self._subject_subscriptions:
            # Subject-based subscribers (can be any agent or external handler)
            for callback in self._subject_subscriptions[message.subject]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(message)
                    else:
                        callback(message)
                except Exception as e:
                    logger.error(f"Error in subject subscriber for {message.subject}: {e}", exc_info=True)

        # Deliver to recipients
        for recipient_id in recipients:
            await self._deliver_message(message, recipient_id)

    async def _deliver_message(self, message: AgentMessage, recipient_id: str) -> None:
        """Deliver a message to a specific agent.

        Args:
            message: Message to deliver.
            recipient_id: ID of the recipient agent.
        """
        if recipient_id not in self._registered_agents:
            return

        agent_info = self._registered_agents[recipient_id]
        handler = agent_info.get("message_handler")

        if handler:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                logger.error(
                    f"Error delivering message {message.message_id} to agent {recipient_id}: {e}",
                    exc_info=True
                )
        else:
            logger.debug(f"Agent {recipient_id} has no message handler, message {message.message_id} not delivered")

    def get_message_history(
        self,
        agent_id: Optional[str] = None,
        subject: Optional[str] = None,
        limit: int = 100
    ) -> List[AgentMessage]:
        """Get message history with optional filtering.

        Args:
            agent_id: Optional agent ID to filter by.
            subject: Optional subject to filter by.
            limit: Maximum number of messages to return.

        Returns:
            List of matching messages, most recent first.
        """
        messages = self._message_history

        if agent_id:
            messages = [
                m for m in messages
                if m.from_agent_id == agent_id or m.to_agent_id == agent_id
            ]

        if subject:
            messages = [m for m in messages if m.subject == subject]

        # Return most recent first
        return list(reversed(messages[-limit:]))

    def get_registered_agents(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered agents.

        Returns:
            Dictionary mapping agent_id to agent info.
        """
        return self._registered_agents.copy()
