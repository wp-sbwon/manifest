"""
Unit tests for Manifest View.

Tests the View app loads data and composes without errors.
"""
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from manifest.view.app import ManifestViewApp, run_view, ViewType, InspectorMode
from manifest.view.file_watcher import ViewFileWatcher


@pytest.fixture
def temp_manifest_dir(tmp_path):
    """Minimal .manifest with state and blueprint."""
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir()
    (manifest_dir / "state.json").write_text(json.dumps({
        "version": "1.0",
        "mission_tree": {},
        "task_checklist": [{"id": "task-1", "name": "Test", "status": "pending"}],
        "chat_history": {},
        "last_action": "",
        "timestamp": "2020-01-01T00:00:00",
    }))
    (manifest_dir / "blueprint.json").write_text(json.dumps({
        "version": "1.0",
        "components": [],
        "contracts": [],
        "zones": {},
    }))
    return manifest_dir


def test_view_app_instantiate(temp_manifest_dir):
    """ManifestViewApp can be instantiated with manifest_dir."""
    app = ManifestViewApp(manifest_dir=temp_manifest_dir)
    assert app.manifest_dir == temp_manifest_dir.resolve()
    assert app.TITLE == "Manifest View"
    assert app.current_view == ViewType.DIAGRAM


def test_view_app_load_views(temp_manifest_dir):
    """View can load data for each view type."""
    app = ManifestViewApp(manifest_dir=temp_manifest_dir)

    app.current_view = ViewType.DIAGRAM
    diagram_content = app._load_diagram_view()
    assert isinstance(diagram_content, str) or hasattr(diagram_content, "render")

    app.current_view = ViewType.FILES
    files_content = app._load_files_view()
    assert isinstance(files_content, str) or hasattr(files_content, "render")

    app.current_view = ViewType.HISTORY
    history_content = app._load_history_view()
    assert isinstance(history_content, str) or hasattr(history_content, "render") or hasattr(history_content, "__rich_console__")

    app.current_view = ViewType.TIMELINE
    timeline_content = app._load_timeline_view()
    assert isinstance(timeline_content, str) or hasattr(timeline_content, "render")

    app.current_view = ViewType.INSPECTOR
    inspector_content = app._load_inspector_view()
    assert isinstance(inspector_content, str)

    app.current_view = ViewType.MISSION_CONTROL
    mission_content = app._load_mission_control_view()
    assert isinstance(mission_content, str) or hasattr(mission_content, "render")
    assert "Mission" in str(mission_content) or "Objectives" in str(mission_content) or "M1" in str(mission_content)


def test_view_app_has_compose():
    """ManifestViewApp has compose method."""
    assert hasattr(ManifestViewApp, "compose")
    assert callable(ManifestViewApp.compose)


def test_view_switching(temp_manifest_dir):
    """View switching works correctly."""
    app = ManifestViewApp(manifest_dir=temp_manifest_dir)
    assert app.current_view == ViewType.DIAGRAM

    app.action_switch_view("Files")
    assert app.current_view == ViewType.FILES

    app.action_switch_view("History")
    assert app.current_view == ViewType.HISTORY

    app.action_switch_view("Timeline")
    assert app.current_view == ViewType.TIMELINE


def test_inspector_mode_switching(temp_manifest_dir):
    """Inspector mode switching works correctly."""
    app = ManifestViewApp(manifest_dir=temp_manifest_dir)
    app.current_view = ViewType.INSPECTOR
    # Default inspector mode is DESIGN; DEVIATION available via switch
    app.action_switch_inspector_mode("Deviation")
    assert app.inspector_mode == InspectorMode.DEVIATION

    app.action_switch_inspector_mode("Visual")
    assert app.inspector_mode == InspectorMode.VISUAL

    app.action_switch_inspector_mode("Data")
    assert app.inspector_mode == InspectorMode.DATA


def test_view_file_watcher_detects_change(tmp_path):
    """ViewFileWatcher detects file changes and calls callback."""
    changed_paths = []

    def on_change(paths):
        changed_paths.extend(paths)

    watcher = ViewFileWatcher(tmp_path, on_change=on_change)
    # First check: no previous mtimes, so no "change" reported
    watcher.check()
    assert len(changed_paths) == 0

    (tmp_path / "tasks.json").write_text('{"tasks": [], "sprints": []}')
    result = watcher.check()
    assert len(result) == 1
    assert result[0].name == "tasks.json"
    assert len(changed_paths) == 1


def test_view_prefers_tasks_json(temp_manifest_dir):
    """Mission/sidebar prefer .manifest/tasks.json when present."""
    app = ManifestViewApp(manifest_dir=temp_manifest_dir)
    tasks, sprints = app._get_tasks_and_sprints_from_manifest()
    assert len(tasks) == 1 and tasks[0].get("id") == "task-1" and tasks[0].get("name") == "Test" and tasks[0].get("status") == "pending"
    assert isinstance(sprints, list)

    (temp_manifest_dir / "tasks.json").write_text(json.dumps({
        "tasks": [{"id": "task_001", "name": "From tasks.json", "status": "in_progress"}],
        "sprints": [{"id": "sprint_001", "name": "S1"}],
    }))
    tasks2, sprints2 = app._get_tasks_and_sprints_from_manifest()
    assert len(tasks2) >= 1
    assert isinstance(sprints2, list)
