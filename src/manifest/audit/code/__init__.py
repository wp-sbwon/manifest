"""
Code analysis and extraction.

- CodeExtractor: Extracts code structure to generate Actual Code (blueprint_code.json)
- DeviationAuditor: Compares code against design plan to detect deviation
"""
from .code_extractor import CodeExtractor, Component, Contract
from .deviation_auditor import DeviationAuditor, DeviationConflict, Severity

# Backward compatibility
DriftAuditor = DeviationAuditor
DriftConflict = DeviationConflict

__all__ = [
    "CodeExtractor",
    "Component",
    "Contract",
    "DeviationAuditor",
    "DeviationConflict",
    "DriftAuditor",
    "DriftConflict",
    "Severity",
]
