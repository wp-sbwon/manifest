"""
Sprint management for Manifest.

This module handles Sprint data operations including loading, saving, and
updating test information. Sprints are collections of tasks that are
executed together, and they include integration and E2E test data.

The SprintManager centralizes sprint-related business logic that was
previously duplicated across multiple agent files, improving maintainability.
"""
from typing import Dict, Any, Optional, List
from manifest.core.state_manager import StateManager
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class SprintManager:
    """Manages Sprint data and operations.

    Handles loading, saving, and updating sprint information including
    test data. Sprints organize tasks into logical groups and track
    integration and E2E test status and results.

    Attributes:
        state_manager: Reference to StateManager for persistence operations.
    """

    def __init__(self, state_manager: StateManager):
        """Initialize the sprint manager.

        Args:
            state_manager: StateManager instance used for loading and saving
                sprint data.
        """
        self.state_manager = state_manager

    def load_sprint(self, sprint_id: str) -> Optional[Dict[str, Any]]:
        """Load sprint data by ID.

        Delegates to StateManager but adds validation and logging. Logs
        a warning if the sprint is not found.

        Args:
            sprint_id: Unique identifier of the sprint to load.

        Returns:
            Dictionary containing sprint data if found, None otherwise.
            A warning is logged if the sprint doesn't exist.
        """
        sprint_data = self.state_manager.load_sprint(sprint_id)
        if not sprint_data:
            logger.warning(f"Sprint not found: {sprint_id}")
        return sprint_data

    def save_sprint(self, sprint_data: Dict[str, Any]) -> bool:
        """Save sprint data to disk.

        Delegates to StateManager for the actual persistence. The StateManager
        ensures the sprint data structure is normalized before saving.

        Args:
            sprint_data: Dictionary containing sprint data to save. Must
                include an "id" field.

        Returns:
            True if save was successful, False otherwise.
        """
        return self.state_manager.save_sprint(sprint_data)

    def update_sprint_tests(
        self,
        sprint_id: str,
        test_type: str,  # "integration" or "e2e"
        status: str,
        test_files: Optional[List[str]] = None,
        test_plan: Optional[str] = None,
        test_results: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update sprint test data.

        Args:
            sprint_id: Sprint ID
            test_type: Type of test ("integration" or "e2e")
            status: Test status
            test_files: Optional list of test files
            test_plan: Optional test plan
            test_results: Optional test results

        Returns:
            True if successful, False otherwise
        """
        sprint_data = self.load_sprint(sprint_id)
        if not sprint_data:
            logger.error(f"Cannot update tests for non-existent sprint: {sprint_id}")
            return False

        test_key = f"{test_type}_tests"
        if test_key not in sprint_data:
            sprint_data[test_key] = {}

        sprint_data[test_key]["status"] = status
        if test_files is not None:
            sprint_data[test_key]["test_files"] = test_files
        if test_plan is not None:
            sprint_data[test_key]["test_plan"] = test_plan
        if test_results is not None:
            sprint_data[test_key]["test_results"] = test_results

        success = self.save_sprint(sprint_data)
        if success:
            logger.info(f"Updated {test_type} tests for sprint {sprint_id}: {status}")
        else:
            logger.error(f"Failed to save sprint {sprint_id} after test update")

        return success

    def get_sprint_tests(self, sprint_id: str, test_type: str) -> Optional[Dict[str, Any]]:
        """Get test data for a specific test type in a sprint.

        Args:
            sprint_id: ID of the sprint to query.
            test_type: Type of test to retrieve. Must be "integration" or "e2e".

        Returns:
            Dictionary containing test data if sprint exists and has test
            data, None otherwise.
        """
        sprint_data = self.load_sprint(sprint_id)
        if not sprint_data:
            return None

        test_key = f"{test_type}_tests"
        return sprint_data.get(test_key)

    def update_sprint_e2e_test_execution_results(
        self,
        sprint_id: str,
        task_id: str,
        content: str
    ) -> bool:
        """Append E2E test execution results to a sprint.

        Adds a new execution result entry to the sprint's E2E test execution
        history. This is called when a task completes and triggers E2E test
        execution.

        Args:
            sprint_id: ID of the sprint to update.
            task_id: ID of the task that triggered the test execution.
            content: Test execution output or results as a string.

        Returns:
            True if the sprint was found and updated successfully, False
            otherwise. Errors are logged.
        """
        sprint_data = self.load_sprint(sprint_id)
        if not sprint_data:
            logger.error(f"Cannot update E2E test results for non-existent sprint: {sprint_id}")
            return False

        if "e2e_tests" not in sprint_data:
            sprint_data["e2e_tests"] = {}

        if "execution_results" not in sprint_data["e2e_tests"]:
            sprint_data["e2e_tests"]["execution_results"] = []

        execution_result = {
            "task_id": task_id,
            "content": content,
            "timestamp": None  # Can be added if needed
        }

        sprint_data["e2e_tests"]["execution_results"].append(execution_result)

        return self.save_sprint(sprint_data)
