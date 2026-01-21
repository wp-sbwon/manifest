"""
OMOC Bridge - Direct integration with OMOC (Oh My Open Code).
Integrates OMOC agent system and terminal router directly instead of IPC.
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional, Callable, Awaitable
from manifest.core.state_manager import StateManager
from manifest.core.config import ConfigManager
from manifest.omoc.router.terminal_router import TerminalRouter
from manifest.omoc.agent.orchestrator import Orchestrator
from manifest.omoc.agent.manager import AgentManager
from manifest.omoc.agent.executor import AgentExecutor
from manifest.agents.watchdog import AgentWatchdog


class OMOCBridge:
    """
    Direct integration bridge to OMOC functionality.
    Uses OMOC code directly instead of IPC communication.
    """
    
    def __init__(
        self,
        state_manager: StateManager,
        config_manager: Optional[ConfigManager] = None,
        working_dir: Optional[Path] = None
    ):
        self.state_manager = state_manager
        self.config_manager = config_manager
        self.working_dir = working_dir or Path.cwd()
        
        # Resource monitor
        try:
            import docker
            docker_client = docker.from_env()
            self.resource_monitor = ResourceMonitor(docker_client)
        except Exception:
            self.resource_monitor = ResourceMonitor(None)
        
        # Watchdog for monitoring
        self.watchdog = AgentWatchdog(state_manager, None, check_interval=5.0)
        self.watchdog.set_resource_monitor(self.resource_monitor)
        
        # Terminal router for command execution (with watchdog)
        self.terminal_router = TerminalRouter(self.working_dir, watchdog=self.watchdog)
        
        # Update watchdog's terminal router reference
        self.watchdog.terminal_router = self.terminal_router
        
        # Agent executor for LLM calls
        self.executor = AgentExecutor(config_manager or ConfigManager(), state_manager) if config_manager else None
        
        # OMOC Agent system
        self.orchestrator = Orchestrator(state_manager)
        self.agent_manager = AgentManager(state_manager, executor=self.executor)
        
        self.is_connected = False
        self._message_id_counter = 0
        self._active_agents: Dict[str, Dict[str, Any]] = {}  # task_id -> agent info
    
    async def start(self) -> bool:
        """
        Initialize OMOC integration.
        Loads state and initializes OMOC agent system.
        """
        try:
            # Initialize terminal router (already done in __init__)
            # Start watchdog
            await self.watchdog.start()
            
            # OMOC agent system is already initialized in __init__
            
            self.is_connected = True
            return True
        except Exception as e:
            print(f"Error initializing OMOC: {e}")
            self.is_connected = False
            return False
    
    async def stop(self):
        """Stop OMOC integration and clean up resources."""
        self.is_connected = False
        
        # Stop watchdog
        await self.watchdog.stop()
        
        # Cancel all active commands
        for command_id in list(self.terminal_router.active_commands.keys()):
            self.terminal_router.cancel_command(command_id)
        
        # Stop all active agents
        for task_id in list(self._active_agents.keys()):
            await self.stop_agent(task_id)
            
        # TODO: Clean up OMOC agent system when integrated
        # if self.agent_manager:
        #     await self.agent_manager.shutdown()
    
    # Legacy IPC methods removed - now using direct integration
    # _read_messages, _handle_message, send_message are no longer needed
    
    async def start_mission(self, task_id: str, mission_description: str = "") -> bool:
        """
        Start a mission with the given task ID.
        
        Args:
            task_id: Task identifier
            mission_description: Optional mission description
        """
        success = await self.orchestrator.start_mission(task_id, mission_description)
        if success:
            self.state_manager.set_last_action(f"Started mission: {task_id}")
            await self.state_manager.save_state()
        return success
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get current mission status.
        TODO: Integrate with OMOC orchestrator when available.
        """
        state = self.state_manager.get_state()
        return {
            "status": "active",
            "data": {
                "mission_tree": state.get("mission_tree", {}),
                "task_checklist": state.get("task_checklist", []),
                "active_agents": len(self._active_agents)
            }
        }
    
    async def promote_task(self, task_id: str, stage: str) -> bool:
        """
        Promote a task to a new stage.
        TODO: Integrate with OMOC orchestrator when available.
        """
        tasks = self.state_manager.get_task_checklist()
        for task in tasks:
            if task.get("id") == task_id:
                task["stage"] = stage
                self.state_manager.set_task_checklist(tasks)
                await self.state_manager.save_state()
                return True
        return False
    
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
        """
        Start an agent mission with scoped context and model config.
        
        Args:
            task_id: Task identifier
            agent_type: Type of agent (prometheus, sisyphus, test, review)
            context: Agent context (tiered context)
            model_config: Model configuration
        """
        # Create agent using OMOC agent manager
        agent = await self.agent_manager.create_agent(
            agent_type=agent_type,
            context=context,
            model_config=model_config,
            task_id=task_id
        )
        
        # Start the agent
        success = await self.agent_manager.start_agent(task_id)
        
        if success:
            channel = f"squad-{task_id}-{agent_type}"
            self.state_manager.add_chat_message(
                channel,
                "assistant",
                f"[{agent_type.upper()}] Agent started for task {task_id}\n"
                f"Context tiers: {', '.join([k for k in context.keys() if k.startswith('tier_')])}\n"
                f"Model: {model_config.get('model', 'default')}"
            )
            
            self._active_agents[task_id] = {
                "agent": agent,
                "agent_type": agent_type,
                "status": "active",
                "channel": channel,
                "context": context,
                "model_config": model_config
            }
            
            await self.state_manager.save_state()
        
        return success
    
    async def get_agent_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get status of agent working on task.
        
        Args:
            task_id: Task identifier
        """
        agent_info = self.agent_manager.get_agent(task_id)
        
        if not agent_info:
            return {"status": "not_active", "data": {}}
        
        # Get channel info from active agents
        active_info = self._active_agents.get(task_id, {})
        channel = active_info.get("channel", f"squad-{task_id}")
        history = self.state_manager.get_chat_history(channel)
        
        return {
            "status": agent_info.get("status", "unknown"),
            "data": {
                "task_id": task_id,
                "agent_type": agent_info.get("type"),
                "message_count": len(history),
                "channel": channel
            }
        }
    
    async def stop_agent(self, task_id: str) -> bool:
        """
        Stop agent working on task.
        
        Args:
            task_id: Task identifier
        """
        # Stop agent using OMOC agent manager
        success = await self.agent_manager.stop_agent(task_id)
        
        if success:
            active_info = self._active_agents.get(task_id, {})
            channel = active_info.get("channel", f"squad-{task_id}")
            
            self.state_manager.add_chat_message(
                channel,
                "assistant",
                f"Agent stopped for task {task_id}"
            )
            
            if task_id in self._active_agents:
                del self._active_agents[task_id]
            
            await self.state_manager.save_state()
        
        return success