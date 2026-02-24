"""Unit tests for GitManager."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from manifest.core.git_manager import GitManager, DEFAULT_BOTTOM_UP_TIMEOUT


@pytest.mark.unit
def test_git_manager_not_available_when_no_repo() -> None:
    """GitManager.is_available is False when not in a git repo."""
    with patch("manifest.core.git_manager.GIT_AVAILABLE", True):
        with patch("git.Repo") as mock_repo:
            mock_repo.side_effect = Exception("not a git repo")
            mgr = GitManager(Path("/nonexistent"))
            assert mgr.is_available() is False


@pytest.mark.unit
def test_get_current_branch_returns_unknown_when_unavailable() -> None:
    """get_current_branch returns 'unknown' when git unavailable."""
    mgr = GitManager(Path("/tmp"))
    mgr.repo = None
    assert mgr.get_current_branch() == "unknown"


@pytest.mark.unit
def test_bottom_up_timeout_constant() -> None:
    """DEFAULT_BOTTOM_UP_TIMEOUT is set."""
    assert DEFAULT_BOTTOM_UP_TIMEOUT > 0


@pytest.mark.unit
def test_get_pending_bottom_up_count() -> None:
    """GitManager.get_pending_bottom_up_count returns int."""
    n = GitManager.get_pending_bottom_up_count()
    assert isinstance(n, int)
    assert n >= 0
