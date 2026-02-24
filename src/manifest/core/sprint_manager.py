"""Sprint persistence: save, load, list. Normalizes test structure."""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List

import aiofiles

from manifest.core.logger import get_logger

logger = get_logger(__name__)


def _ensure_sprint_test_structure(sprint_data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure sprint data has required test structure (integration_tests, e2e_tests)."""
    default_tests = {
        "status": "pending",
        "test_files": [],
        "test_cases": [],
        "test_skeleton": "",
        "test_plan": "",
        "written_at": None,
        "execution_results": [],
    }
    for key in ("integration_tests", "e2e_tests"):
        if key not in sprint_data:
            sprint_data[key] = dict(default_tests)
        else:
            section = sprint_data[key]
            section.setdefault("status", "pending")
            section.setdefault("test_files", [])
            section.setdefault("test_cases", [])
            section.setdefault("execution_results", [])
    return sprint_data


class SprintManager:
    """Sprint file I/O and structure normalization."""

    def __init__(self, manifest_dir: Path):
        self.manifest_dir = Path(manifest_dir)
        self.sprints_dir = self.manifest_dir / "sprints"

    def get_sprints_dir(self) -> Path:
        return self.sprints_dir

    def save_sprint(self, sprint_data: Dict[str, Any]) -> bool:
        """Save sprint to sprint-{id}.json."""
        try:
            sprint_data = _ensure_sprint_test_structure(dict(sprint_data))
            self.sprints_dir.mkdir(parents=True, exist_ok=True)
            sprint_id = sprint_data.get("id", "unknown")
            path = self.sprints_dir / f"sprint-{sprint_id}.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(sprint_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error("Error saving Sprint: %s", e, exc_info=True)
            return False

    async def save_sprint_async(self, sprint_data: Dict[str, Any]) -> bool:
        """Save sprint to sprint-{id}.json asynchronously."""
        try:
            sprint_data = _ensure_sprint_test_structure(dict(sprint_data))
            self.sprints_dir.mkdir(parents=True, exist_ok=True)
            sprint_id = sprint_data.get("id", "unknown")
            path = self.sprints_dir / f"sprint-{sprint_id}.json"
            async with aiofiles.open(path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(sprint_data, indent=2, ensure_ascii=False))
            return True
        except Exception as e:
            logger.error("Error saving Sprint: %s", e, exc_info=True)
            return False

    def load_sprint(self, sprint_id: str) -> Optional[Dict[str, Any]]:
        """Load sprint from sprint-{id}.json."""
        path = self.sprints_dir / f"sprint-{sprint_id}.json"
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return _ensure_sprint_test_structure(data)
        except Exception as e:
            logger.error("Error loading Sprint: %s", e, exc_info=True)
            return None

    def list_sprints(self) -> List[str]:
        """List sprint IDs from sprint-*.json files."""
        if not self.sprints_dir.exists():
            return []
        return sorted(
            p.stem.replace("sprint-", "")
            for p in self.sprints_dir.glob("sprint-*.json")
        )
