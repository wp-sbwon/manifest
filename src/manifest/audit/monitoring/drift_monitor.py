"""Backward compatibility: use DeviationMonitor (design plan vs actual code)."""
from .deviation_monitor import DeviationMonitor

__all__ = ["DriftMonitor"]
DriftMonitor = DeviationMonitor
