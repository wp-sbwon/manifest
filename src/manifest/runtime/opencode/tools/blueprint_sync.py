"""
OpenCode Blueprint Sync and Deviation Check tools.

Compare Design Plan vs Actual Code (top-down vs bottom-up), detect deviation
(component status: healthy/planned/deviation/extra), and run sync workflow.
"""
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
from manifest.audit.blueprint.blueprint_synchronizer import BlueprintSynchronizer
from manifest.audit.blueprint.blueprint_comparator import BlueprintComparator
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class BlueprintSyncTool:
    """Blueprint synchronization and drift detection tool."""

    def __init__(self, manifest_dir: Optional[Path] = None):
        self.manifest_dir = (manifest_dir or Path(".manifest")).resolve()
        self._synchronizer = BlueprintSynchronizer(manifest_dir=self.manifest_dir)
        self._comparator = BlueprintComparator()

    def _load_both_blueprints(
        self, with_metadata: bool = True
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Load design and code blueprints. Single place for load options."""
        top = BlueprintLoader.load_blueprint(
            self.manifest_dir,
            with_metadata=with_metadata,
            default_source="llm_design",
        )
        bottom = BlueprintLoader.load_code_blueprint(self.manifest_dir)
        return top, bottom

    def compare_blueprints(self) -> Dict[str, Any]:
        """Compare top-down vs bottom-up blueprints; return conflict report."""
        try:
            top_down, bottom_up = self._load_both_blueprints(with_metadata=True)
            conflicts = self._comparator.compare_blueprints(top_down, bottom_up)
            return {
                "ok": True,
                "conflicts": [c.to_dict() for c in conflicts],
                "count": len(conflicts),
            }
        except Exception as e:
            logger.error("compare_blueprints failed: %s", e, exc_info=True)
            return {"ok": False, "error": str(e), "conflicts": [], "count": 0}

    def detect_deviation(self) -> Dict[str, Any]:
        """Detect deviation (Design Plan vs Actual Code); return component statuses (healthy/planned/deviation/extra)."""
        try:
            top_down, bottom_up = self._load_both_blueprints(with_metadata=True)
            status_info = self._synchronizer.calculate_implementation_status(
                top_down, bottom_up
            )
            return {
                "ok": True,
                "node_statuses": status_info.get("node_statuses", {}),
                "feature_completions": status_info.get("feature_completions", {}),
            }
        except Exception as e:
            logger.error("detect_deviation failed: %s", e, exc_info=True)
            return {"ok": False, "error": str(e), "node_statuses": {}}

    def detect_drift(self) -> Dict[str, Any]:
        """Alias for detect_deviation."""
        return self.detect_deviation()

    def sync_blueprint(self, mode: str = "workflow") -> Dict[str, Any]:
        """Synchronize blueprints (strict | workflow)."""
        try:
            top_down, bottom_up = self._load_both_blueprints(with_metadata=False)
            result = self._synchronizer.sync_blueprints(
                top_down, bottom_up, mode=mode
            )
            return {"ok": result.get("success", False), "result": result}
        except Exception as e:
            logger.error("sync_blueprint failed: %s", e, exc_info=True)
            return {"ok": False, "error": str(e)}

    def compare_all_docs(self) -> Dict[str, Any]:
        """Compare all doc types (blueprint, intent, architecture) between top-down and bottom-up.
        Returns implementation progress (missing in bottom-up) separately from deviation (conflicts)."""
        try:
            result = self._synchronizer.compare_all_docs(self.manifest_dir)
            return {"ok": True, "result": result}
        except Exception as e:
            logger.error("compare_all_docs failed: %s", e, exc_info=True)
            return {"ok": False, "error": str(e), "result": None}


class DeviationCheckTool:
    """Thin wrapper for deviation detection (Design Plan vs Actual Code)."""

    def __init__(self, manifest_dir: Optional[Path] = None):
        self.manifest_dir = (manifest_dir or Path(".manifest")).resolve()
        self._sync_tool = BlueprintSyncTool(manifest_dir=self.manifest_dir)

    def check(self) -> Dict[str, Any]:
        """Return deviation status (node_statuses: healthy/planned/deviation/extra)."""
        return self._sync_tool.detect_deviation()


# Alias
DriftCheckTool = DeviationCheckTool
