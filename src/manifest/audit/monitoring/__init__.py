"""
File and structure monitoring.

- CodeWatcher: Watches code and updates blueprint_code.json (Actual Code)
- DeviationMonitor: Design Plan vs Actual Code alignment (drives CodeWatcher)
"""
from .file_watcher import FileWatcher
from .structure_manager import StructureManager, StructuralChange, BlueprintUpdateSuggestion
from .code_watcher import CodeWatcher
from .deviation_monitor import DeviationMonitor

# Backward compatibility
DriftMonitor = DeviationMonitor

__all__ = [
    "FileWatcher",
    "StructureManager",
    "StructuralChange",
    "BlueprintUpdateSuggestion",
    "CodeWatcher",
    "DeviationMonitor",
    "DriftMonitor",
]
