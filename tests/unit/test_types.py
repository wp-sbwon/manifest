"""
Unit tests for type definitions.

Tests type aliases and data structures.
"""
import pytest
from manifest.core.types import (
    TaskDict,
    PRDDict,
    SprintDict
)


def test_task_dict_structure():
    """Test TaskDict structure."""
    task: TaskDict = {
        "id": "task-1",
        "name": "Test Task",
        "description": "Test",
        "status": "pending",
        "stage": "planning",
        "sprint_id": None,
        "dependencies": [],
        "subtasks": [],
        "created_at": "2026-01-26T00:00:00",
        "updated_at": "2026-01-26T00:00:00"
    }
    
    assert task["id"] == "task-1"
    assert task["name"] == "Test Task"
    assert isinstance(task, dict)


def test_prd_dict_structure():
    """Test PRDDict structure."""
    prd: PRDDict = {
        "title": "Test PRD",
        "requirements": ["Req 1"],
        "version": "1.0"
    }
    
    assert prd["title"] == "Test PRD"
    assert isinstance(prd, dict)


def test_sprint_dict_structure():
    """Test SprintDict structure."""
    sprint: SprintDict = {
        "id": "sprint-1",
        "name": "Test Sprint",
        "status": "planning",
        "tasks": [],
        "created_at": "2026-01-26T00:00:00"
    }
    
    assert sprint["id"] == "sprint-1"
    assert isinstance(sprint, dict)
