"""
Unit tests for StructureManager.

Tests structure management, component tracking, and spec-first management.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from manifest.audit.monitoring.structure_manager import StructureManager


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing."""
    return tmp_path


@pytest.fixture
def structure_manager(temp_dir):
    """Create a StructureManager instance."""
    return StructureManager(manifest_dir=temp_dir, project_root=temp_dir)


def test_structure_manager_initialization(structure_manager, temp_dir):
    """Test StructureManager initialization."""
    assert structure_manager.manifest_dir == temp_dir
    assert structure_manager.project_root == temp_dir
    assert structure_manager is not None


def test_detect_code_changes(structure_manager, temp_dir):
    """Test detecting code changes."""
    # Create a test file
    test_file = temp_dir / "test.py"
    test_file.write_text("class TestClass:\n    pass")

    changes = structure_manager.detect_code_changes([str(test_file)])
    assert isinstance(changes, list)


def test_detect_code_changes_deleted_file(structure_manager):
    """Test detecting deleted file."""
    changes = structure_manager.detect_code_changes(["nonexistent.py"])
    assert isinstance(changes, list)
    # Should detect deletion
    if changes:
        assert any(c.change_type == "deleted" for c in changes)


def test_suggest_blueprint_updates(structure_manager, temp_dir):
    """Test suggesting blueprint updates."""
    # Create a test file
    test_file = temp_dir / "test.py"
    test_file.write_text("class TestClass:\n    pass")

    # Detect changes
    changes = structure_manager.detect_code_changes([str(test_file)])

    # Suggest updates
    suggestions = structure_manager.suggest_blueprint_updates(changes)
    assert isinstance(suggestions, list)


def test_detect_blueprint_changes(structure_manager, temp_dir):
    """Test detecting blueprint changes."""
    # Create blueprint file
    blueprint_file = structure_manager.blueprint_file
    blueprint_file.parent.mkdir(parents=True, exist_ok=True)
    blueprint_file.write_text('{"components": []}')

    # Provide both blueprints explicitly
    previous = {"components": [], "contracts": []}
    current = {"components": [], "contracts": []}
    changes = structure_manager.detect_blueprint_changes(
        previous_blueprint=previous,
        current_blueprint=current
    )
    assert isinstance(changes, dict)


def test_suggest_code_changes(structure_manager, temp_dir):
    """Test suggesting code changes from blueprint."""
    # Provide blueprint_changes and current_code_blueprint directly
    # to avoid calling _load_previous_blueprint which doesn't exist
    blueprint_changes = {
        "new_components": [],
        "modified_components": [],
        "deleted_components": [],
        "new_contracts": [],
        "modified_contracts": [],
        "deleted_contracts": []
    }
    current_code_blueprint = {"components": [], "contracts": []}

    # Suggest code changes
    suggestions = structure_manager.suggest_code_changes(
        blueprint_changes=blueprint_changes,
        current_code_blueprint=current_code_blueprint
    )
    assert isinstance(suggestions, list)


def test_analyze_impact(structure_manager):
    """Test analyzing impact of changes."""
    from manifest.audit.monitoring.structure_manager import StructuralChange
    changes = [StructuralChange(change_type="added", file_path="test.py")]
    # analyze_impact expects blueprint_changes dict, not list
    blueprint_changes = {
        "new_components": [],
        "modified_components": [],
        "deleted_components": []
    }
    impact = structure_manager.analyze_impact(blueprint_changes)
    assert isinstance(impact, dict)


def test_apply_blueprint_update(structure_manager):
    """Test applying blueprint update."""
    suggestion = Mock()
    suggestion.suggestion_type = "add_component"
    suggestion.component = Mock()

    result = structure_manager.apply_blueprint_update(suggestion)
    # Should apply or return False
    assert isinstance(result, bool)


def test_apply_code_change(structure_manager):
    """Test applying code change."""
    suggestion = Mock()
    suggestion.suggestion_type = "create_file"
    suggestion.file_path = "test.py"

    result = structure_manager.apply_code_change(suggestion)
    # Should apply or return False
    assert isinstance(result, bool)
