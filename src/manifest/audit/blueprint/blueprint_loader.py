"""
Centralized blueprint loading utility.

This module provides a single point for loading blueprint files, eliminating
code duplication across the codebase. It handles loading blueprint.json,
blueprint_code.json, and supports loading with or without metadata.

The BlueprintLoader uses static methods so it can be called without
instantiating a class, making it convenient for one-off loading operations.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class BlueprintLoader:
    """Centralized utility for loading blueprint files.

    Provides static methods for loading blueprint.json and blueprint_code.json
    files. Handles file existence checks, error handling, and optional metadata
    loading. Returns default empty structures if files don't exist or loading fails.
    """

    @staticmethod
    def load_blueprint(
        manifest_dir: Path,
        with_metadata: bool = False,
        default_source: str = "llm_design"
    ) -> Dict[str, Any]:
        """Load blueprint.json file from the manifest directory.

        If with_metadata is True, uses BlueprintMetadata to load with
        additional metadata. Otherwise, loads the raw JSON file.

        Args:
            manifest_dir: Path to the .manifest directory containing blueprint.json.
            with_metadata: Whether to include metadata in the loaded blueprint.
                Metadata includes source information and component details.
            default_source: Default source identifier for metadata when loading
                with metadata enabled.

        Returns:
            Dictionary containing blueprint data (components, contracts, zones).
            Returns default empty structure if file doesn't exist or loading fails.
            Errors are logged but don't raise exceptions.
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
                from manifest.audit.blueprint.blueprint_metadata import load_blueprint_with_metadata
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
        """Load blueprint_code.json file.

        This file contains blueprint information extracted from actual code
        (as opposed to blueprint.json which is the intended design). Used
        for comparing intended design vs actual implementation.

        Args:
            manifest_dir: Path to the .manifest directory containing blueprint_code.json.

        Returns:
            Dictionary containing code-extracted blueprint data.
            Returns default empty structure if file doesn't exist or loading fails.
            Errors are logged but don't raise exceptions.
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
            from manifest.audit.blueprint.blueprint_metadata import load_blueprint_with_metadata
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
