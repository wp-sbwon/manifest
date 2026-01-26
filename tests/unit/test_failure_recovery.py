"""
Unit tests for FailureRecoveryManager.

Tests failure detection, recovery strategies, and error handling.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from manifest.agents.failure_recovery import FailureRecoveryManager


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = Mock()
    coordinator.start_worker_agent = AsyncMock(return_value=True)
    coordinator.start_worker_agent_and_wait = AsyncMock(return_value={"success": True})
    coordinator.state_manager = Mock()
    coordinator.state_manager.get_task_checklist = Mock(return_value=[])
    return coordinator


@pytest.fixture
def recovery_manager(mock_coordinator):
    """Create a FailureRecoveryManager instance."""
    return FailureRecoveryManager(coordinator=mock_coordinator)


def test_recovery_manager_initialization(recovery_manager, mock_coordinator):
    """Test FailureRecoveryManager initialization."""
    assert recovery_manager.coordinator == mock_coordinator
    assert recovery_manager is not None


@pytest.mark.asyncio
async def test_analyze_failure(recovery_manager):
    """Test analyzing a failure."""
    # FailureRecoveryManager doesn't have analyze_failure, it's on FailureAnalyzer
    from manifest.agents.failure_recovery import FailureAnalyzer
    
    analysis = FailureAnalyzer.analyze_failure(
        error="Test error",
        agent_type="coder",
        stage="coder"
    )
    assert isinstance(analysis, dict)
    assert "failure_type" in analysis


@pytest.mark.asyncio
async def test_suggest_recovery_strategy(recovery_manager):
    """Test suggesting recovery strategy."""
    # FailureRecoveryManager doesn't have suggest_recovery_strategy
    # The analyze_failure already returns recovery_strategies
    from manifest.agents.failure_recovery import FailureAnalyzer
    
    analysis = FailureAnalyzer.analyze_failure(
        error="Test error",
        agent_type="coder",
        stage="coder"
    )
    strategies = analysis.get("recovery_strategies", [])
    assert len(strategies) > 0


@pytest.mark.asyncio
async def test_execute_recovery(recovery_manager):
    """Test executing recovery."""
    # FailureRecoveryManager uses attempt_recovery with specific parameters
    # Mock the coordinator's start_worker_agent_and_wait to return a proper result
    recovery_manager.coordinator.start_worker_agent_and_wait = AsyncMock(return_value={"success": True})
    
    failure_result = {
        "error": "Test error",
        "output": ""
    }
    
    # Patch asyncio.sleep to avoid waiting
    with patch('asyncio.sleep', new_callable=AsyncMock):
        result = await recovery_manager.attempt_recovery(
            task_id="task-1",
            stage="coder",
            agent_type="coder",
            failure_result=failure_result
        )
        assert isinstance(result, dict)
        assert "recovered" in result
