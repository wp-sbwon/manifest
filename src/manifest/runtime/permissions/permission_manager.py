"""
Permission Manager - OpenCode-style role-based permission system.

This module implements a permission system that controls what operations agents
can perform. It follows OpenCode conventions with support for:
- Permission values: "allow", "ask", "deny"
- Wildcard patterns: "*" (any characters), "?" (single character)
- Last matching rule wins
- Global and per-agent permissions
"""
import re
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from manifest.core.config import ConfigManager
from manifest.core.logger import get_logger

logger = get_logger(__name__)


# Default permissions for each agent type
DEFAULT_PERMISSIONS = {
    "orchestrator": {
        "read": "allow",
        "write": "allow",
        "edit": "allow",
        "bash": "allow",
        "websearch": "allow",
        "webfetch": "allow"
    },
    "planner": {
        "read": "allow",
        "write": "deny",
        "edit": "deny",
        "bash": "deny",
        "websearch": "allow",
        "webfetch": "allow"
    },
    "coder": {
        "read": "allow",
        "write": "allow",
        "edit": "allow",
        "bash": "allow",
        "websearch": "ask",
        "webfetch": "ask"
    },
    "test": {
        "read": "allow",
        "write": "allow",
        "edit": "allow",
        "bash": "allow",
        "websearch": "ask",
        "webfetch": "ask"
    },
    "debug": {
        "read": "allow",
        "write": "deny",
        "edit": "ask",
        "bash": "allow",
        "websearch": "allow",
        "webfetch": "allow"
    },
    "approver": {
        "read": "allow",
        "write": "deny",
        "edit": "deny",
        "bash": "deny",
        "websearch": "deny",
        "webfetch": "deny"
    },
    "review": {
        "read": "allow",
        "write": "deny",
        "edit": "deny",
        "bash": "deny",
        "websearch": "deny",
        "webfetch": "deny"
    },
    "project_review": {
        "read": "allow",
        "write": "deny",
        "edit": "deny",
        "bash": "deny",
        "websearch": "ask",
        "webfetch": "ask"
    },
    "e2e_test": {
        "read": "allow",
        "write": "allow",
        "edit": "allow",
        "bash": "allow",
        "websearch": "ask",
        "webfetch": "ask"
    },
    "integration_test": {
        "read": "allow",
        "write": "allow",
        "edit": "allow",
        "bash": "allow",
        "websearch": "ask",
        "webfetch": "ask"
    }
}


class PermissionManager:
    """Manages permissions for agents following OpenCode conventions.
    
    Supports global and per-agent permissions with wildcard pattern matching.
    Permission values can be "allow", "ask", or "deny". The last matching
    rule wins when multiple patterns match.
    
    Attributes:
        config_manager: ConfigManager instance for loading permissions.
        agent_type: Type of agent this manager is for.
        global_permissions: Global permission rules.
        agent_permissions: Per-agent permission rules.
    """
    
    def __init__(
        self,
        config_manager: ConfigManager,
        agent_type: str
    ):
        """Initialize the permission manager.
        
        Args:
            config_manager: ConfigManager instance for loading permissions.
            agent_type: Type of agent (e.g., "coder", "planner").
        """
        self.config_manager = config_manager
        self.agent_type = agent_type
        self.global_permissions: Dict[str, Any] = {}
        self.agent_permissions: Dict[str, Any] = {}
        self._load_permissions()
    
    def _load_permissions(self) -> None:
        """Load permissions from agent_config.json."""
        try:
            agent_config = self.config_manager._load_agent_config()
            permissions_config = agent_config.get("agent_permissions", {})
            
            # Load global permissions
            global_config = permissions_config.get("global", {})
            self.global_permissions = global_config.get("permission", {})
            
            # Load agent-specific permissions
            agent_config_section = permissions_config.get("agent", {})
            agent_perm_config = agent_config_section.get(self.agent_type, {})
            self.agent_permissions = agent_perm_config.get("permission", {})
            
        except Exception as e:
            logger.warning(f"Error loading permissions, using defaults: {e}")
            # Use defaults if loading fails
            self.global_permissions = {}
            self.agent_permissions = DEFAULT_PERMISSIONS.get(self.agent_type, {})
    
    def check_permission(
        self,
        permission_type: str,
        resource: Optional[Union[str, List[str]]] = None
    ) -> str:
        """Check if an operation is allowed for this agent.
        
        Checks permissions in this order:
        1. Agent-specific permissions (highest priority)
        2. Global permissions
        3. Default permissions (fallback)
        
        For permission types that support patterns (like "bash"), the resource
        parameter is used for pattern matching. For example, if checking "bash"
        permission for command "git push --force", the resource would be
        "git push --force".
        
        Args:
            permission_type: Type of permission to check (e.g., "read", "write",
                "edit", "bash", "websearch", "webfetch").
            resource: Optional resource to check against patterns. For "bash",
                this would be the command string. For file operations, this
                could be a file path.
        
        Returns:
            Permission value: "allow", "ask", or "deny"
        """
        # First check agent-specific permissions
        agent_perm = self._check_permission_in_config(
            self.agent_permissions,
            permission_type,
            resource
        )
        if agent_perm is not None:
            return agent_perm
        
        # Then check global permissions
        global_perm = self._check_permission_in_config(
            self.global_permissions,
            permission_type,
            resource
        )
        if global_perm is not None:
            return global_perm
        
        # Finally, use default permissions
        default_perms = DEFAULT_PERMISSIONS.get(self.agent_type, {})
        return default_perms.get(permission_type, "deny")
    
    def _check_permission_in_config(
        self,
        config: Dict[str, Any],
        permission_type: str,
        resource: Optional[Union[str, List[str]]] = None
    ) -> Optional[str]:
        """Check permission in a specific config dictionary.
        
        Supports both simple string values and object-based pattern matching.
        For pattern matching, the last matching rule wins.
        
        Args:
            config: Permission configuration dictionary.
            permission_type: Type of permission to check.
            resource: Optional resource for pattern matching.
        
        Returns:
            Permission value if found, None otherwise.
        """
        perm_config = config.get(permission_type)
        
        if perm_config is None:
            return None
        
        # Simple string value (e.g., "allow", "deny", "ask")
        if isinstance(perm_config, str):
            return perm_config
        
        # Object-based pattern matching (e.g., {"*": "allow", "rm *": "deny"})
        if isinstance(perm_config, dict):
            if resource is None:
                # No resource provided, check for "*" pattern
                return perm_config.get("*")
            
            # Convert resource to string if it's a list (e.g., command args)
            if isinstance(resource, list):
                resource_str = " ".join(str(arg) for arg in resource)
            else:
                resource_str = str(resource)
            
            # Find matching patterns (last match wins)
            matched_value = None
            matched_patterns = []
            
            for pattern, value in perm_config.items():
                if self._pattern_matches(pattern, resource_str):
                    matched_patterns.append((pattern, value))
                    matched_value = value
            
            # If multiple patterns match, last one wins (OpenCode convention)
            if matched_patterns:
                # Sort by pattern specificity (more specific patterns first)
                # Then take the last one (as per OpenCode: last matching rule wins)
                matched_patterns.sort(key=lambda x: self._pattern_specificity(x[0]))
                return matched_patterns[-1][1]
            
            # No pattern matched, check for "*" fallback
            return perm_config.get("*")
        
        return None
    
    def _pattern_matches(self, pattern: str, text: str) -> bool:
        """Check if a pattern matches text.
        
        Supports OpenCode-style wildcards:
        - "*" matches any characters (including none)
        - "?" matches a single character
        
        Args:
            pattern: Pattern string with wildcards.
            text: Text to match against.
        
        Returns:
            True if pattern matches text, False otherwise.
        """
        # Convert OpenCode pattern to regex
        # Escape special regex characters except * and ?
        escaped = re.escape(pattern)
        # Replace escaped \* with .* (any characters)
        escaped = escaped.replace(r"\*", ".*")
        # Replace escaped \? with . (single character)
        escaped = escaped.replace(r"\?", ".")
        
        # Match entire string
        regex = f"^{escaped}$"
        
        try:
            return bool(re.match(regex, text))
        except re.error:
            logger.warning(f"Invalid pattern: {pattern}")
            return False
    
    def _pattern_specificity(self, pattern: str) -> int:
        """Calculate pattern specificity for sorting.
        
        More specific patterns (fewer wildcards) should be checked first.
        This helps ensure that specific rules are evaluated before general ones.
        
        Args:
            pattern: Pattern string.
        
        Returns:
            Specificity score (higher = more specific).
        """
        # Count wildcards (fewer wildcards = more specific)
        wildcard_count = pattern.count("*") + pattern.count("?")
        # Longer patterns are generally more specific
        length = len(pattern)
        # Return negative wildcard count so fewer wildcards = higher score
        return length - wildcard_count * 10
    
    def get_effective_permissions(self) -> Dict[str, str]:
        """Get all effective permissions for this agent.
        
        Returns a dictionary mapping permission types to their effective values,
        taking into account agent-specific, global, and default permissions.
        
        Returns:
            Dictionary of permission_type -> permission_value.
        """
        all_permission_types = [
            "read", "write", "edit", "bash", "websearch", "webfetch"
        ]
        
        effective = {}
        for perm_type in all_permission_types:
            effective[perm_type] = self.check_permission(perm_type)
        
        return effective
