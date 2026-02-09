"""
Sprint workflow execution and management.

This module handles Sprint-level operations including starting sprints,
writing Sprint-level tests (integration and E2E), and executing tasks
in parallel. Sprint tests are written in the background (non-blocking)
while tasks start immediately.

The SprintExecutor was separated from AgentCoordinator to improve code
organization and maintainability.
"""
import asyncio
from typing import Dict, Any, Optional
from manifest.core.sprint_manager import SprintManager
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class SprintExecutor:
    """Executes Sprint workflows including test writing and task execution.

    Handles starting sprints, writing Sprint-level tests, and coordinating
    parallel task execution. Sprint tests are written asynchronously in the
    background so they don't block task execution.

    Attributes:
        coordinator: Reference to AgentCoordinator for accessing services.
        state_manager: Reference to StateManager for persistence.
        context_provider: Reference to ContextProvider for Sprint context.
        config_manager: Reference to ConfigManager for agent configurations.
        agent_bridge: Reference to AgentBridge for starting agents.
        task_scoper: Reference to TaskScoper for parallel execution validation.
        sprint_manager: SprintManager instance for Sprint data operations.
    """

    def __init__(self, coordinator: Any):
        """Initialize the Sprint executor.

        Args:
            coordinator: AgentCoordinator instance that provides access to
                all necessary services and managers.
        """
        self.coordinator = coordinator
        self.state_manager = coordinator.state_manager
        self.context_provider = coordinator.context_provider
        self.config_manager = coordinator.config_manager
        self.agent_bridge = coordinator.agent_bridge
        self.task_scoper = coordinator.task_scoper
        self.sprint_manager = SprintManager(self.state_manager)

    async def start_sprint(self, sprint_id: str, max_parallel: int = 10) -> Dict[str, Any]:
        """Start a sprint by executing all its tasks in parallel.

        This method does two things simultaneously:
        1. Starts writing Sprint-level tests in the background (non-blocking)
        2. Immediately starts executing tasks in parallel (respecting max_parallel)

        Tasks don't wait for test writing to complete. The test writing
        happens asynchronously and updates the Sprint data when done.

        Tasks are grouped for parallel execution based on dependency analysis
        from TaskScoper. Conflicts are logged but don't prevent execution.

        Args:
            sprint_id: Unique identifier of the sprint to start.
            max_parallel: Maximum number of tasks to run simultaneously.
                Defaults to 10. This prevents resource exhaustion.

        Returns:
            Dictionary containing:
            - success: True if all tasks started successfully
            - started_tasks: List of task IDs that started
            - failed_tasks: List of task IDs that failed to start
            - parallel_groups: List of task groups for parallel execution
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
            asyncio.create_task(self.coordinator.execute_worker_squad(task_id))
        return True

    async def write_sprint_tests(self, sprint_id: str) -> Dict[str, Any]:
        """Write Integration and E2E tests for a sprint (TDD approach).

        This method runs as a background task and doesn't block sprint
        execution. It starts two agents: one for integration tests and one
        for E2E tests. Both agents write tests based on the Sprint scope
        and context.

        The Sprint test status is updated throughout the process: "writing"
        when started, "written" on success, or "failed" on error.

        Args:
            sprint_id: ID of the sprint to write tests for.

        Returns:
            Dictionary with test writing results including success status
            and status for both integration and E2E tests.
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
        """Run Sprint-level Integration and E2E tests after a task completes.

        This method is called automatically when a task finishes its Worker
        Squad workflow. It runs both integration and E2E tests to verify
        that the task's changes don't break Sprint-level functionality.

        This runs as a background task and doesn't block the Worker Squad
        completion. Test results are stored with the Sprint data.

        Args:
            sprint_id: ID of the sprint the task belongs to.
            task_id: ID of the task that just completed.

        Returns:
            Dictionary with test execution results including success status
            and execution status for both test types.
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
