"""
File Manager for OpenCode-style file operations.

This module provides file operations (edit, write, read, grep, glob, list)
following OpenCode conventions. All operations are checked against
PermissionManager for role-based access control.
"""
import re
import glob as pyglob
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from pathlib import Path
from manifest.core.logger import get_logger

if TYPE_CHECKING:
    from manifest.runtime.permissions.permission_manager import PermissionManager

logger = get_logger(__name__)


class FileManager:
    """Manages file operations with permission checking.
    
    Provides OpenCode-style file operations:
    - edit: Exact string replacement
    - write: Create/overwrite file
    - read: Read file (with optional line range)
    - grep: Search for patterns
    - glob: Find files by pattern
    - list: List directory contents
    
    All operations check permissions before execution.
    """
    
    def __init__(
        self,
        working_dir: Optional[Path] = None,
        permission_manager: Optional["PermissionManager"] = None,
        agent_type: Optional[str] = None
    ):
        """Initialize file manager.
        
        Args:
            working_dir: Base directory for file operations. Defaults to current directory.
            permission_manager: PermissionManager instance for access control.
            agent_type: Type of agent using this manager (for permission checks).
        """
        self.working_dir = working_dir or Path.cwd()
        self.permission_manager = permission_manager
        self.agent_type = agent_type
    
    def _check_permission(self, permission_type: str, resource: Optional[str] = None) -> str:
        """Check permission for an operation.
        
        Args:
            permission_type: Type of permission (read, write, edit).
            resource: Optional resource path to check.
            
        Returns:
            "allow", "ask", or "deny"
        """
        if not self.permission_manager or not self.agent_type:
            return "allow"  # No permission manager = allow all
        
        return self.permission_manager.check_permission(permission_type, resource)
    
    def _resolve_path(self, file_path: str) -> Path:
        """Resolve file path relative to working directory.
        
        Args:
            file_path: Path relative to working directory.
            
        Returns:
            Resolved absolute Path.
        """
        if Path(file_path).is_absolute():
            return Path(file_path)
        return (self.working_dir / file_path).resolve()
    
    def edit(
        self,
        file_path: str,
        old_string: str,
        new_string: str
    ) -> Dict[str, Any]:
        """Edit a file by replacing exact string match.
        
        This is the primary way to modify existing files. The old_string
        must match exactly (including whitespace and newlines) for the
        replacement to succeed.
        
        Args:
            file_path: Path to file relative to working directory.
            old_string: Exact string to replace.
            new_string: Replacement string.
            
        Returns:
            Dict with 'success', 'message', and optional 'error'.
        """
        resolved_path = self._resolve_path(file_path)
        
        # Check permission
        permission = self._check_permission("edit", str(resolved_path))
        if permission == "deny":
            return {
                "success": False,
                "error": "Permission denied",
                "message": f"Edit operation denied for '{file_path}'"
            }
        elif permission == "ask":
            # Return permission_required flag for UI approval
            return {
                "success": False,
                "error": "Permission approval required",
                "message": f"Edit operation requires approval for '{file_path}'",
                "permission_required": True,
                "permission_type": "edit",
                "resource": file_path
            }
        
        try:
            # Read file
            if not resolved_path.exists():
                return {
                    "success": False,
                    "error": "File not found",
                    "message": f"File '{file_path}' does not exist"
                }
            
            content = resolved_path.read_text(encoding='utf-8')
            
            # Check if old_string exists
            if old_string not in content:
                return {
                    "success": False,
                    "error": "String not found",
                    "message": f"Old string not found in '{file_path}'. The string must match exactly including whitespace and newlines."
                }
            
            # Replace
            new_content = content.replace(old_string, new_string, 1)  # Replace first occurrence only
            
            # Write back
            resolved_path.write_text(new_content, encoding='utf-8')
            
            return {
                "success": True,
                "message": f"Successfully edited '{file_path}'"
            }
        except Exception as e:
            logger.error(f"Error editing file '{file_path}': {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Error editing '{file_path}': {e}"
            }
    
    def write(
        self,
        file_path: str,
        content: str
    ) -> Dict[str, Any]:
        """Create or overwrite a file.
        
        Args:
            file_path: Path to file relative to working directory.
            content: Complete file content.
            
        Returns:
            Dict with 'success', 'message', and optional 'error'.
        """
        resolved_path = self._resolve_path(file_path)
        
        # Check permission
        permission = self._check_permission("write", str(resolved_path))
        if permission == "deny":
            return {
                "success": False,
                "error": "Permission denied",
                "message": f"Write operation denied for '{file_path}'"
            }
        elif permission == "ask":
            # Return permission_required flag for UI approval
            return {
                "success": False,
                "error": "Permission approval required",
                "message": f"Write operation requires approval for '{file_path}'",
                "permission_required": True,
                "permission_type": "write",
                "resource": file_path
            }
        
        try:
            # Create parent directories if needed
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            resolved_path.write_text(content, encoding='utf-8')
            
            return {
                "success": True,
                "message": f"Successfully wrote '{file_path}'"
            }
        except Exception as e:
            logger.error(f"Error writing file '{file_path}': {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Error writing '{file_path}': {e}"
            }
    
    def read(
        self,
        file_path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None
    ) -> Dict[str, Any]:
        """Read a file or line range.
        
        Args:
            file_path: Path to file relative to working directory.
            start_line: Optional starting line (1-indexed).
            end_line: Optional ending line (1-indexed, inclusive).
            
        Returns:
            Dict with 'success', 'content', and optional 'error'.
        """
        resolved_path = self._resolve_path(file_path)
        
        # Check permission
        permission = self._check_permission("read", str(resolved_path))
        if permission == "deny":
            return {
                "success": False,
                "error": "Permission denied",
                "content": "",
                "message": f"Read operation denied for '{file_path}'"
            }
        elif permission == "ask":
            logger.warning(
                f"Permission 'ask' for read '{file_path}' by agent '{self.agent_type}' - "
                "allowing for now (approval not implemented)"
            )
        
        try:
            if not resolved_path.exists():
                return {
                    "success": False,
                    "error": "File not found",
                    "content": "",
                    "message": f"File '{file_path}' does not exist"
                }
            
            content = resolved_path.read_text(encoding='utf-8')
            
            # Handle line range
            if start_line is not None or end_line is not None:
                lines = content.split('\n')
                start = (start_line or 1) - 1  # Convert to 0-indexed
                end = end_line if end_line is not None else len(lines)
                
                if start < 0:
                    start = 0
                if end > len(lines):
                    end = len(lines)
                
                selected_lines = lines[start:end]
                content = '\n'.join(selected_lines)
            
            return {
                "success": True,
                "content": content,
                "message": f"Successfully read '{file_path}'"
            }
        except Exception as e:
            logger.error(f"Error reading file '{file_path}': {e}")
            return {
                "success": False,
                "error": str(e),
                "content": "",
                "message": f"Error reading '{file_path}': {e}"
            }
    
    def grep(
        self,
        pattern: str,
        file_path: str
    ) -> Dict[str, Any]:
        """Search for pattern in file using regex.
        
        Args:
            pattern: Regular expression pattern.
            file_path: Path to file relative to working directory.
            
        Returns:
            Dict with 'success', 'matches' (list of line numbers and content), and optional 'error'.
        """
        resolved_path = self._resolve_path(file_path)
        
        # Check permission
        permission = self._check_permission("read", str(resolved_path))
        if permission == "deny":
            return {
                "success": False,
                "error": "Permission denied",
                "matches": [],
                "message": f"Grep operation denied for '{file_path}'"
            }
        elif permission == "ask":
            logger.warning(
                f"Permission 'ask' for grep '{file_path}' by agent '{self.agent_type}' - "
                "allowing for now (approval not implemented)"
            )
        
        try:
            if not resolved_path.exists():
                return {
                    "success": False,
                    "error": "File not found",
                    "matches": [],
                    "message": f"File '{file_path}' does not exist"
                }
            
            content = resolved_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            matches = []
            try:
                regex = re.compile(pattern)
                for i, line in enumerate(lines, 1):
                    if regex.search(line):
                        matches.append({
                            "line": i,
                            "content": line
                        })
            except re.error as e:
                return {
                    "success": False,
                    "error": f"Invalid regex pattern: {e}",
                    "matches": [],
                    "message": f"Invalid regex pattern '{pattern}': {e}"
                }
            
            return {
                "success": True,
                "matches": matches,
                "message": f"Found {len(matches)} matches in '{file_path}'"
            }
        except Exception as e:
            logger.error(f"Error grepping file '{file_path}': {e}")
            return {
                "success": False,
                "error": str(e),
                "matches": [],
                "message": f"Error grepping '{file_path}': {e}"
            }
    
    def glob(self, pattern: str) -> Dict[str, Any]:
        """Find files matching glob pattern.
        
        Args:
            pattern: Glob pattern (e.g., '*.py', 'src/**/*.ts').
            
        Returns:
            Dict with 'success', 'files' (list of matching paths), and optional 'error'.
        """
        try:
            # Resolve pattern relative to working directory
            if not Path(pattern).is_absolute():
                search_path = self.working_dir / pattern
            else:
                search_path = Path(pattern)
            
            matches = []
            for match in pyglob.glob(str(search_path), recursive=True):
                rel_path = Path(match).relative_to(self.working_dir)
                matches.append(str(rel_path))
            
            return {
                "success": True,
                "files": sorted(matches),
                "message": f"Found {len(matches)} files matching '{pattern}'"
            }
        except Exception as e:
            logger.error(f"Error globbing pattern '{pattern}': {e}")
            return {
                "success": False,
                "error": str(e),
                "files": [],
                "message": f"Error globbing '{pattern}': {e}"
            }
    
    def list(self, directory: Optional[str] = None) -> Dict[str, Any]:
        """List files and directories.
        
        Args:
            directory: Path to directory (relative to working directory).
                If None, lists current working directory.
            
        Returns:
            Dict with 'success', 'items' (list of file/dir names), and optional 'error'.
        """
        if directory:
            resolved_path = self._resolve_path(directory)
        else:
            resolved_path = self.working_dir
        
        # Check permission
        permission = self._check_permission("read", str(resolved_path))
        if permission == "deny":
            return {
                "success": False,
                "error": "Permission denied",
                "items": [],
                "message": f"List operation denied for '{directory or '.'}'"
            }
        elif permission == "ask":
            logger.warning(
                f"Permission 'ask' for list '{directory or '.'}' by agent '{self.agent_type}' - "
                "allowing for now (approval not implemented)"
            )
        
        try:
            if not resolved_path.exists():
                return {
                    "success": False,
                    "error": "Directory not found",
                    "items": [],
                    "message": f"Directory '{directory or '.'}' does not exist"
                }
            
            if not resolved_path.is_dir():
                return {
                    "success": False,
                    "error": "Not a directory",
                    "items": [],
                    "message": f"'{directory or '.'}' is not a directory"
                }
            
            items = []
            for item in sorted(resolved_path.iterdir()):
                item_type = "directory" if item.is_dir() else "file"
                items.append({
                    "name": item.name,
                    "type": item_type
                })
            
            return {
                "success": True,
                "items": items,
                "message": f"Listed {len(items)} items in '{directory or '.'}'"
            }
        except Exception as e:
            logger.error(f"Error listing directory '{directory or '.'}': {e}")
            return {
                "success": False,
                "error": str(e),
                "items": [],
                "message": f"Error listing '{directory or '.'}': {e}"
            }
