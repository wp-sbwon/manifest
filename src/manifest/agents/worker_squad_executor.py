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
from typing import Dict, Any, Optional
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
    
    def set_timeout(self, stage: str, timeout: float):
        """Set timeout for a specific stage."""
        self.timeouts[stage] = timeout
    
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
        # Publish workflow started event
        if hasattr(self.coordinator, 'event_bus'):
            await self.coordinator.event_bus.publish(WorkflowEvent(
                event_type=WorkflowEventType.WORKFLOW_STARTED,
                task_id=task_id,
                data={"workflow_type": "worker_squad"}
            ))
        
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
        test_result = await self._execute_test_stage(task_id, previous_stages)
        test_result["status"] = "completed" if test_result.get("success") else "failed"
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
        
        # Extract plan from parsed data
        plan = result.get("parsed_data", {}).get("plan", {})
        if not plan:
            # Try to extract plan from output
            output = result.get("output", "")
            if output:
                plan = {"description": output[:500]}  # Use first 500 chars as plan description
        
        return {
            "success": result.get("success", False),
            "output": result.get("output", ""),
            "plan": plan,
            "parsed_data": result.get("parsed_data", {}),
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
        
        # Extract test skeleton and plan from parsed data
        parsed_data = result.get("parsed_data", {})
        test_skeleton = parsed_data.get("test_skeleton", "")
        test_plan = parsed_data.get("test_plan", "")
        
        return {
            "success": result.get("success", False),
            "status": "completed" if result.get("success") else "failed",
            "test_skeleton": test_skeleton,
            "test_plan": test_plan,
            "tdd_mode": True,
            "output": result.get("output", ""),
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
