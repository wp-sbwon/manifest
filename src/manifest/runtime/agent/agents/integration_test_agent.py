"""
Integration test agent for component and service integration testing.

This module provides the IntegrationTestAgent class which handles writing
and executing integration tests. Integration tests verify that components
work together correctly, testing communication between services, APIs, and
modules.

The agent supports both TDD mode (write tests first) and execution mode
(run tests after implementation), and operates at the Sprint level to test
component integrations across the Sprint scope.
"""
from typing import Dict, Any, Optional, List, AsyncIterator, TYPE_CHECKING
from manifest.runtime.agent.core.executor import AgentExecutor
from manifest.core.state_manager import StateManager

if TYPE_CHECKING:
    from manifest.runtime.router.terminal_router import TerminalRouter


INTEGRATION_TEST_IDENTITY = """
**Identity**: Integration Testing Specialist

**Core Competencies**:
- Component integration testing
- API integration testing
- Service integration testing
- Database integration testing
- Cross-module integration validation
- Integration test result analysis

**Operating Modes**:
1. **TDD Mode**: Write failing integration tests first (before implementation)
2. **Test Execution Mode**: Run integration tests after implementation
"""

SPRINT_TDD_INTEGRATION_TEST_PROMPT_TEMPLATE = """
{INTEGRATION_TEST_IDENTITY}

## TDD MODE: Write Integration Tests First (Sprint Scope)

**You are in TDD (Test-Driven Development) mode for Sprint-level Integration Testing. Your task is to write FAILING integration tests BEFORE implementation.**

### TDD Workflow:
1. **Red Phase**: Write integration tests that define the desired component/service integration behavior
2. Tests should FAIL initially (implementation doesn't exist yet)
3. Tests should be comprehensive and cover:
   - Component-to-component integration
   - API endpoint integration
   - Service-to-service communication
   - Database integration
   - External service integration (if applicable)
   - Error handling in integration scenarios

### Sprint Information:
Sprint ID: {sprint_id}
Sprint Name: {sprint_name}
Sprint Description: {sprint_description}

### Sprint Scope:
Tasks: {task_list}
Components: {component_list}
APIs: {api_list}

### Architecture & Blueprint:
{architecture_info}

{blueprint_info}

### PRD Requirements:
{prd_info}

## YOUR TASK

1. Analyze the Sprint scope, Architecture, and Blueprint carefully
2. Design comprehensive integration test cases covering:
   - All component integrations within Sprint scope
   - API integrations between services
   - Data flow between components
   - Error scenarios in integration points
3. Write integration test code that:
   - Defines expected integration behavior
   - Will FAIL initially (implementation doesn't exist)
   - Covers all integration requirements from the Sprint scope
   - Uses appropriate testing framework (pytest, unittest, jest, etc.)
4. Save test files in the appropriate test directory
5. Provide test skeleton/plan summary

## INTEGRATION TEST REQUIREMENTS

- Write complete, runnable integration test code
- Tests should be in appropriate test files (e.g., `test_integration_*.py`, `integration/*.test.js`)
- Tests should verify:
  - Component A can communicate with Component B
  - API endpoints work correctly with other services
  - Data flows correctly through the system
  - Error handling works at integration boundaries
- Ensure tests will fail initially (this is expected in TDD)
- Include test descriptions/comments explaining what each test validates

## OUTPUT FORMAT

Provide:
1. Test file paths where integration tests were written
2. Integration test skeleton/plan summary
3. List of integration test cases created
4. Integration points covered
"""

INTEGRATION_TEST_EXECUTION_PROMPT_TEMPLATE = """
{INTEGRATION_TEST_IDENTITY}

## INTEGRATION TEST EXECUTION MODE: Run Tests After Implementation

**You are in Integration Test Execution mode. Your task is to run integration tests and validate component/service integration.**

### Sprint Information:
Sprint ID: {sprint_id}
Sprint Name: {sprint_name}

### Task Information:
Task ID: {task_id}
Task Name: {task_name}
Task Description: {task_description}

### Implementation Details:
{implementation_details}

### Integration Test Files:
{test_files}

## YOUR TASK

1. Run the integration test suite
2. Collect test results
3. Analyze pass/fail status
4. Report detailed test results including:
   - Number of integration tests passed
   - Number of integration tests failed
   - Integration points that failed
   - Error messages for failed tests
   - Component communication issues
5. Provide recommendations if tests fail

## INTEGRATION TEST EXECUTION REQUIREMENTS

- Execute all relevant integration tests
- Capture both stdout and stderr
- Parse test results accurately
- Report failures with clear error messages
- Identify which integration points failed
- Provide actionable feedback for fixing integration failures
"""


class IntegrationTestAgent:
    """Integration test agent for writing and executing integration tests.

    Handles Sprint-level integration testing which verifies that components
    communicate correctly with each other. Integration tests ensure APIs,
    services, and modules work together as expected.

    The agent supports TDD mode (write tests before implementation) and
    execution mode (run tests after implementation). Test results are saved
    to Sprint data for tracking.

    Attributes:
        agent_id: Unique identifier for this agent instance.
        executor: AgentExecutor for making LLM API calls.
        state_manager: StateManager for persisting test results.
        message_history: List of conversation messages for context.
    """

    def __init__(
        self,
        agent_id: str,
        executor: AgentExecutor,
        state_manager: StateManager
    ):
        """Initialize the integration test agent.

        Args:
            agent_id: Unique identifier for this agent.
            executor: Executor instance for LLM API calls.
            state_manager: State manager for saving test results to Sprint data.
        """
        self.agent_id = agent_id
        self.executor = executor
        self.state_manager = state_manager
        self.terminal_router = terminal_router
        self.message_history: List[Dict[str, str]] = []

    async def write_tdd_tests(
        self,
        sprint_id: str,
        context: Dict[str, Any],
        model_config: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """Write integration tests in TDD mode for a Sprint.

        In TDD mode, integration tests are written before implementation.
        The agent analyzes the Sprint scope, blueprint components, and
        contracts to create comprehensive integration tests that define
        expected component interactions. These tests should initially fail.

        Args:
            sprint_id: ID of the sprint to write integration tests for.
            context: Tiered context including PRD, architecture, blueprint,
                and Sprint task/component information.
            model_config: Dictionary with provider, model, and api_key.

        Yields:
            Dictionaries with type "chunk" (streaming) or "complete" (finished).
            Content contains integration test code. Test information is extracted
            and saved to Sprint data when complete.
        """
        # Generate TDD integration test prompt
        prompt = self._generate_sprint_tdd_integration_test_prompt(sprint_id, context)

        # Execute agent
        async for chunk in self.executor.execute_agent(
            agent_id=self.agent_id,
            agent_type="integration_test",
            prompt=prompt,
            model_config=model_config,
            context=context,
            message_history=self.message_history
        ):
            # Save to message history
            if chunk.get("type") == "chunk":
                if not self.message_history or self.message_history[-1]["role"] != "assistant":
                    self.message_history.append({"role": "assistant", "content": ""})
                self.message_history[-1]["content"] += chunk.get("content", "")
            elif chunk.get("type") == "complete":
                # Save complete response and extract test information
                await self._save_tdd_integration_test_results(sprint_id, chunk.get("content", ""))

            yield chunk

    async def run_integration_tests(
        self,
        sprint_id: str,
        task_id: str,
        context: Dict[str, Any],
        model_config: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """Run integration tests after a task completes.

        Executes the integration test suite to verify that component
        integrations still work correctly after the task's changes. This
        ensures the implementation doesn't break component communication.

        Args:
            sprint_id: ID of the sprint the task belongs to.
            task_id: ID of the task that just completed.
            context: Tiered context including implementation details and
                test file locations from TDD stage.
            model_config: Dictionary with provider, model, and api_key.

        Yields:
            Dictionaries with type "chunk" (streaming) or "complete" (finished).
            Content contains test execution output. Results are parsed and
            saved to Sprint data when complete.
        """
        # Generate integration test execution prompt
        prompt = self._generate_integration_test_execution_prompt(sprint_id, task_id, context)

        # Execute agent
        async for chunk in self.executor.execute_agent(
            agent_id=self.agent_id,
            agent_type="integration_test",
            prompt=prompt,
            model_config=model_config,
            context=context,
            message_history=self.message_history
        ):
            # Save to message history
            if chunk.get("type") == "chunk":
                if not self.message_history or self.message_history[-1]["role"] != "assistant":
                    self.message_history.append({"role": "assistant", "content": ""})
                self.message_history[-1]["content"] += chunk.get("content", "")
            elif chunk.get("type") == "complete":
                # Save test results
                await self._save_integration_test_execution_results(sprint_id, task_id, chunk.get("content", ""))

            yield chunk

    def _generate_sprint_tdd_integration_test_prompt(self, sprint_id: str, context: Dict[str, Any]) -> str:
        """Generate Sprint-level TDD integration test prompt."""
        # Get Sprint information
        from manifest.core.sprint_manager import SprintManager
        sprint_manager = SprintManager(self.state_manager)
        sprint_data = sprint_manager.load_sprint(sprint_id)
        sprint_name = sprint_data.get("name", "") if sprint_data else ""
        sprint_description = sprint_data.get("description", "") if sprint_data else ""

        # Get Sprint tasks
        tasks = self.state_manager.get_task_checklist()
        sprint_tasks = [t for t in tasks if t.get("sprint_id") == sprint_id]
        task_list = "\n".join([f"- {t.get('name', t.get('id', ''))}: {t.get('description', '')}" for t in sprint_tasks])

        # Extract component and API information from context
        blueprint = context.get("tier_1", {}).get("blueprint", {})
        components = blueprint.get("components", [])
        component_list = "\n".join([f"- {c.get('name', c.get('id', ''))}" for c in components[:10]])  # Limit to first 10

        # Extract APIs from contracts
        contracts = blueprint.get("contracts", [])
        api_list = "\n".join([f"- {c.get('name', c.get('id', ''))}" for c in contracts[:10]])

        # Get Architecture info
        architecture = context.get("tier_1", {}).get("architecture", {})
        architecture_info = f"""
Architecture:
{self._format_architecture(architecture)}
"""

        # Get Blueprint info
        blueprint_info = f"""
Blueprint:
{self._format_blueprint(blueprint)}
"""

        # Get PRD info
        prd_data = context.get("tier_1", {}).get("prd", {})
        prd_info = f"""
PRD:
{self._format_prd(prd_data)}
"""

        return SPRINT_TDD_INTEGRATION_TEST_PROMPT_TEMPLATE.format(
            INTEGRATION_TEST_IDENTITY=INTEGRATION_TEST_IDENTITY,
            sprint_id=sprint_id,
            sprint_name=sprint_name,
            sprint_description=sprint_description,
            task_list=task_list or "No tasks defined",
            component_list=component_list or "No components defined",
            api_list=api_list or "No APIs defined",
            architecture_info=architecture_info,
            blueprint_info=blueprint_info,
            prd_info=prd_info
        )

    def _generate_integration_test_execution_prompt(self, sprint_id: str, task_id: str, context: Dict[str, Any]) -> str:
        """Generate integration test execution prompt."""
        # Get Sprint information
        from manifest.core.sprint_manager import SprintManager
        sprint_manager = SprintManager(self.state_manager)
        sprint_data = sprint_manager.load_sprint(sprint_id)
        sprint_name = sprint_data.get("name", "") if sprint_data else ""

        # Get Task information
        tasks = self.state_manager.get_task_checklist()
        task = next((t for t in tasks if t.get("id") == task_id), None)
        task_name = task.get("name", "") if task else ""
        task_description = task.get("description", "") if task else ""

        # Get implementation details from context
        worker_squad_stages = task.get("worker_squad_stages", {}) if task else {}
        coder_output = worker_squad_stages.get("coder", {}).get("output", "")
        files_modified = worker_squad_stages.get("coder", {}).get("files_modified", [])
        implementation_details = f"""
Coder Output: {coder_output[:500]}...
Files Modified: {', '.join(files_modified) if files_modified else 'None'}
"""

        # Get test files from Sprint data
        integration_tests = sprint_data.get("integration_tests", {}) if sprint_data else {}
        test_files = integration_tests.get("test_files", [])
        test_files_str = "\n".join(test_files) if test_files else "Integration test files from Sprint TDD stage"

        return INTEGRATION_TEST_EXECUTION_PROMPT_TEMPLATE.format(
            INTEGRATION_TEST_IDENTITY=INTEGRATION_TEST_IDENTITY,
            sprint_id=sprint_id,
            sprint_name=sprint_name,
            task_id=task_id,
            task_name=task_name,
            task_description=task_description,
            implementation_details=implementation_details,
            test_files=test_files_str
        )

    def _format_architecture(self, architecture: Dict[str, Any]) -> str:
        """Format architecture data for prompt."""
        if not architecture:
            return "No architecture data available"

        features = architecture.get("features", [])
        requirements = architecture.get("requirements", [])

        formatted = []
        if features:
            formatted.append("Features:")
            for feature in features[:5]:  # Limit to first 5
                formatted.append(f"  - {feature.get('name', feature.get('id', ''))}")

        if requirements:
            formatted.append("\nRequirements:")
            for req in requirements[:5]:
                formatted.append(f"  - {req.get('desc', req.get('id', ''))}")

        return "\n".join(formatted) if formatted else "No architecture details"

    def _format_blueprint(self, blueprint: Dict[str, Any]) -> str:
        """Format blueprint data for prompt."""
        if not blueprint:
            return "No blueprint data available"

        components = blueprint.get("components", [])
        contracts = blueprint.get("contracts", [])

        formatted = []
        if components:
            formatted.append("Components:")
            for comp in components[:10]:  # Limit to first 10
                formatted.append(f"  - {comp.get('name', comp.get('id', ''))}")

        if contracts:
            formatted.append("\nContracts:")
            for contract in contracts[:5]:
                formatted.append(f"  - {contract.get('name', contract.get('id', ''))}")

        return "\n".join(formatted) if formatted else "No blueprint details"

    def _format_prd(self, prd_data: Dict[str, Any]) -> str:
        """Format PRD data for prompt."""
        if not prd_data:
            return "No PRD data available"

        title = prd_data.get("title", "")
        overview = prd_data.get("overview", "")

        formatted = []
        if title:
            formatted.append(f"Title: {title}")
        if overview:
            formatted.append(f"Overview: {overview[:200]}...")

        return "\n".join(formatted) if formatted else "No PRD details"

    async def _save_tdd_integration_test_results(self, sprint_id: str, content: str):
        """Save TDD integration test writing results to Sprint data."""
        # Extract test information from content
        import re
        test_files = []
        test_cases = []

        # Look for test file paths
        file_patterns = [
            r"test_integration[_\w]*\.py",
            r"integration[_\w]*\.test\.js",
            r"tests?/integration/[^\s]+",
        ]
        for pattern in file_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            test_files.extend(matches)

        # Look for test case names
        test_case_patterns = [
            r"def test_\w+",
            r"it\(['\"]([^'\"]+)['\"]",
            r"test\(['\"]([^'\"]+)['\"]",
        ]
        for pattern in test_case_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            test_cases.extend([m if isinstance(m, str) else m[0] if m else "" for m in matches])

        test_results = {
            "status": "written",
            "output": content,
            "test_files": list(set(test_files)),
            "test_cases": list(set(test_cases)),
            "test_skeleton": content,
            "test_plan": self._extract_test_plan(content),
            "tdd_mode": True,
            "written_at": self._get_timestamp()
        }

        # Update Sprint data
        from manifest.core.sprint_manager import SprintManager
        sprint_manager = SprintManager(self.state_manager)
        sprint_data = sprint_manager.load_sprint(sprint_id)
        if sprint_data:
            sprint_data["integration_tests"] = test_results
            from manifest.core.sprint_manager import SprintManager
            sprint_manager = SprintManager(self.state_manager)
            sprint_manager.save_sprint(sprint_data)
            await self.state_manager.save_state()

    async def _save_integration_test_execution_results(self, sprint_id: str, task_id: str, content: str):
        """Save integration test execution results."""
        # Parse test results from content
        import re
        test_results = {
            "status": "executed",
            "output": content,
            "tests_passed": 0,
            "tests_failed": 0,
            "details": [],
            "executed_at": self._get_timestamp()
        }

        # Extract test results
        passed_patterns = [
            r"(\d+)\s+passed",
            r"(\d+)\s+tests?\s+passed",
            r"PASSED[:\s]+(\d+)",
        ]
        failed_patterns = [
            r"(\d+)\s+failed",
            r"(\d+)\s+tests?\s+failed",
            r"FAILED[:\s]+(\d+)",
        ]

        for pattern in passed_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                test_results["tests_passed"] = int(match.group(1))
                break

        for pattern in failed_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                test_results["tests_failed"] = int(match.group(1))
                break

        # Determine overall status
        if test_results["tests_failed"] > 0:
            test_results["status"] = "failed"
        elif test_results["tests_passed"] > 0:
            test_results["status"] = "passed"
        elif "passed" in content.lower() or "success" in content.lower():
            test_results["status"] = "passed"
        elif "failed" in content.lower() or "error" in content.lower():
            test_results["status"] = "failed"

        # Update Sprint data - append to execution_results
        from manifest.core.sprint_manager import SprintManager
        sprint_manager = SprintManager(self.state_manager)
        sprint_data = sprint_manager.load_sprint(sprint_id)
        if sprint_data:
            if "integration_tests" not in sprint_data:
                sprint_data["integration_tests"] = {}
            if "execution_results" not in sprint_data["integration_tests"]:
                sprint_data["integration_tests"]["execution_results"] = []

            # Add task_id to result
            test_results["task_id"] = task_id
            sprint_data["integration_tests"]["execution_results"].append(test_results)
            sprint_data["integration_tests"]["status"] = "executed"

            from manifest.core.sprint_manager import SprintManager
            sprint_manager = SprintManager(self.state_manager)
            sprint_manager.save_sprint(sprint_data)
            await self.state_manager.save_state()

    def _extract_test_plan(self, content: str) -> str:
        """Extract test plan summary from content."""
        import re
        plan_patterns = [
            r"test plan[:\s]+([^\n]+)",
            r"integration test cases[:\s]+([^\n]+)",
            r"## Test Plan\n([^\n]+)",
        ]
        for pattern in plan_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1) if match.groups() else match.group(0)
        return "Integration test plan extracted from test code"

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()
