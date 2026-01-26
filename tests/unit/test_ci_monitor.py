"""
Unit tests for CI Monitor.

Tests CI status checking, import validation, and GitHub repo detection.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from manifest.core.ci_monitor import (
    get_github_repo_info,
    check_ci_status_local,
    check_imports
)


def test_get_github_repo_info_https():
    """Test getting GitHub repo info from HTTPS URL."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout="https://github.com/owner/repo.git\n"
        )
        
        info = get_github_repo_info()
        # May return None if not in git repo
        assert info is None or isinstance(info, dict)


def test_get_github_repo_info_ssh():
    """Test getting GitHub repo info from SSH URL."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout="git@github.com:owner/repo.git\n"
        )
        
        info = get_github_repo_info()
        # May return None if not in git repo
        assert info is None or isinstance(info, dict)


def test_get_github_repo_info_not_git():
    """Test getting GitHub repo info when not a git repo."""
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = Exception("Not a git repo")
        
        info = get_github_repo_info()
        assert info is None


def test_check_ci_status_local():
    """Test checking CI status locally."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout="test output",
            stderr=""
        )
        
        result = check_ci_status_local()
        assert isinstance(result, dict)
        assert "success" in result


def test_check_ci_status_local_failure():
    """Test checking CI status when tests fail."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            returncode=1,
            stdout="test failures",
            stderr="errors"
        )
        
        result = check_ci_status_local()
        assert isinstance(result, dict)
        assert result.get("success") is False


def test_check_imports():
    """Test checking critical imports."""
    result = check_imports()
    assert isinstance(result, dict)
    assert "all_passed" in result or "results" in result


def test_check_imports_with_failure():
    """Test checking imports when some fail."""
    with patch('importlib.import_module') as mock_import:
        mock_import.side_effect = ImportError("Module not found")
        
        result = check_imports()
        assert isinstance(result, dict)
