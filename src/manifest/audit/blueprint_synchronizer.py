"""
Blueprint Synchronizer - Enforces synchronization between top-down and bottom-up blueprints.
Handles conflict resolution workflow with worker squad, planner review, and user approval.
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict

from manifest.audit.blueprint_comparator import BlueprintComparator, BlueprintConflict
from manifest.audit.drift_auditor import Severity


@dataclass
class ConflictReport:
    """Represents a conflict report for workflow processing."""
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
        """Convert to dictionary."""
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
    """Enforces synchronization between top-down and bottom-up blueprints."""
    
    def __init__(self, manifest_dir: Path = None, conflicts_dir: Path = None):
        self.manifest_dir = manifest_dir or Path(".manifest")
        self.conflicts_dir = conflicts_dir or (self.manifest_dir / "conflicts")
        self.conflicts_dir.mkdir(parents=True, exist_ok=True)
        self.comparator = BlueprintComparator()
    
    def detect_mismatch(
        self,
        top_down: Dict[str, Any],
        bottom_up: Dict[str, Any]
    ) -> Optional[ConflictReport]:
        """Detect conflicts between blueprints and create conflict report."""
        conflicts = self.comparator.compare_blueprints(top_down, bottom_up)
        
        if not conflicts:
            return None
        
        # Filter out INFO level conflicts for mismatch detection
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
                conflict = BlueprintConflict(
                    severity=Severity(c_dict["severity"]),
                    type=ConflictType(c_dict["type"]),
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
        """Request planner (Prometheus) to review conflict and set flag."""
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
        
        # Save updated report
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
