"""
PRD (Product Requirements Document) management for Manifest.

This module handles loading and saving PRD data, which contains the high-level
requirements and specifications for the project. PRD files are stored as
JSON in the manifest directory and can be accessed synchronously or
asynchronously.

The PRDManager was separated from StateManager to improve code organization
and follows the single responsibility principle.
"""
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import json
import aiofiles
from manifest.core.state_manager import StateManager
from manifest.core.types import PRDDict
from manifest.core.logger import get_logger
from manifest.core.prd_schema import validate_prd

logger = get_logger(__name__)


class PRDManager:
    """Manages PRD (Product Requirements Document) operations.

    Handles loading and saving PRD data to/from disk. PRD files contain
    project requirements, specifications, and high-level design information
    that guide agent work.

    Attributes:
        state_manager: Reference to StateManager for accessing manifest directory.
    """

    def __init__(self, state_manager: StateManager):
        """Initialize the PRD manager.

        Args:
            state_manager: StateManager instance used to determine where
                PRD files are stored.
        """
        self.state_manager = state_manager

    def get_prd_file(self) -> Path:
        """Get the path to the PRD file.

        Returns:
            Path object pointing to prd.json in the manifest directory.
        """
        return self.state_manager.manifest_dir / "prd.json"

    def save_prd(self, prd_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Save PRD data to disk synchronously after validation.

        Validates against the fixed PRD schema (timestamp versioning only).
        Invalid PRDs are not saved.

        Args:
            prd_data: Dictionary containing PRD data to save.

        Returns:
            (True, []) if save was successful; (False, list of error messages) otherwise.
        """
        valid, errors = validate_prd(prd_data)
        if not valid:
            logger.warning("PRD validation failed: %s", errors)
            return False, errors
        try:
            prd_file = self.get_prd_file()
            prd_file.parent.mkdir(parents=True, exist_ok=True)
            with open(prd_file, "w", encoding="utf-8") as f:
                json.dump(prd_data, f, indent=2, ensure_ascii=False)
            from manifest.core.design_history import record_design_save
            record_design_save(self.state_manager.manifest_dir, "prd", "prd.json")
            return True, []
        except Exception as e:
            logger.error(f"Error saving PRD: {e}", exc_info=True)
            return False, [str(e)]

    async def save_prd_async(self, prd_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Save PRD data to disk asynchronously after validation.

        Returns:
            (True, []) if save was successful; (False, list of error messages) otherwise.
        """
        valid, errors = validate_prd(prd_data)
        if not valid:
            logger.warning("PRD validation failed: %s", errors)
            return False, errors
        try:
            prd_file = self.get_prd_file()
            prd_file.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(prd_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(prd_data, indent=2, ensure_ascii=False))
            return True, []
        except Exception as e:
            logger.error(f"Error saving PRD: {e}", exc_info=True)
            return False, [str(e)]

    def load_prd(self) -> Optional[Dict[str, Any]]:
        """Load PRD data from disk synchronously.

        Returns:
            Dictionary containing PRD data if file exists and is valid,
            None if file doesn't exist or loading fails. Errors are logged.
        """
        prd_file = self.get_prd_file()
        if not prd_file.exists():
            return None

        try:
            with open(prd_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading PRD: {e}", exc_info=True)
            return None

    async def load_prd_async(self) -> Optional[Dict[str, Any]]:
        """Load PRD data from disk asynchronously.

        Uses aiofiles for non-blocking I/O. Useful in async contexts.

        Returns:
            Dictionary containing PRD data if file exists and is valid,
            None if file doesn't exist or loading fails. Errors are logged.
        """
        prd_file = self.get_prd_file()
        if not prd_file.exists():
            return None

        try:
            async with aiofiles.open(prd_file, "r", encoding="utf-8") as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.error(f"Error loading PRD: {e}", exc_info=True)
            return None
