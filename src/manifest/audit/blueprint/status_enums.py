"""Status enums: implementation and conflict workflow. Use .value for serialization."""

from enum import Enum


class ImplementationStatus(str, Enum):
    """Entity implementation status from design/code comparison."""

    PLANNED = "planned"
    HEALTHY = "healthy"
    PARTIAL = "partial"
    DEVIATION = "deviation"
    EXTRA = "extra"


class ConflictWorkflowStatus(str, Enum):
    """Conflict report workflow status. Transitions: pending -> planner_review -> user_approval -> resolved|rejected."""

    PENDING = "pending"
    PLANNER_REVIEW = "planner_review"
    USER_APPROVAL = "user_approval"
    RESOLVED = "resolved"
    REJECTED = "rejected"

    @classmethod
    def is_terminal(cls, status: str) -> bool:
        """True if status is resolved or rejected (no further transitions)."""
        return status in (cls.RESOLVED.value, cls.REJECTED.value)

    @classmethod
    def allowed_transitions(cls) -> dict:
        """Map status -> list of valid next statuses."""
        return {
            cls.PENDING.value: [cls.PLANNER_REVIEW.value],
            cls.PLANNER_REVIEW.value: [cls.USER_APPROVAL.value, cls.REJECTED.value],
            cls.USER_APPROVAL.value: [cls.RESOLVED.value, cls.REJECTED.value],
            cls.RESOLVED.value: [],
            cls.REJECTED.value: [],
        }

    @classmethod
    def can_transition(cls, from_status: str, to_status: str) -> bool:
        """True if transition from_status -> to_status is allowed."""
        allowed = cls.allowed_transitions().get(from_status, [])
        return to_status in allowed
