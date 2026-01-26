"""
Unit tests for GitManager.

Tests git operations, status checking, and diff tracking.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from manifest.core.git_manager import GitManager


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing."""
    return tmp_path


@pytest.fixture
def git_manager(temp_dir):
    """Create a GitManager instance."""
    return GitManager(project_root=temp_dir)


def test_git_manager_initialization(git_manager, temp_dir):
    """Test GitManager initialization."""
    assert git_manager.project_root == temp_dir
    assert git_manager is not None


def test_is_available(git_manager):
    """Test checking if git is available."""
    is_available = git_manager.is_available()
    assert isinstance(is_available, bool)


def test_get_diff(git_manager):
    """Test getting git diff."""
    with patch('manifest.core.git_manager.git') as mock_git:
        mock_repo = Mock()
        mock_repo.git.diff.return_value = "diff --git a/test.py b/test.py"
        git_manager.repo = mock_repo
        
        diff = git_manager.get_diff()
        assert isinstance(diff, str)


def test_get_current_branch(git_manager):
    """Test getting current branch."""
    with patch('manifest.core.git_manager.git') as mock_git:
        mock_repo = Mock()
        mock_branch = Mock()
        mock_branch.name = "main"
        mock_repo.active_branch = mock_branch
        git_manager.repo = mock_repo
        
        branch = git_manager.get_current_branch()
        assert isinstance(branch, str)
        assert branch == "main"


def test_get_latest_commits(git_manager):
    """Test getting latest commits."""
    with patch('manifest.core.git_manager.git') as mock_git:
        mock_repo = Mock()
        mock_commit1 = Mock()
        mock_commit1.hexsha = "abc123"
        mock_commit1.message = "Test commit 1"
        mock_commit1.author.name = "Test User"
        mock_commit1.committed_datetime.isoformat = lambda: "2024-01-01T00:00:00"
        mock_commit2 = Mock()
        mock_commit2.hexsha = "def456"
        mock_commit2.message = "Test commit 2"
        mock_commit2.author.name = "Test User"
        mock_commit2.committed_datetime.isoformat = lambda: "2024-01-02T00:00:00"
        mock_repo.iter_commits.return_value = [mock_commit1, mock_commit2]
        git_manager.repo = mock_repo
        
        commits = git_manager.get_latest_commits(limit=5)
        assert isinstance(commits, list)
        assert len(commits) == 2


def test_create_commit(git_manager):
    """Test creating a commit."""
    with patch('manifest.core.git_manager.git') as mock_git:
        mock_repo = Mock()
        mock_repo.git.add.return_value = None
        mock_repo.index.commit.return_value = Mock(hexsha="abc123")
        git_manager.repo = mock_repo
        
        commit_hash = git_manager.create_commit("Test commit")
        assert commit_hash == "abc123"


def test_generate_commit_message(git_manager):
    """Test generating commit message from task."""
    task = {
        "name": "Implement feature",
        "description": "Add new functionality"
    }
    message = git_manager.generate_commit_message(task)
    assert isinstance(message, str)
    assert "Implement feature" in message
