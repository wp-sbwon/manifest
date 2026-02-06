"""Alias: DeviationAuditor, DeviationConflict."""
from .deviation_auditor import (
    Severity,
    DeviationConflict,
    DeviationAuditor,
)

__all__ = ["Severity", "DriftConflict", "DriftAuditor"]
DriftConflict = DeviationConflict
DriftAuditor = DeviationAuditor
