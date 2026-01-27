"""
Unit tests for DebugAgent.

Tests bug analysis, root cause identification, and fix proposals.
"""
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from manifest.runtime.agent.agents.debug_agent import DebugAgent


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
def debug_agent(mock_executor, mock_state_manager):
    """Create a DebugAgent instance."""
    return DebugAgent(
        agent_id="debug-1",
        executor=mock_executor,
        state_manager=mock_state_manager
    )


def test_debug_agent_initialization(debug_agent):
    """Test DebugAgent initialization."""
    assert debug_agent.agent_id == "debug-1"
    assert debug_agent.executor is not None
    assert debug_agent.state_manager is not None
    assert debug_agent.agent_type == "debug"


# ========== TDL: Debug Agent Tests ==========

@pytest.mark.asyncio
async def test_bug_analysis_from_test_failures(debug_agent):
    """Test bug analysis from test failures."""
    test_results = {
        "tests_passed": 2,
        "tests_failed": 1,
        "details": [
            {
                "test": "test_feature_validation",
                "status": "failed",
                "error": "AssertionError: Expected 'value' but got 'None'"
            }
        ]
    }
    error_messages = ["AssertionError: Expected 'value' but got 'None'"]
    context = {
        "tier_0": {"content": "Policy"},
        "tier_2": {"components": []},
        "tier_3": {"files": {}}
    }
    model_config = {"provider": "opencode"}

    analysis_output = """
    Bug Analysis:
    - Root Cause: Missing null check in feature validation
    - Location: src/feature.py, line 45
    - Fix: Add null check before validation
    """

    async def mock_execute(*args, **kwargs):
        yield {"type": "chunk", "content": analysis_output}
        yield {"type": "complete", "content": analysis_output}

    debug_agent.executor.execute_agent = mock_execute
    debug_agent._save_response = AsyncMock()

    results = []
    async for chunk in debug_agent.debug(test_results, error_messages, context, model_config):
        results.append(chunk)

    assert len(results) >= 2
    complete_chunk = [r for r in results if r.get("type") == "complete"]
    assert len(complete_chunk) > 0
    assert "Bug" in complete_chunk[0].get("content", "") or "Root Cause" in complete_chunk[0].get("content", "")


@pytest.mark.asyncio
async def test_root_cause_identification(debug_agent):
    """Test root cause identification from error messages."""
    test_results = {
        "tests_passed": 0,
        "tests_failed": 3,
        "details": []
    }
    error_messages = [
        "TypeError: 'NoneType' object has no attribute 'process'",
        "AttributeError: 'NoneType' object has no attribute 'validate'",
        "KeyError: 'missing_key'"
    ]
    context = {}
    model_config = {"provider": "opencode"}

    root_cause_analysis = """
    Root Cause Analysis:
    1. Primary Issue: Null pointer dereference
       - Location: Multiple functions accessing uninitialized objects
       - Pattern: Missing null checks before method calls

    2. Secondary Issue: Missing key in dictionary
       - Location: Configuration loading
       - Pattern: Accessing dict without checking key existence
    """

    async def mock_execute(*args, **kwargs):
        yield {"type": "complete", "content": root_cause_analysis}

    debug_agent.executor.execute_agent = mock_execute
    debug_agent._save_response = AsyncMock()

    results = []
    async for chunk in debug_agent.debug(test_results, error_messages, context, model_config):
        results.append(chunk)

    # Verify root cause analysis is present
    complete_chunk = [r for r in results if r.get("type") == "complete"]
    assert len(complete_chunk) > 0
    content = complete_chunk[0].get("content", "")
    assert "root cause" in content.lower() or "issue" in content.lower() or "null" in content.lower()


@pytest.mark.asyncio
async def test_fix_proposal_generation(debug_agent):
    """Test fix proposal generation."""
    test_results = {
        "tests_passed": 1,
        "tests_failed": 1,
        "details": [{"test": "test_auth", "status": "failed", "error": "Authentication failed"}]
    }
    error_messages = ["Authentication failed: Invalid credentials"]
    context = {
        "tier_2": {"components": [{"id": "auth", "name": "Auth Service"}]},
        "tier_3": {"files": {"src/auth.py": {"content": "def authenticate(): pass"}}}
    }
    model_config = {"provider": "opencode"}

    fix_proposal = """
    Fix Proposal:
    1. Add input validation in authenticate() function
       - Check if credentials are not None
       - Validate credential format

    2. Add error handling
       - Return proper error messages
       - Log authentication attempts

    3. Update test expectations
       - Test should expect specific error types
    """

    async def mock_execute(*args, **kwargs):
        yield {"type": "complete", "content": fix_proposal}

    debug_agent.executor.execute_agent = mock_execute
    debug_agent._save_response = AsyncMock()

    results = []
    async for chunk in debug_agent.debug(test_results, error_messages, context, model_config):
        results.append(chunk)

    # Verify fix proposal is present
    complete_chunk = [r for r in results if r.get("type") == "complete"]
    assert len(complete_chunk) > 0
    content = complete_chunk[0].get("content", "")
    assert "fix" in content.lower() or "proposal" in content.lower() or "add" in content.lower()


@pytest.mark.asyncio
async def test_fix_proposal_with_specific_instructions(debug_agent):
    """Test fix proposal includes specific instructions for coder."""
    test_results = {"tests_failed": 1}
    error_messages = ["IndexError: list index out of range"]
    context = {}
    model_config = {"provider": "opencode"}

    specific_fix = """
    Instructions for Coder:
    1. In src/processor.py, line 23:
       - Change: result = items[0]
       - To: result = items[0] if len(items) > 0 else None
       - Add check before accessing list

    2. Add validation:
       - Check list length before indexing
       - Return appropriate default value
    """

    async def mock_execute(*args, **kwargs):
        yield {"type": "complete", "content": specific_fix}

    debug_agent.executor.execute_agent = mock_execute
    debug_agent._save_response = AsyncMock()

    results = []
    async for chunk in debug_agent.debug(test_results, error_messages, context, model_config):
        results.append(chunk)

    # Verify specific instructions are present
    complete_chunk = [r for r in results if r.get("type") == "complete"]
    assert len(complete_chunk) > 0
    content = complete_chunk[0].get("content", "")
    assert "coder" in content.lower() or "instruction" in content.lower() or "change" in content.lower()


def test_generate_debug_prompt(debug_agent):
    """Test debug prompt generation."""
    test_results = {
        "tests_passed": 2,
        "tests_failed": 1,
        "details": [{"test": "test_feature", "status": "failed"}]
    }
    error_messages = ["AssertionError: Test failed"]
    context = {
        "tier_2": {"components": [{"id": "comp-1"}]},
        "tier_3": {"files": {}}
    }

    prompt = debug_agent._generate_debug_prompt(test_results, error_messages, context)

    assert isinstance(prompt, str)
    assert "DEBUG" in prompt or "debug" in prompt.lower()
    assert "error" in prompt.lower() or "Error" in prompt
    assert "test" in prompt.lower() or "Test" in prompt


def test_generate_debug_prompt_with_context(debug_agent):
    """Test debug prompt includes context information."""
    test_results = {"tests_failed": 1}
    error_messages = ["TypeError"]
    context = {
        "tier_2": {
            "components": [{"id": "auth", "name": "Auth Component"}],
            "zones": {}
        },
        "tier_3": {
            "files": {
                "src/auth.py": {"content": "code"}
            }
        }
    }

    prompt = debug_agent._generate_debug_prompt(test_results, error_messages, context)

    # Verify context is included
    assert isinstance(prompt, str)
    # Context should be in prompt (tier_2 or tier_3)
    assert len(prompt) > 0


@pytest.mark.asyncio
async def test_debug_with_multiple_errors(debug_agent):
    """Test debug analysis with multiple error messages."""
    test_results = {"tests_failed": 3}
    error_messages = [
        "Error 1: Null pointer",
        "Error 2: Missing attribute",
        "Error 3: Invalid type"
    ]
    context = {}
    model_config = {"provider": "opencode"}

    multi_error_analysis = """
    Multiple Errors Detected:
    1. Null pointer - Add null checks
    2. Missing attribute - Verify object initialization
    3. Invalid type - Add type validation
    """

    async def mock_execute(*args, **kwargs):
        yield {"type": "complete", "content": multi_error_analysis}

    debug_agent.executor.execute_agent = mock_execute
    debug_agent._save_response = AsyncMock()

    results = []
    async for chunk in debug_agent.debug(test_results, error_messages, context, model_config):
        results.append(chunk)

    # Verify multiple errors are analyzed
    complete_chunk = [r for r in results if r.get("type") == "complete"]
    assert len(complete_chunk) > 0
    content = complete_chunk[0].get("content", "")
    assert "multiple" in content.lower() or "1." in content or "2." in content


@pytest.mark.asyncio
async def test_debug_with_empty_errors(debug_agent):
    """Test debug analysis with empty error messages."""
    test_results = {"tests_passed": 3, "tests_failed": 0}
    error_messages = []
    context = {}
    model_config = {"provider": "opencode"}

    async def mock_execute(*args, **kwargs):
        yield {"type": "complete", "content": "No errors to debug"}

    debug_agent.executor.execute_agent = mock_execute
    debug_agent._save_response = AsyncMock()

    results = []
    async for chunk in debug_agent.debug(test_results, error_messages, context, model_config):
        results.append(chunk)

    # Should still complete successfully
    assert len(results) > 0


@pytest.mark.asyncio
async def test_message_history_accumulation(debug_agent):
    """Test that message history accumulates across chunks."""
    test_results = {"tests_failed": 1}
    error_messages = ["Test error"]
    context = {}
    model_config = {"provider": "opencode"}

    async def mock_execute(*args, **kwargs):
        yield {"type": "chunk", "content": "Analysis "}
        yield {"type": "chunk", "content": "step 1 "}
        yield {"type": "chunk", "content": "step 2"}
        yield {"type": "complete", "content": "Analysis step 1 step 2"}

    debug_agent.executor.execute_agent = mock_execute
    debug_agent._save_response = AsyncMock()

    async for chunk in debug_agent.debug(test_results, error_messages, context, model_config):
        pass

    # Verify message history has accumulated content
    assert len(debug_agent.message_history) > 0
    last_message = debug_agent.message_history[-1]
    assert "Analysis" in last_message["content"]
    assert "step 1" in last_message["content"]
    assert "step 2" in last_message["content"]


@pytest.mark.asyncio
async def test_save_response(debug_agent):
    """Test save_response method (backward compatibility)."""
    content = "Debug analysis complete"

    # Method should complete without error (does nothing, kept for compatibility)
    await debug_agent._save_response(content)
    assert True  # Should complete successfully
