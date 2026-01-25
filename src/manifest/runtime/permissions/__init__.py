"""
Permission management system for Manifest agents.

This module provides role-based permission management following OpenCode conventions.
Agents can be granted or denied access to specific operations (read, write, edit, bash,
websearch, webfetch) based on their role and configuration.
"""
from manifest.runtime.permissions.permission_manager import PermissionManager

__all__ = ["PermissionManager"]
