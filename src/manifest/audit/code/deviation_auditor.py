"""Severity levels for blueprint comparator conflicts."""
from enum import Enum


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    IN_PROGRESS = "in_progress"
