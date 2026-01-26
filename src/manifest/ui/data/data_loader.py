"""
Data loading for Manifest application.

This module handles loading of all application data files including intent.json,
blueprint.json, and project.json. The DataLoader was separated from ManifestApp
to improve code organization and follows the single responsibility principle.

All loading methods are async to support non-blocking I/O operations.
"""
import json
from pathlib import Path
from typing import Dict, Any
from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class DataLoader:
    """Handles loading and refreshing of all application data files.

    Manages loading of intent.json, blueprint.json, and project.json files.
    Caches loaded data in instance attributes and provides methods to reload
    individual files or all files at once.

    Attributes:
        manifest_dir: Path to the .manifest directory where data files are stored.
        intent_data: Cached intent.json data.
        blueprint_data: Cached blueprint.json data.
        project_data: Cached project.json data.
    """

    def __init__(self, manifest_dir: Path):
        """Initialize the data loader.

        Args:
            manifest_dir: Path to the .manifest directory containing data files.
        """
        self.manifest_dir = manifest_dir
        self.intent_data: Dict[str, Any] = {}
        self.blueprint_data: Dict[str, Any] = {}
        self.project_data: Dict[str, Any] = {}

    async def load_intent_data(self) -> Dict[str, Any]:
        """Load intent.json file from the manifest directory.

        The intent file contains project goals, sprints, and features.
        If the file doesn't exist or loading fails, returns default empty
        structure. Errors are logged but don't raise exceptions.

        Returns:
            Dictionary containing intent data. Includes version, sprint,
            and features fields.
        """
        intent_file = self.manifest_dir / "intent.json"
        if intent_file.exists():
            try:
                with open(intent_file, "r", encoding="utf-8") as f:
                    self.intent_data = json.load(f)
            except Exception as e:
                logger.error(f"Error loading intent data: {e}", exc_info=True)
                self.intent_data = {"version": "1.0", "sprint": "", "features": []}
        else:
            self.intent_data = {"version": "1.0", "sprint": "", "features": []}

        return self.intent_data

    async def load_blueprint_data(self) -> Dict[str, Any]:
        """Load blueprint.json data with metadata.

        Uses BlueprintLoader to load the blueprint file which contains
        architecture components, contracts, and zones. Metadata is
        included to provide additional context about components.

        If loading fails, returns a default empty blueprint structure.
        Errors are logged but don't raise exceptions.

        Returns:
            Dictionary containing blueprint data with components, contracts,
            zones, and metadata.
        """
        try:
            self.blueprint_data = BlueprintLoader.load_blueprint(
                self.manifest_dir,
                with_metadata=True,
                default_source="llm_design"
            )
        except Exception as e:
            logger.error(f"Error loading blueprint data: {e}", exc_info=True)
            self.blueprint_data = {
                "version": "1.0",
                "components": [],
                "contracts": [],
                "zones": {}
            }

        return self.blueprint_data

    async def load_project_data(self) -> Dict[str, Any]:
        """Load project.json data.

        For the Manifest project itself, looks in docs/project-manifest/.
        For user projects, looks in .manifest/ directory. This follows the
        "strict doc > view" principle where documentation takes precedence.

        If the file doesn't exist or loading fails, returns an empty dictionary.
        Errors are logged but don't raise exceptions.

        Returns:
            Dictionary containing project metadata and information.
        """
        # For Manifest project itself, load from docs/project-manifest/
        project_file = Path("docs/project-manifest/project.json")
        if not project_file.exists():
            # Fallback: try .manifest/ for user projects
            project_file = self.manifest_dir / "project.json"

        if project_file.exists():
            try:
                with open(project_file, "r", encoding="utf-8") as f:
                    self.project_data = json.load(f)
            except Exception as e:
                logger.error(f"Error loading project data: {e}", exc_info=True)
                self.project_data = {}
        else:
            self.project_data = {}

        return self.project_data

    async def reload_all(self) -> Dict[str, Any]:
        """Reload all data files from disk.

        Convenience method that reloads intent, blueprint, and project data
        in sequence. Useful for refreshing the UI after external changes
        to data files.

        Returns:
            Dictionary containing all three data types:
            - intent: Intent data
            - blueprint: Blueprint data
            - project: Project data
        """
        await self.load_intent_data()
        await self.load_blueprint_data()
        await self.load_project_data()

        return {
            "intent": self.intent_data,
            "blueprint": self.blueprint_data,
            "project": self.project_data
        }
