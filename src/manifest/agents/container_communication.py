"""
Container Communication - Inter-container messaging and state synchronization.
Enables agents running in different containers to communicate and share state.
"""
import asyncio
import json
import httpx
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
import uuid


class ContainerMessageBus:
    """
    Message bus for inter-container communication.
    Supports HTTP-based messaging and state synchronization.
    """
    
    def __init__(self, base_url: str = "http://manifest-app:8000"):
        """
        Initialize message bus.
        
        Args:
            base_url: Base URL for the main app container
        """
        self.base_url = base_url
        self.client: Optional[httpx.AsyncClient] = None
        self.message_queue: List[Dict[str, Any]] = []
        self.subscribers: Dict[str, List[callable]] = {}  # topic -> callbacks
    
    async def connect(self):
        """Connect to message bus."""
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def disconnect(self):
        """Disconnect from message bus."""
        if self.client:
            await self.client.aclose()
            self.client = None
    
    async def send_message(
        self,
        topic: str,
        message: Dict[str, Any],
        target_agent: Optional[str] = None
    ) -> bool:
        """
        Send a message to a topic or specific agent.
        
        Args:
            topic: Message topic (e.g., "task-update", "agent-status")
            message: Message payload
            target_agent: Optional target agent ID
            
        Returns:
            True if message sent successfully
        """
        if not self.client:
            await self.connect()
        
        payload = {
            "id": str(uuid.uuid4()),
            "topic": topic,
            "timestamp": datetime.now().isoformat(),
            "payload": message,
            "target_agent": target_agent
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/messages",
                json=payload
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error sending message: {e}")
            # Fallback: store locally
            self.message_queue.append(payload)
            return False
    
    async def subscribe(
        self,
        topic: str,
        callback: callable
    ):
        """
        Subscribe to messages on a topic.
        
        Args:
            topic: Topic to subscribe to
            callback: Async callback function(message) -> None
        """
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        self.subscribers[topic].append(callback)
    
    async def receive_messages(
        self,
        topic: Optional[str] = None,
        timeout: float = 5.0
    ) -> List[Dict[str, Any]]:
        """
        Receive messages from the bus.
        
        Args:
            topic: Optional topic filter
            timeout: Timeout in seconds
            
        Returns:
            List of messages
        """
        if not self.client:
            await self.connect()
        
        try:
            params = {}
            if topic:
                params["topic"] = topic
            
            response = await self.client.get(
                f"{self.base_url}/api/messages",
                params=params,
                timeout=timeout
            )
            
            if response.status_code == 200:
                return response.json().get("messages", [])
        except Exception as e:
            print(f"Error receiving messages: {e}")
        
        return []
    
    async def broadcast_state_update(
        self,
        agent_id: str,
        state: Dict[str, Any]
    ) -> bool:
        """
        Broadcast state update to all agents.
        
        Args:
            agent_id: Agent identifier
            state: State update
            
        Returns:
            True if broadcast successful
        """
        return await self.send_message(
            topic="state-update",
            message={
                "agent_id": agent_id,
                "state": state
            }
        )
    
    async def request_agent_status(
        self,
        agent_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Request status from another agent.
        
        Args:
            agent_id: Target agent ID
            
        Returns:
            Agent status or None
        """
        if not self.client:
            await self.connect()
        
        try:
            response = await self.client.get(
                f"{self.base_url}/api/agents/{agent_id}/status",
                timeout=10.0
            )
            
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error requesting agent status: {e}")
        
        return None


class ContainerStateSync:
    """
    State synchronization between containers.
    Keeps agent states in sync across containers.
    """
    
    def __init__(
        self,
        state_manager: Any,  # StateManager
        message_bus: ContainerMessageBus
    ):
        """
        Initialize state synchronizer.
        
        Args:
            state_manager: State manager instance
            message_bus: Message bus for communication
        """
        self.state_manager = state_manager
        self.message_bus = message_bus
        self.sync_interval = 5.0  # seconds
        self._sync_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start state synchronization."""
        await self.message_bus.subscribe("state-update", self._handle_state_update)
        self._sync_task = asyncio.create_task(self._sync_loop())
    
    async def stop(self):
        """Stop state synchronization."""
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
    
    async def _sync_loop(self):
        """Periodic state synchronization loop."""
        while True:
            try:
                await asyncio.sleep(self.sync_interval)
                await self._sync_state()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in sync loop: {e}")
    
    async def _sync_state(self):
        """Synchronize state with other containers."""
        # Get current state
        state = self.state_manager.get_state()
        
        # Broadcast state update
        await self.message_bus.broadcast_state_update(
            agent_id="local",
            state={
                "mission_tree": state.get("mission_tree", {}),
                "task_checklist": state.get("task_checklist", []),
                "timestamp": datetime.now().isoformat()
            }
        )
    
    async def _handle_state_update(self, message: Dict[str, Any]):
        """Handle incoming state update."""
        payload = message.get("payload", {})
        agent_id = payload.get("agent_id")
        state = payload.get("state", {})
        
        # Merge state updates (conflict resolution needed in production)
        current_state = self.state_manager.get_state()
        
        # Update mission tree if provided
        if "mission_tree" in state:
            current_mission = current_state.get("mission_tree", {})
            # Merge logic (simple merge for now)
            current_state["mission_tree"] = {**current_mission, **state["mission_tree"]}
            self.state_manager.set_mission_tree(current_state["mission_tree"])
        
        # Update task checklist if provided
        if "task_checklist" in state:
            current_tasks = current_state.get("task_checklist", [])
            # Merge task updates
            task_map = {t.get("id"): t for t in current_tasks}
            for task in state["task_checklist"]:
                task_id = task.get("id")
                if task_id:
                    task_map[task_id] = {**task_map.get(task_id, {}), **task}
            self.state_manager.set_task_checklist(list(task_map.values()))
        
        await self.state_manager.save_state()
