"""
Unit tests for SprintManager.

Tests sprint loading, saving, and test management.
"""
import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from manifest.core.sprint_manager import SprintManager
from manifest.core.state_manager import StateManager


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing."""
    return tmp_path


@pytest.fixture
def state_manager(temp_dir):
    """Create a StateManager instance."""
    return StateManager(manifest_dir=temp_dir)


@pytest.fixture
def sprint_manager(state_manager):
    """Create a SprintManager instance."""
    return SprintManager(state_manager=state_manager)


def test_sprint_manager_initialization(sprint_manager, state_manager):
    """Test SprintManager initialization."""
    assert sprint_manager.state_manager == state_manager
    assert sprint_manager is not None


def test_load_sprint(sprint_manager):
    """Test loading a sprint."""
    sprint_id = "sprint-1"
    sprint_data = {
        "id": sprint_id,
        "name": "Test Sprint",
        "description": "Test description"
    }
    
    # Save sprint first
    sprint_manager.save_sprint(sprint_data)
    
    # Load it
    loaded = sprint_manager.load_sprint(sprint_id)
    assert loaded is not None
    assert loaded.get("id") == sprint_id
    assert loaded.get("name") == "Test Sprint"


def test_load_sprint_not_found(sprint_manager):
    """Test loading non-existent sprint."""
    sprint = sprint_manager.load_sprint("nonexistent")
    assert sprint is None


def test_save_sprint(sprint_manager):
    """Test saving a sprint."""
    sprint_data = {
        "id": "sprint-1",
        "name": "Test Sprint",
        "description": "Test description"
    }
    
    result = sprint_manager.save_sprint(sprint_data)
    assert result is True
    
    # Verify it was saved
    loaded = sprint_manager.load_sprint("sprint-1")
    assert loaded is not None
    assert loaded.get("name") == "Test Sprint"


def test_update_sprint_tests(sprint_manager):
    """Test updating sprint tests."""
    sprint_id = "sprint-1"
    sprint_data = {
        "id": sprint_id,
        "name": "Test Sprint"
    }
    sprint_manager.save_sprint(sprint_data)
    
    result = sprint_manager.update_sprint_tests(
        sprint_id=sprint_id,
        test_type="integration",
        status="planned",
        test_files=["test1.py", "test2.py"]
    )
    
    assert result is True
    
    # Verify test data was saved
    sprint = sprint_manager.load_sprint(sprint_id)
    assert sprint is not None
    assert "integration_tests" in sprint
    assert sprint["integration_tests"]["status"] == "planned"


def test_get_sprint_tests(sprint_manager):
    """Test getting sprint tests."""
    sprint_id = "sprint-1"
    sprint_data = {
        "id": sprint_id,
        "name": "Test Sprint",
        "integration_tests": {
            "status": "planned",
            "test_files": ["test1.py"]
        }
    }
    sprint_manager.save_sprint(sprint_data)
    
    tests = sprint_manager.get_sprint_tests(sprint_id, "integration")
    assert tests is not None
    assert tests["status"] == "planned"


def test_update_sprint_e2e_test_execution_results(sprint_manager):
    """Test updating E2E test execution results."""
    sprint_id = "sprint-1"
    sprint_data = {
        "id": sprint_id,
        "name": "Test Sprint"
    }
    sprint_manager.save_sprint(sprint_data)
    
    result = sprint_manager.update_sprint_e2e_test_execution_results(
        sprint_id=sprint_id,
        task_id="task-1",
        content="Test execution output"
    )
    
    assert result is True
    
    # Verify results were saved
    sprint = sprint_manager.load_sprint(sprint_id)
    assert sprint is not None
    assert "e2e_tests" in sprint
    assert "execution_results" in sprint["e2e_tests"]
    assert len(sprint["e2e_tests"]["execution_results"]) == 1
