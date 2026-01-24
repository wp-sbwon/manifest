"""
Code analysis and extraction.

This package contains modules for analyzing code structure:
- CodeExtractor: Extracts code structure to generate bottom-up blueprint
- DriftAuditor: Detects architecture drift by comparing code against blueprint
"""
from .code_extractor import CodeExtractor, Component, Contract
from .drift_auditor import DriftAuditor, DriftConflict, Severity

__all__ = [
    "CodeExtractor",
    "Component",
    "Contract",
    "DriftAuditor",
    "DriftConflict",
    "Severity",
]
