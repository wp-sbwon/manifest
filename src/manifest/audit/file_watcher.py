"""
File Watcher - Monitors file system changes for Spec-First Management.
Uses Git to detect changed files and triggers structural change analysis.
"""
import subprocess
from pathlib import Path
from typing import List, Optional, Set, Callable
from datetime import datetime


class FileWatcher:
    """
    Watches for file changes using Git.
    Detects modified, added, and deleted files.
    """
    
    def __init__(self, project_root: Path = None):
        """
        Initialize file watcher.
        
        Args:
            project_root: Project root directory (default: current directory)
        """
        self.project_root = project_root or Path.cwd()
        self._change_callbacks: List[Callable[[List[str]], None]] = []
        self._last_check: Optional[datetime] = None
    
    def is_git_repo(self) -> bool:
        """Check if project is a Git repository."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def get_changed_files(
        self,
        since: Optional[datetime] = None,
        include_untracked: bool = True
    ) -> List[str]:
        """
        Get list of changed files using Git.
        
        Args:
            since: Only get changes since this time (optional)
            include_untracked: Include untracked files
            
        Returns:
            List of file paths (relative to project root)
        """
        if not self.is_git_repo():
            return []
        
        changed_files = []
        
        try:
            # Get modified and staged files
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return []
            
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                
                status = line[:2]
                file_path = line[3:].strip()
                
                # M = modified, A = added, D = deleted, ?? = untracked
                if status[0] in ["M", "A", "D"] or status[1] in ["M", "A", "D"]:
                    changed_files.append(file_path)
                elif include_untracked and status == "??":
                    # Untracked file
                    changed_files.append(file_path)
            
            # Filter by time if specified
            if since:
                filtered = []
                for file_path in changed_files:
                    path = self.project_root / file_path
                    if path.exists():
                        mtime = datetime.fromtimestamp(path.stat().st_mtime)
                        if mtime >= since:
                            filtered.append(file_path)
                    else:
                        # Deleted file - include if we're tracking deletions
                        filtered.append(file_path)
                changed_files = filtered
            
        except Exception as e:
            print(f"Error getting changed files: {e}")
            return []
        
        return changed_files
    
    def get_file_diff(self, file_path: str) -> Optional[str]:
        """
        Get Git diff for a specific file.
        
        Args:
            file_path: Path to file (relative to project root)
            
        Returns:
            Diff string or None
        """
        if not self.is_git_repo():
            return None
        
        try:
            result = subprocess.run(
                ["git", "diff", file_path],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout
            
            # Try staged changes
            result = subprocess.run(
                ["git", "diff", "--staged", file_path],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout
            
        except Exception:
            pass
        
        return None
    
    def register_change_callback(self, callback: Callable[[List[str]], None]):
        """
        Register a callback to be called when files change.
        
        Args:
            callback: Function that takes a list of changed file paths
        """
        self._change_callbacks.append(callback)
    
    def check_changes(self) -> List[str]:
        """
        Check for file changes and notify callbacks.
        
        Returns:
            List of changed file paths
        """
        changed_files = self.get_changed_files(since=self._last_check)
        
        if changed_files:
            # Filter to only code files
            code_extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".cpp", ".c", ".h"}
            code_files = [
                f for f in changed_files
                if Path(f).suffix in code_extensions
            ]
            
            if code_files:
                # Notify callbacks
                for callback in self._change_callbacks:
                    try:
                        callback(code_files)
                    except Exception as e:
                        print(f"Error in change callback: {e}")
            
            self._last_check = datetime.now()
        
        return changed_files
