"""Status enums: implementation and conflict workflow. Use .value for serialization."""

from enum import Enum


class ImplementationStatus(str, Enum):
    """Entity implementation status from design/code comparison."""

    PLANNED = "planned"
    HEALTHY = "healthy"
    PARTIAL = "partial"
    DEVIATION = "deviation"
    EXTRA = "extra"


_TRANSITIONS = {
    "pending": ["planner_review"],
    "planner_review": ["user_approval", "rejected"],
    "user_approval": ["resolved", "rejected"],
    "resolved": [],
    "rejected": [],
}


class ConflictWorkflowStatus(str, Enum):
    PENDING = "pending"
    PLANNER_REVIEW = "planner_review"
    USER_APPROVAL = "user_approval"
    RESOLVED = "resolved"
    REJECTED = "rejected"

    @classmethod
    def is_terminal(cls, status: str) -> bool:
        return status in (cls.RESOLVED.value, cls.REJECTED.value)

    @classmethod
    def allowed_transitions(cls) -> dict:
        return _TRANSITIONS.copy()

    @classmethod
    def can_transition(cls, from_status: str, to_status: str) -> bool:
        return to_status in _TRANSITIONS.get(from_status, [])
