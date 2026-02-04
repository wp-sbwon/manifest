"""
Agent coordination and lifecycle management for Manifest.

Orchestrates execution of agent types (orchestrator, planner, coder, etc.)
with task boundaries and scoping. Manages agent startup, execution, and
communication; supports in-process and container-based execution (Podman).

Delegates workflows to WorkerSquadExecutor and SprintExecutor. LLM and tools are run by the configured backend (primary: OpenCode).
"""
import asyncio
from typing import Dict, Any, Optional, List
from manifest.bridge.agent_bridge import AgentBridge
from manifest.agents.context_provider import ContextProvider
from manifest.agents.task_scoper import TaskScoper
from manifest.agents.container_manager import ContainerManager
from manifest.agents.worker_squad_executor import WorkerSquadExecutor
from manifest.agents.sprint_executor import SprintExecutor
from manifest.core.config import ConfigManager
from manifest.core.state_manager import StateManager
from manifest.core.logger import get_logger
from manifest.agents.workflow_event_bus import WorkflowEventBus, WorkflowEvent, WorkflowEventType
from manifest.agents.agent_output_parser import parse_agent_output as parse_agent_output_module
from manifest.agents.workflow_definition import get_next_stage_in_order

logger = get_logger(__name__)


class AgentCoordinator:
    """Coordinates agent execution and lifecycle management.

    Central coordinator for agent operations: orchestrator and worker startup,
    workflow delegation to WorkerSquadExecutor and SprintExecutor, and
    in-process or container-based execution (Podman). LLM and tools are run by the configured backend (primary: OpenCode).

    Attributes:
        agent_bridge: Bridge for agent communication and execution.
        context_provider: Provides context data for agents.
        task_scoper: Manages task scoping and boundaries.
        config_manager: Handles configuration and API keys.
        state_manager: Manages application state persistence.
        active_agents: Dictionary tracking currently active agents.
        terminal_router: Router for terminal command execution.
        orchestrator: Orchestrator agent instance.
        agent_manager: Manager for agent lifecycle.
        container_manager: Manager for container operations (Podman/Docker API).
        use_containers: Whether containers are available and enabled.
        state_sync: Container state synchronization handler (if using containers).
        worker_squad_executor: Executor for Worker Squad workflows.
        sprint_executor: Executor for Sprint operations.
    """

    def __init__(
        self,
        agent_bridge: AgentBridge,
        context_provider: ContextProvider,
        task_scoper: TaskScoper,
        config_manager: ConfigManager,
        state_manager: StateManager
    ):
        """Initialize the agent coordinator.

        Sets up all necessary components including container management,
        state synchronization, and workflow executors. Detects if the
        container runtime (Podman/Docker API) is available and configures
        container execution accordingly.

        Args:
            agent_bridge: Bridge instance for agent communication.
            context_provider: Provider for agent context data.
            task_scoper: Scoper for managing task boundaries.
            config_manager: Manager for configuration and API keys.
            state_manager: Manager for state persistence.
        """
        self.agent_bridge = agent_bridge
        self.context_provider = context_provider
        self.task_scoper = task_scoper
        self.config_manager = config_manager
        self.state_manager = state_manager
        self.active_agents: Dict[str, Dict[str, Any]] = {}  # task_id -> agent info

        # Access to agent components from bridge
        self.terminal_router = agent_bridge.terminal_router
        self.orchestrator = agent_bridge.orchestrator
        self.agent_manager = agent_bridge.agent_manager

        # Set up container management. Container runtime (Podman) is required for worker squad.
        self.container_manager = ContainerManager(require_docker=True, auto_start=True)
        self.use_containers = self.container_manager.is_docker_available()

        # Initialize container state synchronization if using containers
        if self.use_containers:
            from manifest.agents.container_communication import ContainerStateSync
            self.state_sync = ContainerStateSync(state_manager, self.container_manager.message_bus)
        else:
            self.state_sync = None

        # Create workflow event bus for automation
        self.event_bus = WorkflowEventBus()

        # Agent-to-agent message bus for direct communication
        from manifest.agents.agent_message_bus import AgentMessageBus
        self.message_bus = AgentMessageBus()

        # Make message_bus available to agent_bridge
        if hasattr(self.agent_bridge, 'message_bus'):
            self.agent_bridge.message_bus = self.message_bus
        else:
            # Set as attribute if not already set
            self.agent_bridge.message_bus = self.message_bus

        # Worker registration (single responsibility: active_agents + task state)
        self._worker_registration = WorkerRegistration(state_manager)

        # Create workflow executors
        self.worker_squad_executor = WorkerSquadExecutor(self)
        self.sprint_executor = SprintExecutor(self)

    async def start(self) -> None:
        """Start the coordinator and initialize container communication.

        If container execution is enabled, starts the state synchronization
        service to keep state consistent between the main process and
        containerized agents.
        """
        if self.use_containers and self.state_sync:
            await self.state_sync.start()
            logger.info("Container state synchronization started.")

    async def start_orchestrator(self, mission_description: str) -> bool:
        """Start the orchestrator agent with a mission description.

        The orchestrator is the top-level agent that breaks down high-level
        missions into tasks. It receives Tier 0-1 context (policies, PRD,
        architecture) and the mission description.

        Args:
            mission_description: High-level description of what needs to be
                accomplished. The orchestrator will break this down into tasks.

        Returns:
            True if orchestrator started successfully, False otherwise.
        """
        # Get orchestrator context (Tier 0-1)
        context = self.context_provider.get_orchestrator_context()

        # Add mission description to context
        context["mission_description"] = mission_description

        # Get model config for orchestrator
        model_config = self.config_manager.get_agent_model_config("orchestrator")

        # Start via agent bridge
        success = await self.agent_bridge.start_agent_mission(
            task_id="orchestrator",
            agent_type="orchestrator",
            context=context,
            model_config=model_config
        )

        if success:
            self.active_agents["orchestrator"] = {
                "agent_type": "orchestrator",
                "status": "active",
                "channel": "squad-orchestrator-orchestrator"
            }
            # Update state
            self.state_manager.set_last_action(f"Started orchestrator: {mission_description}")
            await self._persist_state()

        return success

    async def start_worker_agent(
        self,
        task_id: str,
        agent_type: str,
        use_container: Optional[bool] = None,
        stage: Optional[str] = None,
        previous_stages: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Start a worker agent to work on a specific task.

        Worker agents (planner, coder, test, etc.) are started with task-specific
        context and scope. The agent can run either directly or in a container
        (Podman via Docker-compatible API), depending on configuration and availability.

        The agent receives context including the task description, scope boundaries,
        and results from previous stages if this is part of a multi-stage workflow.

        Args:
            task_id: Unique identifier of the task the agent will work on.
            agent_type: Type of worker agent to start. Valid values: "planner",
                "coder", "test", "debug", "approver", "self_review", etc.
            use_container: Whether to force container execution. If None, uses
                the coordinator's default (auto-detects container runtime availability).
            stage: Current stage in the workflow (e.g., "planner", "tdd_test",
                "coder", "test", "debug", "self_review", "approver"). Used to
                provide stage-specific context.
            previous_stages: Dictionary containing results from previous stages
                in the workflow. Used to provide context about what's already
                been done.

        Returns:
            True if the agent started successfully, False if the task doesn't
            exist or startup failed.
        """
        # Validate task exists
        tasks = self.state_manager.get_task_checklist()
        task = next((t for t in tasks if t.get("id") == task_id), None)
        if not task:
            return False

        # Get stage-specific context if stage is provided
        if stage and hasattr(self.context_provider, 'get_stage_specific_context'):
            context = self.context_provider.get_stage_specific_context(
                task_id, agent_type, stage, previous_stages or {}
            )
        else:
            # Fallback to standard worker context
            context = self.context_provider.get_worker_context(task_id, agent_type)

        # Validate scope
        task_scope = context.get("task_scope", {})
        if not task_scope.get("components") and not task_scope.get("allowed_files"):
            # No scope defined - warn but continue
            logger.warning(f"Task {task_id} has no defined scope")

        # Get model config for agent type (needed for context size validation)
        model_config = self.config_manager.get_agent_model_config(agent_type)

        # Validate task granularity (with context for size validation)
        granularity_validation = self.task_scoper.validate_task_granularity(
            task_id, context=context, model_config=model_config
        )
        if not granularity_validation.get("valid"):
            errors = granularity_validation.get("errors", [])
            for error in errors:
                logger.error(f"Task {task_id} granularity error: {error}")
            # Continue anyway, but log the error

        if granularity_validation.get("warnings"):
            for warning in granularity_validation.get("warnings", []):
                logger.warning(f"Task {task_id} granularity warning: {warning}")

        # Validate context size (from context or granularity validation)
        context_validation = context.get("context_size_validation")
        if not context_validation:
            context_validation = granularity_validation.get("context_size_validation")

        if context_validation and not context_validation.get("valid"):
            excess = context_validation.get("excess_tokens", 0)
            logger.error(
                f"Task {task_id} context size exceeds model limit by {excess} tokens. "
                f"Suggestions: {', '.join(context_validation.get('suggestions', []))}"
            )
            # Continue anyway, but the agent may fail at runtime

        # Get model config for agent type (already retrieved above for context validation)

        # Determine execution mode
        should_use_container = use_container if use_container is not None else self.use_containers

        if should_use_container and self.container_manager.is_docker_available():
            # Start agent in container (Podman/Docker API)
            container_id = await self.container_manager.start_agent_container(
                task_id=task_id,
                agent_type=agent_type,
                environment={
                    "TASK_ID": task_id,
                    "AGENT_TYPE": agent_type,
                    **{f"CONTEXT_{k.upper()}": str(v) for k, v in context.items()}
                }
            )

            if container_id:
                channel = f"squad-{task_id}-{agent_type}"
                self._register_worker_agent(
                    task_id=task_id,
                    agent_type=agent_type,
                    channel=channel,
                    task_scope=task_scope,
                    task=task,
                    tasks=tasks,
                    execution_mode="container",
                    container_id=container_id,
                    last_action_msg=f"Started {agent_type} agent in container for task {task_id}",
                )
                await self._persist_state()
                return True
            else:
                # Fall back to in-process execution if container fails
                logger.warning("Failed to start container, falling back to in-process execution")

        # Start via agent bridge (in-process)
        success = await self.agent_bridge.start_agent_mission(
            task_id=task_id,
            agent_type=agent_type,
            context=context,
            model_config=model_config,
            stage=stage
        )

        if success:
            channel = f"squad-{task_id}-{agent_type}"
            self._register_worker_agent(
                task_id=task_id,
                agent_type=agent_type,
                channel=channel,
                task_scope=task_scope,
                task=task,
                tasks=tasks,
                execution_mode="direct",
                last_action_msg=f"Started {agent_type} agent for task {task_id}",
            )
            await self._persist_state()

        return success

    async def start_worker_agent_and_wait(
        self,
        task_id: str,
        agent_type: str,
        use_container: Optional[bool] = None,
        stage: Optional[str] = None,
        previous_stages: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """Start a worker agent and wait for completion.

        This method starts an agent and waits for it to complete, then returns
        the parsed results. This is used by Worker Squad to ensure each stage
        completes before moving to the next.

        Args:
            task_id: Unique identifier of the task the agent will work on.
            agent_type: Type of worker agent to start.
            use_container: Whether to force container execution.
            stage: Current stage in the workflow.
            previous_stages: Dictionary containing results from previous stages.
            timeout: Optional timeout in seconds. If None, waits indefinitely.

        Returns:
            Dictionary containing:
            - success: Boolean indicating if agent completed successfully
            - output: Full agent output text
            - parsed_data: Parsed/structured data from output (if available)
            - status: Agent completion status
            - error: Optional error message if failed

        Completion detection order (canonical, checked in this sequence):
        1. task_id not in active_agents (agent was removed from coordinator's active list)
        2. bridge._active_agents[task_id].completed or status in [completed, stopped, failed]
           (PRIMARY CHECK: bridge sets completed=True when it receives a type=complete chunk)
        3. executor.active_sessions[session_id].status == "completed" (if executor available)
        4. get_agent_status() returning completed/stopped/failed (fallback status check)
        5. Channel history completion markers (text-based indicators like "[complete]", "[done]")
        6. completed_at timestamp in bridge._active_agents (after 10s of no new messages)

        Note: The bridge marks agents as completed immediately when receiving a "complete" chunk
        (see agent_bridge.py:_handle_agent_chunk). This is the most reliable completion signal.
        """
        import asyncio

        # Start the agent
        success = await self.start_worker_agent(
            task_id, agent_type, use_container, stage, previous_stages
        )

        if not success:
            return {
                "success": False,
                "output": "",
                "parsed_data": {},
                "status": "failed_to_start",
                "error": "Failed to start agent"
            }

        # Get channel for this agent
        channel = f"squad-{task_id}-{agent_type}"

        # Wait for agent completion by monitoring channel
        wait_iteration, timed_out = await self._wait_for_agent_completion(task_id, channel, timeout)
        if timed_out:
            return {
                "success": False,
                "output": "",
                "parsed_data": {},
                "status": "timeout",
                "error": f"Agent execution timed out after {timeout} seconds"
            }

        # Get final output from channel
        history = self.state_manager.get_chat_history(channel)
        output = "\n".join([
            msg.get("content", "")
            for msg in history
            if msg.get("role") == "assistant"
        ])

        # Try to get tool_execution_summary from task state (if available)
        # This is more reliable than parsing from output text
        tool_execution_summary = None
        tasks = self.state_manager.get_task_checklist()
        task = next((t for t in tasks if t.get("id") == task_id), None)
        if task and "tool_execution" in task:
            tool_execution = task.get("tool_execution", {})
            tool_execution_summary = tool_execution.get("last_summary")

        # Parse output based on agent type and stage
        parsed_data = self._parse_agent_output(agent_type, stage, output, tool_execution_summary)

        # Determine final status - check multiple sources for reliability
        max_wait_iterations = 300  # Must match _wait_for_agent_completion
        if wait_iteration >= max_wait_iterations:
            status = "timeout"
            success = False
            logger.warning(f"Agent {task_id} timed out after {timeout or 'default'} seconds")
        elif task_id not in self.active_agents:
            # Agent was removed from active_agents (completed)
            status = "completed"
            success = True
            logger.debug(f"Agent {task_id} completed (removed from active_agents)")
        elif self.agent_bridge and task_id in self.agent_bridge._active_agents:
            # Check bridge's active_agents status (most reliable)
            agent_info = self.agent_bridge._active_agents[task_id]
            bridge_status = agent_info.get("status", "unknown")
            bridge_completed = agent_info.get("completed", False)

            if bridge_completed or bridge_status in ["completed", "stopped"]:
                status = "completed"
                success = bridge_status != "failed"
                logger.debug(f"Agent {task_id} completed (bridge status: {bridge_status}, completed: {bridge_completed})")
            elif bridge_status == "failed":
                status = "failed"
                success = False
                logger.debug(f"Agent {task_id} failed (bridge status: failed)")
            else:
                # Fallback to agent_status check
                agent_status = await self.get_agent_status(task_id)
                status = agent_status.get("status", "unknown")
                success = status == "completed"
                logger.debug(f"Agent {task_id} status from get_agent_status: {status}")
        else:
            # Fallback: check via get_agent_status
            agent_status = await self.get_agent_status(task_id)
            status = agent_status.get("status", "unknown")
            success = status == "completed"
            logger.debug(f"Agent {task_id} status from get_agent_status (fallback): {status}")

        # Publish agent completion event
        if success:
            await self.event_bus.publish(WorkflowEvent(
                event_type=WorkflowEventType.AGENT_COMPLETED,
                task_id=task_id,
                stage=stage,
                agent_type=agent_type,
                data={
                    "parsed_data": parsed_data,
                    "output_length": len(output)
                }
            ))
            await self.event_bus.publish(WorkflowEvent(
                event_type=WorkflowEventType.STAGE_COMPLETED,
                task_id=task_id,
                stage=stage,
                agent_type=agent_type,
                data={"result": parsed_data}
            ))
            # Trigger next stage event
            await self.event_bus.publish(WorkflowEvent(
                event_type=WorkflowEventType.TRIGGER_NEXT_STAGE,
                task_id=task_id,
                stage=stage,
                agent_type=agent_type,
                data={"completed_stage": stage, "next_stage": self._get_next_stage(stage)}
            ))
        else:
            await self.event_bus.publish(WorkflowEvent(
                event_type=WorkflowEventType.AGENT_FAILED,
                task_id=task_id,
                stage=stage,
                agent_type=agent_type,
                data={"error": f"Agent status: {status}"}
            ))
            await self.event_bus.publish(WorkflowEvent(
                event_type=WorkflowEventType.STAGE_FAILED,
                task_id=task_id,
                stage=stage,
                agent_type=agent_type,
                data={"error": f"Agent status: {status}"}
            ))

        # Remove from active_agents so observed status (active_task_ids) is correct
        self.active_agents.pop(task_id, None)
        await self._persist_state()

        return {
            "success": success,
            "output": output,
            "parsed_data": parsed_data,
            "status": status,
            "error": None if success else f"Agent status: {status}"
        }

    def _get_next_stage(self, current_stage: Optional[str]) -> Optional[str]:
        """Get the next stage in the workflow sequence. Uses canonical order from workflow_definition."""
        return get_next_stage_in_order(current_stage)

    async def _persist_state(self) -> None:
        """Sync active_task_ids from active_agents (for observed status in View) and save state."""
        task_ids = [tid for tid in self.active_agents if tid != "orchestrator"]
        self.state_manager.set_active_task_ids(task_ids)
        await self.state_manager.save_state()

    def _persist_state_sync(self) -> None:
        """Sync active_task_ids and save state synchronously (e.g. from sync stop_agent path)."""
        task_ids = [tid for tid in self.active_agents if tid != "orchestrator"]
        self.state_manager.set_active_task_ids(task_ids)
        self.state_manager.save_state_sync()

    def _register_worker_agent(
        self,
        task_id: str,
        agent_type: str,
        channel: str,
        task_scope: Dict[str, Any],
        task: Dict[str, Any],
        tasks: List[Dict[str, Any]],
        execution_mode: str = "direct",
        container_id: Optional[str] = None,
        last_action_msg: Optional[str] = None,
    ) -> None:
        """Register a worker agent in active_agents and update task state. Delegates to WorkerRegistration."""
        self._worker_registration.register(
            active_agents=self.active_agents,
            task_id=task_id,
            agent_type=agent_type,
            channel=channel,
            task_scope=task_scope,
            task=task,
            tasks=tasks,
            execution_mode=execution_mode,
            container_id=container_id,
            last_action_msg=last_action_msg,
        )

    async def _wait_for_agent_completion(
        self,
        task_id: str,
        channel: str,
        timeout: Optional[float],
    ) -> tuple:
        """Wait for agent completion by polling status and channel.

        Returns:
            Tuple of (wait_iteration: int, timed_out: bool). If timed_out is True,
            caller should return a timeout result immediately.
        """
        start_time = asyncio.get_event_loop().time()
        last_message_count = 0
        max_wait_iterations = 300  # 5 minutes max (1 second per iteration)
        wait_iteration = 0

        while wait_iteration < max_wait_iterations:
            if timeout and (asyncio.get_event_loop().time() - start_time) > timeout:
                return (wait_iteration, True)

            if task_id not in self.active_agents:
                logger.debug(f"Agent {task_id} completed (removed from active_agents)")
                break

            if self.agent_bridge and task_id in self.agent_bridge._active_agents:
                agent_info = self.agent_bridge._active_agents[task_id]
                if agent_info.get("completed") or agent_info.get("status") in ["completed", "stopped", "failed"]:
                    logger.debug(f"Agent {task_id} completed (bridge status: {agent_info.get('status')})")
                    break

            if self.agent_bridge and hasattr(self.agent_bridge, 'executor'):
                executor = self.agent_bridge.executor
                if executor and hasattr(executor, 'active_sessions') and task_id in executor.active_sessions:
                    if executor.active_sessions[task_id].get("status") == "completed":
                        logger.debug(f"Agent {task_id} completed (executor session status: completed)")
                        break

            agent_status = await self.get_agent_status(task_id)
            if agent_status.get("status") in ["completed", "stopped", "failed"]:
                logger.debug(f"Agent {task_id} completed (agent_status: {agent_status.get('status')})")
                break

            history = self.state_manager.get_chat_history(channel)
            current_message_count = len(history)

            if current_message_count > last_message_count and history:
                recent_messages = history[-min(5, len(history)):]
                for msg in reversed(recent_messages):
                    content = msg.get("content", "")
                    if any(indicator in content.lower() for indicator in [
                        "[complete]", "[finished]", "[done]", "task completed",
                        "agent completed", "execution completed"
                    ]):
                        logger.debug(f"Agent {task_id} completed (completion indicator found in message)")
                        break
                    if msg.get("completed") or msg.get("type") == "complete":
                        logger.debug(f"Agent {task_id} completed (completion metadata in message)")
                        break
                else:
                    pass

            last_message_count = current_message_count

            if wait_iteration > 10 and current_message_count == last_message_count:
                if self.agent_bridge and task_id in self.agent_bridge._active_agents:
                    agent_info = self.agent_bridge._active_agents[task_id]
                    if agent_info.get("completed_at"):
                        logger.debug(f"Agent {task_id} completed (completed_at timestamp found)")
                        break

            await asyncio.sleep(1.0)
            wait_iteration += 1

        return (wait_iteration, False)

    def _parse_agent_output(
        self,
        agent_type: str,
        stage: Optional[str],
        output: str,
        tool_execution_summary: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Parse agent output to extract structured data. Delegates to agent_output_parser."""
        return parse_agent_output_module(
            agent_type=agent_type,
            stage=stage,
            output=output,
            tool_execution_summary=tool_execution_summary,
        )

    async def stop_agent(self, task_id: str) -> bool:
        """Stop an agent that's currently working on a task.

        Stops the agent and cleans up resources. For containerized agents,
        stops the container. For in-process execution, stops the agent
        process through the agent bridge.

        Args:
            task_id: ID of the task whose agent should be stopped.

        Returns:
            True if the agent was found and stopped successfully, False
            if the agent wasn't active or stopping failed.
        """
        if task_id not in self.active_agents:
            return False

        agent_info = self.active_agents[task_id]
        execution_mode = agent_info.get("execution_mode", "direct")

        success = False

        if execution_mode == "container":
            # Stop the container
            success = await self.container_manager.stop_agent_container(task_id)
        else:
            # Stop via agent bridge
            success = await self.agent_bridge.stop_agent(task_id)

        if success:
            # Remove from active agents first so _persist_state writes correct active_task_ids
            del self.active_agents[task_id]
            # Update task status
            tasks = self.state_manager.get_task_checklist()
            task = next((t for t in tasks if t.get("id") == task_id), None)
            if task and "agent" in task:
                task["agent"]["status"] = "stopped"
                self.state_manager.set_task_checklist(tasks)
            await self._persist_state()

        return success

    async def get_agent_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of agent working on task."""
        if task_id not in self.active_agents:
            return {"status": "not_active", "data": {}}

        agent_info = self.active_agents[task_id]
        execution_mode = agent_info.get("execution_mode", "direct")

        if execution_mode == "container":
            # Get container status
            container_status = await self.container_manager.get_container_status(task_id)
            if container_status:
                return {
                    "status": container_status.get("status", "unknown"),
                    "data": {
                        "execution_mode": "container",
                        "container_id": container_status.get("container_id"),
                        "cpu_usage": container_status.get("cpu_usage"),
                        "memory_usage": container_status.get("memory_usage"),
                        "memory_limit": container_status.get("memory_limit"),
                        **container_status.get("metadata", {})
                    }
                }
            else:
                return {"status": "not_active", "data": {}}
        else:
            # Get status via agent bridge
            status = await self.agent_bridge.get_agent_status(task_id)
            if status:
                status["data"]["execution_mode"] = "direct"
            return status

    def get_active_agents(self) -> Dict[str, Dict[str, Any]]:
        """Get all active agents."""
        return self.active_agents.copy()

    def get_agent_channel(self, task_id: str) -> Optional[str]:
        """Get channel name for agent working on task."""
        agent_info = self.active_agents.get(task_id)
        return agent_info.get("channel") if agent_info else None

    async def handle_blueprint_conflict(self, conflict_issue: Dict[str, Any], task_id: str) -> bool:
        """Handle a blueprint drift conflict by requesting planner review.

        When code drifts from the blueprint, this method creates a conflict
        record and requests that the planner agent review the issue. The
        conflict information is stored with the task for tracking.

        Args:
            conflict_issue: Dictionary describing the conflict, including
                component ID, conflict type, severity, and details.
            task_id: ID of the task where the conflict was detected.

        Returns:
            True if conflict was recorded successfully. Note that actual
            planner review integration is pending.
        """
        from manifest.audit.blueprint.blueprint_synchronizer import BlueprintSynchronizer

        synchronizer = BlueprintSynchronizer()

        # Create request to resend task to worker squad with conflict context
        resend_request = synchronizer.resend_to_worker_squad(task_id, conflict_issue)

        # Request planner to review the conflict
        planner_request = synchronizer.request_planner_review(conflict_issue)

        # Store conflict information with the task
        tasks = self.state_manager.get_task_checklist()
        for task in tasks:
            if task.get("id") == task_id:
                task["conflict"] = {
                    "issue": conflict_issue,
                    "status": "planner_review",
                    "resend_request": resend_request
                }
                self.state_manager.set_task_checklist(tasks)
                await self._persist_state()
                break

        # Send to planner via agent bridge
        if self.agent_bridge:
            planner_result = await self.agent_bridge.send_to_planner(planner_request, task_id)
            if planner_result.get("success"):
                logger.info(
                    f"Planner review started for conflict in task {task_id}. "
                    f"Channel: {planner_result.get('channel')}"
                )
                # Store planner task ID in conflict record
                for task in tasks:
                    if task.get("id") == task_id and "conflict" in task:
                        task["conflict"]["planner_task_id"] = planner_result.get("planner_task_id")
                        task["conflict"]["planner_channel"] = planner_result.get("channel")
                        self.state_manager.set_task_checklist(tasks)
                        await self._persist_state()
                        break
            else:
                logger.error(
                    f"Failed to send conflict to planner for task {task_id}: "
                    f"{planner_result.get('error', 'Unknown error')}"
                )
        else:
            logger.warning("Agent bridge not available, cannot send to planner")

        return True

    async def start_sprint(self, sprint_id: str, max_parallel: int = 10) -> Dict[str, Any]:
        """Start a sprint by executing all its tasks in parallel.

        Delegates to SprintExecutor which handles the actual sprint execution,
        including test writing and task parallelization.

        Args:
            sprint_id: ID of the sprint to start.
            max_parallel: Maximum number of tasks to run simultaneously.
                Defaults to 10.

        Returns:
            Dictionary with execution results including started tasks,
            failed tasks, and parallel groups.
        """
        return await self.sprint_executor.start_sprint(sprint_id, max_parallel)

    async def _start_task_worker_squad(self, task_id: str) -> bool:
        """Start the Worker Squad workflow for a task in the background.

        This is an internal helper method that launches the Worker Squad
        executor as a background task, making it non-blocking.

        Args:
            task_id: ID of the task to start Worker Squad for.

        Returns:
            Always returns True (execution happens in background).
        """
        # Launch Worker Squad workflow asynchronously (non-blocking)
        asyncio.create_task(self.worker_squad_executor.execute(task_id))
        return True

    async def execute_worker_squad(self, task_id: str) -> Dict[str, Any]:
        """Execute the complete Worker Squad workflow for a task.

        Delegates to WorkerSquadExecutor which handles the multi-stage
        workflow (planner, TDD test, coder, test, debug, self review, approver).

        Args:
            task_id: ID of the task to execute Worker Squad for.

        Returns:
            Dictionary with execution results including success status and
            results from each stage.
        """
        return await self.worker_squad_executor.execute(task_id)

    async def review_project_requirements(self, task_id: str) -> Dict[str, Any]:
        """Review project-level requirements compliance after task completion.

        This is a higher-level review that happens after Worker Squad completes.
        It runs E2E tests and performs a project review to ensure the work
        meets overall project requirements, not just the specific task.

        The workflow:
        1. Run E2E tests to verify end-to-end functionality
        2. Run project review agent to check requirements compliance

        Args:
            task_id: ID of the task that completed Worker Squad and needs
                project-level review.

        Returns:
            Dictionary containing:
            - requirements_met: Boolean indicating if requirements are satisfied
            - findings: List of issues or observations
            - recommendations: List of suggested improvements
            - e2e_test: Results from E2E test execution
            - project_review: Results from project review agent
        """
        results = {}

        # 1. Run E2E tests first
        e2e_success = await self.start_worker_agent(task_id, "e2e_test")
        e2e_result = {
            "status": "completed" if e2e_success else "failed",
            "test_results": {}
        }
        results["e2e_test"] = e2e_result

        # Save E2E test results
        tasks = self.state_manager.get_task_checklist()
        task = next((t for t in tasks if t.get("id") == task_id), None)
        if task:
            task["e2e_test"] = e2e_result
            self.state_manager.set_task_checklist(tasks)
            await self._persist_state()

        # If E2E tests failed, still proceed to Project Review but note the failure
        if not e2e_success:
            results["e2e_test"]["status"] = "failed"
            results["e2e_test"]["error"] = "E2E test agent failed to start"

        # 2. Project Review (even if E2E tests failed, we still review)
        project_review_success = await self.start_worker_agent(task_id, "project_review")

        if project_review_success:
            # Get review results (would be from agent output)
            project_review_result = {
                "requirements_met": True,
                "findings": [],
                "recommendations": []
            }
            results["project_review"] = project_review_result

            # If E2E tests failed, add to findings
            if e2e_result.get("status") == "failed":
                project_review_result["findings"].append("E2E tests failed or did not run")
                project_review_result["requirements_met"] = False

            return {
                "requirements_met": project_review_result["requirements_met"],
                "findings": project_review_result["findings"],
                "recommendations": project_review_result["recommendations"],
                **results
            }

        return {
            "requirements_met": False,
            "findings": ["Project review agent failed to start"],
            "recommendations": [],
            **results
        }
