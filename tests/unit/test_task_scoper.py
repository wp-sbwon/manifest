"""
Unit tests for task_scoper.py
"""
import pytest
import json
from pathlib import Path
from manifest.agents.task_scoper import TaskScoper


@pytest.fixture
def temp_manifest_dir(tmp_path):
    """Create temporary manifest directory with test data."""
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir()

    # Create blueprint.json
    blueprint = {
        "version": "1.0",
        "zones": {
            "client": [],
            "server": [
                {
                    "id": "comp-1",
                    "name": "AuthService",
                    "files": ["src/auth/service.py", "src/auth/models.py"]
                }
            ],
            "data": []
        },
        "components": [
            {
                "id": "comp-1",
                "name": "AuthService",
                "files": ["src/auth/service.py", "src/auth/models.py"],
                "directory": "src/auth"
            }
        ],
        "contracts": []
    }
    with open(manifest_dir / "blueprint.json", "w") as f:
        json.dump(blueprint, f)

    # Create intent.json
    intent = {
        "version": "1.0",
        "sprint": "Test Sprint",
        "features": [
            {
                "id": "feature-1",
                "name": "Auth Feature",
                "tasks": ["task-1"],
                "reqs": [
                    {"id": "REQ-1", "desc": "Login functionality"}
                ]
            }
        ]
    }
    with open(manifest_dir / "intent.json", "w") as f:
        json.dump(intent, f)

    return manifest_dir


def test_task_scoper_init(temp_manifest_dir):
    """Test TaskScoper initialization."""
    scoper = TaskScoper(temp_manifest_dir)
    assert scoper.manifest_dir == temp_manifest_dir
    assert scoper._blueprint_data is not None
    assert scoper._intent_data is not None


def test_get_task_context(temp_manifest_dir):
    """Test getting task context."""
    scoper = TaskScoper(temp_manifest_dir)
    context = scoper.get_task_context("task-1")

    assert "components" in context
    assert "files" in context
    assert "requirements" in context
    assert "allowed_modifications" in context


def test_validate_task_scope(temp_manifest_dir):
    """Test task scope validation."""
    scoper = TaskScoper(temp_manifest_dir)

    # File in scope
    assert scoper.validate_task_scope("task-1", "src/auth/service.py") == True

    # File not in scope
    assert scoper.validate_task_scope("task-1", "src/other/file.py") == False


def test_get_task_scope_summary(temp_manifest_dir):
    """Test getting task scope summary."""
    scoper = TaskScoper(temp_manifest_dir)
    summary = scoper.get_task_scope_summary("task-1")

    assert "task_id" in summary
    assert "component_count" in summary
    assert "file_count" in summary
    assert summary["task_id"] == "task-1"
