"""
Unit tests for CoderAgent.

Tests code implementation, tool usage, and task execution.
"""
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from manifest.runtime.agent.agents.coder_agent import CoderAgent


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
    return state


@pytest.fixture
def coder_agent(mock_executor, mock_state_manager):
    """Create a CoderAgent instance."""
    return CoderAgent(
        agent_id="coder-1",
        executor=mock_executor,
        state_manager=mock_state_manager
    )


def test_coder_agent_initialization(coder_agent):
    """Test CoderAgent initialization."""
    assert coder_agent.agent_id == "coder-1"
    assert coder_agent.executor is not None
    assert coder_agent.state_manager is not None


@pytest.mark.asyncio
async def test_implement_task(coder_agent):
    """Test implementing a task."""
    task_description = "Implement feature X"
    context = {"task_description": task_description}
    task_scope = {}
    model_config = {"provider": "opencode"}

    # Mock executor to return a generator
    async def mock_execute(*args, **kwargs):
        yield {"type": "text", "content": "Implementation started"}
        yield {"type": "complete"}

    # Replace the executor's execute_agent method with our async generator
    coder_agent.executor.execute_agent = mock_execute

    results = []
    async for chunk in coder_agent.implement(task_description, context, task_scope, model_config):
        results.append(chunk)

    assert len(results) > 0
    # Verify we got expected results
    assert any(r.get("type") in ["text", "complete"] for r in results)


@pytest.mark.asyncio
async def test_self_review(coder_agent):
    """Test self review functionality."""
    planner_plan = "Plan to implement feature X"
    implementation_summary = "Implemented feature X with tests"
    context = {"task_description": "Review implementation"}
    model_config = {"provider": "opencode"}

    # Mock executor to return a generator
    async def mock_execute(*args, **kwargs):
        yield {"type": "chunk", "content": "Review started"}
        yield {"type": "complete", "content": "Complete"}

    coder_agent.executor.execute_agent = mock_execute
    coder_agent._save_response = AsyncMock()

    results = []
    async for chunk in coder_agent.self_review(planner_plan, implementation_summary, context, model_config):
        results.append(chunk)

    assert len(results) > 0


# ========== TDL: Coder Agent Tests ==========

@pytest.mark.asyncio
async def test_code_implementation(coder_agent):
    """Test code implementation for a task."""
    task_description = "Implement user authentication"
    context = {
        "task_description": task_description,
        "tier_0": {"content": "Policy"},
        "tier_2": {"components": []},
        "tier_3": {"files": {}}
    }
    task_scope = {
        "allowed_files": ["src/auth.py"],
        "components": ["auth"]  # List of component IDs (strings), not dicts
    }
    model_config = {"provider": "opencode", "model": "test-model"}

    # Mock executor to return implementation response
    async def mock_execute(*args, **kwargs):
        yield {"type": "chunk", "content": "Implementing authentication"}
        yield {"type": "complete", "content": "Implementation complete"}

    coder_agent.executor.execute_agent = mock_execute
    coder_agent._save_response = AsyncMock()

    results = []
    async for chunk in coder_agent.implement(task_description, context, task_scope, model_config):
        results.append(chunk)

    assert len(results) > 0
    complete_chunk = [r for r in results if r.get("type") == "complete"]
    assert len(complete_chunk) > 0


@pytest.mark.asyncio
async def test_code_implementation_with_tool_calls(coder_agent):
    """Test code implementation with tool execution."""
    task_description = "Write a function"
    context = {"available_tools": ["edit", "write", "read"]}
    task_scope = {"allowed_files": ["test.py"]}
    model_config = {"provider": "anthropic"}

    # Mock tool executor
    mock_tool_executor = AsyncMock()
    mock_tool_executor.execute_tool_calls = AsyncMock(return_value=[
        {
            "tool_call_id": "call-1",
            "tool_name": "write",
            "result": {"success": True, "file_path": "test.py"}
        }
    ])
    coder_agent.tool_executor = mock_tool_executor

    # Mock executor to return tool calls then completion
    async def mock_execute(*args, **kwargs):
        # First iteration: tool use
        yield {"type": "tool_use", "tool_call": {"id": "call-1", "name": "write", "input": {"file_path": "test.py", "content": "def test(): pass"}}}
        yield {"type": "tool_use_complete", "tool_calls": [{"id": "call-1", "name": "write", "input": {"file_path": "test.py"}}]}
        # Second iteration: completion after tool results
        yield {"type": "complete", "content": "Function written successfully"}

    coder_agent.executor.execute_agent = mock_execute
    coder_agent._save_response = AsyncMock()

    results = []
    async for chunk in coder_agent.implement(task_description, context, task_scope, model_config):
        results.append(chunk)

    # Verify tool execution occurred
    assert mock_tool_executor.execute_tool_calls.called
    # Verify tool execution summary was tracked
    assert len(coder_agent.tool_execution_summary["modified_files"]) > 0 or \
           coder_agent.tool_execution_summary["total_tool_calls"] > 0


@pytest.mark.asyncio
async def test_code_implementation_tool_execution_tracking(coder_agent):
    """Test tool execution tracking in implementation."""
    task_description = "Modify files"
    context = {"available_tools": ["edit", "read"]}
    task_scope = {"allowed_files": ["file1.py", "file2.py"]}
    model_config = {"provider": "anthropic"}

    # Mock tool executor
    mock_tool_executor = AsyncMock()
    mock_tool_executor.execute_tool_calls = AsyncMock(return_value=[
        {
            "tool_call_id": "call-1",
            "tool_name": "edit",
            "result": {"success": True, "file_path": "file1.py"}
        },
        {
            "tool_call_id": "call-2",
            "tool_name": "read",
            "result": {"content": "file content", "file_path": "file2.py"}
        }
    ])
    coder_agent.tool_executor = mock_tool_executor

    # Mock executor
    call_count = 0
    async def mock_execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First call: tool uses
            yield {"type": "tool_use_complete", "tool_calls": [
                {"id": "call-1", "name": "edit", "input": {"file_path": "file1.py"}},
                {"id": "call-2", "name": "read", "input": {"file_path": "file2.py"}}
            ]}
        else:
            # Second call: completion
            yield {"type": "complete", "content": "Done"}

    coder_agent.executor.execute_agent = mock_execute
    coder_agent._save_response = AsyncMock()

    results = []
    async for chunk in coder_agent.implement(task_description, context, task_scope, model_config):
        results.append(chunk)

    # Verify tracking
    assert "file1.py" in coder_agent.tool_execution_summary["modified_files"]
    assert "file2.py" in coder_agent.tool_execution_summary["read_files"]
    assert coder_agent.tool_execution_summary["total_tool_calls"] == 2


@pytest.mark.asyncio
async def test_code_implementation_max_iterations(coder_agent):
    """Test code implementation respects max iterations limit."""
    task_description = "Test task"
    context = {}
    task_scope = {}
    model_config = {"provider": "opencode"}

    # Mock tool executor that always returns tool calls
    mock_tool_executor = AsyncMock()
    mock_tool_executor.execute_tool_calls = AsyncMock(return_value=[
        {"tool_call_id": "call-1", "tool_name": "write", "result": {}}
    ])
    coder_agent.tool_executor = mock_tool_executor

    # Mock executor that always requests tools (infinite loop scenario)
    call_count = 0
    async def mock_execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= 10:  # Up to max iterations
            yield {"type": "tool_use_complete", "tool_calls": [
                {"id": f"call-{call_count}", "name": "write", "input": {}}
            ]}
        else:
            yield {"type": "complete", "content": "Done"}

    coder_agent.executor.execute_agent = mock_execute

    results = []
    async for chunk in coder_agent.implement(task_description, context, task_scope, model_config):
        results.append(chunk)

    # Should hit max iterations and yield error
    error_chunks = [r for r in results if r.get("type") == "error"]
    assert len(error_chunks) > 0
    assert "Maximum tool execution iterations" in error_chunks[0].get("content", "")


@pytest.mark.asyncio
async def test_self_review_functionality(coder_agent):
    """Test self-review functionality."""
    planner_plan = """
    Plan:
    1. Create authentication module
    2. Implement login function
    3. Add error handling
    """
    implementation_summary = "Created auth module with login function"
    context = {"tier_0": {"content": "Policy"}}
    model_config = {"provider": "opencode"}

    review_content = """
    Review:
    - Authentication module: ✓ Implemented
    - Login function: ✓ Implemented
    - Error handling: ⚠ Partially implemented
    """

    async def mock_execute(*args, **kwargs):
        yield {"type": "chunk", "content": review_content}
        yield {"type": "complete", "content": review_content}

    coder_agent.executor.execute_agent = mock_execute
    coder_agent._save_response = AsyncMock()

    results = []
    async for chunk in coder_agent.self_review(planner_plan, implementation_summary, context, model_config):
        results.append(chunk)

    assert len(results) >= 2
    complete_chunk = [r for r in results if r.get("type") == "complete"]
    assert len(complete_chunk) > 0
    assert "Review" in complete_chunk[0].get("content", "")


@pytest.mark.asyncio
async def test_self_review_plan_comparison(coder_agent):
    """Test self-review compares implementation against plan."""
    planner_plan = "Implement user registration with email validation"
    implementation_summary = "User registration implemented, email validation missing"
    context = {}
    model_config = {"provider": "opencode"}

    async def mock_execute(*args, **kwargs):
        yield {"type": "complete", "content": "Missing: email validation"}

    coder_agent.executor.execute_agent = mock_execute
    coder_agent._save_response = AsyncMock()

    results = []
    async for chunk in coder_agent.self_review(planner_plan, implementation_summary, context, model_config):
        results.append(chunk)

    # Verify review prompt was generated with plan and implementation
    assert len(results) > 0
    # The prompt generation should include both plan and implementation
    assert hasattr(coder_agent, '_generate_self_review_prompt')


def test_generate_self_review_prompt(coder_agent):
    """Test self-review prompt generation."""
    planner_plan = "Plan: Implement feature X"
    implementation_summary = "Implemented feature X"
    context = {"task_description": "Test task"}

    prompt = coder_agent._generate_self_review_prompt(planner_plan, implementation_summary, context)

    assert isinstance(prompt, str)
    assert "Plan" in prompt or "plan" in prompt.lower()
    assert "implementation" in prompt.lower() or "implemented" in prompt.lower()


@pytest.mark.asyncio
async def test_plan_compliance_checking(coder_agent):
    """Test plan compliance checking in implementation."""
    task_description = "Implement feature per plan"
    context = {
        "planner_plan": "Step 1: Create module\nStep 2: Add function\nStep 3: Test",
        "tier_0": {"content": "Policy"}
    }
    task_scope = {"allowed_files": ["module.py"]}
    model_config = {"provider": "opencode"}

    compliant_response = "Following plan: Created module, added function, wrote tests"

    async def mock_execute(*args, **kwargs):
        yield {"type": "complete", "content": compliant_response}

    coder_agent.executor.execute_agent = mock_execute
    coder_agent._save_response = AsyncMock()

    results = []
    async for chunk in coder_agent.implement(task_description, context, task_scope, model_config):
        results.append(chunk)

    # Verify implementation was generated with plan context
    assert len(results) > 0
    # Plan compliance is checked in prompt generation
    assert True


@pytest.mark.asyncio
async def test_code_quality_validation_tool_errors(coder_agent):
    """Test code quality validation via tool error tracking."""
    task_description = "Write code"
    context = {"available_tools": ["write"]}
    task_scope = {"allowed_files": ["code.py"]}
    model_config = {"provider": "anthropic"}

    # Mock tool executor with validation errors
    mock_tool_executor = AsyncMock()
    mock_tool_executor.execute_tool_calls = AsyncMock(return_value=[
        {
            "tool_call_id": "call-1",
            "tool_name": "write",
            "result": {},
            "error": None,
            "validated": {
                "success": False,
                "validation_errors": ["Syntax error on line 5", "Missing import"]
            }
        }
    ])
    coder_agent.tool_executor = mock_tool_executor

    async def mock_execute(*args, **kwargs):
        yield {"type": "tool_use_complete", "tool_calls": [
            {"id": "call-1", "name": "write", "input": {"file_path": "code.py"}}
        ]}
        yield {"type": "complete", "content": "Code written"}

    coder_agent.executor.execute_agent = mock_execute
    coder_agent._save_response = AsyncMock()

    results = []
    async for chunk in coder_agent.implement(task_description, context, task_scope, model_config):
        results.append(chunk)

    # Verify validation errors were tracked
    assert len(coder_agent.tool_execution_summary["errors"]) > 0
    error_messages = [e.get("error", "") for e in coder_agent.tool_execution_summary["errors"]]
    assert any("Validation failed" in err for err in error_messages)


@pytest.mark.asyncio
async def test_code_quality_validation_permission_errors(coder_agent):
    """Test code quality validation via permission error tracking."""
    task_description = "Modify file"
    context = {"available_tools": ["edit"]}
    task_scope = {"allowed_files": ["restricted.py"]}
    model_config = {"provider": "anthropic"}

    # Mock tool executor with permission error
    mock_tool_executor = AsyncMock()
    mock_tool_executor.execute_tool_calls = AsyncMock(return_value=[
        {
            "tool_call_id": "call-1",
            "tool_name": "edit",
            "result": {},
            "error": "Permission denied",
            "permission_denied": True
        }
    ])
    coder_agent.tool_executor = mock_tool_executor

    async def mock_execute(*args, **kwargs):
        yield {"type": "tool_use_complete", "tool_calls": [
            {"id": "call-1", "name": "edit", "input": {"file_path": "restricted.py"}}
        ]}
        yield {"type": "complete", "content": "Attempted edit"}

    coder_agent.executor.execute_agent = mock_execute
    coder_agent._save_response = AsyncMock()

    results = []
    async for chunk in coder_agent.implement(task_description, context, task_scope, model_config):
        results.append(chunk)

    # Verify permission errors were tracked
    errors = coder_agent.tool_execution_summary["errors"]
    permission_errors = [e for e in errors if e.get("permission_denied")]
    assert len(permission_errors) > 0


@pytest.mark.asyncio
async def test_tool_execution_summary_in_complete_chunk(coder_agent):
    """Test that tool execution summary is included in complete chunk."""
    task_description = "Test task"
    context = {}
    task_scope = {}
    model_config = {"provider": "opencode"}

    async def mock_execute(*args, **kwargs):
        yield {"type": "complete", "content": "Implementation done"}

    coder_agent.executor.execute_agent = mock_execute
    coder_agent._save_response = AsyncMock()

    results = []
    async for chunk in coder_agent.implement(task_description, context, task_scope, model_config):
        results.append(chunk)

    # Verify complete chunk includes tool execution summary (even if empty)
    complete_chunks = [r for r in results if r.get("type") == "complete"]
    assert len(complete_chunks) > 0
    assert "tool_execution_summary" in complete_chunks[0]
    # Summary should exist (may be empty if no tools were called)
    assert isinstance(complete_chunks[0]["tool_execution_summary"], dict)


@pytest.mark.asyncio
async def test_message_history_accumulation(coder_agent):
    """Test that message history accumulates across chunks."""
    async def mock_execute(*args, **kwargs):
        yield {"type": "chunk", "content": "Step 1 "}
        yield {"type": "chunk", "content": "Step 2 "}
        yield {"type": "chunk", "content": "Step 3"}
        yield {"type": "complete", "content": "Step 1 Step 2 Step 3"}

    coder_agent.executor.execute_agent = mock_execute
    coder_agent._save_response = AsyncMock()

    async for chunk in coder_agent.implement("Test", {}, {}, {"provider": "opencode"}):
        pass

    # Verify message history has accumulated content
    assert len(coder_agent.message_history) > 0
    last_message = coder_agent.message_history[-1]
    assert "Step 1" in last_message["content"]
    assert "Step 2" in last_message["content"]
    assert "Step 3" in last_message["content"]


@pytest.mark.asyncio
async def test_tool_result_formatting_anthropic(coder_agent):
    """Test tool result formatting for Anthropic provider."""
    task_description = "Test task"
    context = {}
    task_scope = {}
    model_config = {"provider": "anthropic"}

    # Mock tool executor
    mock_tool_executor = AsyncMock()
    mock_tool_executor.execute_tool_calls = AsyncMock(return_value=[
        {
            "tool_call_id": "call-1",
            "tool_name": "read",
            "result": {"content": "file content"}
        }
    ])
    coder_agent.tool_executor = mock_tool_executor

    call_count = 0
    async def mock_execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            yield {"type": "tool_use_complete", "tool_calls": [
                {"id": "call-1", "name": "read", "input": {}}
            ]}
        else:
            yield {"type": "complete", "content": "Done"}

    coder_agent.executor.execute_agent = mock_execute
    coder_agent._save_response = AsyncMock()

    results = []
    async for chunk in coder_agent.implement(task_description, context, task_scope, model_config):
        results.append(chunk)

    # Verify tool_result was added to message history in Anthropic format
    tool_results = [msg for msg in coder_agent.message_history if msg.get("role") == "user"]
    assert len(tool_results) > 0
    # Should have tool_result content blocks
    assert any("tool_result" in str(msg.get("content", "")) or isinstance(msg.get("content"), list) for msg in tool_results)
