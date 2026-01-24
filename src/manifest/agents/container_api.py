"""
Container API - HTTP API for inter-container communication.
Provides REST endpoints for agents to communicate.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
import asyncio
from datetime import datetime
import uuid

# Message models
class Message(BaseModel):
    """Message model for inter-container communication.
    
    Represents a message sent between containers or agents. Messages
    are routed by topic and can target specific agents.
    
    Attributes:
        id: Unique message identifier.
        topic: Message topic/category for routing.
        timestamp: ISO timestamp when message was created.
        payload: Message data dictionary.
        target_agent: Optional target agent ID for direct messaging.
    """
    id: str
    topic: str
    timestamp: str
    payload: Dict[str, Any]
    target_agent: Optional[str] = None


class MessageResponse(BaseModel):
    """Response model for message posting operations.
    
    Indicates whether a message was successfully posted to the
    message bus and provides the message ID for tracking.
    
    Attributes:
        success: Whether the message was posted successfully.
        message_id: ID of the posted message.
    """
    success: bool
    message_id: str


# Global message store (in production, use Redis or similar)
_message_store: Dict[str, List[Dict[str, Any]]] = {}  # topic -> messages
_agent_statuses: Dict[str, Dict[str, Any]] = {}  # agent_id -> status


def create_container_api(state_manager=None) -> FastAPI:
    """
    Create FastAPI app for container communication.
    
    Args:
        state_manager: Optional state manager for state sync
        
    Returns:
        FastAPI application
    """
    app = FastAPI(title="Manifest Container API")
    
    # CORS middleware for container communication
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.post("/api/messages", response_model=MessageResponse)
    async def post_message(message: Message):
        """Post a message to the message bus."""
        topic = message.topic
        
        if topic not in _message_store:
            _message_store[topic] = []
        
        message_dict = message.dict()
        _message_store[topic].append(message_dict)
        
        # Keep only last 100 messages per topic
        if len(_message_store[topic]) > 100:
            _message_store[topic] = _message_store[topic][-100:]
        
        return MessageResponse(success=True, message_id=message.id)
    
    @app.get("/api/messages")
    async def get_messages(
        topic: Optional[str] = None, 
        since: Optional[str] = None,
        target_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get messages from the message bus.
        
        Args:
            topic: Optional topic filter.
            since: Optional ISO timestamp to get messages after.
            target_agent: Optional target agent ID filter.
        """
        if topic:
            messages = _message_store.get(topic, [])
        else:
            # Return all messages
            all_messages = []
            for topic_msgs in _message_store.values():
                all_messages.extend(topic_msgs)
            messages = sorted(all_messages, key=lambda x: x.get("timestamp", ""))
        
        # Filter by timestamp
        if since:
            messages = [m for m in messages if m.get("timestamp", "") > since]
            
        # Filter by target agent (include broadcast messages with target_agent=None)
        if target_agent:
            messages = [m for m in messages if m.get("target_agent") in [None, target_agent]]
        
        return {"messages": messages}
    
    @app.get("/api/agents/{agent_id}/status")
    async def get_agent_status(agent_id: str) -> Dict[str, Any]:
        """Get status of an agent."""
        status = _agent_statuses.get(agent_id, {"status": "not_found"})
        return status
    
    @app.post("/api/agents/{agent_id}/status")
    async def update_agent_status(agent_id: str, status: Dict[str, Any]) -> Dict[str, Any]:
        """Update agent status."""
        _agent_statuses[agent_id] = {
            **status,
            "last_updated": datetime.now().isoformat()
        }
        return {"success": True}
    
    @app.get("/api/health")
    async def health_check() -> Dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}
    
    return app
