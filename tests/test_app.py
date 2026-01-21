"""
Integration tests for app.py
"""
import pytest
import json
import tempfile
import shutil
from pathlib import Path
from textual.app import App


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def setup_manifest_dir(temp_dir):
    """Set up a manifest directory with test data."""
    manifest_dir = temp_dir / ".manifest"
    manifest_dir.mkdir()
    
    # Create test intent.json
    intent_data = {
        "version": "1.0",
        "sprint": "Test Sprint",
        "features": [
            {
                "name": "Test Feature",
                "status": "wip",
                "reqs": [
                    {"id": "REQ-01", "desc": "Test Requirement", "state": "done"}
                ]
            }
        ]
    }
    (manifest_dir / "intent.json").write_text(json.dumps(intent_data))
    
    # Create test blueprint.json
    blueprint_data = {
        "version": "1.0",
        "zones": {
            "client": [],
            "server": [],
            "data": []
        },
        "components": [
            {
                "id": "comp1",
                "name": "TestComponent",
                "type": "class",
                "zone": "client",
                "status": "active"
            }
        ],
        "contracts": []
    }
    (manifest_dir / "blueprint.json").write_text(json.dumps(blueprint_data))
    
    return manifest_dir


def test_intent_data_loading(setup_manifest_dir):
    """Test that intent.json can be loaded."""
    intent_file = setup_manifest_dir / "intent.json"
    assert intent_file.exists()
    
    data = json.loads(intent_file.read_text())
    assert data["version"] == "1.0"
    assert len(data["features"]) == 1
    assert data["features"][0]["name"] == "Test Feature"


def test_blueprint_data_loading(setup_manifest_dir):
    """Test that blueprint.json can be loaded."""
    blueprint_file = setup_manifest_dir / "blueprint.json"
    assert blueprint_file.exists()
    
    data = json.loads(blueprint_file.read_text())
    assert data["version"] == "1.0"
    assert len(data["components"]) == 1
    assert data["components"][0]["name"] == "TestComponent"


def test_state_persistence_workflow(setup_manifest_dir):
    """Test state persistence workflow."""
    from manifest.core.state_manager import StateManager
    
    state_manager = StateManager(manifest_dir=setup_manifest_dir)
    
    # Set state
    state_manager.set_mission_tree({"mission1": {"status": "active"}})
    state_manager.set_task_checklist([
        {"id": "task1", "name": "Test Task", "status": "pending"}
    ])
    state_manager.add_chat_message("main", "user", "Test message")
    
    # Save
    assert state_manager.save_state_sync() is True
    
    # Load in new manager
    new_manager = StateManager(manifest_dir=setup_manifest_dir)
    state = new_manager.get_state()
    
    assert state["mission_tree"]["mission1"]["status"] == "active"
    assert len(state["task_checklist"]) == 1
    assert len(state["chat_history"]["main"]) == 1


def test_drift_audit_integration(setup_manifest_dir, temp_dir):
    """Test drift audit integration."""
    from manifest.audit.drift_auditor import DriftAuditor
    
    # Create a test Python file
    test_file = temp_dir / "test_component.py"
    test_file.write_text("""
class TestComponent:
    def method1(self):
        pass
""")
    
    # Set up blueprint
    blueprint_file = setup_manifest_dir / "blueprint.json"
    blueprint_data = {
        "version": "1.0",
        "components": [
            {
                "id": "comp1",
                "name": "TestComponent",
                "type": "class",
                "methods": ["method1", "method2"]  # method2 missing in code
            }
        ]
    }
    blueprint_file.write_text(json.dumps(blueprint_data))
    
    # Run audit
    auditor = DriftAuditor(manifest_dir=setup_manifest_dir)
    conflicts = auditor.audit_project(temp_dir)
    
    # Should find missing method
    assert len(conflicts) > 0
    assert any("method2" in c.message for c in conflicts)