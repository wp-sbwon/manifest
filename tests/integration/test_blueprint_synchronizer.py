"""
Unit tests for blueprint_synchronizer.py
"""
import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from manifest.audit.blueprint.blueprint_synchronizer import BlueprintSynchronizer, ConflictReport
from manifest.audit.blueprint.blueprint_comparator import BlueprintConflict, ConflictType
from manifest.audit.code.drift_auditor import Severity


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def synchronizer(temp_dir):
    """Create a BlueprintSynchronizer instance."""
    manifest_dir = temp_dir / ".manifest"
    manifest_dir.mkdir()
    return BlueprintSynchronizer(manifest_dir)


@pytest.fixture
def sample_top_down():
    """Sample top-down blueprint."""
    return {
        "version": "1.0",
        "components": [
            {"id": "comp-1", "name": "TestClass", "type": "class", "methods": ["method1", "method2"]}
        ],
        "contracts": [],
        "zones": {"client": [], "server": [], "data": []}
    }


@pytest.fixture
def sample_bottom_up():
    """Sample bottom-up blueprint."""
    return {
        "version": "1.0",
        "source": "code_extraction",
        "components": [
            {"id": "comp-1", "name": "TestClass", "type": "class", "methods": ["method1"]}
        ],
        "contracts": [],
        "zones": {"client": [], "server": [], "data": []}
    }


def test_detect_mismatch(synchronizer, sample_top_down, sample_bottom_up):
    """Test detecting mismatches between blueprints."""
    report = synchronizer.detect_mismatch(sample_top_down, sample_bottom_up)
    
    assert report is not None
    assert len(report.conflicts) > 0
    assert report.status == "pending"


def test_detect_mismatch_no_conflicts(synchronizer):
    """Test that no report is created when blueprints match."""
    blueprint = {
        "version": "1.0",
        "components": [],
        "contracts": [],
        "zones": {"client": [], "server": [], "data": []}
    }
    
    report = synchronizer.detect_mismatch(blueprint, blueprint)
    assert report is None


def test_create_conflict_issue(synchronizer):
    """Test creating conflict issue."""
    conflicts = [
        BlueprintConflict(
            severity=Severity.ERROR,
            type=ConflictType.MISSING_COMPONENT,
            message="Test conflict"
        )
    ]
    
    issue = synchronizer.create_conflict_issue(conflicts, "task-1")
    
    assert issue["type"] == "blueprint_conflict"
    assert issue["task_id"] == "task-1"
    assert issue["summary"]["total"] == 1
    assert issue["summary"]["errors"] == 1


def test_save_and_load_conflict_report(synchronizer, sample_top_down, sample_bottom_up):
    """Test saving and loading conflict reports."""
    report = synchronizer.detect_mismatch(sample_top_down, sample_bottom_up)
    assert report is not None
    
    report.task_id = "test-task-1"
    file_path = synchronizer.save_conflict_report(report)
    
    assert file_path.exists()
    
    # Load report
    loaded = synchronizer.load_conflict_report(file_path)
    assert loaded is not None
    assert loaded.task_id == "test-task-1"
    assert len(loaded.conflicts) == len(report.conflicts)


def test_resend_to_worker_squad(synchronizer):
    """Test preparing resend request for worker squad."""
    conflict_issue = {
        "type": "blueprint_conflict",
        "task_id": "task-1",
        "conflicts": []
    }
    
    request = synchronizer.resend_to_worker_squad("task-1", conflict_issue)
    
    assert request["action"] == "resend_with_conflict"
    assert request["task_id"] == "task-1"
    assert "conflict_issue" in request


def test_request_planner_review(synchronizer):
    """Test requesting planner review."""
    conflict_issue = {
        "type": "blueprint_conflict",
        "conflicts": []
    }
    
    request = synchronizer.request_planner_review(conflict_issue)
    
    assert request["action"] == "planner_review"
    assert "request" in request
    assert request["request"]["options"] == ["necessary", "violation"]


def test_request_user_approval_necessary(synchronizer):
    """Test requesting user approval when planner flags as necessary."""
    conflict_issue = {
        "type": "blueprint_conflict",
        "conflicts": []
    }
    
    request = synchronizer.request_user_approval(conflict_issue, "necessary")
    
    assert request["action"] == "user_approval"
    assert request["planner_flag"] == "necessary"


def test_request_user_approval_violation(synchronizer):
    """Test that no approval is needed when planner flags as violation."""
    conflict_issue = {
        "type": "blueprint_conflict",
        "conflicts": []
    }
    
    request = synchronizer.request_user_approval(conflict_issue, "violation")
    
    assert request["action"] == "no_approval_needed"
    assert request["planner_flag"] == "violation"


def test_update_conflict_status(synchronizer, sample_top_down, sample_bottom_up):
    """Test updating conflict report status."""
    report = synchronizer.detect_mismatch(sample_top_down, sample_bottom_up)
    assert report is not None
    
    report.task_id = "test-task-1"
    synchronizer.save_conflict_report(report)
    
    # Update status
    result = synchronizer.update_conflict_status(
        report,
        "planner_review",
        planner_flag="necessary"
    )
    
    assert result is True
    assert report.status == "planner_review"
    assert report.planner_flag == "necessary"


def test_sync_blueprints_strict_mode(synchronizer, sample_top_down, sample_bottom_up):
    """Test strict mode synchronization."""
    result = synchronizer.sync_blueprints(
        sample_top_down,
        sample_bottom_up,
        mode="strict"
    )
    
    assert result["success"] is False
    assert result["blocked"] is True


def test_sync_blueprints_workflow_mode(synchronizer, sample_top_down, sample_bottom_up):
    """Test workflow mode synchronization."""
    result = synchronizer.sync_blueprints(
        sample_top_down,
        sample_bottom_up,
        mode="workflow"
    )
    
    assert result["workflow_triggered"] is True
    assert "conflict_report" in result


def test_sync_blueprints_no_conflicts(synchronizer):
    """Test synchronization when blueprints match."""
    blueprint = {
        "version": "1.0",
        "components": [],
        "contracts": [],
        "zones": {"client": [], "server": [], "data": []}
    }
    
    result = synchronizer.sync_blueprints(blueprint, blueprint, mode="workflow")
    
    assert result["success"] is True
    assert result["workflow_triggered"] is False
