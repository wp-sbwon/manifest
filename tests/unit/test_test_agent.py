"""
Unit tests for TestAgent.

Tests test generation, execution, and result parsing.
"""
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from manifest.runtime.agent.agents.test_agent import TestAgent


@pytest.fixture
def mock_executor():
    """Create a mock executor."""
    executor = AsyncMock()
    executor.execute_agent = AsyncMock()
    return executor


@pytest.fixture
def mock_state_manager():
    """Create a mock state manager."""
    state = Mock()
    state.get_task_checklist = Mock(return_value=[])
    state.add_chat_message = Mock()
    state.save_state = AsyncMock()
    state.set_task_checklist = Mock()
    return state


@pytest.fixture
def test_agent(mock_executor, mock_state_manager):
    """Create a TestAgent instance."""
    return TestAgent(
        agent_id="test-1",
        executor=mock_executor,
        state_manager=mock_state_manager
    )


def test_test_agent_initialization(test_agent):
    """Test TestAgent initialization."""
    assert test_agent.agent_id == "test-1"
    assert test_agent.executor is not None
    assert test_agent.state_manager is not None
    assert test_agent.agent_type == "test"


# ========== TDL: Test Agent Tests ==========

@pytest.mark.asyncio
async def test_test_skeleton_generation(test_agent):
    """Test test skeleton generation in TDD mode."""
    task_id = "task-1"
    context = {
        "task_description": "Implement authentication",
        "planner_plan": "Plan: Create auth module",
        "task_scope": {
            "allowed_files": ["src/auth.py"],
            "components": [{"id": "auth", "name": "Auth Component"}]
        }
    }
    model_config = {"provider": "opencode"}

    test_skeleton = """
    Test skeleton:
    - test_login_success
    - test_login_failure
    - test_logout
    """

    async def mock_execute(*args, **kwargs):
        yield {"type": "chunk", "content": test_skeleton}
        yield {"type": "complete", "content": test_skeleton}

    test_agent.executor.execute_agent = mock_execute
    test_agent._save_tdd_test_results = AsyncMock()

    results = []
    async for chunk in test_agent.write_tdd_tests(task_id, context, model_config):
        results.append(chunk)

    assert len(results) >= 2
    complete_chunk = [r for r in results if r.get("type") == "complete"]
    assert len(complete_chunk) > 0
    assert "test" in complete_chunk[0].get("content", "").lower()


@pytest.mark.asyncio
async def test_test_skeleton_generation_with_test_files(test_agent):
    """Test test skeleton generation includes test file paths."""
    task_id = "task-1"
    context = {
        "task_description": "Implement feature",
        "planner_plan": "Plan steps",
        "task_scope": {"allowed_files": ["src/feature.py"]}
    }
    model_config = {"provider": "opencode"}

    test_output = """
    Test files created:
    - tests/test_feature.py

    Test cases:
    1. test_feature_creation
    2. test_feature_validation
    """

    async def mock_execute(*args, **kwargs):
        yield {"type": "complete", "content": test_output}

    test_agent.executor.execute_agent = mock_execute
    test_agent._save_tdd_test_results = AsyncMock()

    results = []
    async for chunk in test_agent.write_tdd_tests(task_id, context, model_config):
        results.append(chunk)

    # Verify test files were mentioned
    complete_chunk = [r for r in results if r.get("type") == "complete"]
    assert len(complete_chunk) > 0
    content = complete_chunk[0].get("content", "")
    assert "test" in content.lower() or "tests" in content.lower()


@pytest.mark.asyncio
async def test_test_execution(test_agent):
    """Test test execution after implementation."""
    task_id = "task-1"
    context = {
        "task_description": "Test implementation",
        "implementation_details": "Code implemented",
        "test_files": ["tests/test_feature.py"]
    }
    model_config = {"provider": "opencode"}

    execution_output = "Running tests...\n3 passed, 0 failed"

    async def mock_execute(*args, **kwargs):
        yield {"type": "chunk", "content": execution_output}
        yield {"type": "complete", "content": execution_output}

    test_agent.executor.execute_agent = mock_execute
    test_agent._save_test_execution_results = AsyncMock()

    results = []
    async for chunk in test_agent.run_tests(task_id, context, model_config):
        results.append(chunk)

    assert len(results) > 0
    complete_chunk = [r for r in results if r.get("type") == "complete"]
    assert len(complete_chunk) > 0


@pytest.mark.asyncio
async def test_test_execution_with_tool_calls(test_agent):
    """Test test execution with tool calls (bash commands)."""
    task_id = "task-1"
    context = {"test_files": ["tests/test_feature.py"]}
    model_config = {"provider": "anthropic"}

    # Mock tool executor
    mock_tool_executor = AsyncMock()
    mock_tool_executor.execute_tool_calls = AsyncMock(return_value=[
        {
            "tool_call_id": "call-1",
            "tool_name": "bash",
            "result": {"stdout": "3 passed", "stderr": "", "exit_code": 0}
        }
    ])
    test_agent.tool_executor = mock_tool_executor

    call_count = 0
    async def mock_execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            yield {"type": "tool_use_complete", "tool_calls": [
                {"id": "call-1", "name": "bash", "input": {"command": "pytest", "args": ["tests/test_feature.py"]}}
            ]}
        else:
            yield {"type": "complete", "content": "Tests executed: 3 passed"}

    test_agent.executor.execute_agent = mock_execute
    test_agent._save_test_execution_results = AsyncMock()

    results = []
    async for chunk in test_agent.run_tests(task_id, context, model_config):
        results.append(chunk)

    # Verify tool execution occurred
    assert mock_tool_executor.execute_tool_calls.called
    # Verify command was tracked
    assert len(test_agent.tool_execution_summary["executed_commands"]) > 0


@pytest.mark.asyncio
async def test_test_result_parsing(test_agent):
    """Test test result parsing from execution output."""
    task_id = "task-1"
    context = {"test_files": ["tests/test_feature.py"]}
    model_config = {"provider": "opencode"}

    test_results = """
    Test Results:
    ============
    tests/test_feature.py::test_feature_creation PASSED
    tests/test_feature.py::test_feature_validation PASSED
    tests/test_feature.py::test_feature_error FAILED

    ============
    2 passed, 1 failed
    """

    async def mock_execute(*args, **kwargs):
        yield {"type": "complete", "content": test_results}

    test_agent.executor.execute_agent = mock_execute
    test_agent._save_test_execution_results = AsyncMock()

    results = []
    async for chunk in test_agent.run_tests(task_id, context, model_config):
        results.append(chunk)

    # Verify results were parsed and saved
    test_agent._save_test_execution_results.assert_called_once()
    # Verify content contains test results
    complete_chunk = [r for r in results if r.get("type") == "complete"]
    assert len(complete_chunk) > 0
    assert "passed" in complete_chunk[0].get("content", "").lower() or \
           "failed" in complete_chunk[0].get("content", "").lower()


@pytest.mark.asyncio
async def test_test_result_parsing_with_coverage(test_agent):
    """Test test result parsing includes coverage information."""
    task_id = "task-1"
    context = {"test_files": ["tests/test_feature.py"]}
    model_config = {"provider": "opencode"}

    test_results_with_coverage = """
    Test Results:
    3 passed, 0 failed

    Coverage: 85%
    Lines: 100/120 covered
    """

    async def mock_execute(*args, **kwargs):
        yield {"type": "complete", "content": test_results_with_coverage}

    test_agent.executor.execute_agent = mock_execute
    test_agent._save_test_execution_results = AsyncMock()

    results = []
    async for chunk in test_agent.run_tests(task_id, context, model_config):
        results.append(chunk)

    # Verify coverage information is present
    complete_chunk = [r for r in results if r.get("type") == "complete"]
    assert len(complete_chunk) > 0
    content = complete_chunk[0].get("content", "")
    assert "coverage" in content.lower() or "covered" in content.lower()


@pytest.mark.asyncio
async def test_test_failure_analysis(test_agent):
    """Test test failure analysis."""
    task_id = "task-1"
    context = {
        "test_files": ["tests/test_feature.py"],
        "implementation_details": "Code implemented"
    }
    model_config = {"provider": "opencode"}

    failure_output = """
    Test Failures:
    ============
    tests/test_feature.py::test_feature_error FAILED
    AssertionError: Expected 'value' but got 'other'

    Recommendations:
    - Check feature implementation
    - Verify input validation
    """

    async def mock_execute(*args, **kwargs):
        yield {"type": "complete", "content": failure_output}

    test_agent.executor.execute_agent = mock_execute
    test_agent._save_test_execution_results = AsyncMock()

    results = []
    async for chunk in test_agent.run_tests(task_id, context, model_config):
        results.append(chunk)

    # Verify failure analysis is present
    complete_chunk = [r for r in results if r.get("type") == "complete"]
    assert len(complete_chunk) > 0
    content = complete_chunk[0].get("content", "")
    assert "failed" in content.lower() or "error" in content.lower() or \
           "assertion" in content.lower()


@pytest.mark.asyncio
async def test_test_failure_analysis_with_recommendations(test_agent):
    """Test test failure analysis includes recommendations."""
    task_id = "task-1"
    context = {"test_files": ["tests/test_feature.py"]}
    model_config = {"provider": "opencode"}

    failure_with_recommendations = """
    Test Failures:
    1 test failed

    Error: AssertionError in test_feature_validation

    Recommendations:
    1. Fix input validation logic
    2. Add error handling
    3. Check edge cases
    """

    async def mock_execute(*args, **kwargs):
        yield {"type": "complete", "content": failure_with_recommendations}

    test_agent.executor.execute_agent = mock_execute
    test_agent._save_test_execution_results = AsyncMock()

    results = []
    async for chunk in test_agent.run_tests(task_id, context, model_config):
        results.append(chunk)

    # Verify recommendations are present
    complete_chunk = [r for r in results if r.get("type") == "complete"]
    assert len(complete_chunk) > 0
    content = complete_chunk[0].get("content", "")
    assert "recommendation" in content.lower() or "fix" in content.lower()


@pytest.mark.asyncio
async def test_save_tdd_test_results(test_agent):
    """Test saving TDD test results to task state."""
    task_id = "task-1"
    content = """
    Test files:
    - tests/test_auth.py

    Test cases:
    1. test_login
    2. test_logout
    """

    # Mock state manager methods
    test_agent.state_manager.get_task_checklist = Mock(return_value=[{"id": task_id}])
    test_agent.state_manager.set_task_checklist = Mock()
    test_agent.state_manager.save_state = AsyncMock()

    await test_agent._save_tdd_test_results(task_id, content)

    # Verify task was updated with test information
    test_agent.state_manager.set_task_checklist.assert_called_once()
    test_agent.state_manager.save_state.assert_called_once()


@pytest.mark.asyncio
async def test_save_test_execution_results(test_agent):
    """Test saving test execution results to task state."""
    task_id = "task-1"
    content = """
    Test Results:
    3 passed, 1 failed

    Failed: test_feature_error
    Error: AssertionError
    """

    # Mock state manager
    test_agent.state_manager.get_task_checklist = Mock(return_value=[{"id": task_id}])
    test_agent.state_manager.set_task_checklist = Mock()
    test_agent.state_manager.save_state = AsyncMock()

    await test_agent._save_test_execution_results(task_id, content)

    # Verify results were saved
    test_agent.state_manager.set_task_checklist.assert_called_once()
    test_agent.state_manager.save_state.assert_called_once()


def test_generate_tdd_test_prompt(test_agent):
    """Test TDD test prompt generation."""
    task_id = "task-1"
    context = {
        "task_description": "Implement feature",
        "planner_plan": "Plan steps",
        "task_scope": {
            "allowed_files": ["src/feature.py"],
            "components": [{"id": "feature", "name": "Feature Component"}]
        }
    }

    prompt = test_agent._generate_tdd_test_prompt(task_id, context)

    assert isinstance(prompt, str)
    assert task_id in prompt
    assert "TDD" in prompt or "test" in prompt.lower()
    assert "plan" in prompt.lower() or "planner" in prompt.lower()


def test_generate_test_execution_prompt(test_agent):
    """Test test execution prompt generation."""
    task_id = "task-1"
    context = {
        "task_description": "Test implementation",
        "implementation_details": "Code implemented",
        "test_files": ["tests/test_feature.py"]
    }

    prompt = test_agent._generate_test_execution_prompt(task_id, context)

    assert isinstance(prompt, str)
    assert task_id in prompt
    assert "test" in prompt.lower() or "execution" in prompt.lower()


def test_extract_test_plan(test_agent):
    """Test extraction of test plan from content."""
    content = """
    Test Plan:
    1. Test feature creation
    2. Test feature validation
    3. Test error handling
    """

    test_plan = test_agent._extract_test_plan(content)

    assert isinstance(test_plan, str)
    assert len(test_plan) > 0
    assert "test" in test_plan.lower() or "plan" in test_plan.lower()


@pytest.mark.asyncio
async def test_message_history_accumulation(test_agent):
    """Test that message history accumulates across chunks."""
    async def mock_execute(*args, **kwargs):
        yield {"type": "chunk", "content": "Test 1 "}
        yield {"type": "chunk", "content": "Test 2 "}
        yield {"type": "chunk", "content": "Test 3"}
        yield {"type": "complete", "content": "Test 1 Test 2 Test 3"}

    test_agent.executor.execute_agent = mock_execute
    test_agent._save_tdd_test_results = AsyncMock()

    async for chunk in test_agent.write_tdd_tests("task-1", {}, {"provider": "opencode"}):
        pass

    # Verify message history has accumulated content
    assert len(test_agent.message_history) > 0
    last_message = test_agent.message_history[-1]
    assert "Test 1" in last_message["content"]
    assert "Test 2" in last_message["content"]
    assert "Test 3" in last_message["content"]
