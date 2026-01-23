"""
Runtime Agent System
Agent orchestration and terminal routing system.
"""
from typing import Optional

__version__ = "0.1.0"

# Export OpenCode adapter
from manifest.runtime.opencode_adapter import OpenCodeAdapter, get_opencode_status, OPENCODE_AVAILABLE

# Export Shadow Manager
from manifest.runtime.shadow_manager import ShadowManager, ShadowProcess

__all__ = [
    "OpenCodeAdapter",
    "get_opencode_status",
    "OPENCODE_AVAILABLE",
    "ShadowManager",
    "ShadowProcess"
]
