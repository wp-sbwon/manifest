"""
Data Loader - Handles loading and refreshing of application data.
Separated from ManifestApp to improve maintainability.
"""
import json
from pathlib import Path
from typing import Dict, Any
from manifest.audit.blueprint_loader import BlueprintLoader
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class DataLoader:
    """Handles loading and refreshing of application data."""
    
    def __init__(self, manifest_dir: Path):
        """
        Initialize Data Loader.
        
        Args:
            manifest_dir: Path to .manifest directory
        """
        self.manifest_dir = manifest_dir
        self.intent_data: Dict[str, Any] = {}
        self.blueprint_data: Dict[str, Any] = {}
        self.project_data: Dict[str, Any] = {}
    
    async def load_intent_data(self) -> Dict[str, Any]:
        """
        Load intent.json data.
        
        Returns:
            Intent data dictionary
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
        """
        Load blueprint.json data with metadata.
        
        Returns:
            Blueprint data dictionary
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
        """
        Load project.json data (strict doc > view).
        
        Note: project.json is now in docs/project-manifest/ for Manifest project documentation.
        For user projects, this would be in .manifest/ directory.
        
        Returns:
            Project data dictionary
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
        """
        Reload all data sources.
        
        Returns:
            Dictionary with all loaded data
        """
        await self.load_intent_data()
        await self.load_blueprint_data()
        await self.load_project_data()
        
        return {
            "intent": self.intent_data,
            "blueprint": self.blueprint_data,
            "project": self.project_data
        }
