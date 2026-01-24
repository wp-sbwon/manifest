"""
Audit modules - Architecture drift detection.

This package provides modules for auditing code structure and detecting drift:
- Blueprint management and synchronization
- Code analysis and extraction
- Metadata management
- File and structure monitoring
"""
from .code.drift_auditor import DriftAuditor
from .code.code_extractor import CodeExtractor, Component, Contract
from .blueprint.blueprint_comparator import BlueprintComparator, BlueprintConflict, ConflictType
from .blueprint.blueprint_synchronizer import BlueprintSynchronizer, ConflictReport

__all__ = [
    "DriftAuditor",
    "CodeExtractor",
    "Component",
    "Contract",
    "BlueprintComparator",
    "BlueprintConflict",
    "ConflictType",
    "BlueprintSynchronizer",
    "ConflictReport"
]
