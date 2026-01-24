"""
Blueprint Loader - Centralized Blueprint loading utility.
Eliminates code duplication across multiple modules.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class BlueprintLoader:
    """Centralized Blueprint loading utility."""
    
    @staticmethod
    def load_blueprint(
        manifest_dir: Path,
        with_metadata: bool = False,
        default_source: str = "llm_design"
    ) -> Dict[str, Any]:
        """
        Load blueprint.json with optional metadata.
        
        Args:
            manifest_dir: Path to .manifest directory
            with_metadata: Whether to load with metadata
            default_source: Default source for metadata
            
        Returns:
            Blueprint data dictionary
        """
        blueprint_file = manifest_dir / "blueprint.json"
        
        if not blueprint_file.exists():
            logger.debug(f"Blueprint file not found: {blueprint_file}")
            return {
                "version": "1.0",
                "components": [],
                "contracts": [],
                "zones": {}
            }
        
        try:
            if with_metadata:
                from manifest.audit.blueprint_metadata import load_blueprint_with_metadata
                return load_blueprint_with_metadata(
                    blueprint_file,
                    default_source,
                    False
                )
            else:
                with open(blueprint_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading blueprint from {blueprint_file}: {e}", exc_info=True)
            return {
                "version": "1.0",
                "components": [],
                "contracts": [],
                "zones": {}
            }
    
    @staticmethod
    def load_code_blueprint(manifest_dir: Path) -> Dict[str, Any]:
        """
        Load blueprint_code.json.
        
        Args:
            manifest_dir: Path to .manifest directory
            
        Returns:
            Code-extracted blueprint data dictionary
        """
        code_blueprint_file = manifest_dir / "blueprint_code.json"
        
        if not code_blueprint_file.exists():
            logger.debug(f"Code blueprint file not found: {code_blueprint_file}")
            return {
                "version": "1.0",
                "components": [],
                "contracts": []
            }
        
        try:
            from manifest.audit.blueprint_metadata import load_blueprint_with_metadata
            return load_blueprint_with_metadata(
                code_blueprint_file,
                "code_extraction",
                True
            )
        except Exception as e:
            logger.error(f"Error loading code blueprint from {code_blueprint_file}: {e}", exc_info=True)
            return {
                "version": "1.0",
                "components": [],
                "contracts": []
            }
    
    @staticmethod
    def save_blueprint(
        manifest_dir: Path,
        blueprint_data: Dict[str, Any],
        backup: bool = True
    ) -> bool:
        """
        Save blueprint.json with optional backup.
        
        Args:
            manifest_dir: Path to .manifest directory
            blueprint_data: Blueprint data to save
            backup: Whether to create backup before saving
            
        Returns:
            True if successful, False otherwise
        """
        blueprint_file = manifest_dir / "blueprint.json"
        
        try:
            # Create backup if requested
            if backup and blueprint_file.exists():
                backup_file = manifest_dir / "blueprint.json.backup"
                import shutil
                shutil.copy2(blueprint_file, backup_file)
                logger.debug(f"Created backup: {backup_file}")
            
            # Save blueprint
            with open(blueprint_file, "w", encoding="utf-8") as f:
                json.dump(blueprint_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Blueprint saved to {blueprint_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving blueprint to {blueprint_file}: {e}", exc_info=True)
            return False
