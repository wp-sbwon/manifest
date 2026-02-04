"""
OpenCode Architect tool: write top-down docs only (PRD, architecture, intent).

The Architect agent can ideate with the user and persist only these docs.
No other write/edit permissions; this tool is the only way to persist top-down docs.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional

from manifest.core.logger import get_logger
from manifest.core.state_manager import StateManager
from manifest.core.prd_manager import PRDManager
from manifest.audit.metadata.architecture_metadata import save_architecture_with_metadata
from manifest.core.design_history import record_design_save

logger = get_logger(__name__)

VALID_ACTIONS = ("write_prd", "write_architecture", "write_intent", "ideate")


class ArchitectTool:
    """Tool for writing top-down docs only: PRD, architecture, intent.

    Writes only to .manifest/prd.json, .manifest/architecture.json, .manifest/intent.json.
    No other file writes. Use for Architect agent (ideation + top-down doc authoring).
    """

    def __init__(self, manifest_dir: Optional[Path] = None):
        self.manifest_dir = (manifest_dir or Path(".manifest")).resolve()
        self._state_manager = StateManager(self.manifest_dir)
        self._prd_manager = PRDManager(self._state_manager)

    def run(self, action: str, content: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run an architect action. Only writes to PRD, architecture, or intent files.

        Args:
            action: One of write_prd, write_architecture, write_intent, ideate.
            content: For write_* actions, the document content (dict). Ignored for ideate.

        Returns:
            Dict with ok, message, and optional error.
        """
        action = (action or "").strip().lower()
        if action not in VALID_ACTIONS:
            return {
                "ok": False,
                "error": f"Invalid action: {action}. Valid: {', '.join(VALID_ACTIONS)}",
            }
        if action == "ideate":
            return {
                "ok": True,
                "message": "Ideation mode. Use write_prd, write_architecture, or write_intent to persist top-down docs.",
            }
        if not content or not isinstance(content, dict):
            return {"ok": False, "error": "Missing or invalid content (must be a JSON object)."}
        try:
            if action == "write_prd":
                return self._write_prd(content)
            if action == "write_architecture":
                return self._write_architecture(content)
            if action == "write_intent":
                return self._write_intent(content)
        except Exception as e:
            logger.error("architect_tool %s error: %s", action, e, exc_info=True)
            return {"ok": False, "error": str(e)}
        return {"ok": False, "error": f"Unknown action: {action}"}

    def _write_prd(self, prd_data: Dict[str, Any]) -> Dict[str, Any]:
        """Write PRD to .manifest/prd.json only."""
        if self._prd_manager.save_prd(prd_data):
            return {"ok": True, "message": "PRD saved to .manifest/prd.json"}
        return {"ok": False, "error": "Failed to save PRD"}

    def _write_architecture(self, architecture: Dict[str, Any]) -> Dict[str, Any]:
        """Write architecture to .manifest/architecture.json only."""
        arch_file = self.manifest_dir / "architecture.json"
        if save_architecture_with_metadata(architecture, arch_file):
            return {"ok": True, "message": "Architecture saved to .manifest/architecture.json"}
        return {"ok": False, "error": "Failed to save architecture"}

    def _write_intent(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Write intent to .manifest/intent.json only."""
        intent_file = self.manifest_dir / "intent.json"
        try:
            self.manifest_dir.mkdir(parents=True, exist_ok=True)
            with open(intent_file, "w", encoding="utf-8") as f:
                json.dump(intent_data, f, indent=2, ensure_ascii=False)
            record_design_save(self.manifest_dir, "intent", "intent.json")
            return {"ok": True, "message": "Intent saved to .manifest/intent.json"}
        except Exception as e:
            logger.error("architect_tool write_intent error: %s", e, exc_info=True)
            return {"ok": False, "error": str(e)}
