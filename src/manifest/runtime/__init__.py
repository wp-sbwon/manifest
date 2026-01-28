"""
Runtime Agent System
Agent orchestration and terminal routing system.
"""
from typing import Optional

__version__ = "0.1.0"

# Export Shadow Manager
from manifest.runtime.shadow_manager import ShadowManager, ShadowProcess

__all__ = [
    "ShadowManager",
    "ShadowProcess"
]
