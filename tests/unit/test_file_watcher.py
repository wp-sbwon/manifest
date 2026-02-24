from pathlib import Path

import pytest

from manifest.view.file_watcher import ViewFileWatcher


@pytest.mark.unit
def test_file_watcher_is_watched_design_file() -> None:
    calls: list = []

    def on_change(paths):
        calls.append(paths)

    watcher = ViewFileWatcher(Path("/tmp/.manifest"), on_change)
    assert watcher._is_watched(watcher.manifest_dir / "blueprint_design.json") is True


@pytest.mark.unit
def test_file_watcher_is_watched_conflicts_dir() -> None:
    def on_change(paths):
        pass

    watcher = ViewFileWatcher(Path("/tmp/.manifest"), on_change)
    assert watcher._is_watched(watcher.manifest_dir / "conflicts" / "report.json") is True


@pytest.mark.unit
def test_file_watcher_not_watched_outside() -> None:
    def on_change(paths):
        pass

    watcher = ViewFileWatcher(Path("/tmp/.manifest"), on_change)
    assert watcher._is_watched(Path("/tmp/other.json")) is False
