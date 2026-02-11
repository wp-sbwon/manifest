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

from manifest.core.logger import get_logger
from manifest.audit.blueprint.blueprint_comparator import BlueprintComparator, BlueprintConflict, ConflictType
from manifest.audit.code.deviation_auditor import Severity
from manifest.audit.entity_schema import PROJECT_ROOT_ID, top_layer_entities
from manifest.audit import doc_set

logger = get_logger(__name__)


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
        """Compare design and code blueprints. Returns implementation progress and deviation conflicts."""
        manifest_dir = manifest_dir or self.manifest_dir
        top_blueprint = doc_set.load_top_down(manifest_dir, "blueprint")
        bottom_blueprint = doc_set.load_bottom_up(manifest_dir, "blueprint")
        blueprint_conflicts = self.comparator.compare_blueprints(top_blueprint, bottom_blueprint)
        implementation_progress = [c for c in blueprint_conflicts if c.severity == Severity.IN_PROGRESS]
        deviation_conflicts = [c for c in blueprint_conflicts if c.severity in [Severity.ERROR, Severity.WARNING]]
        info_conflicts = [c for c in blueprint_conflicts if c.severity == Severity.INFO]

        return {
            "blueprint": {
                "implementation_progress": [c.to_dict() for c in implementation_progress],
                "deviation_conflicts": [c.to_dict() for c in deviation_conflicts],
                "info": [c.to_dict() for c in info_conflicts],
            },
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
                        conflict_type = next(
                            (ct for ct in ConflictType if ct.value == conflict_type_str),
                            ConflictType.METHOD_MISMATCH
                        )
                else:
                    conflict_type = conflict_type_str

                conflict = BlueprintConflict(
                    severity=Severity(c_dict["severity"]),
                    type=conflict_type,
                    message=c_dict["message"],
                    top_down_node=c_dict.get("top_down_node"),
                    bottom_up_node=c_dict.get("bottom_up_node"),
                    file_path=c_dict.get("file_path"),
                    node_id=c_dict.get("node_id")
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
        except Exception as e:
            logger.debug("build_conflict_report failed: %s", e)
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
        """Synchronize blueprints based on mode.

        - strict: block if any ERROR/WARNING conflicts.
        - workflow: trigger conflict workflow (report, planner, user approval).
        - merge: not implemented; only runs comparator and returns conflict count (merged=False). A warning is logged.
        """
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
            # Not implemented: no auto-merge; only report conflict count.
            logger.warning(
                "sync_blueprints(mode='merge') is not implemented; returning conflict count only (merged=False). "
                "Use mode='workflow' for conflict resolution."
            )
            conflicts = self.comparator.compare_blueprints(top_down, bottom_up)
            return {
                "success": True,
                "merged": False,
                "conflicts": len(conflicts)
            }

        return {"success": False, "error": f"Unknown mode: {mode}"}

    def calculate_implementation_status(
        self,
        top_down: Dict[str, Any],
        bottom_up: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Calculate implementation status for components (planned/deviation/healthy/extra).
        Feature completion derived from top_down (root's children = features). New schema only.
        """
        def _by_id_and_name(entities: List[Dict[str, Any]]):
            by_id: Dict[str, Dict[str, Any]] = {}
            by_name: Dict[str, Dict[str, Any]] = {}
            for ent in entities:
                if (ent.get("id") or "") == PROJECT_ROOT_ID:
                    continue
                eid = ent.get("id", "")
                name = self.comparator._entity_display_name(ent)
                if eid:
                    by_id[eid] = ent
                if name:
                    by_name[name] = ent
            return by_id, by_name

        td_entities = top_down.get("entities") or []
        bu_entities = bottom_up.get("entities") or []
        td_components_by_id, td_components_by_name = _by_id_and_name(td_entities)
        bu_components_by_id, bu_components_by_name = _by_id_and_name(bu_entities)

        node_statuses: Dict[str, str] = {}
        node_deviations: Dict[str, List[str]] = {}

        for comp_id, td_comp in td_components_by_id.items():
            comp_name = self.comparator._entity_display_name(td_comp)

            bu_comp = bu_components_by_id.get(comp_id)
            if not bu_comp and comp_name:
                bu_comp = bu_components_by_name.get(comp_name)

            if not bu_comp:
                node_statuses[comp_id] = "planned"
            else:
                conflicts = self.comparator.compare_entities([td_comp], [bu_comp])
                significant_conflicts = [
                    c for c in conflicts
                    if c.severity in [Severity.ERROR, Severity.WARNING]
                ]

                if significant_conflicts:
                    node_statuses[comp_id] = "deviation"
                    node_deviations[comp_id] = [c.message for c in significant_conflicts]
                else:
                    node_statuses[comp_id] = "healthy"

        for comp_id, bu_comp in bu_components_by_id.items():
            comp_name = self.comparator._entity_display_name(bu_comp)
            if comp_id not in td_components_by_id:
                if comp_name not in td_components_by_name:
                    node_statuses[comp_id] = "extra"

        # Feature completion from top-down blueprint (top-layer entities = features)
        feature_completions: Dict[str, float] = {}
        for entity in top_layer_entities(top_down):
            feature_id = entity.get("id", "")
            feature_entity_ids = list(entity.get("children") or [])

            if not feature_entity_ids:
                feature_completions[feature_id] = 0.0
                continue

            healthy_count = 0
            total_count = len(feature_entity_ids)
            for ent_id in feature_entity_ids:
                status = node_statuses.get(ent_id, "planned")
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
            "node_statuses": node_statuses,
            "node_deviations": node_deviations,
            "feature_completions": feature_completions
        }

    def update_blueprint_with_status(
        self,
        blueprint: Dict[str, Any],
        status_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update blueprint entities with implementation status and feature completion."""
        component_statuses = status_info.get("node_statuses", {})
        component_deviations = status_info.get("node_deviations", {})
        feature_completions = status_info.get("feature_completions", {})

        entities_list = blueprint.get("entities") or []
        for ent in entities_list:
            ent_id = ent.get("id", "")
            if ent_id in component_statuses:
                ent["status"] = component_statuses[ent_id]
                if ent_id in component_deviations:
                    ent["deviation_details"] = component_deviations[ent_id]

        for entity in top_layer_entities(blueprint):
            feature_id = entity.get("id", "")
            if feature_id in feature_completions:
                entity["completion_percentage"] = feature_completions[feature_id]
            completion = entity.get("completion_percentage", 0)
            if completion == 100:
                entity["status"] = "done"
            elif completion > 0:
                entity["status"] = "wip"
            else:
                entity["status"] = "pending"

        return blueprint
