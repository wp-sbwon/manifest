"""Unit tests for GitManager."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from manifest.core.git_manager import GitManager


@pytest.mark.unit
def test_git_manager_not_available_when_no_repo() -> None:
    """GitManager.is_available is False when not in a git repo."""
    with patch("manifest.core.git_manager.GIT_AVAILABLE", True):
        with patch("git.Repo") as mock_repo:
            mock_repo.side_effect = Exception("not a git repo")
            mgr = GitManager(Path("/nonexistent"))
            assert mgr.is_available() is False


@pytest.mark.unit
def test_get_latest_commits_returns_empty_when_unavailable() -> None:
    """get_latest_commits returns [] when git unavailable."""
    mgr = GitManager(Path("/tmp"))
    mgr.repo = None
    assert mgr.get_latest_commits() == []


@pytest.mark.unit
def test_get_commits_for_paths_returns_empty_when_unavailable() -> None:
    """get_commits_for_paths returns [] when git unavailable."""
    mgr = GitManager(Path("/tmp"))
    mgr.repo = None
    assert mgr.get_commits_for_paths(["foo.json"]) == []
