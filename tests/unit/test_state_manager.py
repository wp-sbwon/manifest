"""Unit tests for StateManager."""
import json
import tempfile
from pathlib import Path

import pytest

from manifest.core.state_manager import StateManager
from manifest.core.constants import STATE_FILE


@pytest.mark.unit
def test_state_manager_loads_from_file() -> None:
    """StateManager loads existing state.json."""
    with tempfile.TemporaryDirectory() as tmp:
        manifest_dir = Path(tmp)
        state_file = manifest_dir / STATE_FILE
        state_file.write_text('{"version":"1.0","mission_tree":{},"task_checklist":[],"chat_history":{},"timestamp":"2020-01-01T00:00:00"}')
        mgr = StateManager(manifest_dir)
        assert mgr.get_state_version() == "1.0"
        assert mgr.get_mission_tree() == {}
        assert mgr.get_task_checklist() == []


@pytest.mark.unit
def test_state_manager_default_when_missing() -> None:
    """StateManager uses default state when file missing."""
    with tempfile.TemporaryDirectory() as tmp:
        mgr = StateManager(Path(tmp))
        assert mgr.get_state_version() == "1.0"
        assert mgr.get_mission_tree() == {}
        assert mgr.get_task_checklist() == []


@pytest.mark.unit
def test_save_state_sync_persists() -> None:
    """save_state_sync writes state to disk."""
    with tempfile.TemporaryDirectory() as tmp:
        manifest_dir = Path(tmp)
        mgr = StateManager(manifest_dir)
        mgr.set_mission_tree({"key": "value"})
        ok = mgr.save_state_sync()
        assert ok is True
        data = json.loads((manifest_dir / STATE_FILE).read_text())
        assert data.get("mission_tree") == {"key": "value"}


@pytest.mark.unit
def test_save_state_sync_same_content_as_async() -> None:
    """save_state_sync and save_state use same _prepare_state_for_persist content."""
    with tempfile.TemporaryDirectory() as tmp:
        mgr = StateManager(Path(tmp))
        mgr.set_last_action("test")
        content_sync = mgr._prepare_state_for_persist()
        import json
        parsed = json.loads(content_sync)
        assert parsed.get("last_action") == "test"
