"""
Git Manager - Handles Git operations for the Timeline tab.
"""
from pathlib import Path
from typing import Dict, Any, Optional, List

from manifest.core.logger import get_logger

logger = get_logger(__name__)

try:
    import git
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False


class GitManager:
    """Manages Git operations for timeline (commits by path, latest commits)."""

    def __init__(
        self,
        project_root: Optional[Path] = None,
        search_parent_directories: bool = True,
    ):
        self.project_root = (project_root or Path.cwd()).resolve()
        self.repo = None
        if GIT_AVAILABLE:
            try:
                self.repo = git.Repo(
                    self.project_root,
                    search_parent_directories=search_parent_directories,
                )
            except Exception:
                logger.warning("Not a git repository")

    def is_available(self) -> bool:
        """Check if Git and repository are available."""
        return GIT_AVAILABLE and self.repo is not None

    def get_latest_commits(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get latest commits."""
        if not self.is_available():
            return []

        commits = []
        try:
            for commit in self.repo.iter_commits(max_count=limit):
                commits.append({
                    "hash": commit.hexsha,
                    "author": commit.author.name,
                    "message": commit.message.strip(),
                    "timestamp": commit.committed_datetime.isoformat(),
                    "short_hash": commit.hexsha[:8]
                })
        except Exception as e:
            logger.error(f"Error getting commits: {e}")

        return commits

    def get_commits_for_paths(
        self,
        paths: List[str],
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Commits that touched any of the given paths (relative to project_root)."""
        if not self.is_available() or not paths:
            return []
        commits = []
        try:
            for commit in self.repo.iter_commits(max_count=limit, paths=paths):
                commits.append({
                    "hash": commit.hexsha,
                    "author": commit.author.name,
                    "message": commit.message.strip(),
                    "timestamp": commit.committed_datetime.isoformat(),
                    "short_hash": commit.hexsha[:8],
                })
        except Exception as e:
            logger.debug("get_commits_for_paths failed: %s", e)
        return commits
