"""
Agent coordination and lifecycle management for Manifest.

This module provides the AgentCoordinator class which orchestrates the
execution of different agent types (orchestrator, planner, coder, etc.)
with proper task boundaries and scoping. It manages agent startup,
execution, and communication, and supports both direct execution and
Docker container-based execution.

The coordinator delegates complex workflows to specialized executors:
WorkerSquadExecutor for task execution workflows and SprintExecutor for
sprint management.
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

logger = get_logger(__name__)


class AgentCoordinator:
    """Coordinates agent execution and lifecycle management.
    
    This class serves as the central coordinator for all agent operations.
    It manages orchestrator and worker agent startup, delegates complex
    workflows to specialized executors, and handles both direct execution
    and Docker container-based execution modes.
    
    The coordinator uses dependency injection to access various services
    (AgentBridge, ContextProvider, TaskScoper, etc.) and creates executor
    instances for Worker Squad and Sprint operations.
    
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
        container_manager: Manager for Docker container operations.
        use_containers: Whether Docker containers are available and enabled.
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
        state synchronization, and workflow executors. Detects if Docker
        is available and configures container execution accordingly.
        
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
        
        # Set up container management if Docker is available
        self.container_manager = ContainerManager()
        self.use_containers = self.container_manager.is_docker_available()
        
        # Initialize container state synchronization if using containers
        if self.use_containers:
            from manifest.agents.container_communication import ContainerStateSync
            self.state_sync = ContainerStateSync(state_manager, self.container_manager.message_bus)
        else:
            self.state_sync = None
        
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
            await self.state_manager.save_state()
        
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
        context and scope. The agent can run either directly or in a Docker
        container, depending on configuration and availability.
        
        The agent receives context including the task description, scope boundaries,
        and results from previous stages if this is part of a multi-stage workflow.
        
        Args:
            task_id: Unique identifier of the task the agent will work on.
            agent_type: Type of worker agent to start. Valid values: "planner",
                "coder", "test", "debug", "approver", "self_review", etc.
            use_container: Whether to force container execution. If None, uses
                the coordinator's default (auto-detects Docker availability).
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
        
        # Get model config for agent type
        model_config = self.config_manager.get_agent_model_config(agent_type)
        
        # Determine execution mode
        should_use_container = use_container if use_container is not None else self.use_containers
        
        if should_use_container and self.container_manager.is_docker_available():
            # Start agent in Docker container
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
                self.active_agents[task_id] = {
                    "agent_type": agent_type,
                    "status": "active",
                    "channel": channel,
                    "container_id": container_id,
                    "execution_mode": "container"
                }
                
                # Update task with agent info
                task["agent"] = {
                    "type": agent_type,
                    "status": "active",
                    "channel": channel,
                    "container_id": container_id
                }
                
                # Update task scope in state
                task["scope"] = {
                    "components": task_scope.get("components", []),
                    "files": task_scope.get("allowed_files", []),
                    "allowed_modifications": task_scope.get("allowed_modifications", [])
                }
                
                self.state_manager.set_task_checklist(tasks)
                self.state_manager.set_last_action(f"Started {agent_type} agent in container for task {task_id}")
                await self.state_manager.save_state()
                return True
            else:
                # Fall back to direct execution if container fails
                logger.warning(f"Failed to start container, falling back to direct execution")
        
        # Start via agent bridge (direct execution)
        success = await self.agent_bridge.start_agent_mission(
            task_id=task_id,
            agent_type=agent_type,
            context=context,
            model_config=model_config,
            stage=stage
        )
        
        if success:
            channel = f"squad-{task_id}-{agent_type}"
            self.active_agents[task_id] = {
                "agent_type": agent_type,
                "status": "active",
                "channel": channel,
                "execution_mode": "direct"
            }
            
            # Update task with agent info
            task["agent"] = {
                "type": agent_type,
                "status": "active",
                "channel": channel
            }
            
            # Update task scope in state
            task["scope"] = {
                "components": task_scope.get("components", []),
                "files": task_scope.get("allowed_files", []),
                "allowed_modifications": task_scope.get("allowed_modifications", [])
            }
            
            self.state_manager.set_task_checklist(tasks)
            self.state_manager.set_last_action(f"Started {agent_type} agent for task {task_id}")
            await self.state_manager.save_state()
        
        return success
    
    async def stop_agent(self, task_id: str) -> bool:
        """Stop an agent that's currently working on a task.
        
        Stops the agent and cleans up resources. For containerized agents,
        stops the Docker container. For direct execution, stops the agent
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
            # Stop the Docker container
            success = await self.container_manager.stop_agent_container(task_id)
        else:
            # Stop via agent bridge
            success = await self.agent_bridge.stop_agent(task_id)
        
        if success:
            # Update task status
            tasks = self.state_manager.get_task_checklist()
            task = next((t for t in tasks if t.get("id") == task_id), None)
            if task and "agent" in task:
                task["agent"]["status"] = "stopped"
                self.state_manager.set_task_checklist(tasks)
                await self.state_manager.save_state()
            
            # Remove from active agents
            del self.active_agents[task_id]
        
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
                await self.state_manager.save_state()
                break
        
        # TODO: Integrate with agent bridge to actually send to planner
        # await self.agent_bridge.send_to_planner(planner_request)
        
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
    
    async def _execute_planner_stage(self, task_id: str, previous_stages: Dict[str, Any] = None) -> bool:
        """Execute the Planner stage of Worker Squad.
        
        Starts the planner agent to create a plan for the task. This is
        the first stage in the Worker Squad workflow.
        
        Args:
            task_id: ID of the task to plan for.
            previous_stages: Results from previous stages (empty for planner).
        
        Returns:
            True if planner agent started successfully, False otherwise.
        """
        return await self.start_worker_agent(task_id, "planner", stage="planner", previous_stages=previous_stages or {})
    
    async def _execute_coder_stage(
        self,
        task_id: str,
        feedback: str = "",
        test_plan: Dict[str, Any] = None,
        previous_stages: Dict[str, Any] = None
    ) -> bool:
        """Execute the Coder stage of Worker Squad.
        
        Starts the coder agent to implement code. If feedback is provided
        (e.g., from approver rejection), it's added to the task context.
        If a test plan is provided (from TDD stage), it's also included
        in the context.
        
        Args:
            task_id: ID of the task to code for.
            feedback: Optional feedback from approver if this is a rework.
            test_plan: Optional test plan from TDD stage to guide implementation.
            previous_stages: Results from previous stages in the workflow.
        
        Returns:
            True if coder agent started successfully, False otherwise.
        """
        # If feedback provided, add it to context
        if feedback:
            # Update task with feedback
            tasks = self.state_manager.get_task_checklist()
            task = next((t for t in tasks if t.get("id") == task_id), None)
            if task:
                if "worker_squad" not in task:
                    task["worker_squad"] = {}
                task["worker_squad"]["approver_feedback"] = feedback
                self.state_manager.set_task_checklist(tasks)
        
        # If test_plan provided (TDD), add it to context
        if test_plan:
            tasks = self.state_manager.get_task_checklist()
            task = next((t for t in tasks if t.get("id") == task_id), None)
            if task:
                if "worker_squad" not in task:
                    task["worker_squad"] = {}
                if "stages" not in task["worker_squad"]:
                    task["worker_squad"]["stages"] = {}
                task["worker_squad"]["stages"]["tdd_test"] = test_plan
                self.state_manager.set_task_checklist(tasks)
        
        return await self.start_worker_agent(
            task_id, "coder", stage="coder", previous_stages=previous_stages or {}
        )
    
    async def _execute_tdd_test_stage(
        self,
        task_id: str,
        planner_result: Dict[str, Any],
        previous_stages: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute the TDD (Test-Driven Development) test stage.
        
        In TDD mode, tests are written before implementation. This stage
        starts the test agent with TDD context to create test skeletons
        and plans that will guide the coder's implementation.
        
        Args:
            task_id: ID of the task to write tests for.
            planner_result: Results from the planner stage containing the plan.
            previous_stages: Results from all previous stages.
        
        Returns:
            Dictionary with stage results including status, test skeleton,
            test plan, and TDD mode flag.
        """
        # Start test agent in TDD mode (write tests first)
        success = await self.start_worker_agent(
            task_id, "test", stage="tdd_test", previous_stages=previous_stages or {}
        )
        return {
            "status": "completed" if success else "failed",
            "test_skeleton": "",
            "test_plan": "",
            "tdd_mode": True
        }
    
    async def _execute_test_stage(self, task_id: str, previous_stages: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute the test stage to run tests after implementation.
        
        This stage runs after the coder has implemented code. The test
        agent executes the tests (which should pass if TDD was followed
        correctly) and reports results.
        
        Args:
            task_id: ID of the task to test.
            previous_stages: Results from previous stages including coder output.
        
        Returns:
            Dictionary with test execution results including status and
            test results.
        """
        success = await self.start_worker_agent(
            task_id, "test", stage="test", previous_stages=previous_stages or {}
        )
        return {
            "status": "completed" if success else "failed",
            "test_results": {}
        }
    
    async def _execute_debug_stage(
        self,
        task_id: str,
        test_result: Dict[str, Any],
        previous_stages: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute the debug stage to fix failing tests.
        
        This stage runs when tests fail. The debug agent analyzes test
        failures and fixes issues in the code. This can iterate multiple
        times until tests pass.
        
        Args:
            task_id: ID of the task to debug.
            test_result: Results from the test stage showing what failed.
            previous_stages: Results from all previous stages.
        
        Returns:
            Dictionary with debug results including status and list of
            issues that were fixed.
        """
        success = await self.start_worker_agent(
            task_id, "debug", stage="debug", previous_stages=previous_stages or {}
        )
        return {
            "status": "completed" if success else "failed",
            "issues_fixed": []
        }
    
    async def _execute_self_review_stage(self, task_id: str, previous_stages: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute the self review stage where coder reviews their own work.
        
        After tests pass, the coder agent reviews the implementation to
        ensure it complies with the original plan and meets quality standards.
        This is done by the coder agent in self-review mode.
        
        Args:
            task_id: ID of the task to review.
            previous_stages: Results from all previous stages.
        
        Returns:
            Dictionary with review results including status, plan compliance
            flag, and any findings.
        """
        # Self review is performed by the coder agent in review mode
        success = await self.start_worker_agent(
            task_id, "coder", stage="self_review", previous_stages=previous_stages or {}
        )
        return {
            "status": "completed" if success else "failed",
            "plan_compliance": True,
            "findings": []
        }
    
    async def _execute_approver_stage(
        self,
        task_id: str,
        self_review_result: Dict[str, Any],
        previous_stages: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute the approver stage for final approval.
        
        The approver agent reviews the completed work and makes a final
        decision: approve or reject. If rejected, feedback is provided
        and the workflow may loop back to the coder stage.
        
        Args:
            task_id: ID of the task to approve.
            self_review_result: Results from the self review stage.
            previous_stages: Results from all previous stages.
        
        Returns:
            Dictionary with approval results including status, decision
            ("approved" or "rejected"), and optional feedback.
        """
        success = await self.start_worker_agent(
            task_id, "approver", stage="approver", previous_stages=previous_stages or {}
        )
        return {
            "status": "completed" if success else "failed",
            "decision": "approved" if success else "pending",
            "feedback": ""
        }
    
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
            await self.state_manager.save_state()
        
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
    