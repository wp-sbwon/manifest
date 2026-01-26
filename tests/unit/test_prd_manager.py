"""
Unit tests for PRDManager.

Tests PRD loading, saving, and management operations.
"""
import pytest
import json
from unittest.mock import Mock, patch
from pathlib import Path
from manifest.core.prd_manager import PRDManager
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
def prd_manager(state_manager):
    """Create a PRDManager instance."""
    return PRDManager(state_manager=state_manager)


def test_prd_manager_initialization(prd_manager, state_manager):
    """Test PRDManager initialization."""
    assert prd_manager.state_manager == state_manager
    assert prd_manager is not None


def test_get_prd_file(prd_manager, temp_dir):
    """Test getting PRD file path."""
    prd_file = prd_manager.get_prd_file()
    assert prd_file == temp_dir / "prd.json"


def test_save_prd(prd_manager):
    """Test saving PRD data."""
    prd_data = {
        "title": "Test PRD",
        "requirements": ["Req 1", "Req 2"]
    }
    
    result = prd_manager.save_prd(prd_data)
    assert result is True
    
    # Verify file was created
    prd_file = prd_manager.get_prd_file()
    assert prd_file.exists()


def test_save_prd_async(prd_manager):
    """Test saving PRD data asynchronously."""
    import asyncio
    
    prd_data = {
        "title": "Test PRD",
        "requirements": ["Req 1"]
    }
    
    async def run_test():
        result = await prd_manager.save_prd_async(prd_data)
        assert result is True
    
    asyncio.run(run_test())


def test_load_prd(prd_manager):
    """Test loading PRD data."""
    # Save first
    prd_data = {
        "title": "Test PRD",
        "requirements": ["Req 1"]
    }
    prd_manager.save_prd(prd_data)
    
    # Load
    loaded = prd_manager.load_prd()
    assert loaded is not None
    assert loaded.get("title") == "Test PRD"


def test_load_prd_not_found(prd_manager):
    """Test loading PRD when file doesn't exist."""
    loaded = prd_manager.load_prd()
    # Should return None or empty dict
    assert loaded is None or isinstance(loaded, dict)


def test_load_prd_async(prd_manager):
    """Test loading PRD data asynchronously."""
    import asyncio
    
    # Save first
    prd_data = {"title": "Test PRD"}
    prd_manager.save_prd(prd_data)
    
    async def run_test():
        loaded = await prd_manager.load_prd_async()
        assert loaded is not None
    
    asyncio.run(run_test())


def test_save_prd_error_handling(prd_manager):
    """Test error handling when saving PRD fails."""
    # Make directory read-only to cause error (if possible)
    # Or mock file write to raise error
    with patch('builtins.open', side_effect=PermissionError("Permission denied")):
        result = prd_manager.save_prd({"title": "Test"})
        # Should handle error gracefully
        assert result is False


def test_load_prd_invalid_json(prd_manager):
    """Test loading PRD with invalid JSON."""
    prd_file = prd_manager.get_prd_file()
    prd_file.parent.mkdir(parents=True, exist_ok=True)
    prd_file.write_text("invalid json {")
    
    loaded = prd_manager.load_prd()
    # Should handle invalid JSON gracefully
    assert loaded is None or isinstance(loaded, dict)
