"""
File and structure monitoring.

This package contains modules for monitoring code changes:
- FileWatcher: Monitors file system changes
- StructureManager: Manages structural changes and enforces Spec-First Development
- CodeWatcher: Watches code and updates blueprint_code.json
- DriftMonitor: Real-time drift monitoring (drives CodeWatcher)
"""
from .file_watcher import FileWatcher
from .structure_manager import StructureManager, StructuralChange, BlueprintUpdateSuggestion
from .code_watcher import CodeWatcher
from .drift_monitor import DriftMonitor

__all__ = [
    "FileWatcher",
    "StructureManager",
    "StructuralChange",
    "BlueprintUpdateSuggestion",
    "CodeWatcher",
    "DriftMonitor",
]
