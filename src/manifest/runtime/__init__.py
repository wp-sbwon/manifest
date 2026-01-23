"""
Runtime Agent System
Agent orchestration and terminal routing system.
"""
from typing import Optional

__version__ = "0.1.0"

# Export OpenCode adapter
from manifest.runtime.opencode_adapter import OpenCodeAdapter, get_opencode_status, OPENCODE_AVAILABLE

__all__ = [
    "OpenCodeAdapter",
    "get_opencode_status",
    "OPENCODE_AVAILABLE"
]
