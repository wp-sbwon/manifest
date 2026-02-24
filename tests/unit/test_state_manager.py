import json
import tempfile
from pathlib import Path

import pytest

from manifest.core.state_manager import StateManager
from manifest.core.constants import STATE_FILE


@pytest.mark.unit
def test_state_manager_loads_from_file() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        manifest_dir = Path(tmp)
        state_file = manifest_dir / STATE_FILE
        state_file.write_text(
            '{"version":"1.0","chat_history":{},"health_metrics":null,"timestamp":"2020-01-01T00:00:00"}'
        )
        mgr = StateManager(manifest_dir)
        assert mgr.get_state_version() == "1.0"
        assert mgr.get_chat_history() == []
        assert mgr.get_health_metrics() is None


@pytest.mark.unit
def test_state_manager_default_when_missing() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        mgr = StateManager(Path(tmp))
        assert mgr.get_state_version() == "1.0"
        assert mgr.get_chat_history() == []
        assert mgr.get_health_metrics() is None


@pytest.mark.unit
def test_save_state_sync_persists() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        manifest_dir = Path(tmp)
        mgr = StateManager(manifest_dir)
        mgr.set_health_metrics({"code_quality": "ok"})
        ok = mgr.save_state_sync()
        assert ok is True
        data = json.loads((manifest_dir / STATE_FILE).read_text())
        assert data.get("health_metrics") == {"code_quality": "ok"}


@pytest.mark.unit
def test_save_state_sync_same_content_as_async() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        mgr = StateManager(Path(tmp))
        mgr.add_chat_message("main", "user", "hi")
        content = mgr._prepare_state_for_persist()
        parsed = json.loads(content)
        assert parsed.get("chat_history", {}).get("main")
        assert parsed["chat_history"]["main"][0]["content"] == "hi"
