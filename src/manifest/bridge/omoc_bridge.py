"""
OMOC Bridge - IPC engine for communicating with Oh My Open Code.
Handles state persistence, message protocol, and agent coordination.
"""
import asyncio
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Callable, Awaitable
from manifest.core.state_manager import StateManager


class OMOCBridge:
    """IPC bridge to OMOC process via standard I/O pipes."""
    
    def __init__(self, state_manager: StateManager, omoc_path: Optional[str] = None):
        self.state_manager = state_manager
        self.omoc_path = omoc_path or "omoc"  # Default to 'omoc' command
        self.process: Optional[subprocess.Popen] = None
        self.reader_task: Optional[asyncio.Task] = None
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.response_callbacks: Dict[str, Callable[[Dict[str, Any]], Awaitable[None]]] = {}
        self.is_connected = False
        self._message_id_counter = 0
        self._standalone_mode = False  # True when OMOC is not available, use simulation
    
    async def start(self) -> bool:
        """Start the OMOC process and establish IPC connection."""
        # Check if OMOC is available
        if not self.is_omoc_available():
            # Fall back to standalone mode (simulated OMOC)
            self.is_connected = True
            self._standalone_mode = True
            # Load state
            state = self.state_manager.get_state()
            # In standalone mode, we'll simulate agent responses
            return True
        
        try:
            # Start OMOC process with pipes
            self.process = subprocess.Popen(
                [self.omoc_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Start reader task
            self.reader_task = asyncio.create_task(self._read_messages())
            self.is_connected = True
            self._standalone_mode = False
            
            # Load state and send to OMOC
            state = self.state_manager.get_state()
            await self.send_message({
                "type": "init",
                "payload": {"state": state}
            })
            
            return True
        except Exception as e:
            print(f"Error starting OMOC: {e}")
            # Fall back to standalone mode
            self.is_connected = True
            self._standalone_mode = True
            return True
    
    async def stop(self):
        """Stop the OMOC process."""
        self.is_connected = False
        
        # If in standalone mode, nothing to stop
        if self._standalone_mode:
            return
        
        if self.reader_task:
            self.reader_task.cancel()
            try:
                await self.reader_task
            except asyncio.CancelledError:
                pass
        
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
    
    async def _read_messages(self):
        """Continuously read messages from OMOC stdout."""
        if not self.process or not self.process.stdout:
            return
        
        while self.is_connected:
            try:
                line = await asyncio.to_thread(self.process.stdout.readline)
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                try:
                    message = json.loads(line)
                    await self._handle_message(message)
                except json.JSONDecodeError:
                    print(f"Invalid JSON from OMOC: {line}")
            except Exception as e:
                if self.is_connected:
                    print(f"Error reading from OMOC: {e}")
                break
    
    async def _handle_message(self, message: Dict[str, Any]):
        """Handle incoming message from OMOC."""
        msg_type = message.get("type")
        msg_id = message.get("id")
        
        if msg_type == "response" and msg_id:
            # Handle response to a previous command
            callback = self.response_callbacks.pop(msg_id, None)
            if callback:
                await callback(message)
        elif msg_type == "state_update":
            # Update state from OMOC
            payload = message.get("payload", {})
            if "mission_tree" in payload:
                self.state_manager.set_mission_tree(payload["mission_tree"])
            if "task_checklist" in payload:
                self.state_manager.set_task_checklist(payload["task_checklist"])
            await self.state_manager.save_state()
        elif msg_type == "agent_output":
            # Agent output for a channel
            payload = message.get("payload", {})
            channel = payload.get("channel", "main")
            content = payload.get("content", "")
            role = payload.get("role", "assistant")
            self.state_manager.add_chat_message(channel, role, content)
            await self.state_manager.save_state()
        elif msg_type == "error":
            print(f"OMOC error: {message.get('payload', {}).get('message', 'Unknown error')}")
    
    async def send_message(self, message: Dict[str, Any], callback: Optional[Callable] = None) -> Optional[str]:
        """Send a message to OMOC."""
        # If in standalone mode, simulate response
        if self._standalone_mode:
            if callback:
                # Simulate a successful response
                await callback({
                    "type": "response",
                    "status": "ok",
                    "data": {"mode": "standalone", "message": "Simulated response"}
                })
            return "standalone-msg-id"
        
        if not self.is_connected or not self.process or not self.process.stdin:
            return None
        
        # Add message ID for response tracking
        msg_id = str(self._message_id_counter)
        self._message_id_counter += 1
        message["id"] = msg_id
        
        if callback:
            self.response_callbacks[msg_id] = callback
        
        try:
            message_str = json.dumps(message) + "\n"
            self.process.stdin.write(message_str)
            self.process.stdin.flush()
            return msg_id
        except Exception as e:
            print(f"Error sending message to OMOC: {e}")
            if msg_id in self.response_callbacks:
                del self.response_callbacks[msg_id]
            return None
    
    async def start_mission(self, task_id: str) -> bool:
        """Start a mission with the given task ID."""
        result = {"success": False}
        
        async def callback(response: Dict[str, Any]):
            result["success"] = response.get("status") == "ok"
            result["data"] = response.get("data", {})
        
        await self.send_message({
            "type": "command",
            "command": "start_mission",
            "payload": {"task_id": task_id}
        }, callback)
        
        # Wait for response (with timeout)
        await asyncio.sleep(0.1)  # Give time for response
        return result["success"]
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current mission status."""
        result = {"status": "unknown", "data": {}}
        
        async def callback(response: Dict[str, Any]):
            result["status"] = response.get("status", "unknown")
            result["data"] = response.get("data", {})
        
        await self.send_message({
            "type": "command",
            "command": "get_status",
            "payload": {}
        }, callback)
        
        await asyncio.sleep(0.1)
        return result
    
    async def promote_task(self, task_id: str, stage: str) -> bool:
        """Promote a task to a new stage."""
        result = {"success": False}
        
        async def callback(response: Dict[str, Any]):
            result["success"] = response.get("status") == "ok"
        
        await self.send_message({
            "type": "command",
            "command": "promote_task",
            "payload": {"task_id": task_id, "stage": stage}
        }, callback)
        
        await asyncio.sleep(0.1)
        return result["success"]
    
    async def get_agent_output(self, channel: str) -> list:
        """Get agent output for a channel."""
        return self.state_manager.get_chat_history(channel)
    
    async def start_agent_mission(
        self,
        task_id: str,
        agent_type: str,
        context: Dict[str, Any],
        model_config: Dict[str, Any]
    ) -> bool:
        """Start an agent mission with scoped context and model config."""
        # If in standalone mode, simulate agent start
        if self._standalone_mode:
            # Simulate agent start
            channel = f"squad-{task_id}-{agent_type}"
            self.state_manager.add_chat_message(
                channel,
                "assistant",
                f"[{agent_type.upper()}] Agent started for task {task_id}\n"
                f"Context tiers: {', '.join([k for k in context.keys() if k.startswith('tier_')])}\n"
                f"Model: {model_config.get('model', 'default')}"
            )
            await self.state_manager.save_state()
            return True
        
        result = {"success": False}
        
        async def callback(response: Dict[str, Any]):
            result["success"] = response.get("status") == "ok"
            result["data"] = response.get("data", {})
        
        await self.send_message({
            "type": "agent_start",
            "command": "start_agent_mission",
            "payload": {
                "task_id": task_id,
                "agent_type": agent_type,
                "context": context,
                "model_config": model_config
            }
        }, callback)
        
        # Wait for response
        await asyncio.sleep(0.2)  # Give more time for agent start
        return result["success"]
    
    async def get_agent_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of agent working on task."""
        # If in standalone mode, return simulated status
        if self._standalone_mode:
            # Check if there's chat history for this task
            channel = None
            for ch in self.state_manager.get_chat_history("main"):
                if task_id in str(ch.get("content", "")):
                    channel = f"squad-{task_id}"
                    break
            
            if channel:
                history = self.state_manager.get_chat_history(channel)
                return {
                    "status": "active",
                    "data": {
                        "task_id": task_id,
                        "message_count": len(history),
                        "mode": "standalone"
                    }
                }
            return {"status": "not_active", "data": {}}
        
        result = {"status": "unknown", "data": {}}
        
        async def callback(response: Dict[str, Any]):
            result["status"] = response.get("status", "unknown")
            result["data"] = response.get("data", {})
        
        await self.send_message({
            "type": "agent_status",
            "command": "get_agent_status",
            "payload": {"task_id": task_id}
        }, callback)
        
        await asyncio.sleep(0.1)
        return result
    
    async def stop_agent(self, task_id: str) -> bool:
        """Stop agent working on task."""
        result = {"success": False}
        
        async def callback(response: Dict[str, Any]):
            result["success"] = response.get("status") == "ok"
        
        await self.send_message({
            "type": "agent_stop",
            "command": "stop_agent",
            "payload": {"task_id": task_id}
        }, callback)
        
        await asyncio.sleep(0.1)
        return result["success"]
    
    def is_omoc_available(self) -> bool:
        """Check if OMOC command is available."""
        try:
            result = subprocess.run(
                ["which", self.omoc_path],
                capture_output=True,
                timeout=2
            )
            return result.returncode == 0
        except Exception:
            return False