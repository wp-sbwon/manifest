"""
Type definitions for Manifest using TypedDict.

This module provides structured type hints for commonly used dictionary
structures throughout the codebase. Using TypedDict helps with type checking
and makes the expected structure of data dictionaries explicit and documented.

All TypedDict classes here represent the structure of JSON-serializable data
that flows through the application, making it easier to understand what
fields are expected and their types.
"""
from typing import TypedDict, List, Optional, Dict, Any
from datetime import datetime


class TaskDict(TypedDict, total=False):
    """Structure of a task dictionary.

    Represents a single task in the system. All fields are optional (total=False)
    to allow for partial task data during creation or updates.

    Attributes:
        id: Unique identifier for the task (e.g., "task-1").
        description: Human-readable description of what the task involves.
        status: Current status of the task. Valid values: "pending", "wip",
            "done", "blocked", "cancelled", "completed".
        sprint_id: Optional ID of the sprint this task belongs to.
        dependencies: List of task IDs that this task depends on.
        agent: Optional dictionary containing agent assignment information.
        scope: Optional dictionary defining the task's scope and boundaries.
        worker_squad: Optional dictionary containing Worker Squad execution data.
        e2e_test: Optional dictionary containing E2E test results for this task.
    """
    id: str
    description: str
    status: str  # "pending", "wip", "done", "blocked", "cancelled", "completed"
    sprint_id: Optional[str]
    dependencies: List[str]
    agent: Optional[Dict[str, Any]]
    scope: Optional[Dict[str, Any]]
    worker_squad: Optional[Dict[str, Any]]
    e2e_test: Optional[Dict[str, Any]]


class ChatMessageDict(TypedDict):
    """Structure of a chat message.

    Represents a single message in a chat conversation. All fields are required.

    Attributes:
        role: Role of the message sender (e.g., "user", "assistant", "system").
        content: Text content of the message.
        timestamp: ISO format timestamp of when the message was created.
    """
    role: str
    content: str
    timestamp: str


class StateDict(TypedDict, total=False):
    """Structure of the main application state.

    Represents the complete state of the Manifest application, including
    tasks, chat history, and mission structure. This is what gets saved
    to state.json.

    Attributes:
        version: Version string of the state format (e.g., "1.0").
        mission_tree: Dictionary containing the hierarchical mission structure.
        task_checklist: List of all tasks in the system.
        chat_history: Dictionary mapping channel names to lists of messages.
        last_action: String describing the last action performed.
        timestamp: ISO format timestamp of when state was last updated.
    """
    version: str
    mission_tree: Dict[str, Any]
    task_checklist: List[TaskDict]
    chat_history: Dict[str, List[ChatMessageDict]]
    last_action: str
    timestamp: str


class SprintDict(TypedDict, total=False):
    """Sprint dictionary structure."""
    id: str
    name: str
    description: str
    status: str
    integration_tests: Optional[Dict[str, Any]]
    e2e_tests: Optional[Dict[str, Any]]
    created_at: str
    updated_at: str


class PRDDict(TypedDict, total=False):
    """PRD dictionary structure."""
    version: str
    name: str
    description: str
    requirements: List[Dict[str, Any]]
    created_at: str
    updated_at: str


class WorkerSquadStageDict(TypedDict, total=False):
    """Worker Squad stage result dictionary."""
    status: str  # "completed", "failed", "pending"
    output: str
    plan: Optional[str]
    test_skeleton: Optional[str]
    test_plan: Optional[str]
    test_results: Optional[Dict[str, Any]]
    files_modified: Optional[List[str]]
    issues_fixed: Optional[List[str]]
    plan_compliance: Optional[bool]
    findings: Optional[List[str]]
    decision: Optional[str]  # "approved", "rejected", "pending"
    feedback: Optional[str]
    iteration: Optional[int]
    tdd_mode: Optional[bool]


class WorkerSquadResultDict(TypedDict, total=False):
    """Worker Squad execution result dictionary."""
    success: bool
    stages: Dict[str, WorkerSquadStageDict]
    error: Optional[str]


class ModelConfigDict(TypedDict, total=False):
    """Model configuration dictionary."""
    provider: str
    model: str
    api_key: Optional[str]
    use_default_key: bool
    temperature: Optional[float]
    max_tokens: Optional[int]


class AgentConfigDict(TypedDict, total=False):
    """Agent configuration dictionary."""
    agent_type: str
    task_id: str
    context: Dict[str, Any]
    model_config: ModelConfigDict
    stage: Optional[str]


class BlueprintComponentDict(TypedDict, total=False):
    """Blueprint component dictionary."""
    id: str
    name: str
    type: str
    path: Optional[str]
    description: Optional[str]
    dependencies: Optional[List[str]]
    metadata: Optional[Dict[str, Any]]


class DriftConflictDict(TypedDict, total=False):
    """Drift conflict dictionary."""
    component_id: str
    component_name: str
    conflict_type: str
    severity: str  # "ERROR", "WARNING", "INFO"
    message: str
    file_path: Optional[str]
    line_number: Optional[int]
