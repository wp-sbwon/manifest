"""
E2E (End-to-End) test agent for system-wide testing.

This module provides the E2ETestAgent class which handles writing and
executing end-to-end tests. E2E tests verify complete user workflows from
start to finish, testing the system as a whole rather than individual
components.

The agent supports both TDD mode (write tests first) and execution mode
(run tests after implementation), and operates at the Sprint level to
test complete user journeys.
"""
from typing import Dict, Any, Optional, List, AsyncIterator, TYPE_CHECKING
from manifest.runtime.agent.core.executor import AgentExecutor
from manifest.core.state_manager import StateManager

if TYPE_CHECKING:
    from manifest.runtime.router.terminal_router import TerminalRouter


E2E_TEST_IDENTITY = """
**Identity**: E2E Testing Specialist

**Core Competencies**:
- End-to-end testing strategy
- Integration testing
- User scenario testing
- API endpoint testing (if applicable)
- System-wide test execution
- Test result analysis

**Operating Modes**:
1. **TDD Mode**: Write failing E2E tests first (before implementation)
2. **Test Execution Mode**: Run E2E tests after implementation
"""

SPRINT_TDD_E2E_TEST_PROMPT_TEMPLATE = """
{E2E_TEST_IDENTITY}

## TDD MODE: Write E2E Tests First (Sprint Scope)

**You are in TDD (Test-Driven Development) mode for Sprint-level E2E Testing. Your task is to write FAILING end-to-end tests BEFORE implementation.**

### TDD Workflow:
1. **Red Phase**: Write E2E tests that define the desired user workflows and system behavior
2. Tests should FAIL initially (implementation doesn't exist yet)
3. Tests should be comprehensive and cover:
   - Complete user workflows from start to finish
   - Multi-step user scenarios
   - Cross-component user journeys
   - System-wide functionality
   - Error scenarios in user workflows
   - Edge cases in user interactions

### Sprint Information:
Sprint ID: {sprint_id}
Sprint Name: {sprint_name}
Sprint Description: {sprint_description}

### Sprint Scope:
Tasks: {task_list}
User Flows: {user_flows}

### Architecture & Blueprint:
{architecture_info}

{blueprint_info}

### PRD Requirements:
{prd_info}

## YOUR TASK

1. Analyze the Sprint scope, Architecture, Blueprint, and PRD carefully
2. Design comprehensive E2E test cases covering:
   - All user workflows defined in PRD
   - Complete user journeys across Sprint scope
   - Multi-step scenarios from user perspective
   - System-wide functionality validation
   - Error handling in user workflows
3. Write E2E test code that:
   - Defines expected user workflow behavior
   - Will FAIL initially (implementation doesn't exist)
   - Covers all user scenarios from the Sprint scope
   - Uses appropriate testing framework (pytest, playwright, cypress, etc.)
4. Save test files in the appropriate test directory
5. Provide test skeleton/plan summary

## E2E TEST REQUIREMENTS

- Write complete, runnable E2E test code
- Tests should be in appropriate test files (e.g., `test_e2e_*.py`, `e2e/*.test.js`)
- Tests should verify:
  - Complete user workflows from start to finish
  - User can complete entire tasks/scenarios
  - System behaves correctly across all components
  - Error handling works in user workflows
- Ensure tests will fail initially (this is expected in TDD)
- Include test descriptions/comments explaining what user workflow each test validates

## OUTPUT FORMAT

Provide:
1. Test file paths where E2E tests were written
2. E2E test skeleton/plan summary
3. List of E2E test cases created
4. User workflows covered
"""


class E2ETestAgent:
    """E2E test agent for writing and executing end-to-end tests.

    Handles Sprint-level E2E testing which verifies complete user workflows
    across the entire system. E2E tests ensure that all components work
    together correctly from the user's perspective.

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
        state_manager: StateManager,
        terminal_router: Optional["TerminalRouter"] = None
    ):
        """Initialize the E2E test agent.

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
        """Write E2E tests in TDD mode for a Sprint.

        In TDD mode, E2E tests are written before implementation. The agent
        analyzes the Sprint scope, PRD user flows, architecture, and
        blueprint to create comprehensive E2E tests that define expected
        user workflows. These tests should initially fail.

        Args:
            sprint_id: ID of the sprint to write E2E tests for.
            context: Tiered context including PRD, architecture, blueprint,
                and Sprint task information.
            model_config: Dictionary with provider, model, and api_key.

        Yields:
            Dictionaries with type "chunk" (streaming) or "complete" (finished).
            Content contains E2E test code. Test information is extracted
            and saved to Sprint data when complete.
        """
        # Generate TDD E2E test prompt
        prompt = self._generate_sprint_tdd_e2e_test_prompt(sprint_id, context)

        # Execute agent
        async for chunk in self.executor.execute_agent(
            agent_id=self.agent_id,
            agent_type="e2e_test",
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
                await self._save_tdd_e2e_test_results(sprint_id, chunk.get("content", ""))

            yield chunk

    async def run_e2e_tests(
        self,
        task_id: str,
        context: Dict[str, Any],
        model_config: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """Run E2E tests after task implementation.

        Executes the E2E test suite to verify that user workflows still
        function correctly after the task's changes. This ensures the
        implementation doesn't break existing functionality.

        Args:
            task_id: ID of the task whose changes should be tested.
            context: Tiered context including implementation details and
                test file locations.
            model_config: Dictionary with provider, model, and api_key.

        Yields:
            Dictionaries with type "chunk" (streaming) or "complete" (finished).
            Content contains test execution output. Results are parsed and
            saved to task state when complete.
        """
        # Generate prompt
        prompt = self._generate_e2e_test_prompt(task_id, context)

        # Execute agent
        async for chunk in self.executor.execute_agent(
            agent_id=self.agent_id,
            agent_type="e2e_test",
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
                # Save complete response
                await self._save_test_results(task_id, chunk.get("content", ""))

            yield chunk

    def _generate_e2e_test_prompt(self, task_id: str, context: Dict[str, Any]) -> str:
        """Generate E2E test prompt."""
        # Get task information
        tasks = self.state_manager.get_task_checklist()
        task = next((t for t in tasks if t.get("id") == task_id), None)
        task_name = task.get("name", "") if task else ""
        task_description = task.get("description", "") if task else ""

        # Get worker squad results
        worker_squad_stages = task.get("worker_squad_stages", {}) if task else {}

        prompt = f"""
{E2E_TEST_IDENTITY}

## TASK INFORMATION

Task ID: {task_id}
Task Name: {task_name}
Task Description: {task_description}

## WORKER SQUAD RESULTS

### Planner
{worker_squad_stages.get("planner", {}).get("output", "N/A")}

### Coder Implementation
{worker_squad_stages.get("coder", {}).get("output", "N/A")}

### Test Results
{worker_squad_stages.get("test", {}).get("test_results", "N/A")}

## CONTEXT

{self._format_context(context)}

## YOUR TASK

1. Review the Worker Squad implementation
2. Design comprehensive E2E tests covering:
   - User workflows end-to-end
   - Integration between components
   - System-wide functionality
   - API endpoints (if applicable)
3. Execute E2E tests
4. Analyze test results
5. Report findings and recommendations

## E2E TEST REQUIREMENTS

- Test complete user scenarios
- Verify integration between all affected components
- Test error handling and edge cases
- Validate system behavior under realistic conditions
- Ensure no regressions in existing functionality
"""
        return prompt

    def _generate_sprint_tdd_e2e_test_prompt(self, sprint_id: str, context: Dict[str, Any]) -> str:
        """Generate Sprint-level TDD E2E test prompt."""
        # Get Sprint information
        sprint_data = self.state_manager.load_sprint(sprint_id)
        sprint_name = sprint_data.get("name", "") if sprint_data else ""
        sprint_description = sprint_data.get("description", "") if sprint_data else ""

        # Get Sprint tasks
        tasks = self.state_manager.get_task_checklist()
        sprint_tasks = [t for t in tasks if t.get("sprint_id") == sprint_id]
        task_list = "\n".join([f"- {t.get('name', t.get('id', ''))}: {t.get('description', '')}" for t in sprint_tasks])

        # Get user flows from PRD
        prd_data = context.get("tier_1", {}).get("prd", {})
        user_flows = prd_data.get("user_flows", [])
        user_flows_str = "\n".join([f"- {flow.get('persona', 'User')}: {flow.get('steps', [])}" for flow in user_flows[:5]]) if user_flows else "No user flows defined"

        # Get Architecture info
        architecture = context.get("tier_1", {}).get("architecture", {})
        architecture_info = f"""
Architecture:
{self._format_architecture(architecture)}
"""

        # Get Blueprint info
        blueprint = context.get("tier_1", {}).get("blueprint", {})
        blueprint_info = f"""
Blueprint:
{self._format_blueprint(blueprint)}
"""

        # Get PRD info
        prd_info = f"""
PRD:
{self._format_prd(prd_data)}
"""

        return SPRINT_TDD_E2E_TEST_PROMPT_TEMPLATE.format(
            E2E_TEST_IDENTITY=E2E_TEST_IDENTITY,
            sprint_id=sprint_id,
            sprint_name=sprint_name,
            sprint_description=sprint_description,
            task_list=task_list or "No tasks defined",
            user_flows=user_flows_str,
            architecture_info=architecture_info,
            blueprint_info=blueprint_info,
            prd_info=prd_info
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
            for feature in features[:5]:
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
            for comp in components[:10]:
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
        user_flows = prd_data.get("user_flows", [])

        formatted = []
        if title:
            formatted.append(f"Title: {title}")
        if overview:
            formatted.append(f"Overview: {overview[:200]}...")
        if user_flows:
            formatted.append(f"\nUser Flows: {len(user_flows)} flows defined")

        return "\n".join(formatted) if formatted else "No PRD details"

    async def _save_tdd_e2e_test_results(self, sprint_id: str, content: str):
        """Save TDD E2E test writing results to Sprint data."""
        # Extract test information from content
        import re
        test_files = []
        test_cases = []

        # Look for test file paths
        file_patterns = [
            r"test_e2e[_\w]*\.py",
            r"e2e[_\w]*\.test\.js",
            r"tests?/e2e/[^\s]+",
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
            "test_plan": self._extract_e2e_test_plan(content),
            "tdd_mode": True,
            "written_at": self._get_timestamp()
        }

        # Update Sprint data
        sprint_data = self.state_manager.load_sprint(sprint_id)
        if sprint_data:
            sprint_data["e2e_tests"] = test_results
            from manifest.core.sprint_manager import SprintManager
            sprint_manager = SprintManager(self.state_manager)
            sprint_manager.save_sprint(sprint_data)
            await self.state_manager.save_state()

    def _extract_e2e_test_plan(self, content: str) -> str:
        """Extract E2E test plan summary from content."""
        import re
        plan_patterns = [
            r"test plan[:\s]+([^\n]+)",
            r"e2e test cases[:\s]+([^\n]+)",
            r"## Test Plan\n([^\n]+)",
        ]
        for pattern in plan_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1) if match.groups() else match.group(0)
        return "E2E test plan extracted from test code"

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context for prompt."""
        formatted = []

        if "tier_0" in context:
            formatted.append("### Tier 0: Policy & Principles")
            formatted.append(str(context["tier_0"]))

        if "tier_1" in context:
            formatted.append("### Tier 1: Architecture & Blueprint")
            formatted.append(str(context["tier_1"]))

        return "\n".join(formatted)

    def _generate_sprint_e2e_test_execution_prompt(self, sprint_id: str, task_id: str, context: Dict[str, Any]) -> str:
        """Generate Sprint-level E2E test execution prompt."""
        # Get Sprint information
        sprint_data = self.state_manager.load_sprint(sprint_id)
        sprint_name = sprint_data.get("name", "") if sprint_data else ""

        # Get Task information
        tasks = self.state_manager.get_task_checklist()
        task = next((t for t in tasks if t.get("id") == task_id), None)
        task_name = task.get("name", "") if task else ""
        task_description = task.get("description", "") if task else ""

        # Get implementation details
        worker_squad_stages = task.get("worker_squad_stages", {}) if task else {}
        coder_output = worker_squad_stages.get("coder", {}).get("output", "")
        files_modified = worker_squad_stages.get("coder", {}).get("files_modified", [])
        implementation_details = f"""
Coder Output: {coder_output[:500]}...
Files Modified: {', '.join(files_modified) if files_modified else 'None'}
"""

        # Get test files from Sprint data
        e2e_tests = sprint_data.get("e2e_tests", {}) if sprint_data else {}
        test_files = e2e_tests.get("test_files", [])
        test_files_str = "\n".join(test_files) if test_files else "E2E test files from Sprint TDD stage"

        return f"""
{E2E_TEST_IDENTITY}

## E2E TEST EXECUTION MODE: Run Tests After Implementation (Sprint Scope)

**You are in E2E Test Execution mode for Sprint-level testing. Your task is to run E2E tests and validate user workflows.**

### Sprint Information:
Sprint ID: {sprint_id}
Sprint Name: {sprint_name}

### Task Information:
Task ID: {task_id}
Task Name: {task_name}
Task Description: {task_description}

### Implementation Details:
{implementation_details}

### E2E Test Files:
{test_files_str}

## YOUR TASK

1. Run the E2E test suite
2. Collect test results
3. Analyze pass/fail status
4. Report detailed test results including:
   - Number of E2E tests passed
   - Number of E2E tests failed
   - User workflows that failed
   - Error messages for failed tests
   - System-wide functionality issues
5. Provide recommendations if tests fail

## E2E TEST EXECUTION REQUIREMENTS

- Execute all relevant E2E tests
- Capture both stdout and stderr
- Parse test results accurately
- Report failures with clear error messages
- Identify which user workflows failed
- Provide actionable feedback for fixing E2E failures
"""

    async def _save_sprint_e2e_test_execution_results(self, sprint_id: str, task_id: str, content: str):
        """Save Sprint-level E2E test execution results."""
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
        sprint_data = self.state_manager.load_sprint(sprint_id)
        if sprint_data:
            if "e2e_tests" not in sprint_data:
                sprint_data["e2e_tests"] = {}
            if "execution_results" not in sprint_data["e2e_tests"]:
                sprint_data["e2e_tests"]["execution_results"] = []

            # Add task_id to result
            test_results["task_id"] = task_id
            sprint_data["e2e_tests"]["execution_results"].append(test_results)
            sprint_data["e2e_tests"]["status"] = "executed"

            from manifest.core.sprint_manager import SprintManager
            sprint_manager = SprintManager(self.state_manager)
            sprint_manager.save_sprint(sprint_data)
            await self.state_manager.save_state()

    async def _save_test_results(self, task_id: str, content: str):
        """Save E2E test results to state (Task-level, existing behavior)."""
        channel = f"squad-{task_id}-e2e_test"
        self.state_manager.add_chat_message(channel, "assistant", content)

        # Parse test results from content (simplified - in production would parse structured output)
        test_results = {
            "status": "completed",
            "output": content,
            "tests_passed": 0,
            "tests_failed": 0,
            "details": []
        }

        # Extract test results (simplified parsing)
        if "passed" in content.lower() or "success" in content.lower():
            test_results["status"] = "passed"
        elif "failed" in content.lower() or "error" in content.lower():
            test_results["status"] = "failed"

        # Save to task
        tasks = self.state_manager.get_task_checklist()
        task = next((t for t in tasks if t.get("id") == task_id), None)
        if task:
            if "e2e_test" not in task:
                task["e2e_test"] = {}
            task["e2e_test"] = test_results
            self.state_manager.set_task_checklist(tasks)

        await self.state_manager.save_state()
