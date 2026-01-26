"""
Agent bridge for direct integration with the agent system.

This module provides the AgentBridge class which serves as the main integration
point between the UI/coordination layer and the actual agent execution system.
It manages the orchestrator, agent manager, terminal router, and handles
starting agent missions.

The bridge coordinates multiple components including terminal execution,
resource monitoring, watchdog supervision, and shadow process management for
isolated agent execution.
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional, Callable, Awaitable
from manifest.core.state_manager import StateManager
from manifest.core.config import ConfigManager
from manifest.core.logger import get_logger
from manifest.runtime.router.terminal_router import TerminalRouter
from manifest.runtime.agent.core.orchestrator import Orchestrator
from manifest.runtime.agent.core.manager import AgentManager
from manifest.runtime.agent.core.executor import AgentExecutor

logger = get_logger(__name__)


class AgentBridge:
    """Direct integration bridge to agent system functionality.

    This class provides the main interface for starting agents, executing
    missions, and managing agent lifecycle. It coordinates multiple subsystems:
    orchestrator, agent manager, terminal router, resource monitoring, and
    watchdog supervision.

    The bridge can operate agents directly or in shadow processes for isolation.
    It also manages prompt hooks for intercepting and modifying prompts before
    they reach the LLM.

    Attributes:
        state_manager: Manages application state persistence.
        config_manager: Manages configuration and API keys.
        working_dir: Working directory for agent operations.
        resource_monitor: Monitors Docker container resources.
        watchdog: Monitors and supervises agent operations.
        terminal_router: Routes terminal commands for execution.
        executor: Executes agents via LLM API calls.
        orchestrator: Top-level orchestrator agent.
        agent_manager: Manages agent lifecycle and creation.
        shadow_manager: Manages isolated shadow process execution.
        use_shadow_processes: Whether to use shadow processes (configurable).
        is_connected: Whether the bridge is initialized and ready.
        _active_agents: Dictionary tracking active agent sessions.
    """

    def __init__(
        self,
        state_manager: StateManager,
        config_manager: Optional[ConfigManager] = None,
        working_dir: Optional[Path] = None,
        channel_manager: Optional[Any] = None,
        approval_manager: Optional[Any] = None
    ):
        """Initialize the agent bridge.

        Sets up all subsystems including terminal router, orchestrator, agent
        manager, resource monitoring, and watchdog. Configures prompt hooks
        and shadow process management.

        Args:
            state_manager: State manager for persistence.
            config_manager: Optional config manager. If not provided, creates one.
            working_dir: Optional working directory. Defaults to current directory.
            channel_manager: Optional channel manager for UI updates.
            approval_manager: Optional permission approval manager for "ask" permissions.
        """
        self.state_manager = state_manager
        self.config_manager = config_manager
        self.working_dir = working_dir or Path.cwd()
        self.channel_manager = channel_manager
        self.approval_manager = approval_manager

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

        # Agent executor for LLM calls (created via factory)
        # Factory selects backend based on config (direct, opencode)
        from manifest.runtime.agent.core.executor_factory import ExecutorFactory
        self.executor = ExecutorFactory.create_executor(
            config_manager or ConfigManager(),
            state_manager
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
            logger.error(f"Error initializing agent system: {e}", exc_info=True)
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
        # Use batched saving for streaming chunks to reduce I/O
        class BatchSaver:
            """Helper class for batched state saving."""
            def __init__(self, state_manager):
                import time
                self.state_manager = state_manager
                self.last_save_time = time.time()
                self.message_count = 0
                self.time = time

            async def save_if_needed(self):
                """Save state if batch threshold is reached."""
                self.message_count += 1
                current_time = self.time.time()

                # Save immediately if:
                # 1. First message
                # 2. More than 10 messages accumulated
                # 3. More than 5 seconds since last save
                should_save = (
                    self.message_count == 1 or
                    self.message_count >= 10 or
                    (current_time - self.last_save_time) >= 5.0
                )

                if should_save:
                    await self.state_manager.save_state()
                    self.last_save_time = current_time
                    self.message_count = 0

        batch_saver = BatchSaver(self.state_manager)

        async def output_callback(output_channel: str, content: str):
            """Stream shadow process output to state manager.

            Uses batched saving to reduce I/O operations. Saves immediately
            only for important messages or after a batch threshold.
            """
            self.state_manager.add_chat_message(output_channel, "assistant", content)
            await batch_saver.save_if_needed()

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

            # Save immediately for important state change (agent start)
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
        # Create ToolExecutor with approval_manager and auditor for permission requests and logging
        from manifest.runtime.tools.tool_executor import ToolExecutor
        from manifest.runtime.tools.file_manager import FileManager
        from manifest.runtime.permissions.permission_manager import PermissionManager
        from manifest.runtime.tools.tool_execution_auditor import ToolExecutionAuditor

        # Create PermissionManager for this agent type
        permission_manager = PermissionManager(
            config_manager=self.config_manager or ConfigManager(),
            agent_type=agent_type
        )

        # Create FileManager with permission checking
        file_manager = FileManager(
            working_dir=self.working_dir,
            permission_manager=permission_manager,
            agent_type=agent_type
        )

        # Update TerminalRouter with permission manager
        if self.terminal_router:
            self.terminal_router.permission_manager = permission_manager
            self.terminal_router.agent_type = agent_type

        # Create ToolExecutionAuditor for logging
        auditor = ToolExecutionAuditor(manifest_dir=self.state_manager.manifest_dir)

        # Create ToolExecutor with approval_manager and auditor
        tool_executor = ToolExecutor(
            terminal_router=self.terminal_router,
            file_manager=file_manager,
            approval_manager=self.approval_manager,
            auditor=auditor,
            agent_type=agent_type,
            task_id=task_id,
            agent_id=task_id  # Use task_id as agent_id for now
        )

        # Create agent using agent manager
        agent = await self.agent_manager.create_agent(
            agent_type=agent_type,
            context=context,
            model_config=model_config,
            task_id=task_id,
            terminal_router=self.terminal_router,
            tool_executor=tool_executor
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
                "shadow": False,
                "completed": False  # Track completion status
            }

            # Register agent with message bus if available
            if hasattr(self, 'message_bus') and self.message_bus:
                message_bus = self.message_bus
                agent_instance = agent.get("instance")

                # Create message handler for this agent
                async def message_handler(message):
                    """Handle incoming messages for this agent."""
                    if agent_instance and hasattr(agent_instance, 'handle_message'):
                        try:
                            await agent_instance.handle_message(message)
                        except Exception as e:
                            logger.error(f"Error handling message in agent {task_id}: {e}", exc_info=True)

                message_bus.register_agent(
                    agent_id=task_id,
                    agent_type=agent_type,
                    message_handler=message_handler
                )
                logger.debug(f"Agent {task_id} ({agent_type}) registered with message bus")

            await self.state_manager.save_state()

        return success

    async def _handle_agent_chunk(
        self,
        chunk: Dict[str, Any],
        channel: str
    ) -> None:
        """Handle a single agent output chunk and display it.

        Common handler for all agent output chunks including text, tool_use,
        tool_result, and errors. Delegates to channel_manager for state and UI updates
        to avoid duplicate state saving.

        Args:
            chunk: Chunk dictionary with 'type' and content.
            channel: Channel name for this agent's output.
        """
        if not self.channel_manager:
            # Fallback: if no channel_manager, save to state directly
            chunk_type = chunk.get("type")
            if chunk_type == "chunk":
                content = chunk.get("content", "")
                self.state_manager.add_chat_message(channel, "assistant", content)
            elif chunk_type == "complete":
                content = chunk.get("content", "")
                self.state_manager.add_chat_message(channel, "assistant", content)
                await self.state_manager.save_state()
            elif chunk_type == "error":
                error_msg = chunk.get("content", "Unknown error")
                self.state_manager.add_chat_message(channel, "system", f"[red]Error: {error_msg}[/]")
            return

        chunk_type = chunk.get("type")

        if chunk_type == "chunk":
            content = chunk.get("content", "")
            # Delegate to channel_manager (handles state + UI)
            # Don't save immediately for streaming chunks to reduce I/O
            await self.channel_manager.handle_agent_output(channel, content, "assistant", save_immediately=False)
        elif chunk_type == "complete":
            content = chunk.get("content", "")
            # Delegate to channel_manager (handles state + UI + save_state)
            # Save immediately for complete messages to ensure persistence
            await self.channel_manager.handle_agent_output(channel, content, "assistant", save_immediately=True)

            # Mark agent as completed immediately when complete chunk is received
            # Extract task_id from channel (format: "squad-{task_id}-{agent_type}" or "sprint-{sprint_id}-{agent_type}")
            task_id = None
            if channel.startswith("squad-"):
                parts = channel.split("-")
                if len(parts) >= 2:
                    task_id = parts[1]
            elif channel.startswith("sprint-"):
                # For sprint channels, we might not have task_id in channel
                # Try to find task_id from active_agents
                for tid, agent_info in self._active_agents.items():
                    if agent_info.get("channel") == channel:
                        task_id = tid
                        break

            if task_id and task_id in self._active_agents:
                # Mark as completed immediately when complete chunk is received
                self._active_agents[task_id]["completed"] = True
                self._active_agents[task_id]["status"] = "completed"
                # Add completion timestamp
                import time
                self._active_agents[task_id]["completed_at"] = time.time()
                logger.debug(f"Agent {task_id} marked as completed (complete chunk received)")

            # Extract tool execution summary if available (for next stage)
            tool_execution_summary = chunk.get("tool_execution_summary")
            if tool_execution_summary:
                # Store tool execution summary in task state for next stage
                # This will be used by test/debug agents to know what was modified
                if not task_id:
                    task_id = channel.split("-")[1] if "-" in channel and len(channel.split("-")) >= 2 else None
                if task_id:
                    tasks = self.state_manager.get_task_checklist()
                    for task in tasks:
                        if task.get("id") == task_id:
                            if "tool_execution" not in task:
                                task["tool_execution"] = {}
                            task["tool_execution"]["last_summary"] = tool_execution_summary
                            task["tool_execution"]["modified_files"] = tool_execution_summary.get("modified_files", [])
                            task["tool_execution"]["executed_commands"] = tool_execution_summary.get("executed_commands", [])
                            break
        elif chunk_type == "tool_use" or chunk_type == "tool_use_start":
            # Display tool call
            tool_call = chunk.get("tool_call", {})
            tool_name = tool_call.get("name", "unknown")
            tool_id = tool_call.get("id", "unknown")
            tool_input = tool_call.get("input", {})

            tool_display = f"[cyan]🔧 Tool: {tool_name}[/] (id: {tool_id[:8]}...)\n"
            if tool_input:
                tool_display += f"  Input: {json.dumps(tool_input, indent=2)[:200]}...\n"

            # Delegate to channel_manager (handles state + UI)
            await self.channel_manager.handle_agent_output(channel, tool_display, "system")
        elif chunk_type == "tool_result":
            # Display tool result
            tool_name = chunk.get("tool_name", "unknown")
            tool_call_id = chunk.get("tool_call_id", "unknown")
            result = chunk.get("result")
            error = chunk.get("error")

            # Check for permission approval request
            if chunk.get("permission_required"):
                approval_request_id = chunk.get("approval_request_id")
                permission_details = chunk.get("permission_details", {})

                result_display = (
                    f"[yellow]⏸ Permission approval required for {tool_name}[/]\n"
                    f"  Resource: {permission_details.get('resource', 'unknown')}\n"
                    f"  Request ID: {approval_request_id[:8] if approval_request_id else 'unknown'}...\n"
                    f"  [dim]Waiting for user approval...[/]\n"
                )

                # Notify UI about pending permission request
                if self.channel_manager and hasattr(self.channel_manager.app, 'check_pending_permissions'):
                    # Trigger permission check in UI
                    asyncio.create_task(self.channel_manager.app.check_pending_permissions())
            elif error:
                result_display = f"[red]❌ Tool {tool_name} failed:[/] {error}\n"
            else:
                result_str = json.dumps(result, indent=2) if result else "null"
                result_display = f"[green]✅ Tool {tool_name} completed[/] (id: {tool_call_id[:8]}...)\n"
                result_display += f"  Result: {result_str[:300]}...\n" if len(result_str) > 300 else f"  Result: {result_str}\n"

            # Delegate to channel_manager (handles state + UI)
            await self.channel_manager.handle_agent_output(channel, result_display, "system")
        elif chunk_type == "error":
            error_msg = chunk.get("content", "Unknown error")
            error_display = f"[red]Error: {error_msg}[/]"
            # Delegate to channel_manager (handles state + UI)
            await self.channel_manager.handle_agent_output(channel, error_display, "system")

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
                        channel = f"squad-{task_id}-test"
                        await self._handle_agent_chunk(chunk, channel)
                else:
                    # Test execution mode: run tests
                    async for chunk in agent_instance.run_tests(task_id, context, model_config):
                        channel = f"squad-{task_id}-test"
                        await self._handle_agent_chunk(chunk, channel)
            elif agent_type == "planner":
                # Planner agent: call plan method
                # Check if this is a conflict review
                if stage == "conflict_review" or context.get("conflict_review"):
                    # Conflict review mode - use task description from context
                    conflict_review = context.get("conflict_review", {})
                    task_description = context.get("task_description", "Review blueprint conflict")
                    # Create a special task description for conflict review
                    conflict_issue = conflict_review.get("conflict_issue", {})
                    review_request = conflict_review.get("review_request", {})

                    # Build conflict review task description
                    conflict_desc = f"""
BLUEPRINT CONFLICT REVIEW

Conflict Type: {conflict_issue.get('type', 'unknown')}
Component: {conflict_issue.get('component_id', 'unknown')}
Severity: {conflict_issue.get('severity', 'unknown')}
File: {conflict_issue.get('file_path', 'unknown')}

Details: {conflict_issue.get('message', 'No details')}

Review Question: {review_request.get('question', 'Is this change necessary or a violation?')}
"""
                    task_description = conflict_desc

                async for chunk in agent_instance.plan(task_description, context, model_config):
                    channel = f"squad-{task_id}-planner"
                    await self._handle_agent_chunk(chunk, channel)

                    # Special handling for planner complete (conflict review parsing)
                    if chunk.get("type") == "complete":
                        content = chunk.get("content", "")
                        if stage == "conflict_review" or context.get("conflict_review"):
                            await self._parse_planner_conflict_review(
                                task_id, content, context
                            )
            elif agent_type == "coder":
                # Coder agent: call implement method
                task_description = context.get("task_description", "Implement the task")
                task_scope = context.get("task_scope", {})
                async for chunk in agent_instance.implement(task_description, context, task_scope, model_config):
                    channel = f"squad-{task_id}-coder"
                    await self._handle_agent_chunk(chunk, channel)
            elif agent_type == "integration_test":
                # Integration Test agent: call appropriate method based on stage
                sprint_id = context.get("sprint_id")
                if stage == "sprint_tdd_test" and sprint_id:
                    # TDD mode: write integration tests first (Sprint scope)
                    async for chunk in agent_instance.write_tdd_tests(sprint_id, context, model_config):
                        channel = f"sprint-{sprint_id}-integration_test"
                        await self._handle_agent_chunk(chunk, channel)
                else:
                    # Test execution mode: run integration tests
                    sprint_id = context.get("sprint_id")
                    if sprint_id:
                        async for chunk in agent_instance.run_integration_tests(sprint_id, task_id, context, model_config):
                            channel = f"sprint-{sprint_id}-integration_test"
                            await self._handle_agent_chunk(chunk, channel)
            elif agent_type == "e2e_test":
                # E2E Test agent: call appropriate method based on stage
                sprint_id = context.get("sprint_id")
                if stage == "sprint_tdd_test" and sprint_id:
                    # TDD mode: write E2E tests first (Sprint scope)
                    async for chunk in agent_instance.write_tdd_tests(sprint_id, context, model_config):
                        channel = f"sprint-{sprint_id}-e2e_test"
                        await self._handle_agent_chunk(chunk, channel)
                else:
                    # Test execution mode: run E2E tests
                    sprint_id = context.get("sprint_id")
                    task_id_param = context.get("task_id", task_id)
                    if sprint_id and task_id_param:
                        async for chunk in agent_instance.run_e2e_tests(sprint_id=sprint_id, task_id=task_id_param, context=context, model_config=model_config):
                            channel = f"sprint-{sprint_id}-e2e_test"
                            await self._handle_agent_chunk(chunk, channel)
                    elif task_id:
                        # Fallback to task-level E2E test (existing behavior)
                        async for chunk in agent_instance.run_e2e_tests(task_id, context, model_config):
                            channel = f"squad-{task_id}-e2e_test"
                            await self._handle_agent_chunk(chunk, channel)

            # Mark agent as completed after execution finishes
            if task_id in self._active_agents:
                self._active_agents[task_id]["completed"] = True
                self._active_agents[task_id]["status"] = "completed"
        except Exception as e:
            channel = f"squad-{task_id}-{agent_type}"
            self.state_manager.add_chat_message(
                channel, "system", f"Error executing agent: {str(e)}"
            )
            # Mark agent as failed
            if task_id in self._active_agents:
                self._active_agents[task_id]["completed"] = True
                self._active_agents[task_id]["status"] = "failed"

            # Unregister agent from message bus
            if hasattr(self, 'message_bus') and self.message_bus:
                self.message_bus.unregister_agent(task_id)
                logger.debug(f"Agent {task_id} unregistered from message bus")

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
                # Unregister from message bus before removing
                if hasattr(self, 'message_bus') and self.message_bus:
                    self.message_bus.unregister_agent(task_id)
                    logger.debug(f"Agent {task_id} unregistered from message bus")
                del self._active_agents[task_id]

            await self.state_manager.save_state()

        return success

    async def send_to_planner(
        self,
        planner_request: Dict[str, Any],
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a blueprint conflict review request to the planner agent.

        When blueprint conflicts are detected, this method starts a planner
        agent to review the conflict and determine if the code change is
        necessary or an architectural violation.

        Args:
            planner_request: Dictionary containing:
                - action: "planner_review"
                - conflict_issue: Conflict details
                - request: Review request with question and options
            task_id: Optional task ID where the conflict was detected.
                If not provided, generates a temporary ID.

        Returns:
            Dictionary with:
                - success: Boolean indicating if planner was started
                - planner_task_id: ID of the planner review task
                - channel: Channel name for planner output
        """
        if not self.is_connected:
            logger.error("Agent bridge not connected, cannot send to planner")
            return {
                "success": False,
                "error": "Agent bridge not connected"
            }

        # Generate task ID if not provided
        review_task_id = task_id or f"planner-review-{planner_request.get('conflict_issue', {}).get('component_id', 'unknown')}"

        # Extract conflict information
        conflict_issue = planner_request.get("conflict_issue", {})
        review_request = planner_request.get("request", {})

        # Create conflict review task description
        conflict_type = conflict_issue.get("type", "unknown")
        component_id = conflict_issue.get("component_id", "unknown")
        severity = conflict_issue.get("severity", "unknown")
        message = conflict_issue.get("message", "")
        file_path = conflict_issue.get("file_path", "")

        task_description = f"""
BLUEPRINT CONFLICT REVIEW REQUEST

Conflict Type: {conflict_type}
Component ID: {component_id}
Severity: {severity}
File: {file_path}

Conflict Details:
{message}

Review Question: {review_request.get('question', 'Is this code change necessary or an architectural violation?')}

Please review this conflict and determine:
1. Is this change necessary for the implementation?
2. Does this change violate the architectural blueprint?
3. Should the blueprint be updated to reflect this change, or should the code be reverted?

Respond with:
- DECISION: necessary | violation
- REASONING: [your analysis]
- RECOMMENDATION: [what should be done]
"""

        # Get context for planner (Tier 0-1, plus conflict details)
        from manifest.agents.context_provider import ContextProvider
        context_provider = ContextProvider()
        context = context_provider.get_orchestrator_context()

        # Add conflict information to context
        context["conflict_review"] = {
            "conflict_issue": conflict_issue,
            "review_request": review_request,
            "task_id": review_task_id
        }

        # Get model config for planner
        model_config = self.config_manager.get_agent_model_config("planner")

        # Start planner agent for conflict review
        success = await self.start_agent_mission(
            task_id=review_task_id,
            agent_type="planner",
            context=context,
            model_config=model_config,
            stage="conflict_review"
        )

        if success:
            channel = f"squad-{review_task_id}-planner"
            logger.info(f"Planner review started for conflict in task {task_id or 'unknown'}")

            return {
                "success": True,
                "planner_task_id": review_task_id,
                "channel": channel
            }
        else:
            logger.error(f"Failed to start planner review for task {task_id or 'unknown'}")
            return {
                "success": False,
                "error": "Failed to start planner agent"
            }
