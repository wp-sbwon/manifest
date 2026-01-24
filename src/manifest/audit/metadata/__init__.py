"""
Metadata management for architecture and blueprints.

This package contains modules for managing metadata:
- ArchitectureMetadata: Architecture metadata loading and saving
"""
from .architecture_metadata import load_architecture_with_metadata, save_architecture_with_metadata

__all__ = [
    "load_architecture_with_metadata",
    "save_architecture_with_metadata",
]
