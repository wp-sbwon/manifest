"""
Worker Squad workflow execution for tasks.

This module implements the complete Worker Squad workflow, which is a
Test-Driven Development (TDD) process for executing tasks. The workflow
includes multiple stages: planning, test writing, coding, testing, debugging,
self review, and approval.

The WorkerSquadExecutor was separated from AgentCoordinator to improve
code organization and follows the single responsibility principle.

The executor can operate in two modes:
1. Sequential mode: Explicitly calls each stage in order (current default)
2. Event-driven mode: Subscribes to workflow events and automatically
   triggers next stages when agents complete (future enhancement)
"""
import asyncio
from typing import Dict, Any, Optional, List
from manifest.core.logger import get_logger
from manifest.agents.workflow_event_bus import WorkflowEvent, WorkflowEventType
from manifest.agents.failure_recovery import FailureRecoveryManager

logger = get_logger(__name__)


class WorkerSquadExecutor:
    """Executes the complete Worker Squad workflow for tasks.

    The Worker Squad is a multi-agent workflow that follows Test-Driven
    Development principles. It coordinates multiple agent types through
    a structured sequence of stages, with iteration and feedback loops
    built in.

    Attributes:
        coordinator: Reference to AgentCoordinator for starting agents.
        state_manager: Reference to StateManager for persisting stage results.
        timeouts: Dictionary mapping stage names to timeouts in seconds.
    """

    def __init__(self, coordinator: Any):
        """Initialize the Worker Squad executor.

        Args:
            coordinator: AgentCoordinator instance that provides access to
                agent startup methods and other services.
        """
        self.coordinator = coordinator
        self.state_manager = coordinator.state_manager
        self.recovery_manager = FailureRecoveryManager(coordinator)
        self.event_bus = getattr(coordinator, 'event_bus', None)

        # Default timeouts for each stage (in seconds)
        self.timeouts = {
            "planner": 300.0,      # 5 minutes
            "tdd_test": 300.0,     # 5 minutes
            "coder": 900.0,        # 15 minutes
            "test": 300.0,         # 5 minutes
            "debug": 600.0,        # 10 minutes
            "self_review": 300.0,  # 5 minutes
            "approver": 300.0      # 5 minutes
        }

        # Track active workflows for event-driven mode
        self._active_workflows: Dict[str, Dict[str, Any]] = {}  # task_id -> workflow state
        self._event_subscriptions: Dict[str, Any] = {}  # task_id -> subscription callbacks
        self._use_event_driven = False  # Can be enabled per workflow
        self._enable_parallel_execution = False  # Enable parallel execution of independent stages

    def set_timeout(self, stage: str, timeout: float):
        """Set timeout for a specific stage."""
        self.timeouts[stage] = timeout

    def enable_event_driven(self, enabled: bool = True):
        """Enable or disable event-driven workflow execution.

        When enabled, the executor subscribes to workflow events and
        automatically triggers next stages when agents complete. This
        allows for more flexible and responsive workflow execution.

        Args:
            enabled: Whether to enable event-driven mode.
        """
        self._use_event_driven = enabled
        if enabled and self.event_bus:
            logger.info("Event-driven workflow execution enabled")
        else:
            logger.info("Event-driven workflow execution disabled")

    def enable_parallel_execution(self, enabled: bool = True):
        """Enable or disable parallel execution of independent stages.

        When enabled, stages that don't depend on each other can run
        in parallel, improving workflow throughput.

        Args:
            enabled: Whether to enable parallel execution.
        """
        self._enable_parallel_execution = enabled
        if enabled:
            logger.info("Parallel stage execution enabled")
        else:
            logger.info("Parallel stage execution disabled")

    def _get_stage_dependencies(self) -> Dict[str, List[str]]:
        """Get dependency graph for workflow stages.

        Returns:
            Dictionary mapping stage names to lists of prerequisite stages.
        """
        return {
            "planner": [],  # No dependencies
            "tdd_test": ["planner"],  # Depends on planner
            "coder": ["tdd_test"],  # Depends on tdd_test
            "test": ["coder"],  # Depends on coder
            "debug": ["test"],  # Depends on test (only if test failed)
            "self_review": ["test"],  # Depends on test (only if test passed)
            "approver": ["self_review"]  # Depends on self_review
        }

    def _get_ready_stages(
        self,
        completed_stages: set,
        failed_stages: set,
        workflow_state: Dict[str, Any]
    ) -> List[str]:
        """Get list of stages that are ready to execute (dependencies met).

        Args:
            completed_stages: Set of completed stage names.
            failed_stages: Set of failed stage names.
            workflow_state: Current workflow state.

        Returns:
            List of stage names ready to execute.
        """
        dependencies = self._get_stage_dependencies()
        ready = []

        for stage, deps in dependencies.items():
            # Skip if already completed or failed
            if stage in completed_stages or stage in failed_stages:
                continue

            # Check if all dependencies are met
            if all(dep in completed_stages for dep in deps):
                # Additional conditional checks
                if stage == "self_review":
                    # Only ready if test passed
                    test_result = workflow_state.get("stages", {}).get("test", {})
                    if test_result.get("success", False):
                        ready.append(stage)
                elif stage == "debug":
                    # Only ready if test failed
                    test_result = workflow_state.get("stages", {}).get("test", {})
                    if not test_result.get("success", True):
                        ready.append(stage)
                else:
                    ready.append(stage)

        return ready

    async def _setup_event_subscriptions(self, task_id: str):
        """Set up event subscriptions for a workflow.

        Args:
            task_id: Task ID for the workflow.
        """
        if not self.event_bus:
            return

        # Store workflow state
        self._active_workflows[task_id] = {
            "stages": {},
            "current_stage": None,
            "completed_stages": set(),
            "failed_stages": set(),
            "status": "running"
        }

        # Subscribe to stage completion events
        async def on_stage_completed(event: WorkflowEvent):
            if event.task_id != task_id:
                return

            completed_stage = event.stage
            workflow_state = self._active_workflows.get(task_id)
            if not workflow_state:
                return

            # Mark stage as completed
            workflow_state["completed_stages"].add(completed_stage)
            workflow_state["stages"][completed_stage] = event.data.get("result", {})

            # Check if we should trigger next stage
            await self._handle_stage_completion(task_id, completed_stage, event.data)

        # Subscribe to stage failure events
        async def on_stage_failed(event: WorkflowEvent):
            if event.task_id != task_id:
                return

            failed_stage = event.stage
            workflow_state = self._active_workflows.get(task_id)
            if not workflow_state:
                return

            # Mark stage as failed
            workflow_state["failed_stages"].add(failed_stage)

            # Handle failure (recovery or workflow termination)
            await self._handle_stage_failure(task_id, failed_stage, event.data)

        # Store subscriptions for cleanup
        self._event_subscriptions[task_id] = {
            "stage_completed": on_stage_completed,
            "stage_failed": on_stage_failed
        }

        # Register subscriptions
        self.event_bus.subscribe(WorkflowEventType.STAGE_COMPLETED, on_stage_completed)
        self.event_bus.subscribe(WorkflowEventType.STAGE_FAILED, on_stage_failed)

        logger.debug(f"Event subscriptions set up for task {task_id}")

    async def _cleanup_event_subscriptions(self, task_id: str):
        """Clean up event subscriptions for a workflow.

        Args:
            task_id: Task ID for the workflow.
        """
        if not self.event_bus:
            return

        subscriptions = self._event_subscriptions.pop(task_id, {})
        for event_type, callback in [
            (WorkflowEventType.STAGE_COMPLETED, subscriptions.get("stage_completed")),
            (WorkflowEventType.STAGE_FAILED, subscriptions.get("stage_failed"))
        ]:
            if callback:
                self.event_bus.unsubscribe(event_type, callback)

        # Clean up workflow state
        self._active_workflows.pop(task_id, None)
        logger.debug(f"Event subscriptions cleaned up for task {task_id}")

    async def _handle_stage_completion(self, task_id: str, completed_stage: str, stage_data: Dict[str, Any]):
        """Handle stage completion and trigger next stage(s) if appropriate.

        Supports both sequential and parallel execution modes.

        Args:
            task_id: Task ID.
            completed_stage: Name of the completed stage.
            stage_data: Data from the completed stage.
        """
        workflow_state = self._active_workflows.get(task_id)
        if not workflow_state:
            return

        # Update workflow state with completed stage data
        workflow_state["stages"][completed_stage] = stage_data

        if self._enable_parallel_execution:
            # Parallel execution mode: Find all ready stages
            completed_stages = workflow_state.get("completed_stages", set())
            completed_stages.add(completed_stage)
            workflow_state["completed_stages"] = completed_stages

            ready_stages = self._get_ready_stages(
                completed_stages,
                workflow_state.get("failed_stages", set()),
                workflow_state
            )

            if ready_stages:
                logger.info(
                    f"Triggering {len(ready_stages)} ready stage(s) in parallel for task {task_id}: {ready_stages}"
                )
                # Execute all ready stages in parallel
                tasks = [
                    self._execute_stage_async(task_id, stage, workflow_state)
                    for stage in ready_stages
                ]
                # Don't await here - let them run in parallel
                for task in tasks:
                    asyncio.create_task(task)
            else:
                # No ready stages, check if workflow is complete
                if self._is_workflow_complete(workflow_state):
                    await self._finalize_workflow(task_id, workflow_state)
        else:
            # Sequential execution mode: Determine single next stage
            next_stage = self._determine_next_stage(completed_stage, workflow_state, stage_data)

            if next_stage:
                logger.info(f"Auto-triggering next stage {next_stage} for task {task_id} after {completed_stage}")
                # Trigger next stage asynchronously
                asyncio.create_task(self._execute_stage_async(task_id, next_stage, workflow_state))
            else:
                # Check if workflow is complete
                if self._is_workflow_complete(workflow_state):
                    await self._finalize_workflow(task_id, workflow_state)

    async def _handle_stage_failure(self, task_id: str, failed_stage: str, failure_data: Dict[str, Any]):
        """Handle stage failure and decide on recovery or termination.

        Args:
            task_id: Task ID.
            failed_stage: Name of the failed stage.
            failure_data: Failure information.
        """
        workflow_state = self._active_workflows.get(task_id)
        if not workflow_state:
            return

        # Attempt recovery for failed stage
        error = failure_data.get("error", "Unknown error")
        failure_result = {
            "success": False,
            "error": error,
            "output": failure_data.get("output", "")
        }

        recovery_result = await self.recovery_manager.attempt_recovery(
            task_id=task_id,
            stage=failed_stage,
            agent_type=failed_stage,  # Stage name usually matches agent type
            failure_result=failure_result,
            previous_stages=workflow_state.get("stages", {})
        )

        if recovery_result.get("recovered"):
            # Recovery succeeded, mark stage as completed
            workflow_state["completed_stages"].add(failed_stage)
            workflow_state["stages"][failed_stage] = recovery_result["result"]
            # Continue workflow
            await self._handle_stage_completion(task_id, failed_stage, recovery_result["result"])
        else:
            # Recovery failed, check if workflow should terminate
            if self._should_terminate_workflow(failed_stage):
                workflow_state["status"] = "failed"
                if self.event_bus:
                    await self.event_bus.publish(WorkflowEvent(
                        event_type=WorkflowEventType.WORKFLOW_FAILED,
                        task_id=task_id,
                        stage=failed_stage,
                        data={"error": error, "recovery_failed": True}
                    ))
                await self._cleanup_event_subscriptions(task_id)

    def _determine_next_stage(
        self,
        completed_stage: str,
        workflow_state: Dict[str, Any],
        stage_data: Dict[str, Any]
    ) -> Optional[str]:
        """Determine the next stage to execute based on workflow logic and conditions.

        This method implements conditional execution logic:
        - Test stage: Routes to debug if failed, self_review if passed
        - Debug stage: Loops back to test (up to max iterations)
        - Approver stage: Loops back to coder if rejected
        - Supports parallel execution of independent stages

        Args:
            completed_stage: Name of the completed stage.
            workflow_state: Current workflow state.
            stage_data: Data from the completed stage.

        Returns:
            Name of next stage to execute, or None if workflow is complete.
        """
        # Standard workflow sequence
        stage_sequence = {
            "planner": "tdd_test",
            "tdd_test": "coder",
            "coder": "test",
            "test": None,  # Conditional: debug if failed, self_review if passed
            "debug": "test",  # Loop back to test
            "self_review": "approver",
            "approver": None  # Workflow complete
        }

        next_stage = stage_sequence.get(completed_stage)

        # Conditional execution logic

        # 1. Test stage: Check if tests passed
        if completed_stage == "test":
            success = stage_data.get("success", False)
            parsed_data = stage_data.get("parsed_data", {})
            tests_passed = parsed_data.get("tests_passed", 0)
            tests_failed = parsed_data.get("tests_failed", 0)

            if success and tests_failed == 0:
                # All tests passed, proceed to self review
                next_stage = "self_review"
            elif not success or tests_failed > 0:
                # Tests failed, check if we should debug
                debug_count = workflow_state.get("debug_iterations", 0)
                max_debug_iterations = 5

                # Check if errors are recoverable
                errors = parsed_data.get("errors", [])
                recoverable = self._are_errors_recoverable(errors)

                if debug_count < max_debug_iterations and recoverable:
                    next_stage = "debug"
                    workflow_state["debug_iterations"] = debug_count + 1
                    logger.info(
                        f"Test stage failed for task {workflow_state.get('task_id', 'unknown')}, "
                        f"triggering debug (iteration {debug_count + 1}/{max_debug_iterations})"
                    )
                else:
                    # Max iterations reached or errors not recoverable
                    if debug_count >= max_debug_iterations:
                        logger.warning(f"Max debug iterations reached for task {workflow_state.get('task_id', 'unknown')}")
                    else:
                        logger.warning(f"Errors not recoverable for task {workflow_state.get('task_id', 'unknown')}")
                    return None  # Workflow failed

        # 2. Debug stage: Always loop back to test
        if completed_stage == "debug":
            # Debug completed, re-run tests
            next_stage = "test"
            logger.info(f"Debug completed, re-running tests for task {workflow_state.get('task_id', 'unknown')}")

        # 3. Approver stage: Check decision
        if completed_stage == "approver":
            decision = stage_data.get("decision", "pending")
            parsed_data = stage_data.get("parsed_data", {})
            decision_from_parsed = parsed_data.get("decision", decision)

            # Normalize decision value
            decision_lower = str(decision_from_parsed).lower()
            if "approve" in decision_lower or "accept" in decision_lower:
                # Approved, workflow complete
                next_stage = None
            elif "reject" in decision_lower or "deny" in decision_lower:
                # Rejected, loop back to coder with feedback
                feedback = parsed_data.get("feedback") or stage_data.get("feedback", "")
                workflow_state["approver_feedback"] = feedback
                workflow_state["approver_rejections"] = workflow_state.get("approver_rejections", 0) + 1

                # Check max rejection count
                max_rejections = 3
                if workflow_state["approver_rejections"] > max_rejections:
                    logger.warning(f"Max approver rejections reached for task {workflow_state.get('task_id', 'unknown')}")
                    return None  # Workflow failed

                next_stage = "coder"
                logger.info(
                    f"Approver rejected, looping back to coder with feedback "
                    f"(rejection {workflow_state['approver_rejections']}/{max_rejections})"
                )
            else:
                # Pending or unknown, wait or fail
                logger.warning(f"Approver decision is pending/unknown for task {workflow_state.get('task_id', 'unknown')}")
                next_stage = None

        # 4. Self review stage: Check if plan compliance issues found
        if completed_stage == "self_review":
            parsed_data = stage_data.get("parsed_data", {})
            plan_compliant = parsed_data.get("plan_compliant", True)
            findings = parsed_data.get("findings", [])

            if not plan_compliant and findings:
                # Non-compliant, might need to go back to coder
                # For now, proceed to approver (approver can reject if needed)
                logger.info(f"Self review found plan compliance issues: {len(findings)} findings")
            # Proceed to approver (next_stage already set)

        return next_stage

    def _are_errors_recoverable(self, errors: list) -> bool:
        """Check if errors are recoverable (can be fixed by debug agent).

        Args:
            errors: List of error dictionaries or strings.

        Returns:
            True if errors appear recoverable.
        """
        if not errors:
            return True  # No errors, considered recoverable

        # Check for non-recoverable error patterns
        non_recoverable_patterns = [
            "syntax error",
            "import error",
            "module not found",
            "circular import",
            "indentation error"
        ]

        for error in errors:
            error_str = str(error).lower() if isinstance(error, dict) else str(error).lower()
            if isinstance(error, dict):
                error_str = error.get("error", "").lower()

            for pattern in non_recoverable_patterns:
                if pattern in error_str:
                    return False  # Non-recoverable error found

        return True  # Errors appear recoverable

    def _is_workflow_complete(self, workflow_state: Dict[str, Any]) -> bool:
        """Check if workflow is complete.

        Args:
            workflow_state: Current workflow state.

        Returns:
            True if workflow is complete.
        """
        # Required stages for workflow completion
        required_stages = {"planner", "tdd_test", "coder", "test", "self_review", "approver"}
        completed = workflow_state.get("completed_stages", set())
        stages = workflow_state.get("stages", {})

        # Check if all required stages are completed
        all_completed = required_stages.issubset(completed)

        # Check if approver approved (if approver stage exists)
        if "approver" in stages:
            approver_result = stages["approver"]
            approver_data = approver_result.get("parsed_data", {})
            decision = approver_data.get("decision", "pending")
            decision_lower = str(decision).lower()
            if "reject" in decision_lower or "deny" in decision_lower:
                # Rejected, workflow not complete yet (will loop back to coder)
                return False

        return all_completed and workflow_state.get("status") != "failed"

    def _should_terminate_workflow(self, failed_stage: str) -> bool:
        """Determine if workflow should terminate on stage failure.

        Args:
            failed_stage: Name of the failed stage.

        Returns:
            True if workflow should terminate.
        """
        # Critical stages that cause workflow termination on failure
        critical_stages = {"planner", "tdd_test"}
        return failed_stage in critical_stages

    async def _execute_stage_async(self, task_id: str, stage: str, workflow_state: Dict[str, Any]):
        """Execute a stage asynchronously (for event-driven mode).

        Args:
            task_id: Task ID.
            stage: Stage name to execute.
            workflow_state: Current workflow state.
        """
        try:
            workflow_state["current_stage"] = stage

            # Get previous stages data
            previous_stages = workflow_state.get("stages", {})

            # Execute stage based on type
            if stage == "planner":
                result = await self._execute_planner_stage(task_id, previous_stages)
            elif stage == "tdd_test":
                planner_result = previous_stages.get("planner", {})
                result = await self._execute_tdd_test_stage(task_id, planner_result, previous_stages)
            elif stage == "coder":
                # Check for approver feedback
                feedback = workflow_state.get("approver_feedback", "")
                tdd_test_result = previous_stages.get("tdd_test", {})
                test_plan = {"test_plan": tdd_test_result.get("test_plan"), "test_skeleton": tdd_test_result.get("test_skeleton")} if tdd_test_result else None
                result = await self._execute_coder_stage(task_id, feedback=feedback, test_plan=test_plan, previous_stages=previous_stages)
            elif stage == "test":
                result = await self._execute_test_stage(task_id, previous_stages)
            elif stage == "debug":
                test_result = previous_stages.get("test", {})
                result = await self._execute_debug_stage(task_id, test_result, previous_stages)
            elif stage == "self_review":
                result = await self._execute_self_review_stage(task_id, previous_stages)
            elif stage == "approver":
                self_review_result = previous_stages.get("self_review", {})
                result = await self._execute_approver_stage(task_id, self_review_result, previous_stages)
            else:
                logger.error(f"Unknown stage: {stage}")
                return

            # Save stage result
            workflow_state["stages"][stage] = result
            await self.state_manager.save_worker_squad_stage_async(task_id, stage, result)

        except Exception as e:
            logger.error(f"Error executing stage {stage} for task {task_id}: {e}", exc_info=True)
            if self.event_bus:
                await self.event_bus.publish(WorkflowEvent(
                    event_type=WorkflowEventType.STAGE_FAILED,
                    task_id=task_id,
                    stage=stage,
                    data={"error": str(e)}
                ))

    async def _finalize_workflow(self, task_id: str, workflow_state: Dict[str, Any]):
        """Finalize a completed workflow.

        Args:
            task_id: Task ID.
            workflow_state: Final workflow state.
        """
        workflow_state["status"] = "completed"
        stages = workflow_state.get("stages", {})

        if self.event_bus:
            await self.event_bus.publish(WorkflowEvent(
                event_type=WorkflowEventType.WORKFLOW_COMPLETED,
                task_id=task_id,
                data={"stages": stages}
            ))

        await self._cleanup_event_subscriptions(task_id)
        logger.info(f"Workflow completed for task {task_id}")

    async def execute(self, task_id: str) -> Dict[str, Any]:
        """Execute the complete Worker Squad workflow for a task.

        This is the main entry point that orchestrates all stages of the
        Worker Squad process. The workflow follows TDD principles:

        1. Planner: Creates a detailed plan for the task
        2. TDD Test: Writes test skeleton and plan before implementation
        3. Coder: Implements code to make the tests pass
        4. Test: Runs the tests to verify implementation
        5. Debug: Fixes issues if tests fail (iterates up to 5 times)
        6. Self Review: Coder reviews own work for plan compliance
        7. Approver: Final approval (may loop back to coder if rejected)

        Each stage's results are saved to state, and the workflow can
        exit early if any critical stage fails. After successful approval,
        Sprint-level tests are triggered in the background.

        The executor can work in event-driven mode by subscribing to
        workflow events, but currently uses sequential mode for clarity.

        Args:
            task_id: Unique identifier of the task to execute.

        Returns:
            Dictionary containing:
            - success: Boolean indicating if workflow completed successfully
            - stages: Dictionary mapping stage names to their results
            - error: Optional error message if workflow failed
        """
        # Set up event subscriptions if event-driven mode is enabled
        if self._use_event_driven and self.event_bus:
            await self._setup_event_subscriptions(task_id)

        # Publish workflow started event
        if self.event_bus:
            await self.event_bus.publish(WorkflowEvent(
                event_type=WorkflowEventType.WORKFLOW_STARTED,
                task_id=task_id,
                data={"workflow_type": "worker_squad"}
            ))

        # If event-driven mode, start first stage and let events handle the rest
        if self._use_event_driven and self.event_bus:
            workflow_state = self._active_workflows.get(task_id, {})
            # Start with planner stage
            await self._execute_stage_async(task_id, "planner", workflow_state)
            # Wait for workflow completion (events will handle the rest)
            # We'll need to wait for workflow to complete
            max_wait_time = 3600  # 1 hour max
            wait_interval = 1.0
            waited = 0.0
            while waited < max_wait_time:
                workflow_state = self._active_workflows.get(task_id)
                if not workflow_state:
                    break
                if workflow_state.get("status") in ["completed", "failed"]:
                    break
                await asyncio.sleep(wait_interval)
                waited += wait_interval

            # Get final stages from workflow state
            stages = workflow_state.get("stages", {}) if workflow_state else {}
            success = workflow_state.get("status") == "completed" if workflow_state else False

            return {
                "success": success,
                "stages": stages,
                "error": None if success else "Workflow failed or timed out"
            }

        # Sequential mode (original implementation)
        stages = {}
        previous_stages = {}

        # 1. Planner
        planner_result = await self._execute_planner_stage(task_id, previous_stages)
        planner_result["status"] = "completed" if planner_result.get("success") else "failed"
        stages["planner"] = planner_result
        previous_stages["planner"] = planner_result
        # Save stage result
        await self.state_manager.save_worker_squad_stage_async(task_id, "planner", planner_result)
        if not planner_result.get("success"):
            # Attempt recovery
            recovery_result = await self.recovery_manager.attempt_recovery(
                task_id=task_id,
                stage="planner",
                agent_type="planner",
                failure_result=planner_result,
                previous_stages=previous_stages
            )

            if recovery_result.get("recovered"):
                # Recovery succeeded, use recovered result
                planner_result = recovery_result["result"]
                planner_result["status"] = "completed"
                planner_result["recovered"] = True
                planner_result["recovery_strategy"] = recovery_result["strategy_used"].value
                stages["planner"] = planner_result
                previous_stages["planner"] = planner_result
                await self.state_manager.save_worker_squad_stage_async(task_id, "planner", planner_result)
                logger.info(f"Planner stage recovered for task {task_id} using {recovery_result['strategy_used'].value}")
            else:
                # Recovery failed
                error_msg = recovery_result.get("error", planner_result.get("error", "Planner stage failed"))
                # Publish workflow failed event
                if hasattr(self.coordinator, 'event_bus'):
                    await self.coordinator.event_bus.publish(WorkflowEvent(
                        event_type=WorkflowEventType.WORKFLOW_FAILED,
                        task_id=task_id,
                        stage="planner",
                        data={"error": error_msg, "recovery_failed": True}
                    ))
                return {"success": False, "stages": stages, "error": error_msg}

        # 2. Test (TDD - test first)
        tdd_test_result = await self._execute_tdd_test_stage(task_id, planner_result, previous_stages)
        stages["tdd_test"] = tdd_test_result
        previous_stages["tdd_test"] = tdd_test_result
        # Save stage result
        await self.state_manager.save_worker_squad_stage_async(task_id, "tdd_test", tdd_test_result)
        if tdd_test_result.get("status") != "completed":
            # Attempt recovery
            failure_result = {
                "success": tdd_test_result.get('success', False),
                "error": tdd_test_result.get("error", "TDD test stage failed"),
                "output": tdd_test_result.get("output", "")
            }
            recovery_result = await self.recovery_manager.attempt_recovery(
                task_id=task_id,
                stage="tdd_test",
                agent_type="test",
                failure_result=failure_result,
                previous_stages=previous_stages
            )

            if recovery_result.get("recovered"):
                tdd_test_result = recovery_result["result"]
                tdd_test_result["status"] = "completed"
                tdd_test_result["recovered"] = True
                tdd_test_result["recovery_strategy"] = recovery_result["strategy_used"].value
                stages["tdd_test"] = tdd_test_result
                previous_stages["tdd_test"] = tdd_test_result
                await self.state_manager.save_worker_squad_stage_async(task_id, "tdd_test", tdd_test_result)
                logger.info(f"TDD test stage recovered for task {task_id} using {recovery_result['strategy_used'].value}")
            else:
                error_msg = recovery_result.get("error", "TDD test stage failed")
                # Publish workflow failed event
                if hasattr(self.coordinator, 'event_bus'):
                    await self.coordinator.event_bus.publish(WorkflowEvent(
                        event_type=WorkflowEventType.WORKFLOW_FAILED,
                        task_id=task_id,
                        stage="tdd_test",
                        data={"error": error_msg, "recovery_failed": True}
                    ))
                return {"success": False, "stages": stages, "error": error_msg}

        # 3. Coder (implement to pass tests)
        coder_result = await self._execute_coder_stage(task_id, test_plan=tdd_test_result, previous_stages=previous_stages)
        coder_result["status"] = "completed" if coder_result.get("success") else "failed"
        stages["coder"] = coder_result
        previous_stages["coder"] = coder_result
        # Save stage result
        await self.state_manager.save_worker_squad_stage_async(task_id, "coder", coder_result)
        if not coder_result.get("success"):
            # Attempt recovery
            recovery_result = await self.recovery_manager.attempt_recovery(
                task_id=task_id,
                stage="coder",
                agent_type="coder",
                failure_result=coder_result,
                previous_stages=previous_stages
            )

            if recovery_result.get("recovered"):
                coder_result = recovery_result["result"]
                coder_result["status"] = "completed"
                coder_result["recovered"] = True
                coder_result["recovery_strategy"] = recovery_result["strategy_used"].value
                stages["coder"] = coder_result
                previous_stages["coder"] = coder_result
                await self.state_manager.save_worker_squad_stage_async(task_id, "coder", coder_result)
                logger.info(f"Coder stage recovered for task {task_id} using {recovery_result['strategy_used'].value}")
            else:
                error_msg = recovery_result.get("error", coder_result.get("error", "Coder stage failed"))
                # Publish workflow failed event
                if hasattr(self.coordinator, 'event_bus'):
                    await self.coordinator.event_bus.publish(WorkflowEvent(
                        event_type=WorkflowEventType.WORKFLOW_FAILED,
                        task_id=task_id,
                        stage="coder",
                        data={"error": error_msg, "recovery_failed": True}
                    ))
                return {"success": False, "stages": stages, "error": error_msg}

        # 4. Test (run tests)
        # Pass coder's modified files to test stage for better context
        coder_modified_files = coder_result.get("files_modified") or coder_result.get("parsed_data", {}).get("files_modified", [])
        test_result = await self._execute_test_stage(task_id, previous_stages)
        test_result["status"] = "completed" if test_result.get("success") else "failed"
        # Add coder's modified files to test result for debugging
        if coder_modified_files:
            if "parsed_data" not in test_result:
                test_result["parsed_data"] = {}
            test_result["parsed_data"]["coder_modified_files"] = coder_modified_files
        stages["test"] = test_result
        previous_stages["test"] = test_result
        # Save stage result
        await self.state_manager.save_worker_squad_stage_async(task_id, "test", test_result)

        # 5. Debug (iterative if tests fail)
        debug_iterations = 0
        max_debug_iterations = 5
        while not test_result.get("success") and debug_iterations < max_debug_iterations:
            debug_result = await self._execute_debug_stage(task_id, test_result, previous_stages)
            debug_result["iteration"] = debug_iterations + 1
            stages["debug"] = debug_result
            previous_stages["debug"] = debug_result
            # Save stage result
            await self.state_manager.save_worker_squad_stage_async(task_id, "debug", debug_result)
            debug_iterations += 1

            if debug_result.get("success"):
                # Re-run tests after debug
                test_result = await self._execute_test_stage(task_id, previous_stages)
                stages["test"] = test_result
                previous_stages["test"] = test_result
                await self.state_manager.save_worker_squad_stage_async(task_id, "test", test_result)
            else:
                # Attempt recovery for debug failure
                recovery_result = await self.recovery_manager.attempt_recovery(
                    task_id=task_id,
                    stage="debug",
                    agent_type="debug",
                    failure_result=debug_result,
                    previous_stages=previous_stages
                )
                if recovery_result.get("recovered"):
                    debug_result = recovery_result["result"]
                    # ... handle recovered debug ...
                    test_result = await self._execute_test_stage(task_id, previous_stages)
                    stages["test"] = test_result
                    previous_stages["test"] = test_result
                    await self.state_manager.save_worker_squad_stage_async(task_id, "test", test_result)
                else:
                    break

        if not test_result.get("success"):
            # Attempt recovery for final test failure
            recovery_result = await self.recovery_manager.attempt_recovery(
                task_id=task_id,
                stage="test",
                agent_type="test",
                failure_result=test_result,
                previous_stages=previous_stages
            )

            if recovery_result.get("recovered"):
                test_result = recovery_result["result"]
                stages["test"] = test_result
                previous_stages["test"] = test_result
                await self.state_manager.save_worker_squad_stage_async(task_id, "test", test_result)
            else:
                # Publish workflow failed event
                if hasattr(self.coordinator, 'event_bus'):
                    await self.coordinator.event_bus.publish(WorkflowEvent(
                        event_type=WorkflowEventType.WORKFLOW_FAILED,
                        task_id=task_id,
                        stage="test",
                        data={"error": "Tests failed after max debug iterations"}
                    ))
                return {"success": False, "stages": stages, "error": "Tests failed after max debug iterations"}

        # 6. Self Review
        self_review_result = await self._execute_self_review_stage(task_id, previous_stages)
        stages["self_review"] = self_review_result
        previous_stages["self_review"] = self_review_result
        # Save stage result
        await self.state_manager.save_worker_squad_stage_async(task_id, "self_review", self_review_result)

        # 7. Approver
        approver_result = await self._execute_approver_stage(task_id, self_review_result, previous_stages)
        stages["approver"] = approver_result
        previous_stages["approver"] = approver_result
        # Save stage result
        await self.state_manager.save_worker_squad_stage_async(task_id, "approver", approver_result)

        # If approver rejects, go back to coder
        max_approver_iterations = 3
        approver_iterations = 0
        while approver_result.get("decision") == "rejected" and approver_iterations < max_approver_iterations:
            # Go back to coder
            coder_result = await self._execute_coder_stage(
                task_id, approver_result.get("feedback", ""), previous_stages=previous_stages
            )
            coder_result["iteration"] = approver_iterations + 1
            coder_result["status"] = "completed" if coder_result.get("success") else "failed"
            stages["coder"] = coder_result
            previous_stages["coder"] = coder_result
            # Save stage result
            await self.state_manager.save_worker_squad_stage_async(task_id, "coder", coder_result)

            if not coder_result.get("success"):
                return {"success": False, "stages": stages, "error": "Coder failed after approver rejection"}

            # Re-run self review and approver
            self_review_result = await self._execute_self_review_stage(task_id, previous_stages)
            stages["self_review"] = self_review_result
            previous_stages["self_review"] = self_review_result
            # Save stage result
            await self.state_manager.save_worker_squad_stage_async(task_id, "self_review", self_review_result)

            approver_result = await self._execute_approver_stage(task_id, self_review_result, previous_stages)
            stages["approver"] = approver_result
            previous_stages["approver"] = approver_result
            # Save stage result
            await self.state_manager.save_worker_squad_stage_async(task_id, "approver", approver_result)
            approver_iterations += 1

        if approver_result.get("decision") != "approved":
            # Publish workflow failed event
            if hasattr(self.coordinator, 'event_bus'):
                await self.coordinator.event_bus.publish(WorkflowEvent(
                    event_type=WorkflowEventType.WORKFLOW_FAILED,
                    task_id=task_id,
                    stage="approver",
                    data={"error": "Approver did not approve after max iterations"}
                ))
            return {"success": False, "stages": stages, "error": "Approver did not approve after max iterations"}

        # 8. Run Sprint tests in background (NON-BLOCKING)
        # Get sprint_id from task
        tasks = self.state_manager.get_task_checklist()
        task = next((t for t in tasks if t.get("id") == task_id), None)
        sprint_id = task.get("sprint_id") if task else None
        if sprint_id and hasattr(self.coordinator, 'sprint_executor'):
            asyncio.create_task(self.coordinator.sprint_executor.run_sprint_tests(sprint_id, task_id))

        # Publish workflow completed event
        if hasattr(self.coordinator, 'event_bus'):
            await self.coordinator.event_bus.publish(WorkflowEvent(
                event_type=WorkflowEventType.WORKFLOW_COMPLETED,
                task_id=task_id,
                data={
                    "workflow_type": "worker_squad",
                    "stages": list(stages.keys()),
                    "success": True
                }
            ))

        return {
            "success": True,
            "stages": stages
        }

    async def _execute_planner_stage(self, task_id: str, previous_stages: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute Planner stage and wait for completion.

        Args:
            task_id: ID of the task to plan for.
            previous_stages: Results from previous stages (empty for planner).

        Returns:
            Dictionary with stage results including success, output, and parsed data.
        """
        timeout = self.timeouts.get("planner", 300.0)
        result = await self.coordinator.start_worker_agent_and_wait(
            task_id, "planner", stage="planner", previous_stages=previous_stages or {}, timeout=timeout
        )

        # Extract plan from parsed data (improved extraction)
        parsed_data = result.get("parsed_data", {})
        plan = parsed_data.get("plan", {})

        # If plan is a dict, use it directly; if it's a string, wrap it
        if isinstance(plan, str):
            plan = {"description": plan}
        elif not plan:
            # Try to extract plan from output
            output = result.get("output", "")
            if output:
                # Try to extract structured plan from output
                import json
                import re
                # Look for JSON plan
                json_match = re.search(r'\{[^{}]*"plan"[^{}]*\}', output, re.DOTALL)
                if json_match:
                    try:
                        plan = json.loads(json_match.group(0))
                    except:
                        pass

                # If still no plan, use first 500 chars as description
                if not plan:
                    plan = {"description": output[:500]}

        # Extract tasks breakdown if available
        tasks = parsed_data.get("tasks", [])
        estimated_hours = parsed_data.get("estimated_hours")

        return {
            "success": result.get("success", False),
            "output": result.get("output", ""),
            "plan": plan,
            "tasks": tasks,  # Task breakdown for reference
            "estimated_hours": estimated_hours,  # Time estimate
            "parsed_data": parsed_data,
            "error": result.get("error")
        }

    async def _execute_coder_stage(
        self,
        task_id: str,
        feedback: str = "",
        test_plan: Dict[str, Any] = None,
        previous_stages: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute Coder stage and wait for completion.

        Args:
            task_id: ID of the task to code for.
            feedback: Optional feedback from approver if this is a rework.
            test_plan: Optional test plan from TDD stage to guide implementation.
            previous_stages: Results from previous stages in the workflow.

        Returns:
            Dictionary with stage results including success, output, and parsed data.
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

        timeout = self.timeouts.get("coder", 900.0)
        result = await self.coordinator.start_worker_agent_and_wait(
            task_id, "coder", stage="coder", previous_stages=previous_stages or {}, timeout=timeout
        )

        # Extract files modified from parsed data
        files_modified = result.get("parsed_data", {}).get("files_modified", [])

        return {
            "success": result.get("success", False),
            "output": result.get("output", ""),
            "files_modified": files_modified,
            "parsed_data": result.get("parsed_data", {}),
            "error": result.get("error")
        }

    async def _execute_tdd_test_stage(
        self,
        task_id: str,
        planner_result: Dict[str, Any],
        previous_stages: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute TDD Test stage (test-first approach) and wait for completion.

        Args:
            task_id: ID of the task to write tests for.
            planner_result: Results from the planner stage containing the plan.
            previous_stages: Results from all previous stages.

        Returns:
            Dictionary with stage results including status, test skeleton, test plan, and TDD mode flag.
        """
        timeout = self.timeouts.get("tdd_test", 300.0)
        result = await self.coordinator.start_worker_agent_and_wait(
            task_id, "test", stage="tdd_test", previous_stages=previous_stages or {}, timeout=timeout
        )

        # Extract test skeleton and plan from parsed data (improved)
        parsed_data = result.get("parsed_data", {})
        test_skeleton = parsed_data.get("test_skeleton", "")
        test_plan = parsed_data.get("test_plan", "")
        code_blocks = parsed_data.get("code_blocks", [])

        # If test_skeleton not in parsed_data, try to extract from output
        if not test_skeleton:
            output = result.get("output", "")
            if output:
                import re
                # Look for code blocks in output
                code_block_match = re.search(r'```(?:python|py|test)?\n(.*?)```', output, re.DOTALL)
                if code_block_match:
                    test_skeleton = code_block_match.group(1)

        return {
            "success": result.get("success", False),
            "status": "completed" if result.get("success") else "failed",
            "test_skeleton": test_skeleton,
            "test_plan": test_plan,
            "code_blocks": code_blocks,  # All code blocks found
            "tdd_mode": True,
            "output": result.get("output", ""),
            "parsed_data": parsed_data,  # Include full parsed data
            "error": result.get("error")
        }

    async def _execute_test_stage(self, task_id: str, previous_stages: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute Test stage (run tests after implementation) and wait for completion.

        Args:
            task_id: ID of the task to test.
            previous_stages: Results from previous stages including coder output.

        Returns:
            Dictionary with test execution results including success, status, and test results.
        """
        timeout = self.timeouts.get("test", 300.0)
        result = await self.coordinator.start_worker_agent_and_wait(
            task_id, "test", stage="test", previous_stages=previous_stages or {}, timeout=timeout
        )

        # Extract test results from parsed data
        test_results = result.get("parsed_data", {})

        return {
            "success": result.get("success", False),
            "status": "completed" if result.get("success") else "failed",
            "test_results": test_results,
            "output": result.get("output", ""),
            "error": result.get("error")
        }

    async def _execute_debug_stage(
        self,
        task_id: str,
        test_result: Dict[str, Any],
        previous_stages: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute Debug stage and wait for completion.

        Args:
            task_id: ID of the task to debug.
            test_result: Results from the test stage showing what failed.
            previous_stages: Results from all previous stages.

        Returns:
            Dictionary with debug results including status and list of issues that were fixed.
        """
        timeout = self.timeouts.get("debug", 600.0)
        result = await self.coordinator.start_worker_agent_and_wait(
            task_id, "debug", stage="debug", previous_stages=previous_stages or {}, timeout=timeout
        )

        # Extract issues fixed from parsed data
        issues_fixed = result.get("parsed_data", {}).get("issues_fixed", [])

        return {
            "success": result.get("success", False),
            "status": "completed" if result.get("success") else "failed",
            "issues_fixed": issues_fixed,
            "output": result.get("output", ""),
            "error": result.get("error")
        }

    async def _execute_self_review_stage(self, task_id: str, previous_stages: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute Self Review stage (Coder self-review) and wait for completion.

        Args:
            task_id: ID of the task to review.
            previous_stages: Results from all previous stages.

        Returns:
            Dictionary with review results including status, plan compliance flag, and any findings.
        """
        timeout = self.timeouts.get("self_review", 300.0)
        result = await self.coordinator.start_worker_agent_and_wait(
            task_id, "coder", stage="self_review", previous_stages=previous_stages or {}, timeout=timeout
        )

        # Parse findings from output (could be enhanced with structured parsing)
        findings = []
        output = result.get("output", "")
        if "issue" in output.lower() or "problem" in output.lower():
            # Simple extraction - could be improved
            findings.append("Issues found during self-review")

        return {
            "success": result.get("success", False),
            "status": "completed" if result.get("success") else "failed",
            "plan_compliance": result.get("success", False),  # Assume compliance if successful
            "findings": findings,
            "output": output,
            "error": result.get("error")
        }

    async def _execute_approver_stage(
        self,
        task_id: str,
        self_review_result: Dict[str, Any],
        previous_stages: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute Approver stage and wait for completion.

        Args:
            task_id: ID of the task to approve.
            self_review_result: Results from the self review stage.
            previous_stages: Results from all previous stages.

        Returns:
            Dictionary with approval results including status, decision ("approved" or "rejected"), and optional feedback.
        """
        timeout = self.timeouts.get("approver", 300.0)
        result = await self.coordinator.start_worker_agent_and_wait(
            task_id, "approver", stage="approver", previous_stages=previous_stages or {}, timeout=timeout
        )

        # Extract decision and feedback from parsed data
        parsed_data = result.get("parsed_data", {})
        decision = parsed_data.get("decision", "pending")
        feedback = parsed_data.get("feedback", "")

        # If no decision in parsed data, try to infer from output
        if decision == "pending" and result.get("success"):
            output = result.get("output", "").lower()
            if "approved" in output or "approve" in output:
                decision = "approved"
            elif "rejected" in output or "reject" in output:
                decision = "rejected"
            else:
                decision = "approved"  # Default to approved if successful

        return {
            "success": result.get("success", False),
            "status": "completed" if result.get("success") else "failed",
            "decision": decision,
            "feedback": feedback,
            "output": result.get("output", ""),
            "error": result.get("error")
        }
