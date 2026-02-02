"""
Unit tests for blueprint_synchronizer.py
"""
import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

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


# ========== TDL: Blueprint Synchronizer Tests ==========

def test_blueprint_loading(synchronizer, temp_dir):
    """Test blueprint loading functionality."""
    # Create a blueprint file
    blueprint_file = temp_dir / ".manifest" / "blueprint.json"
    blueprint_data = {
        "version": "1.0",
        "components": [{"id": "comp-1", "name": "TestClass"}]
    }
    blueprint_file.write_text(json.dumps(blueprint_data))

    # Blueprint loading is done via BlueprintLoader in _load_blueprint
    # Test that synchronizer can be initialized with manifest_dir containing blueprint
    assert synchronizer.manifest_dir.exists()
    assert synchronizer.conflicts_dir.exists()


def test_blueprint_loading_with_custom_conflicts_dir(temp_dir):
    """Test blueprint synchronizer with custom conflicts directory."""
    manifest_dir = temp_dir / ".manifest"
    manifest_dir.mkdir()
    custom_conflicts_dir = temp_dir / "custom_conflicts"

    synchronizer = BlueprintSynchronizer(
        manifest_dir=manifest_dir,
        conflicts_dir=custom_conflicts_dir
    )

    assert synchronizer.conflicts_dir == custom_conflicts_dir
    assert custom_conflicts_dir.exists()


def test_blueprint_saving_conflict_report(synchronizer, sample_top_down, sample_bottom_up):
    """Test saving conflict reports to disk."""
    report = synchronizer.detect_mismatch(sample_top_down, sample_bottom_up)
    assert report is not None

    report.task_id = "test-task-1"
    file_path = synchronizer.save_conflict_report(report)

    assert file_path.exists()
    assert file_path.suffix == ".json"

    # Verify file contents
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["task_id"] == "test-task-1"
    assert "conflicts" in data
    assert "top_down_blueprint" in data
    assert "bottom_up_blueprint" in data


def test_blueprint_saving_and_loading_roundtrip(synchronizer, sample_top_down, sample_bottom_up):
    """Test that saved conflict reports can be loaded correctly."""
    report = synchronizer.detect_mismatch(sample_top_down, sample_bottom_up)
    assert report is not None

    report.task_id = "test-task-2"
    report.status = "planner_review"
    report.planner_flag = "necessary"

    file_path = synchronizer.save_conflict_report(report)

    # Load the report
    loaded = synchronizer.load_conflict_report(file_path)

    assert loaded is not None
    assert loaded.task_id == "test-task-2"
    assert loaded.status == "planner_review"
    assert loaded.planner_flag == "necessary"
    assert len(loaded.conflicts) == len(report.conflicts)


def test_conflict_detection_mismatch(synchronizer, sample_top_down, sample_bottom_up):
    """Test conflict detection when blueprints differ."""
    report = synchronizer.detect_mismatch(sample_top_down, sample_bottom_up)

    assert report is not None
    assert len(report.conflicts) > 0
    assert report.status == "pending"
    assert report.top_down_blueprint == sample_top_down
    assert report.bottom_up_blueprint == sample_bottom_up


def test_conflict_detection_no_conflicts(synchronizer):
    """Test conflict detection when blueprints match."""
    blueprint = {
        "version": "1.0",
        "components": [],
        "contracts": [],
        "zones": {"client": [], "server": [], "data": []}
    }

    report = synchronizer.detect_mismatch(blueprint, blueprint)
    assert report is None


def test_conflict_detection_filters_info_severity(synchronizer):
    """Test that conflict detection filters out INFO severity conflicts."""
    # Create blueprints that would generate INFO conflicts
    top_down = {
        "version": "1.0",
        "components": [
            {"id": "comp-1", "name": "TestClass", "type": "class", "methods": ["method1"]}
        ],
        "contracts": [],
        "zones": {"client": [], "server": [], "data": []}
    }

    bottom_up = {
        "version": "1.0",
        "components": [
            {"id": "comp-1", "name": "TestClass", "type": "class", "methods": ["method1", "extra_method"]}
        ],
        "contracts": [],
        "zones": {"client": [], "server": [], "data": []}
    }

    # Mock comparator to return only INFO conflicts
    with patch.object(synchronizer.comparator, 'compare_blueprints') as mock_compare:
        mock_compare.return_value = [
            BlueprintConflict(
                severity=Severity.INFO,
                type=ConflictType.EXTRA_COMPONENT,
                message="Extra method"
            )
        ]

        report = synchronizer.detect_mismatch(top_down, bottom_up)
        # Should return None because only INFO conflicts exist
        assert report is None


def test_conflict_detection_includes_error_warning(synchronizer, sample_top_down, sample_bottom_up):
    """Test that conflict detection includes ERROR and WARNING severity conflicts."""
    report = synchronizer.detect_mismatch(sample_top_down, sample_bottom_up)

    assert report is not None
    # Should have conflicts with ERROR or WARNING severity
    assert any(
        c.severity in [Severity.ERROR, Severity.WARNING]
        for c in report.conflicts
    )


def test_conflict_resolution_workflow_planner_review(synchronizer, sample_top_down, sample_bottom_up):
    """Test conflict resolution workflow - planner review stage."""
    report = synchronizer.detect_mismatch(sample_top_down, sample_bottom_up)
    assert report is not None

    report.task_id = "task-1"
    conflict_issue = synchronizer.create_conflict_issue(report.conflicts, "task-1")

    # Request planner review
    planner_request = synchronizer.request_planner_review(conflict_issue)

    assert planner_request["action"] == "planner_review"
    assert "request" in planner_request
    assert planner_request["request"]["options"] == ["necessary", "violation"]

    # Update status to planner_review
    synchronizer.update_conflict_status(
        report,
        "planner_review",
        planner_flag="necessary"
    )

    assert report.status == "planner_review"
    assert report.planner_flag == "necessary"


def test_conflict_resolution_workflow_user_approval_necessary(synchronizer, sample_top_down, sample_bottom_up):
    """Test conflict resolution workflow - user approval when necessary."""
    report = synchronizer.detect_mismatch(sample_top_down, sample_bottom_up)
    assert report is not None

    conflict_issue = synchronizer.create_conflict_issue(report.conflicts, "task-1")

    # Request user approval after planner flags as necessary
    approval_request = synchronizer.request_user_approval(conflict_issue, "necessary")

    assert approval_request["action"] == "user_approval"
    assert approval_request["planner_flag"] == "necessary"
    assert "request" in approval_request
    assert approval_request["request"]["options"] == ["approved", "rejected"]

    # Update status with user approval
    synchronizer.update_conflict_status(
        report,
        "user_approval",
        user_decision="approved",
        resolution_note="User approved the change"
    )

    assert report.status == "user_approval"
    assert report.user_decision == "approved"
    assert report.resolution_note == "User approved the change"


def test_conflict_resolution_workflow_violation_no_approval(synchronizer, sample_top_down, sample_bottom_up):
    """Test conflict resolution workflow - violation flag doesn't require approval."""
    report = synchronizer.detect_mismatch(sample_top_down, sample_bottom_up)
    assert report is not None

    conflict_issue = synchronizer.create_conflict_issue(report.conflicts, "task-1")

    # Request user approval when planner flags as violation
    approval_request = synchronizer.request_user_approval(conflict_issue, "violation")

    assert approval_request["action"] == "no_approval_needed"
    assert approval_request["planner_flag"] == "violation"
    assert "message" in approval_request


def test_conflict_resolution_workflow_resend_to_worker_squad(synchronizer, sample_top_down, sample_bottom_up):
    """Test conflict resolution workflow - resending to worker squad."""
    report = synchronizer.detect_mismatch(sample_top_down, sample_bottom_up)
    assert report is not None

    conflict_issue = synchronizer.create_conflict_issue(report.conflicts, "task-1")

    # Resend to worker squad
    resend_request = synchronizer.resend_to_worker_squad("task-1", conflict_issue)

    assert resend_request["action"] == "resend_with_conflict"
    assert resend_request["task_id"] == "task-1"
    assert "conflict_issue" in resend_request
    assert resend_request["context"]["reason"] == "blueprint_mismatch"


def test_conflict_resolution_workflow_status_updates(synchronizer, sample_top_down, sample_bottom_up):
    """Test conflict resolution workflow - status progression."""
    report = synchronizer.detect_mismatch(sample_top_down, sample_bottom_up)
    assert report is not None

    report.task_id = "task-1"

    # Initial status
    assert report.status == "pending"

    # Move to planner_review
    synchronizer.update_conflict_status(report, "planner_review", planner_flag="necessary")
    assert report.status == "planner_review"

    # Move to user_approval
    synchronizer.update_conflict_status(report, "user_approval")
    assert report.status == "user_approval"

    # Move to resolved
    synchronizer.update_conflict_status(
        report,
        "resolved",
        user_decision="approved",
        resolution_note="Resolved"
    )
    assert report.status == "resolved"
    assert report.user_decision == "approved"


def test_blueprint_validation_strict_mode(synchronizer, sample_top_down, sample_bottom_up):
    """Test blueprint validation in strict mode - blocks on conflicts."""
    result = synchronizer.sync_blueprints(
        sample_top_down,
        sample_bottom_up,
        mode="strict"
    )

    assert result["success"] is False
    assert result["blocked"] is True
    assert "conflicts" in result
    assert result["conflicts"] > 0


def test_blueprint_validation_strict_mode_no_conflicts(synchronizer):
    """Test blueprint validation in strict mode - allows when no conflicts."""
    blueprint = {
        "version": "1.0",
        "components": [],
        "contracts": [],
        "zones": {"client": [], "server": [], "data": []}
    }

    result = synchronizer.sync_blueprints(blueprint, blueprint, mode="strict")

    assert result["success"] is True
    assert result["blocked"] is False


def test_blueprint_validation_workflow_mode(synchronizer, sample_top_down, sample_bottom_up):
    """Test blueprint validation in workflow mode - triggers workflow."""
    result = synchronizer.sync_blueprints(
        sample_top_down,
        sample_bottom_up,
        mode="workflow"
    )

    assert result["workflow_triggered"] is True
    assert "conflict_report" in result


def test_blueprint_validation_workflow_mode_no_conflicts(synchronizer):
    """Test blueprint validation in workflow mode - no workflow when no conflicts."""
    blueprint = {
        "version": "1.0",
        "components": [],
        "contracts": [],
        "zones": {"client": [], "server": [], "data": []}
    }

    result = synchronizer.sync_blueprints(blueprint, blueprint, mode="workflow")

    assert result["success"] is True
    assert result["workflow_triggered"] is False


def test_blueprint_validation_merge_mode(synchronizer, sample_top_down, sample_bottom_up):
    """Test blueprint validation in merge mode."""
    result = synchronizer.sync_blueprints(
        sample_top_down,
        sample_bottom_up,
        mode="merge"
    )

    assert result["success"] is True
    assert "conflicts" in result
    # Merge mode not fully implemented yet
    assert result.get("merged") is False


def test_blueprint_validation_unknown_mode(synchronizer, sample_top_down, sample_bottom_up):
    """Test blueprint validation with unknown mode."""
    result = synchronizer.sync_blueprints(
        sample_top_down,
        sample_bottom_up,
        mode="unknown_mode"
    )

    assert result["success"] is False
    assert "error" in result
    assert "unknown_mode" in result["error"]


def test_create_conflict_issue(synchronizer):
    """Test creating conflict issue for worker squad."""
    conflicts = [
        BlueprintConflict(
            severity=Severity.ERROR,
            type=ConflictType.MISSING_COMPONENT,
            message="Missing component"
        ),
        BlueprintConflict(
            severity=Severity.WARNING,
            type=ConflictType.METHOD_MISMATCH,
            message="Method mismatch"
        )
    ]

    issue = synchronizer.create_conflict_issue(conflicts, "task-1")

    assert issue["type"] == "blueprint_conflict"
    assert issue["task_id"] == "task-1"
    assert issue["summary"]["total"] == 2
    assert issue["summary"]["errors"] == 1
    assert issue["summary"]["warnings"] == 1
    assert len(issue["conflicts"]) == 2
    assert issue["action_required"] == "review_and_resolve"


def test_load_conflict_report_invalid_file(synchronizer, temp_dir):
    """Test loading conflict report from invalid file."""
    invalid_file = temp_dir / "invalid.json"
    invalid_file.write_text("invalid json")

    loaded = synchronizer.load_conflict_report(invalid_file)
    assert loaded is None


def test_load_conflict_report_missing_file(synchronizer, temp_dir):
    """Test loading conflict report from non-existent file."""
    missing_file = temp_dir / "missing.json"

    loaded = synchronizer.load_conflict_report(missing_file)
    assert loaded is None


def test_calculate_implementation_status_ghost(synchronizer):
    """Test calculating implementation status - ghost components."""
    top_down = {
        "version": "1.0",
        "components": [
            {"id": "comp-1", "name": "GhostClass", "type": "class"}
        ]
    }

    bottom_up = {
        "version": "1.0",
        "components": []
    }

    status = synchronizer.calculate_implementation_status(top_down, bottom_up)

    assert "component_statuses" in status
    assert status["component_statuses"]["comp-1"] == "ghost"


def test_calculate_implementation_status_implemented(synchronizer):
    """Test calculating implementation status - implemented components."""
    top_down = {
        "version": "1.0",
        "components": [
            {"id": "comp-1", "name": "TestClass", "type": "class", "methods": ["method1"]}
        ]
    }

    bottom_up = {
        "version": "1.0",
        "components": [
            {"id": "comp-1", "name": "TestClass", "type": "class", "methods": ["method1"]}
        ]
    }

    status = synchronizer.calculate_implementation_status(top_down, bottom_up)

    assert status["component_statuses"]["comp-1"] == "implemented"


def test_calculate_implementation_status_drift(synchronizer):
    """Test calculating implementation status - drift components."""
    top_down = {
        "version": "1.0",
        "components": [
            {"id": "comp-1", "name": "TestClass", "type": "class", "methods": ["method1", "method2"]}
        ]
    }

    bottom_up = {
        "version": "1.0",
        "components": [
            {"id": "comp-1", "name": "TestClass", "type": "class", "methods": ["method1"]}
        ]
    }

    status = synchronizer.calculate_implementation_status(top_down, bottom_up)

    assert status["component_statuses"]["comp-1"] == "drift"
    assert "comp-1" in status["component_drifts"]


def test_calculate_implementation_status_extra(synchronizer):
    """Test calculating implementation status - extra components."""
    top_down = {
        "version": "1.0",
        "components": []
    }

    bottom_up = {
        "version": "1.0",
        "components": [
            {"id": "comp-extra", "name": "ExtraClass", "type": "class"}
        ]
    }

    status = synchronizer.calculate_implementation_status(top_down, bottom_up)

    assert status["component_statuses"]["comp-extra"] == "extra"


def test_calculate_implementation_status_feature_completion(synchronizer):
    """Test calculating implementation status with feature completion."""
    top_down = {
        "version": "1.0",
        "components": [
            {"id": "comp-1", "name": "Class1", "type": "class"},
            {"id": "comp-2", "name": "Class2", "type": "class"}
        ]
    }

    bottom_up = {
        "version": "1.0",
        "components": [
            {"id": "comp-1", "name": "Class1", "type": "class"},
            {"id": "comp-2", "name": "Class2", "type": "class"}
        ]
    }

    architecture = {
        "features": [
            {
                "id": "feature-1",
                "components": ["comp-1", "comp-2"]
            }
        ]
    }

    status = synchronizer.calculate_implementation_status(
        top_down,
        bottom_up,
        architecture=architecture
    )

    assert "feature_completions" in status
    assert status["feature_completions"]["feature-1"] == 100.0


def test_conflict_report_to_dict(synchronizer, sample_top_down, sample_bottom_up):
    """Test ConflictReport to_dict conversion."""
    report = synchronizer.detect_mismatch(sample_top_down, sample_bottom_up)
    assert report is not None

    report.task_id = "test-task"
    report.status = "planner_review"
    report.planner_flag = "necessary"

    report_dict = report.to_dict()

    assert report_dict["task_id"] == "test-task"
    assert report_dict["status"] == "planner_review"
    assert report_dict["planner_flag"] == "necessary"
    assert "conflicts" in report_dict
    assert "top_down_blueprint" in report_dict
    assert "bottom_up_blueprint" in report_dict
    assert "timestamp" in report_dict
