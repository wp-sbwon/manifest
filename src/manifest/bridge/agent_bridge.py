"""
Agent Bridge - Direct integration with agent system.
Integrates agent system and terminal router directly.
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional, Callable, Awaitable
from manifest.core.state_manager import StateManager
from manifest.core.config import ConfigManager
from manifest.runtime.router.terminal_router import TerminalRouter
from manifest.runtime.agent.orchestrator import Orchestrator
from manifest.runtime.agent.manager import AgentManager
from manifest.runtime.agent.executor import AgentExecutor


class AgentBridge:
    """
    Direct integration bridge to agent functionality.
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
        
        # Lazy import to avoid circular dependencies
        from manifest.agents.resource_monitor import ResourceMonitor
        from manifest.agents.watchdog import AgentWatchdog
        
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
        
        # Hook manager for prompt interception
        from manifest.runtime.hooks.prompt_hooks import HookManager, VisualRealityHook
        from manifest.audit.blueprint_synchronizer import BlueprintSynchronizer
        
        hook_manager = HookManager()
        # Register Visual Reality hook
        blueprint_synchronizer = BlueprintSynchronizer()
        visual_reality_hook = VisualRealityHook(state_manager, blueprint_synchronizer)
        hook_manager.register_hook(visual_reality_hook)
        
        # Agent executor for LLM calls (with hooks)
        self.executor = AgentExecutor(
            config_manager or ConfigManager(),
            state_manager,
            hook_manager=hook_manager
        ) if config_manager else None
        
        # Agent system
        self.orchestrator = Orchestrator(state_manager)
        self.agent_manager = AgentManager(state_manager, executor=self.executor)
        
        # Shadow Manager for isolated agent execution (optional)
        from manifest.runtime.shadow_manager import ShadowManager
        self.shadow_manager = ShadowManager(
            working_dir=self.working_dir,
            manifest_dir=state_manager.manifest_dir
        )
        self.use_shadow_processes = False  # Can be enabled via settings
        
        self.is_connected = False
        self._message_id_counter = 0
        self._active_agents: Dict[str, Dict[str, Any]] = {}  # task_id -> agent info
    
    async def start(self) -> bool:
        """
        Initialize agent integration.
        Loads state and initializes agent system.
        """
        try:
            # Initialize terminal router (already done in __init__)
            # Start watchdog
            await self.watchdog.start()
            
            # Agent system is already initialized in __init__
            
            self.is_connected = True
            return True
        except Exception as e:
            print(f"Error initializing agent system: {e}")
            self.is_connected = False
            return False
    
    async def stop(self):
        """Stop agent integration and clean up resources."""
        self.is_connected = False
        
        # Stop watchdog
        await self.watchdog.stop()
        
        # Cancel all active commands
        for command_id in list(self.terminal_router.active_commands.keys()):
            self.terminal_router.cancel_command(command_id)
        
        # Stop all active agents
        for task_id in list(self._active_agents.keys()):
            await self.stop_agent(task_id)
            
        # Clean up agent system
        if self.agent_manager:
            await self.agent_manager.shutdown()
    
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
        model_config: Dict[str, Any],
        stage: Optional[str] = None,
        use_shadow: Optional[bool] = None
    ) -> bool:
        """
        Start an agent mission with scoped context and model config.
        
        Args:
            task_id: Task identifier
            agent_type: Type of agent (orchestrator, planner, coder, test, review)
            context: Agent context (tiered context)
            model_config: Model configuration
            stage: Optional stage (planner, tdd_test, coder, test, etc.)
            use_shadow: Use shadow process (None = use default setting)
        """
        # Determine if shadow process should be used
        use_shadow_process = use_shadow if use_shadow is not None else self.use_shadow_processes
        
        if use_shadow_process:
            # Use Shadow Manager for isolated execution
            return await self._start_shadow_agent(task_id, agent_type, context, model_config, stage)
        else:
            # Use direct execution (existing method)
            return await self._start_direct_agent(task_id, agent_type, context, model_config, stage)
    
    async def _start_shadow_agent(
        self,
        task_id: str,
        agent_type: str,
        context: Dict[str, Any],
        model_config: Dict[str, Any],
        stage: Optional[str] = None
    ) -> bool:
        """Start agent in shadow process."""
        channel = f"shadow-{task_id}-{agent_type}"
        
        # Output callback to stream to state manager
        async def output_callback(output_channel: str, content: str):
            """Stream shadow process output to state manager."""
            self.state_manager.add_chat_message(output_channel, "assistant", content)
            await self.state_manager.save_state()
        
        try:
            process_id = await self.shadow_manager.start_shadow_agent(
                task_id=task_id,
                agent_type=agent_type,
                context=context,
                model_config=model_config,
                stage=stage,
                output_callback=output_callback
            )
            
            # Record shadow process
            self._active_agents[task_id] = {
                "agent_type": agent_type,
                "status": "active",
                "channel": channel,
                "context": context,
                "model_config": model_config,
                "stage": stage,
                "process_id": process_id,
                "shadow": True
            }
            
            # Initial message
            self.state_manager.add_chat_message(
                channel,
                "assistant",
                f"[{agent_type.upper()}] Agent started in shadow process for task {task_id}\n"
                f"Process ID: {process_id}\n"
                f"Stage: {stage or 'default'}\n"
                f"Model: {model_config.get('model', 'default')}"
            )
            
            await self.state_manager.save_state()
            return True
            
        except Exception as e:
            self.state_manager.add_chat_message(
                channel,
                "assistant",
                f"[error] Failed to start shadow agent: {str(e)}"
            )
            await self.state_manager.save_state()
            return False
    
    async def _start_direct_agent(
        self,
        task_id: str,
        agent_type: str,
        context: Dict[str, Any],
        model_config: Dict[str, Any],
        stage: Optional[str] = None
    ) -> bool:
        """Start agent with direct execution (existing method)."""
        # Create agent using agent manager
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
                f"Stage: {stage or 'default'}\n"
                f"Context tiers: {', '.join([k for k in context.keys() if k.startswith('tier_')])}\n"
                f"Model: {model_config.get('model', 'default')}"
            )
            
            # Call agent-specific methods based on stage and agent type
            agent_instance = agent.get("instance")
            if agent_instance:
                # Start agent execution in background
                asyncio.create_task(self._execute_agent_method(
                    agent_instance, agent_type, task_id, context, model_config, stage
                ))
            
            self._active_agents[task_id] = {
                "agent": agent,
                "agent_type": agent_type,
                "status": "active",
                "channel": channel,
                "context": context,
                "model_config": model_config,
                "stage": stage,
                "shadow": False
            }
            
            await self.state_manager.save_state()
        
        return success
    
    async def _execute_agent_method(
        self,
        agent_instance: Any,
        agent_type: str,
        task_id: str,
        context: Dict[str, Any],
        model_config: Dict[str, Any],
        stage: Optional[str] = None
    ):
        """Execute agent-specific method based on type and stage."""
        try:
            if agent_type == "test":
                # Test agent: call appropriate method based on stage
                if stage == "tdd_test":
                    # TDD mode: write tests first
                    async for chunk in agent_instance.write_tdd_tests(task_id, context, model_config):
                        # Save chunks to channel
                        channel = f"squad-{task_id}-test"
                        if chunk.get("type") == "chunk":
                            self.state_manager.add_chat_message(
                                channel, "assistant", chunk.get("content", "")
                            )
                        elif chunk.get("type") == "complete":
                            self.state_manager.add_chat_message(
                                channel, "assistant", chunk.get("content", "")
                            )
                            await self.state_manager.save_state()
                else:
                    # Test execution mode: run tests
                    async for chunk in agent_instance.run_tests(task_id, context, model_config):
                        # Save chunks to channel
                        channel = f"squad-{task_id}-test"
                        if chunk.get("type") == "chunk":
                            self.state_manager.add_chat_message(
                                channel, "assistant", chunk.get("content", "")
                            )
                        elif chunk.get("type") == "complete":
                            self.state_manager.add_chat_message(
                                channel, "assistant", chunk.get("content", "")
                            )
                            await self.state_manager.save_state()
            elif agent_type == "planner":
                # Planner agent: call plan method
                task_description = context.get("task_description", "Plan the task")
                async for chunk in agent_instance.plan(task_description, context, model_config):
                    channel = f"squad-{task_id}-planner"
                    if chunk.get("type") == "chunk":
                        self.state_manager.add_chat_message(
                            channel, "assistant", chunk.get("content", "")
                        )
                    elif chunk.get("type") == "complete":
                        self.state_manager.add_chat_message(
                            channel, "assistant", chunk.get("content", "")
                        )
                        await self.state_manager.save_state()
            elif agent_type == "coder":
                # Coder agent: call implement method
                task_description = context.get("task_description", "Implement the task")
                task_scope = context.get("task_scope", {})
                async for chunk in agent_instance.implement(task_description, context, task_scope, model_config):
                    channel = f"squad-{task_id}-coder"
                    if chunk.get("type") == "chunk":
                        self.state_manager.add_chat_message(
                            channel, "assistant", chunk.get("content", "")
                        )
                    elif chunk.get("type") == "complete":
                        self.state_manager.add_chat_message(
                            channel, "assistant", chunk.get("content", "")
                        )
                        await self.state_manager.save_state()
            elif agent_type == "integration_test":
                # Integration Test agent: call appropriate method based on stage
                sprint_id = context.get("sprint_id")
                if stage == "sprint_tdd_test" and sprint_id:
                    # TDD mode: write integration tests first (Sprint scope)
                    async for chunk in agent_instance.write_tdd_tests(sprint_id, context, model_config):
                        channel = f"sprint-{sprint_id}-integration_test"
                        if chunk.get("type") == "chunk":
                            self.state_manager.add_chat_message(
                                channel, "assistant", chunk.get("content", "")
                            )
                        elif chunk.get("type") == "complete":
                            self.state_manager.add_chat_message(
                                channel, "assistant", chunk.get("content", "")
                            )
                            await self.state_manager.save_state()
                else:
                    # Test execution mode: run integration tests
                    sprint_id = context.get("sprint_id")
                    if sprint_id:
                        async for chunk in agent_instance.run_integration_tests(sprint_id, task_id, context, model_config):
                            channel = f"sprint-{sprint_id}-integration_test"
                            if chunk.get("type") == "chunk":
                                self.state_manager.add_chat_message(
                                    channel, "assistant", chunk.get("content", "")
                                )
                            elif chunk.get("type") == "complete":
                                self.state_manager.add_chat_message(
                                    channel, "assistant", chunk.get("content", "")
                                )
                                await self.state_manager.save_state()
            elif agent_type == "e2e_test":
                # E2E Test agent: call appropriate method based on stage
                sprint_id = context.get("sprint_id")
                if stage == "sprint_tdd_test" and sprint_id:
                    # TDD mode: write E2E tests first (Sprint scope)
                    async for chunk in agent_instance.write_tdd_tests(sprint_id, context, model_config):
                        channel = f"sprint-{sprint_id}-e2e_test"
                        if chunk.get("type") == "chunk":
                            self.state_manager.add_chat_message(
                                channel, "assistant", chunk.get("content", "")
                            )
                        elif chunk.get("type") == "complete":
                            self.state_manager.add_chat_message(
                                channel, "assistant", chunk.get("content", "")
                            )
                            await self.state_manager.save_state()
                else:
                    # Test execution mode: run E2E tests
                    sprint_id = context.get("sprint_id")
                    task_id_param = context.get("task_id", task_id)
                    if sprint_id and task_id_param:
                        async for chunk in agent_instance.run_e2e_tests(sprint_id=sprint_id, task_id=task_id_param, context=context, model_config=model_config):
                            channel = f"sprint-{sprint_id}-e2e_test"
                            if chunk.get("type") == "chunk":
                                self.state_manager.add_chat_message(
                                    channel, "assistant", chunk.get("content", "")
                                )
                            elif chunk.get("type") == "complete":
                                self.state_manager.add_chat_message(
                                    channel, "assistant", chunk.get("content", "")
                                )
                                await self.state_manager.save_state()
                    elif task_id:
                        # Fallback to task-level E2E test (existing behavior)
                        async for chunk in agent_instance.run_e2e_tests(task_id, context, model_config):
                            channel = f"squad-{task_id}-e2e_test"
                            if chunk.get("type") == "chunk":
                                self.state_manager.add_chat_message(
                                    channel, "assistant", chunk.get("content", "")
                                )
                            elif chunk.get("type") == "complete":
                                self.state_manager.add_chat_message(
                                    channel, "assistant", chunk.get("content", "")
                                )
                                await self.state_manager.save_state()
            # Other agent types can be added here as needed
        except Exception as e:
            channel = f"squad-{task_id}-{agent_type}"
            self.state_manager.add_chat_message(
                channel, "system", f"Error executing agent: {str(e)}"
            )
            await self.state_manager.save_state()
    
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
        # Stop agent using agent manager
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