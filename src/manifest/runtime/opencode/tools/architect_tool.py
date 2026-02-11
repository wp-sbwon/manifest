"""
OpenCode Architect tool: write PRD and blueprint only.

The Architect agent can ideate with the user and persist these docs.
"""
from pathlib import Path
from typing import Dict, Any, Optional

from manifest.core.logger import get_logger
from manifest.core.state_manager import StateManager
from manifest.core.prd_manager import PRDManager
from manifest.audit.blueprint.blueprint_loader import BlueprintLoader

logger = get_logger(__name__)

VALID_ACTIONS = ("write_prd", "write_architecture", "ideate")


class ArchitectTool:
    """Tool for writing PRD and blueprint. Writes to .manifest/prd.json and .manifest/blueprint_design.json."""

    def __init__(self, manifest_dir: Optional[Path] = None):
        self.manifest_dir = (manifest_dir or Path(".manifest")).resolve()
        self._state_manager = StateManager(self.manifest_dir)
        self._prd_manager = PRDManager(self._state_manager)

    def run(self, action: str, content: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run an architect action."""
        action = (action or "").strip().lower()
        if action not in VALID_ACTIONS:
            return {
                "ok": False,
                "error": f"Invalid action: {action}. Valid: {', '.join(VALID_ACTIONS)}",
            }
        if action == "ideate":
            return {
                "ok": True,
                "message": "Ideation mode. Use write_prd or write_architecture to persist.",
            }
        if not content or not isinstance(content, dict):
            return {"ok": False, "error": "Missing or invalid content (must be a JSON object)."}
        try:
            if action == "write_prd":
                return self._write_prd(content)
            if action == "write_architecture":
                return self._write_architecture(content)
        except Exception as e:
            logger.error("architect_tool %s error: %s", action, e, exc_info=True)
            return {"ok": False, "error": str(e)}
        return {"ok": False, "error": f"Unknown action: {action}"}

    def _write_prd(self, prd_data: Dict[str, Any]) -> Dict[str, Any]:
        """Write PRD to .manifest/prd.json. Validates against fixed schema; returns errors if invalid."""
        ok, errors = self._prd_manager.save_prd(prd_data)
        if ok:
            return {"ok": True, "message": "PRD saved to .manifest/prd.json"}
        return {
            "ok": False,
            "error": "PRD validation failed",
            "details": errors,
        }

    def _write_architecture(self, blueprint: Dict[str, Any]) -> Dict[str, Any]:
        """Write blueprint to .manifest/blueprint_design.json."""
        if BlueprintLoader.save_blueprint(self.manifest_dir, blueprint, backup=True):
            return {"ok": True, "message": "Blueprint saved to .manifest/blueprint_design.json"}
        return {"ok": False, "error": "Failed to save blueprint"}
