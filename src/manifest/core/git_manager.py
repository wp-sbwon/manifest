"""
Git Manager - Handles Git operations and integration with Manifest.
"""
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List

from manifest.core.logger import get_logger

logger = get_logger(__name__)

# Default timeout for bottom-up docs subprocess (seconds). Override via MANIFEST_BOTTOM_UP_TIMEOUT.
DEFAULT_BOTTOM_UP_TIMEOUT = 300

# Track spawned bottom-up processes for visibility (process objects, cleared after completion).
_bottom_up_processes: List[subprocess.Popen] = []
_bottom_up_lock = threading.Lock()

try:
    import git
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False


class GitManager:
    """Manages Git operations and integration with blueprints and tasks."""

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

    def get_current_branch(self) -> str:
        """Get current branch name."""
        if not self.is_available():
            return "unknown"
        return self.repo.active_branch.name

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

    def create_commit(self, message: str, files: Optional[List[str]] = None) -> Optional[str]:
        """Create a new commit."""
        if not self.is_available():
            return None

        try:
            if files:
                self.repo.index.add(files)
            else:
                self.repo.git.add(A=True)

            commit = self.repo.index.commit(message)
            hexsha = commit.hexsha
            self._trigger_bottom_up_docs_after_commit()
            return hexsha
        except Exception as e:
            logger.error(f"Error creating commit: {e}")
            return None

    def _trigger_bottom_up_docs_after_commit(self) -> None:
        """Trigger bottom-up doc generation in background. Runs in thread with timeout."""
        def _run() -> None:
            timeout = int(os.environ.get("MANIFEST_BOTTOM_UP_TIMEOUT", str(DEFAULT_BOTTOM_UP_TIMEOUT)))
            try:
                root = Path(getattr(self.repo, "working_tree_dir", None) or self.project_root)
                script = root / "scripts" / "run_bottom_up_docs.py"
                if not script.exists():
                    return
                env = {**os.environ}
                env["PYTHONPATH"] = str(root / "src") + (f":{env['PYTHONPATH']}" if env.get("PYTHONPATH") else "")
                proc = subprocess.Popen(
                    [sys.executable, str(script), "--project-root", str(root)],
                    cwd=str(root),
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                with _bottom_up_lock:
                    _bottom_up_processes.append(proc)
                try:
                    proc.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    logger.warning("Bottom-up docs timed out after %ds, killing", timeout)
                    proc.kill()
                    proc.wait()
                finally:
                    with _bottom_up_lock:
                        if proc in _bottom_up_processes:
                            _bottom_up_processes.remove(proc)
            except Exception as e:
                logger.debug("Could not start bottom-up docs after commit: %s", e)

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    @staticmethod
    def get_pending_bottom_up_count() -> int:
        """Number of bottom-up doc processes currently running (for monitoring)."""
        with _bottom_up_lock:
            return len([p for p in _bottom_up_processes if p.poll() is None])

    def generate_commit_message(self, task: Dict[str, Any]) -> str:
        """Generate a commit message from task details."""
        task_id = task.get("id", "unknown")
        task_name = task.get("name", "Work on task")

        # Basic format: "feat(task-id): task name"
        # We can enhance this with more details from worker squad stages
        message = f"feat({task_id}): {task_name}"

        worker_squad = task.get("worker_squad", {})
        stages = worker_squad.get("stages", {})

        if "coder" in stages:
            coder_output = stages["coder"].get("output", "")
            # Try to extract a summary from coder output
            if coder_output:
                summary = coder_output.split('\n')[0][:50]
                if summary:
                    message += f"\n\n{summary}"

        return message

    def sync_blueprint(self, manifest_dir: Path) -> bool:
        """Sync blueprint files with Git (stage them)."""
        if not self.is_available():
            return False

        try:
            blueprint_files = list(manifest_dir.glob("*.json"))
            blueprint_paths = [str(f.relative_to(self.project_root)) for f in blueprint_files]
            self.repo.index.add(blueprint_paths)
            return True
        except Exception as e:
            logger.error(f"Error syncing blueprint: {e}")
            return False

    def get_diff(self) -> str:
        """Get current uncommitted changes."""
        if not self.is_available():
            return ""
        return self.repo.git.diff()

    def push(self, remote: str = "origin", branch: Optional[str] = None) -> bool:
        """Push changes to remote."""
        if not self.is_available():
            return False

        try:
            target_branch = branch or self.get_current_branch()
            self.repo.remotes[remote].push(target_branch)
            return True
        except Exception as e:
            logger.error(f"Error pushing: {e}")
            return False

    def pull(self, remote: str = "origin", branch: Optional[str] = None) -> bool:
        """Pull changes from remote."""
        if not self.is_available():
            return False

        try:
            target_branch = branch or self.get_current_branch()
            self.repo.remotes[remote].pull(target_branch)
            return True
        except Exception as e:
            logger.error(f"Error pulling: {e}")
            return False

    def rollback_to_commit(self, commit_hash: str) -> bool:
        """Rollback codebase to a specific commit."""
        if not self.is_available():
            return False

        try:
            self.repo.git.reset("--hard", commit_hash)
            return True
        except Exception as e:
            logger.error(f"Error rolling back to commit {commit_hash}: {e}")
            return False

    def get_commit_for_task(self, task_id: str) -> Optional[str]:
        """Find the latest commit hash for a specific task."""
        if not self.is_available():
            return None

        try:
            # Search for task ID in commit messages
            for commit in self.repo.iter_commits(max_count=50):
                if f"({task_id})" in commit.message or f" {task_id}:" in commit.message:
                    return commit.hexsha
        except Exception as e:
            logger.debug("find_commit_with_task_id failed: %s", e)
        return None
