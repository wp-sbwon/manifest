"""
Sprint Executor - Executes Sprint workflows including test writing and task execution.
Separated from AgentCoordinator to improve maintainability.
"""
import asyncio
from typing import Dict, Any, Optional
from manifest.core.sprint_manager import SprintManager
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class SprintExecutor:
    """Executes Sprint workflows including test writing and task execution."""
    
    def __init__(self, coordinator: Any):
        """
        Initialize Sprint Executor.
        
        Args:
            coordinator: AgentCoordinator instance (for accessing agent methods)
        """
        self.coordinator = coordinator
        self.state_manager = coordinator.state_manager
        self.context_provider = coordinator.context_provider
        self.config_manager = coordinator.config_manager
        self.agent_bridge = coordinator.agent_bridge
        self.task_scoper = coordinator.task_scoper
        self.sprint_manager = SprintManager(self.state_manager)
    
    async def start_sprint(self, sprint_id: str, max_parallel: int = 10) -> Dict[str, Any]:
        """
        Start a Sprint by executing all tasks in parallel.
        
        **NON-BLOCKING**: Sprint test writing runs in background.
        Tasks start immediately without waiting for test writing.
        
        Args:
            sprint_id: Sprint ID
            max_parallel: Maximum number of tasks to run in parallel
            
        Returns:
            Dict with execution results:
            {
                "success": bool,
                "started_tasks": List[str],
                "failed_tasks": List[str],
                "parallel_groups": List[List[str]]
            }
        """
        # 1. Start Sprint test writing in background (NON-BLOCKING)
        asyncio.create_task(self.write_sprint_tests(sprint_id))
        
        # 2. Get Sprint tasks
        tasks = self.state_manager.get_task_checklist()
        sprint_tasks = [t for t in tasks if t.get("sprint_id") == sprint_id]
        
        if not sprint_tasks:
            return {
                "success": False,
                "error": f"No tasks found for sprint {sprint_id}",
                "started_tasks": [],
                "failed_tasks": [],
                "parallel_groups": []
            }
        
        # 3. Validate parallel execution
        task_ids = [t.get("id") for t in sprint_tasks]
        validation = self.task_scoper.validate_parallel_execution(task_ids)
        
        if not validation["can_parallelize"]:
            # Log conflicts but continue (user/Orchestrator should have validated)
            logger.warning(f"Parallel execution conflicts detected: {validation['conflicts']}")
        
        # 4. Group tasks for parallel execution
        parallel_groups = validation.get("parallel_groups", [task_ids])
        
        # 5. Start tasks in parallel immediately (respecting max_parallel limit)
        # Note: Tasks start without waiting for test writing to complete
        started_tasks = []
        failed_tasks = []
        
        for group in parallel_groups:
            # Limit parallel execution
            limited_group = group[:max_parallel]
            
            # Start all tasks in this group in parallel
            results = await asyncio.gather(
                *[self._start_task_worker_squad(task_id) for task_id in limited_group],
                return_exceptions=True
            )
            
            for task_id, result in zip(limited_group, results):
                if isinstance(result, Exception):
                    failed_tasks.append(task_id)
                    logger.error(f"Failed to start task {task_id}: {result}")
                elif result:
                    started_tasks.append(task_id)
                else:
                    failed_tasks.append(task_id)
        
        return {
            "success": len(failed_tasks) == 0,
            "started_tasks": started_tasks,
            "failed_tasks": failed_tasks,
            "parallel_groups": parallel_groups
        }
    
    async def _start_task_worker_squad(self, task_id: str) -> bool:
        """
        Start Worker Squad for a task (internal helper).
        Executes the full Worker Squad workflow in background.
        """
        # Execute full Worker Squad workflow in background (non-blocking)
        if hasattr(self.coordinator, 'worker_squad_executor'):
            asyncio.create_task(self.coordinator.worker_squad_executor.execute(task_id))
        else:
            # Fallback to old method if executor not available
            asyncio.create_task(self.coordinator.execute_worker_squad(task_id))
        return True
    
    async def write_sprint_tests(self, sprint_id: str) -> Dict[str, Any]:
        """
        Write Integration/E2E tests for Sprint scope (TDD) - Background task.
        
        **NON-BLOCKING**: This method runs in background and does not block Sprint start.
        
        Args:
            sprint_id: Sprint ID
            
        Returns:
            Dict with test writing results
        """
        try:
            # Update Sprint test status to "writing"
            sprint_data = self.sprint_manager.load_sprint(sprint_id)
            if sprint_data:
                if "integration_tests" in sprint_data:
                    sprint_data["integration_tests"]["status"] = "writing"
                if "e2e_tests" in sprint_data:
                    sprint_data["e2e_tests"]["status"] = "writing"
                self.sprint_manager.save_sprint(sprint_data)
            
            # Get Sprint-level context
            sprint_context = self.context_provider.get_sprint_context(sprint_id)
            
            # Get model config
            model_config = self.config_manager.get_model_config("integration_test")
            
            # 1. Write Integration Tests (TDD)
            integration_test_agent_id = f"sprint-{sprint_id}-integration_test"
            integration_success = await self.agent_bridge.start_agent_mission(
                task_id=integration_test_agent_id,
                agent_type="integration_test",
                context={**sprint_context, "sprint_id": sprint_id},
                model_config=model_config,
                stage="sprint_tdd_test"
            )
            
            # 2. Write E2E Tests (TDD)
            e2e_test_agent_id = f"sprint-{sprint_id}-e2e_test"
            e2e_success = await self.agent_bridge.start_agent_mission(
                task_id=e2e_test_agent_id,
                agent_type="e2e_test",
                context={**sprint_context, "sprint_id": sprint_id},
                model_config=model_config,
                stage="sprint_tdd_test"
            )
            
            # Update Sprint test status to "written"
            sprint_data = self.sprint_manager.load_sprint(sprint_id)
            if sprint_data:
                if "integration_tests" in sprint_data:
                    sprint_data["integration_tests"]["status"] = "written" if integration_success else "failed"
                if "e2e_tests" in sprint_data:
                    sprint_data["e2e_tests"]["status"] = "written" if e2e_success else "failed"
                self.sprint_manager.save_sprint(sprint_data)
                await self.state_manager.save_state()
            
            return {
                "success": integration_success and e2e_success,
                "integration_tests": {"status": "written" if integration_success else "failed"},
                "e2e_tests": {"status": "written" if e2e_success else "failed"}
            }
        except Exception as e:
            logger.error(f"Error writing Sprint tests: {e}", exc_info=True)
            # Update status to failed
            sprint_data = self.sprint_manager.load_sprint(sprint_id)
            if sprint_data:
                if "integration_tests" in sprint_data:
                    sprint_data["integration_tests"]["status"] = "failed"
                if "e2e_tests" in sprint_data:
                    sprint_data["e2e_tests"]["status"] = "failed"
                self.sprint_manager.save_sprint(sprint_data)
            return {"success": False, "error": str(e)}
    
    async def run_sprint_tests(self, sprint_id: str, task_id: str) -> Dict[str, Any]:
        """
        Run Sprint-level Integration/E2E tests after Task completion - Background task.
        
        **NON-BLOCKING**: This method runs in background and does not block Worker Squad completion.
        
        Args:
            sprint_id: Sprint ID
            task_id: Task ID that completed
            
        Returns:
            Dict with test execution results
        """
        try:
            # Get Sprint-level context
            sprint_context = self.context_provider.get_sprint_context(sprint_id)
            
            # Get model config
            integration_model_config = self.config_manager.get_model_config("integration_test")
            e2e_model_config = self.config_manager.get_model_config("e2e_test")
            
            # 1. Run Integration Tests
            integration_test_agent_id = f"sprint-{sprint_id}-integration_test-{task_id}"
            integration_success = await self.agent_bridge.start_agent_mission(
                task_id=integration_test_agent_id,
                agent_type="integration_test",
                context={**sprint_context, "sprint_id": sprint_id, "task_id": task_id},
                model_config=integration_model_config,
                stage="sprint_test_execution"
            )
            
            # 2. Run E2E Tests
            e2e_test_agent_id = f"sprint-{sprint_id}-e2e_test-{task_id}"
            e2e_success = await self.agent_bridge.start_agent_mission(
                task_id=e2e_test_agent_id,
                agent_type="e2e_test",
                context={**sprint_context, "sprint_id": sprint_id, "task_id": task_id},
                model_config=e2e_model_config,
                stage="sprint_test_execution"
            )
            
            return {
                "success": integration_success and e2e_success,
                "integration_tests": {"status": "executed" if integration_success else "failed"},
                "e2e_tests": {"status": "executed" if e2e_success else "failed"},
                "task_id": task_id
            }
        except Exception as e:
            logger.error(f"Error running Sprint tests: {e}", exc_info=True)
            return {"success": False, "error": str(e), "task_id": task_id}
