"""Status enums: implementation and conflict workflow. Use .value for serialization."""

from enum import Enum


class ImplementationStatus(str, Enum):
    """Entity implementation status from design/code comparison."""

    PLANNED = "planned"
    HEALTHY = "healthy"
    PARTIAL = "partial"
    DEVIATION = "deviation"
    EXTRA = "extra"
