"""
PRD Manager - Manages PRD (Product Requirements Document) operations.
Separated from StateManager to improve maintainability.
"""
from typing import Dict, Any, Optional
from pathlib import Path
import json
import aiofiles
from manifest.core.state_manager import StateManager
from manifest.core.types import PRDDict
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class PRDManager:
    """Manages PRD operations."""
    
    def __init__(self, state_manager: StateManager):
        """
        Initialize PRD Manager.
        
        Args:
            state_manager: StateManager instance
        """
        self.state_manager = state_manager
    
    def get_prd_file(self) -> Path:
        """Get PRD file path."""
        return self.state_manager.manifest_dir / "prd.json"
    
    def save_prd(self, prd_data: Dict[str, Any]) -> bool:
        """Save PRD to file."""
        try:
            prd_file = self.get_prd_file()
            prd_file.parent.mkdir(parents=True, exist_ok=True)
            with open(prd_file, "w", encoding="utf-8") as f:
                json.dump(prd_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error saving PRD: {e}", exc_info=True)
            return False
    
    async def save_prd_async(self, prd_data: Dict[str, Any]) -> bool:
        """Save PRD to file asynchronously."""
        try:
            prd_file = self.get_prd_file()
            prd_file.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(prd_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(prd_data, indent=2, ensure_ascii=False))
            return True
        except Exception as e:
            logger.error(f"Error saving PRD: {e}", exc_info=True)
            return False
    
    def load_prd(self) -> Optional[Dict[str, Any]]:
        """Load PRD from file."""
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
        """Load PRD from file asynchronously."""
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
