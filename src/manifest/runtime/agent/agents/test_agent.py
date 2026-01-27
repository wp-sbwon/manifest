"""
Test agent for writing and executing tests.

This module provides the TestAgent class which handles both TDD (Test-Driven
Development) test writing and test execution. In TDD mode, it writes tests
before implementation. In execution mode, it runs tests after implementation
and reports results.

The agent extracts test information (files, cases, results) and saves it to
task state for tracking throughout the Worker Squad workflow.
"""
import json
from typing import Dict, Any, Optional, List, AsyncIterator, TYPE_CHECKING
from manifest.runtime.agent.core.executor import AgentExecutor
from manifest.core.state_manager import StateManager
from manifest.runtime.tools.tool_executor import ToolExecutor
from manifest.runtime.tools.tool_definitions import get_tool_definitions

if TYPE_CHECKING:
    from manifest.runtime.router.terminal_router import TerminalRouter


TEST_AGENT_IDENTITY = """
**Identity**: Test Specialist

**Core Competencies**:
- Test-driven development (TDD)
- Test design and implementation
- Test execution and validation
- Test result analysis
- Code coverage analysis

**Operating Modes**:
1. **TDD Mode**: Write failing tests first (before implementation)
2. **Test Execution Mode**: Run tests after implementation
"""

TDD_TEST_PROMPT_TEMPLATE = """
{TEST_AGENT_IDENTITY}

## TDD MODE: Write Tests First

**You are in TDD (Test-Driven Development) mode. Your task is to write FAILING tests BEFORE implementation.**

### TDD Workflow:
1. **Red Phase**: Write tests that define the desired behavior
2. Tests should FAIL initially (implementation doesn't exist yet)
3. Tests should be comprehensive and cover:
   - Happy path scenarios
   - Edge cases
   - Error handling
   - Boundary conditions

### Task Information:
Task ID: {task_id}
Task Name: {task_name}
Task Description: {task_description}

### Planner's Plan:
{planner_plan}

### Task Scope:
Allowed Files: {allowed_files}
Allowed Components: {allowed_components}

## YOUR TASK

1. Analyze the Planner's plan carefully
2. Design comprehensive test cases based on the plan
3. Write test code that:
   - Defines expected behavior
   - Will FAIL initially (implementation doesn't exist)
   - Covers all requirements from the plan
   - Uses appropriate testing framework (pytest, unittest, jest, etc.)
4. Save test files in the appropriate test directory
5. Provide test skeleton/plan summary

## TEST REQUIREMENTS

- Write complete, runnable test code
- Tests should be in appropriate test files (e.g., `test_*.py`, `*.test.js`)
- Tests should be well-structured and readable
- Include test descriptions/comments explaining what each test validates
- Ensure tests will fail initially (this is expected in TDD)

## OUTPUT FORMAT

Provide:
1. Test file paths where tests were written
2. Test skeleton/plan summary
3. List of test cases created
"""

TEST_EXECUTION_PROMPT_TEMPLATE = """
{TEST_AGENT_IDENTITY}

## TEST EXECUTION MODE: Run Tests After Implementation

**You are in Test Execution mode. Your task is to run tests and validate implementation.**

### Task Information:
Task ID: {task_id}
Task Name: {task_name}

### Implementation Details:
{implementation_details}

### Test Files:
{test_files}

## YOUR TASK

1. Run the test suite
2. Collect test results
3. Analyze pass/fail status
4. Report detailed test results including:
   - Number of tests passed
   - Number of tests failed
   - Error messages for failed tests
   - Test coverage (if available)
5. Provide recommendations if tests fail

## TEST EXECUTION REQUIREMENTS

- Execute all relevant tests
- Capture both stdout and stderr
- Parse test results accurately
- Report failures with clear error messages
- Provide actionable feedback for fixing failures
"""


class TestAgent:
    """Test agent for writing and executing tests.

    Handles two modes:
    1. TDD mode: Writes tests before implementation (test-first)
    2. Execution mode: Runs tests after implementation to verify correctness

    The agent extracts test information from its output and saves it to
    task state, including test files created, test cases, and execution results.

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
        terminal_router: Optional["TerminalRouter"] = None,
        tool_executor: Optional[ToolExecutor] = None
    ):
        """Initialize the test agent.

        Args:
            agent_id: Unique identifier for this agent.
            executor: Executor instance for LLM API calls.
            state_manager: State manager for saving test results.
            terminal_router: Optional terminal router (kept for backward compatibility,
                but command execution should use tool_executor instead).
            tool_executor: Optional tool executor for executing tool calls.
                This is the primary way to execute commands and file operations.
        """
        self.agent_id = agent_id
        self.executor = executor
        self.state_manager = state_manager
        # terminal_router kept for backward compatibility, but tool_executor is preferred
        self.terminal_router = terminal_router
        self.tool_executor = tool_executor
        self.message_history: List[Dict[str, str]] = []
        self.agent_type = "test"
        self.message_bus = None  # Will be set by agent_bridge when agent is registered
        self._test_results: Optional[Dict[str, Any]] = None  # Store test results for message responses

        # Track tool execution results
        self.tool_execution_summary: Dict[str, Any] = {
            "modified_files": [],
            "executed_commands": [],
            "read_files": [],
            "errors": [],
            "total_tool_calls": 0
        }

    async def write_tdd_tests(
        self,
        task_id: str,
        context: Dict[str, Any],
        model_config: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """Write tests in TDD (Test-Driven Development) mode.

        In TDD mode, tests are written before implementation. The agent
        analyzes the planner's plan and writes comprehensive tests that
        define the expected behavior. These tests should initially fail
        since implementation doesn't exist yet.

        Args:
            task_id: ID of the task to write tests for.
            context: Tiered context including planner plan and task scope.
            model_config: Dictionary with provider, model, and api_key.

        Yields:
            Dictionaries with type "chunk" (streaming) or "complete" (finished).
            Content contains test code and test plan. Test information is
            extracted and saved to task state when complete.
        """
        # Generate TDD test prompt
        prompt = self._generate_tdd_test_prompt(task_id, context)

        # Execute agent
        async for chunk in self.executor.execute_agent(
            agent_id=self.agent_id,
            agent_type="test",
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
                await self._save_tdd_test_results(task_id, chunk.get("content", ""))

            yield chunk

    async def run_tests(
        self,
        task_id: str,
        context: Dict[str, Any],
        model_config: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Run tests after implementation.

        Args:
            task_id: Task ID
            context: Tiered context
            model_config: Model configuration

        Yields:
            Test execution output chunks
        """
        # Generate test execution prompt
        prompt = self._generate_test_execution_prompt(task_id, context)

        # Get tool definitions
        tools = get_tool_definitions()

        # Reset tool execution summary
        self.tool_execution_summary = {
            "modified_files": [],
            "executed_commands": [],
            "read_files": [],
            "errors": [],
            "total_tool_calls": 0
        }

        # Tool execution loop
        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # Execute agent with tools
            tool_calls_in_this_round = []
            full_response = ""

            async for chunk in self.executor.execute_agent(
                agent_id=self.agent_id,
                agent_type="test",
                prompt=prompt if iteration == 1 else None,
                model_config=model_config,
                context=context,
                message_history=self.message_history,
                tools=tools
            ):
                chunk_type = chunk.get("type")

                if chunk_type == "chunk":
                    content = chunk.get("content", "")
                    full_response += content
                    yield chunk
                elif chunk_type == "tool_use" or chunk_type == "tool_use_start":
                    tool_call = chunk.get("tool_call")
                    if tool_call:
                        tool_calls_in_this_round.append(tool_call)
                        yield chunk
                elif chunk_type == "tool_use_complete":
                    tool_calls = chunk.get("tool_calls", [])
                    tool_calls_in_this_round.extend(tool_calls)
                    yield chunk
                elif chunk_type == "complete":
                    full_response = chunk.get("content", full_response)
                    if full_response:
                        if not self.message_history or self.message_history[-1]["role"] != "assistant":
                            self.message_history.append({"role": "assistant", "content": full_response})
                        else:
                            self.message_history[-1]["content"] = full_response
                    yield chunk
                elif chunk_type == "error":
                    yield chunk
                    return

            # Execute tool calls if any
            if tool_calls_in_this_round and self.tool_executor:
                self.tool_execution_summary["total_tool_calls"] += len(tool_calls_in_this_round)

                tool_results = await self.tool_executor.execute_tool_calls(tool_calls_in_this_round)

                # Parse tool results
                for i, tool_call in enumerate(tool_calls_in_this_round):
                    tool_name = tool_call.get("name", "unknown")
                    tool_input = tool_call.get("input", {})
                    tool_result = tool_results[i] if i < len(tool_results) else {}

                    if tool_name == "bash":
                        command = tool_input.get("command", "unknown")
                        args = tool_input.get("args", [])
                        full_command = f"{command} {' '.join(args) if args else ''}".strip()
                        self.tool_execution_summary["executed_commands"].append(full_command)
                    elif tool_name == "read":
                        file_path = tool_input.get("file_path", "unknown")
                        if file_path not in self.tool_execution_summary["read_files"]:
                            self.tool_execution_summary["read_files"].append(file_path)

                    if tool_result.get("error"):
                        error_info = {
                            "tool": tool_name,
                            "error": tool_result.get("error"),
                            "file_path": tool_input.get("file_path") if tool_name in ["edit", "write", "read"] else None
                        }
                        if tool_result.get("permission_denied"):
                            error_info["permission_denied"] = True
                        if tool_result.get("permission_required"):
                            error_info["permission_required"] = True
                        self.tool_execution_summary["errors"].append(error_info)

                # Format tool results for API
                provider = model_config.get("provider", "anthropic")

                if provider == "anthropic":
                    for result in tool_results:
                        tool_id = result.get("tool_call_id", "unknown")
                        tool_name = result.get("tool_name", "unknown")
                        tool_result = result.get("result")
                        error = result.get("error")

                        if error:
                            tool_result_content = f"Error: {error}"
                        else:
                            tool_result_content = json.dumps(tool_result, indent=2) if tool_result else "null"

                        self.message_history.append({
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": tool_result_content
                            }]
                        })

                        yield {
                            "type": "tool_result",
                            "tool_call_id": tool_id,
                            "tool_name": tool_name,
                            "result": tool_result,
                            "error": error
                        }
                else:
                    # OpenAI format
                    for result in tool_results:
                        tool_id = result.get("tool_call_id", "unknown")
                        tool_name = result.get("tool_name", "unknown")
                        tool_result = result.get("result")
                        error = result.get("error")

                        if error:
                            tool_result_content = f"Error: {error}"
                        else:
                            tool_result_content = json.dumps(tool_result, indent=2) if tool_result else "null"

                        self.message_history.append({
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "name": tool_name,
                            "content": tool_result_content
                        })

                        yield {
                            "type": "tool_result",
                            "tool_call_id": tool_id,
                            "tool_name": tool_name,
                            "result": tool_result,
                            "error": error
                        }

                prompt = None  # Continue conversation
            else:
                # No tool calls, we're done
                if full_response:
                    # Save test results
                    await self._save_test_execution_results(task_id, full_response)
                    # Store test results for message responses
                    self._test_results = {
                        "content": full_response,
                        "task_id": task_id,
                        "agent_id": self.agent_id,
                        "timestamp": __import__("time").time()
                    }
                    yield {
                        "type": "complete",
                        "content": full_response,
                        "tool_execution_summary": self.tool_execution_summary.copy()
                    }
                break

        if iteration >= max_iterations:
            yield {
                "type": "error",
                "content": f"Maximum tool execution iterations ({max_iterations}) reached",
                "tool_execution_summary": self.tool_execution_summary.copy()
            }

    async def handle_message(self, message: "AgentMessage") -> None:
        """Handle incoming messages from other agents.

        Supports request-response pattern for agent-to-agent communication.
        Test agent can respond to requests for test results, test status, etc.

        Args:
            message: AgentMessage instance containing message details.
        """
        from manifest.agents.agent_message_bus import AgentMessage, MessageType
        from manifest.core.logger import get_logger

        logger = get_logger(__name__)

        if message.message_type == MessageType.REQUEST:
            # Handle request messages
            subject = message.subject.lower()
            content = message.content or {}

            if subject in ("test_results", "get_test_results", "test_status"):
                # Respond with test results
                response_content = {
                    "test_results": self._test_results or {},
                    "has_results": self._test_results is not None,
                    "agent_id": self.agent_id
                }
                if self.message_bus:
                    await self.message_bus.respond(
                        from_agent_id=self.agent_id,
                        correlation_id=(message.correlation_id or message.message_id),
                        content=response_content,
                        success=True
                    )

            elif subject in ("test_files", "get_test_files"):
                # Respond with test files created
                test_files = []
                if self._test_results:
                    # Extract test files from results (if available)
                    test_files = self._test_results.get("test_files", [])

                response_content = {
                    "test_files": test_files,
                    "agent_id": self.agent_id
                }
                if self.message_bus:
                    await self.message_bus.respond(
                        from_agent_id=self.agent_id,
                        correlation_id=(message.correlation_id or message.message_id),
                        content=response_content,
                        success=True
                    )

            else:
                # Unknown request - respond with error
                if self.message_bus:
                    await self.message_bus.respond(
                        from_agent_id=self.agent_id,
                        correlation_id=(message.correlation_id or message.message_id),
                        content={"error": f"Unknown request subject: {subject}"},
                        success=False
                    )

        elif message.message_type == MessageType.NOTIFICATION:
            # Handle notifications (one-way messages)
            logger.debug(f"Test agent {self.agent_id} received notification: {message.subject}")

    def _generate_tdd_test_prompt(self, task_id: str, context: Dict[str, Any]) -> str:
        """Generate a prompt for TDD test writing mode.

        Creates a prompt that instructs the agent to write tests first,
        before implementation. The prompt includes the planner's plan,
        task scope, and requirements for comprehensive test coverage.

        Args:
            task_id: ID of the task to write tests for.
            context: Tiered context including planner plan and task scope.

        Returns:
            Complete prompt string for TDD test writing.
        """
        # Get task information
        tasks = self.state_manager.get_task_checklist()
        task = next((t for t in tasks if t.get("id") == task_id), None)
        task_name = task.get("name", "") if task else ""
        task_description = task.get("description", "") if task else ""

        # Get planner plan from context or previous stages
        planner_plan = context.get("planner_plan", "")
        if not planner_plan:
            # Try to get from previous stages
            previous_stages = context.get("previous_stages", {})
            planner_output = previous_stages.get("planner", {})
            planner_plan = planner_output.get("output", planner_output.get("plan", ""))

        # Get task scope
        task_scope = context.get("task_scope", {})
        allowed_files = ", ".join(task_scope.get("allowed_files", []))
        allowed_components = ", ".join([c.get("name", c.get("id", "")) for c in task_scope.get("components", [])])

        return TDD_TEST_PROMPT_TEMPLATE.format(
            TEST_AGENT_IDENTITY=TEST_AGENT_IDENTITY,
            task_id=task_id,
            task_name=task_name,
            task_description=task_description,
            planner_plan=planner_plan or "No plan available",
            allowed_files=allowed_files or "All files",
            allowed_components=allowed_components or "All components"
        )

    def _generate_test_execution_prompt(self, task_id: str, context: Dict[str, Any]) -> str:
        """Generate a prompt for test execution mode.

        Creates a prompt that instructs the agent to run tests and report
        results. Includes implementation details, tool execution summary,
        and test file locations from previous stages.

        Args:
            task_id: ID of the task whose tests should be executed.
            context: Tiered context including implementation details and
                test files from TDD stage.

        Returns:
            Complete prompt string for test execution.
        """
        # Get task information
        tasks = self.state_manager.get_task_checklist()
        task = next((t for t in tasks if t.get("id") == task_id), None)
        task_name = task.get("name", "") if task else ""

        # Get implementation details from context
        coder_output = context.get("coder_output", "")
        files_modified = context.get("files_modified", [])

        # Get tool execution summary from task state (if available)
        tool_execution = task.get("tool_execution", {}) if task else {}
        tool_summary = tool_execution.get("last_summary", {})
        modified_files = tool_summary.get("modified_files", files_modified)
        executed_commands = tool_summary.get("executed_commands", [])
        tool_errors = tool_summary.get("errors", [])

        # Build implementation details with tool execution info
        implementation_details = f"""
Coder Output: {coder_output}
Files Modified: {', '.join(modified_files) if modified_files else 'None'}
"""

        if executed_commands:
            implementation_details += f"\nCommands Executed:\n"
            for cmd in executed_commands:
                implementation_details += f"  - {cmd}\n"

        if tool_errors:
            implementation_details += f"\nTool Execution Errors:\n"
            for error in tool_errors[:5]:  # Limit to first 5 errors
                implementation_details += f"  - {error.get('tool', 'unknown')}: {error.get('error', 'Unknown error')}\n"

        # Get test files from TDD stage
        previous_stages = context.get("previous_stages", {})
        tdd_test_output = previous_stages.get("tdd_test", {})
        test_files = tdd_test_output.get("test_files", [])
        test_files_str = "\n".join(test_files) if test_files else "Test files from TDD stage"

        # Add instruction to test modified files
        if modified_files:
            implementation_details += f"\n\nIMPORTANT: Focus testing on modified files:\n"
            for file_path in modified_files:
                implementation_details += f"  - {file_path}\n"

        return TEST_EXECUTION_PROMPT_TEMPLATE.format(
            TEST_AGENT_IDENTITY=TEST_AGENT_IDENTITY,
            task_id=task_id,
            task_name=task_name,
            implementation_details=implementation_details,
            test_files=test_files_str
        )

    async def _save_tdd_test_results(self, task_id: str, content: str):
        """Save TDD test writing results."""
        channel = f"squad-{task_id}-test"
        self.state_manager.add_chat_message(channel, "assistant", content)

        # Extract test information from content (simplified parsing)
        # In production, would parse structured output or use code extraction
        test_files = []
        test_cases = []

        # Simple extraction: look for test file paths
        import re
        # Look for file paths in content
        file_patterns = [
            r"test[_\w]*\.py",
            r"test[_\w]*\.js",
            r"test[_\w]*\.ts",
            r"tests?/[^\s]+",
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
            "status": "completed",
            "output": content,
            "test_files": list(set(test_files)),
            "test_cases": list(set(test_cases)),
            "test_skeleton": content,  # Full content as skeleton
            "test_plan": self._extract_test_plan(content),
            "tdd_mode": True
        }

        # Save to task
        tasks = self.state_manager.get_task_checklist()
        task = next((t for t in tasks if t.get("id") == task_id), None)
        if task:
            if "worker_squad_stages" not in task:
                task["worker_squad_stages"] = {}
            task["worker_squad_stages"]["tdd_test"] = test_results
            self.state_manager.set_task_checklist(tasks)

        await self.state_manager.save_state()

    def _extract_test_plan(self, content: str) -> str:
        """Extract test plan summary from content."""
        # Simple extraction - look for test plan sections
        import re
        plan_patterns = [
            r"test plan[:\s]+([^\n]+)",
            r"test cases[:\s]+([^\n]+)",
            r"## Test Plan\n([^\n]+)",
        ]
        for pattern in plan_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1) if match.groups() else match.group(0)
        return "Test plan extracted from test code"

    async def _save_test_execution_results(self, task_id: str, content: str) -> None:
        """Save test execution results to task state.

        Parses the test output to extract pass/fail counts and determine
        overall status. Saves the results to the task's worker_squad_stages
        for tracking and decision-making in the workflow.

        Args:
            task_id: ID of the task these test results belong to.
            content: Complete test execution output from the agent.
        """
        channel = f"squad-{task_id}-test"
        self.state_manager.add_chat_message(channel, "assistant", content)

        # Parse test results from content
        test_results = {
            "status": "completed",
            "output": content,
            "tests_passed": 0,
            "tests_failed": 0,
            "details": []
        }

        # Extract test results (simplified parsing)
        import re
        # Look for test result patterns
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

        # Save to task
        tasks = self.state_manager.get_task_checklist()
        task = next((t for t in tasks if t.get("id") == task_id), None)
        if task:
            if "worker_squad_stages" not in task:
                task["worker_squad_stages"] = {}
            task["worker_squad_stages"]["test"] = test_results
            self.state_manager.set_task_checklist(tasks)

        await self.state_manager.save_state()
