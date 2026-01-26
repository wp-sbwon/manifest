"""
Unit tests for FileWatcher.

Tests file system monitoring, change detection, and event handling.
"""
import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from manifest.audit.monitoring.file_watcher import FileWatcher


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing."""
    return tmp_path


@pytest.fixture
def file_watcher(temp_dir):
    """Create a FileWatcher instance."""
    return FileWatcher(project_root=temp_dir)


def test_file_watcher_initialization(file_watcher, temp_dir):
    """Test FileWatcher initialization."""
    assert file_watcher.project_root == temp_dir
    assert file_watcher is not None


def test_is_git_repo(file_watcher, temp_dir):
    """Test checking if directory is a git repo."""
    # Should handle non-git directory gracefully
    is_repo = file_watcher.is_git_repo()
    assert isinstance(is_repo, bool)


def test_get_changed_files(file_watcher):
    """Test getting changed files."""
    changed_files = file_watcher.get_changed_files()
    assert isinstance(changed_files, list)


def test_get_changed_files_with_since(file_watcher):
    """Test getting changed files since a time."""
    from datetime import datetime, timedelta
    since = datetime.now() - timedelta(hours=1)
    changed_files = file_watcher.get_changed_files(since=since)
    assert isinstance(changed_files, list)


def test_get_file_diff(file_watcher, temp_dir):
    """Test getting file diff."""
    test_file = temp_dir / "test.py"
    test_file.write_text("print('hello')")

    diff = file_watcher.get_file_diff("test.py")
    # Should return diff or None
    assert diff is None or isinstance(diff, str)


def test_register_change_callback(file_watcher):
    """Test registering change callback."""
    callback = Mock()
    initial_count = len(file_watcher._change_callbacks)
    file_watcher.register_change_callback(callback)

    # Verify callback was added
    assert len(file_watcher._change_callbacks) == initial_count + 1
    assert callback in file_watcher._change_callbacks


def test_check_changes(file_watcher):
    """Test checking for changes."""
    changed_files = file_watcher.check_changes()
    assert isinstance(changed_files, list)


def test_check_blueprint_changes(file_watcher):
    """Test checking for blueprint changes."""
    has_changes = file_watcher.check_blueprint_changes()
    assert isinstance(has_changes, bool)


def test_get_changed_files_include_untracked(file_watcher, temp_dir):
    """Test getting changed files including untracked."""
    # Create untracked file
    test_file = temp_dir / "untracked.py"
    test_file.write_text("print('test')")

    changed_files = file_watcher.get_changed_files(include_untracked=True)
    assert isinstance(changed_files, list)


def test_get_changed_files_exclude_untracked(file_watcher):
    """Test getting changed files excluding untracked."""
    changed_files = file_watcher.get_changed_files(include_untracked=False)
    assert isinstance(changed_files, list)
