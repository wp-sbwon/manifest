"""
Blueprint synchronization and conflict resolution.

This module handles synchronization between top-down blueprints (intended design)
and bottom-up blueprints (extracted from code). When conflicts are detected,
it manages a resolution workflow involving worker squad review, planner analysis,
and user approval.

The synchronizer detects mismatches, creates conflict reports, and coordinates
the resolution process through multiple stages.
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict

from manifest.audit.blueprint.blueprint_comparator import BlueprintComparator, BlueprintConflict, ConflictType
from manifest.audit.code.deviation_auditor import Severity
from manifest.audit import doc_set
from manifest.audit.doc_comparator import compare_intent, compare_architecture, DocDiff


@dataclass
class ConflictReport:
    """Represents a conflict report for blueprint synchronization workflow.

    Contains all information about conflicts between top-down and bottom-up
    blueprints, including the conflicts themselves, both blueprint versions,
    and the resolution workflow status.

    Attributes:
        task_id: ID of the task where conflicts were detected.
        conflicts: List of BlueprintConflict objects describing the mismatches.
        top_down_blueprint: The intended design blueprint.
        bottom_up_blueprint: The blueprint extracted from actual code.
        timestamp: ISO timestamp when the conflict was detected.
        status: Current workflow status. Values: "pending", "planner_review",
            "user_approval", "resolved", "rejected".
        planner_flag: Planner's assessment. Values: "necessary" (change is needed),
            "violation" (change violates architecture).
        user_decision: User's final decision. Values: "approved", "rejected".
        resolution_note: Optional note explaining how the conflict was resolved.
    """
    task_id: str
    conflicts: List[BlueprintConflict]
    top_down_blueprint: Dict[str, Any]
    bottom_up_blueprint: Dict[str, Any]
    timestamp: str
    status: str = "pending"  # "pending", "planner_review", "user_approval", "resolved", "rejected"
    planner_flag: Optional[str] = None  # "necessary", "violation"
    user_decision: Optional[str] = None  # "approved", "rejected"
    resolution_note: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert the conflict report to a dictionary.

        Useful for serialization to JSON or storage. Converts nested
        BlueprintConflict objects to dictionaries as well.

        Returns:
            Dictionary representation of the conflict report.
        """
        return {
            "task_id": self.task_id,
            "conflicts": [c.to_dict() for c in self.conflicts],
            "top_down_blueprint": self.top_down_blueprint,
            "bottom_up_blueprint": self.bottom_up_blueprint,
            "timestamp": self.timestamp,
            "status": self.status,
            "planner_flag": self.planner_flag,
            "user_decision": self.user_decision,
            "resolution_note": self.resolution_note
        }


class BlueprintSynchronizer:
    """Enforces synchronization between top-down and bottom-up blueprints.

    Detects conflicts when code structure (bottom-up) doesn't match the
    intended design (top-down). Manages the conflict resolution workflow
    through planner review and user approval stages.

    Attributes:
        manifest_dir: Path to .manifest directory.
        conflicts_dir: Directory where conflict reports are stored.
        comparator: BlueprintComparator instance for comparing blueprints.
    """

    def __init__(self, manifest_dir: Path = None, conflicts_dir: Path = None):
        """Initialize the blueprint synchronizer.

        Args:
            manifest_dir: Path to .manifest directory. Defaults to .manifest.
            conflicts_dir: Optional custom directory for conflict reports.
                Defaults to manifest_dir/conflicts.
        """
        self.manifest_dir = manifest_dir or Path(".manifest")
        self.conflicts_dir = conflicts_dir or (self.manifest_dir / "conflicts")
        self.conflicts_dir.mkdir(parents=True, exist_ok=True)
        self.comparator = BlueprintComparator()

    def compare_all_docs(self, manifest_dir: Optional[Path] = None) -> Dict[str, Any]:
        """
        Compare all doc types (blueprint, intent, architecture) between top-down and bottom-up.
        Returns implementation progress (missing in bottom-up) separately from deviation (conflicts).
        """
        manifest_dir = manifest_dir or self.manifest_dir
        top_blueprint = doc_set.load_top_down(manifest_dir, "blueprint")
        bottom_blueprint = doc_set.load_bottom_up(manifest_dir, "blueprint")
        blueprint_conflicts = self.comparator.compare_blueprints(top_blueprint, bottom_blueprint)
        implementation_progress = [c for c in blueprint_conflicts if c.severity == Severity.IN_PROGRESS]
        deviation_conflicts = [c for c in blueprint_conflicts if c.severity in [Severity.ERROR, Severity.WARNING]]
        info_conflicts = [c for c in blueprint_conflicts if c.severity == Severity.INFO]

        top_intent = doc_set.load_top_down(manifest_dir, "intent")
        bottom_intent = doc_set.load_bottom_up(manifest_dir, "intent")
        intent_diffs = compare_intent(top_intent, bottom_intent)

        top_architecture = doc_set.load_top_down(manifest_dir, "architecture")
        bottom_architecture = doc_set.load_bottom_up(manifest_dir, "architecture")
        architecture_diffs = compare_architecture(top_architecture, bottom_architecture)

        return {
            "blueprint": {
                "implementation_progress": [c.to_dict() for c in implementation_progress],
                "deviation_conflicts": [c.to_dict() for c in deviation_conflicts],
                "info": [c.to_dict() for c in info_conflicts],
            },
            "intent": {"diffs": [d.to_dict() for d in intent_diffs]},
            "architecture": {"diffs": [d.to_dict() for d in architecture_diffs]},
        }

    def detect_mismatch(
        self,
        top_down: Dict[str, Any],
        bottom_up: Dict[str, Any]
    ) -> Optional[ConflictReport]:
        """Detect conflicts between two blueprints and create a conflict report.

        Compares the top-down (intended) blueprint against the bottom-up
        (extracted from code) blueprint. Only significant conflicts (ERROR or
        WARNING severity) are included in the report; INFO-level conflicts
        are filtered out.

        Args:
            top_down: Dictionary containing the intended design blueprint.
            bottom_up: Dictionary containing the blueprint extracted from code.

        Returns:
            ConflictReport if conflicts are found, None if blueprints match
            or only minor (INFO) conflicts exist.
        """
        conflicts = self.comparator.compare_blueprints(top_down, bottom_up)

        if not conflicts:
            return None

        # Filter to significant conflicts only (ERROR, WARNING). IN_PROGRESS = implementation progress, not drift.
        significant_conflicts = [
            c for c in conflicts
            if c.severity in [Severity.ERROR, Severity.WARNING]
        ]

        if not significant_conflicts:
            return None

        # Create conflict report
        report = ConflictReport(
            task_id="",  # Will be set when task is known
            conflicts=significant_conflicts,
            top_down_blueprint=top_down,
            bottom_up_blueprint=bottom_up,
            timestamp=datetime.utcnow().isoformat()
        )

        return report

    def create_conflict_issue(
        self,
        conflicts: List[BlueprintConflict],
        task_id: str = ""
    ) -> Dict[str, Any]:
        """Generate structured conflict issue for worker squad."""
        grouped = self.comparator.get_conflicts_by_severity(conflicts)

        issue = {
            "type": "blueprint_conflict",
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total": len(conflicts),
                "errors": len(grouped.get("error", [])),
                "warnings": len(grouped.get("warning", [])),
                "info": len(grouped.get("info", []))
            },
            "conflicts": [c.to_dict() for c in conflicts],
            "action_required": "review_and_resolve"
        }

        return issue

    def save_conflict_report(self, report: ConflictReport) -> Path:
        """Save conflict report to file."""
        timestamp = report.timestamp.replace(":", "-").replace(".", "-")
        task_id = report.task_id or "unknown"
        filename = f"conflict_{timestamp}_{task_id}.json"
        file_path = self.conflicts_dir / filename

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)

        return file_path

    def load_conflict_report(self, file_path: Path) -> Optional[ConflictReport]:
        """Load conflict report from file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Reconstruct conflicts
            conflicts = []
            for c_dict in data.get("conflicts", []):
                # Convert string type to ConflictType enum
                conflict_type_str = c_dict["type"]
                if isinstance(conflict_type_str, str):
                    try:
                        conflict_type = ConflictType(conflict_type_str)
                    except ValueError:
                        # Fallback: try to find by value
                        conflict_type = next(
                            (ct for ct in ConflictType if ct.value == conflict_type_str),
                            ConflictType.METHOD_MISMATCH  # Default fallback
                        )
                else:
                    conflict_type = conflict_type_str

                conflict = BlueprintConflict(
                    severity=Severity(c_dict["severity"]),
                    type=conflict_type,
                    message=c_dict["message"],
                    top_down_component=c_dict.get("top_down_component"),
                    bottom_up_component=c_dict.get("bottom_up_component"),
                    file_path=c_dict.get("file_path"),
                    component_id=c_dict.get("component_id")
                )
                conflicts.append(conflict)

            report = ConflictReport(
                task_id=data.get("task_id", ""),
                conflicts=conflicts,
                top_down_blueprint=data.get("top_down_blueprint", {}),
                bottom_up_blueprint=data.get("bottom_up_blueprint", {}),
                timestamp=data.get("timestamp", ""),
                status=data.get("status", "pending"),
                planner_flag=data.get("planner_flag"),
                user_decision=data.get("user_decision"),
                resolution_note=data.get("resolution_note")
            )

            return report
        except Exception:
            return None

    def resend_to_worker_squad(
        self,
        task_id: str,
        conflict_issue: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare task for resending to worker squad with conflict context."""
        return {
            "action": "resend_with_conflict",
            "task_id": task_id,
            "conflict_issue": conflict_issue,
            "context": {
                "reason": "blueprint_mismatch",
                "requires_resolution": True
            }
        }

    def request_planner_review(
        self,
        conflict_issue: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Request planner to review conflict and set flag."""
        return {
            "action": "planner_review",
            "conflict_issue": conflict_issue,
            "request": {
                "type": "blueprint_conflict_review",
                "question": "Is this code change necessary or an architectural violation?",
                "options": ["necessary", "violation"]
            }
        }

    def request_user_approval(
        self,
        conflict_issue: Dict[str, Any],
        planner_flag: str
    ) -> Dict[str, Any]:
        """Request user approval for necessary changes."""
        if planner_flag != "necessary":
            return {
                "action": "no_approval_needed",
                "planner_flag": planner_flag,
                "message": "Planner flagged as violation, no user approval needed"
            }

        return {
            "action": "user_approval",
            "conflict_issue": conflict_issue,
            "planner_flag": planner_flag,
            "request": {
                "type": "blueprint_sync_approval",
                "message": "Planner flagged change as necessary. Approve to sync blueprint?",
                "options": ["approved", "rejected"]
            }
        }

    def update_conflict_status(
        self,
        report: ConflictReport,
        status: str,
        planner_flag: Optional[str] = None,
        user_decision: Optional[str] = None,
        resolution_note: Optional[str] = None
    ) -> bool:
        """Update conflict report status."""
        report.status = status
        if planner_flag:
            report.planner_flag = planner_flag
        if user_decision:
            report.user_decision = user_decision
        if resolution_note:
            report.resolution_note = resolution_note

        self.save_conflict_report(report)
        return True

    def sync_blueprints(
        self,
        top_down: Dict[str, Any],
        bottom_up: Dict[str, Any],
        mode: str = "workflow"  # "strict", "workflow", "merge"
    ) -> Dict[str, Any]:
        """Synchronize blueprints based on mode."""
        if mode == "strict":
            # Block if conflicts exist
            conflicts = self.comparator.compare_blueprints(top_down, bottom_up)
            significant = [c for c in conflicts if c.severity in [Severity.ERROR, Severity.WARNING]]
            if significant:
                return {
                    "success": False,
                    "blocked": True,
                    "conflicts": len(significant),
                    "message": "Synchronization blocked due to conflicts"
                }
            return {"success": True, "blocked": False}

        elif mode == "workflow":
            # Trigger conflict workflow
            report = self.detect_mismatch(top_down, bottom_up)
            if report:
                return {
                    "success": False,
                    "workflow_triggered": True,
                    "conflict_report": report.to_dict()
                }
            return {"success": True, "workflow_triggered": False}

        elif mode == "merge":
            # Auto-merge compatible changes (future enhancement)
            # For now, just return conflicts
            conflicts = self.comparator.compare_blueprints(top_down, bottom_up)
            return {
                "success": True,
                "merged": False,  # Not implemented yet
                "conflicts": len(conflicts)
            }

        return {"success": False, "error": f"Unknown mode: {mode}"}

    def calculate_implementation_status(
        self,
        top_down: Dict[str, Any],
        bottom_up: Dict[str, Any],
        architecture: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculate implementation status for components (planned/deviation/healthy/extra).
        Also calculates completion percentage for features.

        Args:
            top_down: Top-down blueprint (design)
            bottom_up: Bottom-up blueprint (code)
            architecture: Architecture data (optional, for feature-level completion)

        Returns:
            Dict with component statuses and feature completion percentages
        """
        from manifest.audit.blueprint.blueprint_metadata import load_blueprint_with_metadata

        # Build component lookup
        td_components_by_id: Dict[str, Dict[str, Any]] = {}
        td_components_by_name: Dict[str, Dict[str, Any]] = {}
        for comp in top_down.get("components", []):
            comp_id = comp.get("id", "")
            comp_name = comp.get("name", "")
            if comp_id:
                td_components_by_id[comp_id] = comp
            if comp_name:
                td_components_by_name[comp_name] = comp

        bu_components_by_id: Dict[str, Dict[str, Any]] = {}
        bu_components_by_name: Dict[str, Dict[str, Any]] = {}
        for comp in bottom_up.get("components", []):
            comp_id = comp.get("id", "")
            comp_name = comp.get("name", "")
            if comp_id:
                bu_components_by_id[comp_id] = comp
            if comp_name:
                bu_components_by_name[comp_name] = comp

        # Calculate status for each top-down component (internal names: healthy, planned, deviation, extra)
        component_statuses: Dict[str, str] = {}
        component_deviations: Dict[str, List[str]] = {}

        for comp_id, td_comp in td_components_by_id.items():
            comp_name = td_comp.get("name", "")

            # Try to find in bottom-up by ID first, then by name
            bu_comp = bu_components_by_id.get(comp_id)
            if not bu_comp and comp_name:
                bu_comp = bu_components_by_name.get(comp_name)

            if not bu_comp:
                # In design plan but not in actual code
                component_statuses[comp_id] = "planned"
            else:
                # Exists in both - check for deviation
                conflicts = self.comparator.compare_components([td_comp], [bu_comp])
                significant_conflicts = [
                    c for c in conflicts
                    if c.severity in [Severity.ERROR, Severity.WARNING]
                ]

                if significant_conflicts:
                    component_statuses[comp_id] = "deviation"
                    component_deviations[comp_id] = [c.message for c in significant_conflicts]
                else:
                    component_statuses[comp_id] = "healthy"

        # Mark extra components (in actual code but not in design plan)
        for comp_id, bu_comp in bu_components_by_id.items():
            comp_name = bu_comp.get("name", "")
            if comp_id not in td_components_by_id:
                if comp_name not in td_components_by_name:
                    component_statuses[comp_id] = "extra"

        # Feature completion percentages
        feature_completions: Dict[str, float] = {}
        if architecture:
            features = architecture.get("features", [])
            for feature in features:
                feature_id = feature.get("id", "")
                feature_components = feature.get("components", [])

                if not feature_components:
                    feature_completions[feature_id] = 0.0
                    continue

                healthy_count = 0
                total_count = len(feature_components)
                for comp_id in feature_components:
                    status = component_statuses.get(comp_id, "planned")
                    if status == "healthy":
                        healthy_count += 1
                    elif status == "deviation":
                        healthy_count += 0.5

                if total_count > 0:
                    completion = (healthy_count / total_count) * 100
                    feature_completions[feature_id] = round(completion, 1)
                else:
                    feature_completions[feature_id] = 0.0

        return {
            "component_statuses": component_statuses,
            "component_deviations": component_deviations,
            "feature_completions": feature_completions
        }

    def update_architecture_with_status(
        self,
        architecture: Dict[str, Any],
        status_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update architecture.json with implementation status and completion percentages.

        Args:
            architecture: Architecture dictionary
            status_info: Status information from calculate_implementation_status

        Returns:
            Updated architecture dictionary
        """
        component_statuses = status_info.get("component_statuses", {})
        component_deviations = status_info.get("component_deviations", {})
        feature_completions = status_info.get("feature_completions", {})

        if "components" not in architecture:
            architecture["components"] = []

        for comp in architecture.get("components", []):
            comp_id = comp.get("id", "")
            if comp_id in component_statuses:
                comp["status"] = component_statuses[comp_id]
                if comp_id in component_deviations:
                    comp["deviation_details"] = component_deviations[comp_id]

        # Update feature completion percentages
        for feature in architecture.get("features", []):
            feature_id = feature.get("id", "")
            if feature_id in feature_completions:
                feature["completion_percentage"] = feature_completions[feature_id]

            # Update status based on completion
            completion = feature.get("completion_percentage", 0)
            if completion == 100:
                feature["status"] = "done"
            elif completion > 0:
                feature["status"] = "wip"
            else:
                feature["status"] = "pending"

        return architecture
