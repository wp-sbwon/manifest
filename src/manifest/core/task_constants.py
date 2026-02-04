"""
Single source of truth for task status and stage values.

Use these constants everywhere: OpenCode task tool, TaskManager, types, View.
Keeps wording consistent (e.g. in_progress not "wip", completed not "done", paused for resumable stop).
"""
from typing import Dict

# --- Status (lifecycle) ---
TASK_STATUSES = frozenset({
    "pending",      # Not started; waiting to be picked up
    "in_progress", # Currently being worked on
    "paused",      # Temporarily halted; can be resumed
    "blocked",     # Cannot proceed (dependency or external)
    "completed",   # Work finished successfully
    "cancelled",   # No longer required; will not be done
})

# --- Stage (workflow phase) ---
TASK_STAGES = frozenset({
    "planning",
    "coding",
    "testing",
    "review",
    "done",
})

# Display labels for UI (status value -> human-readable)
STATUS_DISPLAY_LABELS: Dict[str, str] = {
    "pending": "Pending",
    "in_progress": "In progress",
    "paused": "Paused",
    "blocked": "Blocked",
    "completed": "Completed",
    "cancelled": "Cancelled",
}


def is_valid_status(value: str) -> bool:
    """Return True if value is a valid task status."""
    return value in TASK_STATUSES


def is_valid_stage(value: str) -> bool:
    """Return True if value is a valid task stage."""
    return value in TASK_STAGES


def status_display_label(status: str) -> str:
    """Return human-readable label for a status; falls back to the raw value."""
    return STATUS_DISPLAY_LABELS.get(status, status)
