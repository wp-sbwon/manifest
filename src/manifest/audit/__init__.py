"""
Audit modules - Design Plan vs Actual Code.

- Blueprint (design plan) management and synchronization
- Code analysis and extraction (Actual Code)
- Deviation detection
"""
from .code.deviation_auditor import DeviationAuditor
from .code.code_extractor import CodeExtractor, Component, Contract
from .blueprint.blueprint_comparator import BlueprintComparator, BlueprintConflict, ConflictType
from .blueprint.blueprint_synchronizer import BlueprintSynchronizer, ConflictReport

# Alias
DriftAuditor = DeviationAuditor

__all__ = [
    "DeviationAuditor",
    "DriftAuditor",
    "CodeExtractor",
    "Component",
    "Contract",
    "BlueprintComparator",
    "BlueprintConflict",
    "ConflictType",
    "BlueprintSynchronizer",
    "ConflictReport",
]
