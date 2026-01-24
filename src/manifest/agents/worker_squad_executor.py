"""
Worker Squad Executor - Executes Worker Squad workflow for tasks.
Separated from AgentCoordinator to improve maintainability.
"""
import asyncio
from typing import Dict, Any, Optional
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class WorkerSquadExecutor:
    """Executes Worker Squad workflow for tasks."""
    
    def __init__(self, coordinator: Any):
        """
        Initialize Worker Squad Executor.
        
        Args:
            coordinator: AgentCoordinator instance (for accessing agent methods)
        """
        self.coordinator = coordinator
        self.state_manager = coordinator.state_manager
    
    async def execute(self, task_id: str) -> Dict[str, Any]:
        """
        Execute Worker Squad workflow for a task.
        
        Worker Squad flow (TDD):
        1. Planner: Create plan
        2. Test (TDD): Write test skeleton/plan first
        3. Coder: Implement code to pass tests
        4. Test: Run tests
        5. Debug: Fix bugs if tests fail (iterative)
        6. Self Review: Verify plan compliance
        7. Approver: Final approval
        
        Args:
            task_id: Task ID
            
        Returns:
            Dict with execution results:
            {
                "success": bool,
                "stages": {
                    "planner": {...},
                    "tdd_test": {...},
                    "coder": {...},
                    "test": {...},
                    "debug": {...},
                    "self_review": {...},
                    "approver": {...}
                }
            }
        """
        stages = {}
        previous_stages = {}
        
        # 1. Planner
        planner_success = await self._execute_planner_stage(task_id, previous_stages)
        planner_result = {
            "status": "completed" if planner_success else "failed",
            "output": "",
            "plan": ""
        }
        stages["planner"] = planner_result
        previous_stages["planner"] = planner_result
        # Save stage result
        await self.state_manager.save_worker_squad_stage_async(task_id, "planner", planner_result)
        if not planner_success:
            return {"success": False, "stages": stages}
        
        # 2. Test (TDD - test first)
        tdd_test_result = await self._execute_tdd_test_stage(task_id, planner_result, previous_stages)
        stages["tdd_test"] = tdd_test_result
        previous_stages["tdd_test"] = tdd_test_result
        # Save stage result
        await self.state_manager.save_worker_squad_stage_async(task_id, "tdd_test", tdd_test_result)
        if tdd_test_result.get("status") != "completed":
            return {"success": False, "stages": stages, "error": "TDD test stage failed"}
        
        # 3. Coder (implement to pass tests)
        coder_success = await self._execute_coder_stage(task_id, test_plan=tdd_test_result, previous_stages=previous_stages)
        coder_result = {
            "status": "completed" if coder_success else "failed",
            "output": "",
            "files_modified": []
        }
        stages["coder"] = coder_result
        previous_stages["coder"] = coder_result
        # Save stage result
        await self.state_manager.save_worker_squad_stage_async(task_id, "coder", coder_result)
        if not coder_success:
            return {"success": False, "stages": stages}
        
        # 4. Test (run tests)
        test_result = await self._execute_test_stage(task_id, previous_stages)
        stages["test"] = test_result
        previous_stages["test"] = test_result
        # Save stage result
        await self.state_manager.save_worker_squad_stage_async(task_id, "test", test_result)
        
        # 5. Debug (iterative if tests fail)
        debug_iterations = 0
        max_debug_iterations = 5
        while test_result.get("status") == "failed" and debug_iterations < max_debug_iterations:
            debug_result = await self._execute_debug_stage(task_id, test_result, previous_stages)
            debug_result["iteration"] = debug_iterations + 1
            stages["debug"] = debug_result
            previous_stages["debug"] = debug_result
            # Save stage result
            await self.state_manager.save_worker_squad_stage_async(task_id, "debug", debug_result)
            debug_iterations += 1
            
            if debug_result.get("status") == "completed":
                # Re-run tests after debug
                test_result = await self._execute_test_stage(task_id, previous_stages)
                stages["test"] = test_result
                previous_stages["test"] = test_result
                # Save updated test result
                await self.state_manager.save_worker_squad_stage_async(task_id, "test", test_result)
            else:
                break
        
        if test_result.get("status") == "failed":
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
            coder_success = await self._execute_coder_stage(
                task_id, approver_result.get("feedback", ""), previous_stages=previous_stages
            )
            coder_result = {
                "status": "completed" if coder_success else "failed",
                "output": "",
                "iteration": approver_iterations + 1
            }
            stages["coder"] = coder_result
            previous_stages["coder"] = coder_result
            # Save stage result
            await self.state_manager.save_worker_squad_stage_async(task_id, "coder", coder_result)
            
            if not coder_success:
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
            return {"success": False, "stages": stages, "error": "Approver did not approve after max iterations"}
        
        # 8. Run Sprint tests in background (NON-BLOCKING)
        # Get sprint_id from task
        tasks = self.state_manager.get_task_checklist()
        task = next((t for t in tasks if t.get("id") == task_id), None)
        sprint_id = task.get("sprint_id") if task else None
        if sprint_id and hasattr(self.coordinator, 'sprint_executor'):
            asyncio.create_task(self.coordinator.sprint_executor.run_sprint_tests(sprint_id, task_id))
        
        return {
            "success": True,
            "stages": stages
        }
    
    async def _execute_planner_stage(self, task_id: str, previous_stages: Dict[str, Any] = None) -> bool:
        """Execute Planner stage."""
        return await self.coordinator.start_worker_agent(task_id, "planner", stage="planner", previous_stages=previous_stages or {})
    
    async def _execute_coder_stage(
        self,
        task_id: str,
        feedback: str = "",
        test_plan: Dict[str, Any] = None,
        previous_stages: Dict[str, Any] = None
    ) -> bool:
        """Execute Coder stage."""
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
        
        return await self.coordinator.start_worker_agent(
            task_id, "coder", stage="coder", previous_stages=previous_stages or {}
        )
    
    async def _execute_tdd_test_stage(
        self,
        task_id: str,
        planner_result: Dict[str, Any],
        previous_stages: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute TDD Test stage (test-first approach)."""
        # Start test agent with TDD context
        success = await self.coordinator.start_worker_agent(
            task_id, "test", stage="tdd_test", previous_stages=previous_stages or {}
        )
        return {
            "status": "completed" if success else "failed",
            "test_skeleton": "",
            "test_plan": "",
            "tdd_mode": True
        }
    
    async def _execute_test_stage(self, task_id: str, previous_stages: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute Test stage (run tests after implementation)."""
        success = await self.coordinator.start_worker_agent(
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
        """Execute Debug stage."""
        success = await self.coordinator.start_worker_agent(
            task_id, "debug", stage="debug", previous_stages=previous_stages or {}
        )
        return {
            "status": "completed" if success else "failed",
            "issues_fixed": []
        }
    
    async def _execute_self_review_stage(self, task_id: str, previous_stages: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute Self Review stage (Coder self-review)."""
        # Self review is done by Coder agent
        success = await self.coordinator.start_worker_agent(
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
        """Execute Approver stage."""
        success = await self.coordinator.start_worker_agent(
            task_id, "approver", stage="approver", previous_stages=previous_stages or {}
        )
        return {
            "status": "completed" if success else "failed",
            "decision": "approved" if success else "pending",
            "feedback": ""
        }
