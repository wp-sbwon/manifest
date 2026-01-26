"""
Unit tests for ContextProvider.

Tests context generation, tier management, and context retrieval.
"""
import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from manifest.agents.context_provider import ContextProvider


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing."""
    return tmp_path


@pytest.fixture
def mock_task_scoper():
    """Create a mock task scoper."""
    scoper = Mock()
    scoper.get_task_scope = Mock(return_value={})
    return scoper


@pytest.fixture
def context_provider(temp_dir, mock_task_scoper):
    """Create a ContextProvider instance."""
    return ContextProvider(manifest_dir=temp_dir, task_scoper=mock_task_scoper)


def test_context_provider_initialization(context_provider, temp_dir):
    """Test ContextProvider initialization."""
    assert context_provider.manifest_dir == temp_dir
    assert context_provider.task_scoper is not None
    assert context_provider is not None


def test_get_orchestrator_context(context_provider):
    """Test getting orchestrator context."""
    context = context_provider.get_orchestrator_context()
    assert isinstance(context, dict)


def test_get_worker_context(context_provider):
    """Test getting worker context."""
    # Mock task_scoper.get_task_context to return a dict
    context_provider.task_scoper.get_task_context = Mock(return_value={
        "components": [],
        "files": [],
        "allowed_modifications": [],
        "requirements": []
    })
    context = context_provider.get_worker_context("task-1", "coder")
    assert isinstance(context, dict)


def test_get_tier_0_context(context_provider):
    """Test getting Tier 0 context."""
    # ContextProvider uses _load_tier_0, not _get_tier_0_context
    context = context_provider._load_tier_0()
    assert isinstance(context, dict)


def test_get_tier_1_context(context_provider):
    """Test getting Tier 1 context."""
    # ContextProvider uses _load_tier_1, not _get_tier_1_context
    context = context_provider._load_tier_1()
    assert isinstance(context, dict)


def test_get_tier_2_context(context_provider):
    """Test getting Tier 2 context."""
    # ContextProvider uses _load_tier_2_scoped, not _get_tier_2_context
    task_context = {"components": [], "files": []}
    context = context_provider._load_tier_2_scoped(task_context)
    assert isinstance(context, dict)


def test_get_tier_3_context(context_provider):
    """Test getting Tier 3 context."""
    # ContextProvider uses _load_tier_3_scoped, not _get_tier_3_context
    task_context = {"components": [], "files": []}
    context = context_provider._load_tier_3_scoped(task_context)
    assert isinstance(context, dict)
