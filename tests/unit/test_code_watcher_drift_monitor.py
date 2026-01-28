"""
Unit tests for CodeWatcher and DriftMonitor.
"""
import json
import pytest
from pathlib import Path

from manifest.audit.monitoring.code_watcher import CodeWatcher
from manifest.audit.monitoring.drift_monitor import DriftMonitor


@pytest.fixture
def project_with_py(tmp_path):
    """Project root with a Python file."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "foo.py").write_text("def hello(): pass\nclass Bar: pass\n")
    return tmp_path


@pytest.fixture
def manifest_dir(tmp_path):
    """Empty .manifest directory."""
    d = tmp_path / ".manifest"
    d.mkdir()
    return d


def test_code_watcher_force_extract(project_with_py, manifest_dir):
    """CodeWatcher.force_extract() writes blueprint_code.json."""
    watcher = CodeWatcher(project_root=project_with_py, manifest_dir=manifest_dir)
    ok = watcher.force_extract()
    assert ok is True
    blueprint_file = manifest_dir / "blueprint_code.json"
    assert blueprint_file.exists()
    with open(blueprint_file, "r") as f:
        data = json.load(f)
    assert "components" in data or "version" in data


def test_code_watcher_watch_and_extract_updates_on_change(project_with_py, manifest_dir):
    """CodeWatcher.watch_and_extract() updates when code changed."""
    watcher = CodeWatcher(project_root=project_with_py, manifest_dir=manifest_dir)
    ok1 = watcher.watch_and_extract()
    assert ok1 is True
    ok2 = watcher.watch_and_extract()
    assert ok2 is False  # no change
    (project_with_py / "src" / "foo.py").write_text("def hello(): pass\nclass Bar: pass\ndef new(): pass\n")
    ok3 = watcher.watch_and_extract()
    assert ok3 is True


def test_drift_monitor_check_and_update(project_with_py, manifest_dir):
    """DriftMonitor.check_and_update() drives CodeWatcher."""
    monitor = DriftMonitor(project_root=project_with_py, manifest_dir=manifest_dir)
    updated = monitor.check_and_update()
    assert updated is True
    assert (manifest_dir / "blueprint_code.json").exists()


def test_drift_monitor_start_stop(manifest_dir):
    """DriftMonitor start/stop sets is_running."""
    monitor = DriftMonitor(manifest_dir=manifest_dir)
    assert monitor.is_running is False
    monitor.start_monitoring(interval_seconds=5.0)
    assert monitor.is_running is True
    monitor.stop_monitoring()
    assert monitor.is_running is False
