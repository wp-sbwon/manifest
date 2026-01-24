"""
Blueprint management and synchronization.

This package contains modules for managing blueprints:
- BlueprintLoader: Centralized blueprint loading
- BlueprintMetadata: Metadata management for blueprints
- BlueprintComparator: Compares top-down and bottom-up blueprints
- BlueprintSynchronizer: Handles blueprint conflict resolution
"""
from .blueprint_loader import BlueprintLoader
from .blueprint_metadata import load_blueprint_with_metadata, save_blueprint_with_metadata
from .blueprint_comparator import BlueprintComparator, BlueprintConflict, ConflictType
from .blueprint_synchronizer import BlueprintSynchronizer, ConflictReport

__all__ = [
    "BlueprintLoader",
    "load_blueprint_with_metadata",
    "save_blueprint_with_metadata",
    "BlueprintComparator",
    "BlueprintConflict",
    "ConflictType",
    "BlueprintSynchronizer",
    "ConflictReport",
]
