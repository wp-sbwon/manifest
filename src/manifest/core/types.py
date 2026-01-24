"""
Type definitions for Manifest using TypedDict.
Provides structured type hints for commonly used dictionaries.
"""
from typing import TypedDict, List, Optional, Dict, Any
from datetime import datetime


class TaskDict(TypedDict, total=False):
    """Task dictionary structure."""
    id: str
    description: str
    status: str  # "pending", "wip", "done", "blocked"
    sprint_id: Optional[str]
    agent: Optional[Dict[str, Any]]
    scope: Optional[Dict[str, Any]]
    worker_squad: Optional[Dict[str, Any]]
    e2e_test: Optional[Dict[str, Any]]


class ChatMessageDict(TypedDict):
    """Chat message dictionary structure."""
    role: str
    content: str
    timestamp: str


class StateDict(TypedDict, total=False):
    """State dictionary structure."""
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
