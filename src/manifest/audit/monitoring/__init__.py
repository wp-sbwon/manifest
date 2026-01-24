"""
File and structure monitoring.

This package contains modules for monitoring code changes:
- FileWatcher: Monitors file system changes
- StructureManager: Manages structural changes and enforces Spec-First Development
"""
from .file_watcher import FileWatcher
from .structure_manager import StructureManager, StructuralChange, BlueprintUpdateSuggestion

__all__ = [
    "FileWatcher",
    "StructureManager",
    "StructuralChange",
    "BlueprintUpdateSuggestion",
]
