"""
OpenCode Blueprint Sync and Drift Check tools.

Orchestrator uses these to compare top-down vs bottom-up blueprints,
detect drift (component status: implemented/ghost/drift/extra), and
run sync workflow.
"""
from pathlib import Path
from typing import Dict, Any, Optional, List

from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
from manifest.audit.blueprint.blueprint_synchronizer import BlueprintSynchronizer
from manifest.audit.blueprint.blueprint_comparator import BlueprintComparator
from manifest.audit.metadata.architecture_metadata import load_architecture_with_metadata
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class BlueprintSyncTool:
    """Blueprint synchronization and drift detection tool."""

    def __init__(self, manifest_dir: Optional[Path] = None):
        self.manifest_dir = (manifest_dir or Path(".manifest")).resolve()
        self._synchronizer = BlueprintSynchronizer(manifest_dir=self.manifest_dir)
        self._comparator = BlueprintComparator()

    def compare_blueprints(self) -> Dict[str, Any]:
        """Compare top-down vs bottom-up blueprints; return conflict report."""
        try:
            top_down = BlueprintLoader.load_blueprint(
                self.manifest_dir,
                with_metadata=True,
                default_source="llm_design",
            )
            bottom_up = BlueprintLoader.load_code_blueprint(self.manifest_dir)
            conflicts = self._comparator.compare_blueprints(top_down, bottom_up)
            return {
                "ok": True,
                "conflicts": [c.to_dict() for c in conflicts],
                "count": len(conflicts),
            }
        except Exception as e:
            logger.error("compare_blueprints failed: %s", e, exc_info=True)
            return {"ok": False, "error": str(e), "conflicts": [], "count": 0}

    def detect_drift(self) -> Dict[str, Any]:
        """Detect drift; return component statuses (implemented/ghost/drift/extra)."""
        try:
            top_down = BlueprintLoader.load_blueprint(
                self.manifest_dir,
                with_metadata=True,
                default_source="llm_design",
            )
            bottom_up = BlueprintLoader.load_code_blueprint(self.manifest_dir)
            arch_file = self.manifest_dir / "architecture.json"
            architecture = load_architecture_with_metadata(arch_file)
            status_info = self._synchronizer.calculate_implementation_status(
                top_down, bottom_up, architecture
            )
            return {
                "ok": True,
                "component_statuses": status_info.get("component_statuses", {}),
                "feature_completion": status_info.get("feature_completion", {}),
            }
        except Exception as e:
            logger.error("detect_drift failed: %s", e, exc_info=True)
            return {"ok": False, "error": str(e), "component_statuses": {}}

    def sync_blueprint(self, mode: str = "workflow") -> Dict[str, Any]:
        """Synchronize blueprints (strict | workflow | merge)."""
        try:
            top_down = BlueprintLoader.load_blueprint(
                self.manifest_dir,
                with_metadata=False,
            )
            bottom_up = BlueprintLoader.load_code_blueprint(self.manifest_dir)
            result = self._synchronizer.sync_blueprints(
                top_down, bottom_up, mode=mode
            )
            return {"ok": result.get("success", False), "result": result}
        except Exception as e:
            logger.error("sync_blueprint failed: %s", e, exc_info=True)
            return {"ok": False, "error": str(e)}


class DriftCheckTool:
    """Thin wrapper for drift detection (orchestrator drift_check tool)."""

    def __init__(self, manifest_dir: Optional[Path] = None):
        self.manifest_dir = (manifest_dir or Path(".manifest")).resolve()
        self._sync_tool = BlueprintSyncTool(manifest_dir=self.manifest_dir)

    def check(self) -> Dict[str, Any]:
        """Return drift status (component_statuses)."""
        return self._sync_tool.detect_drift()
