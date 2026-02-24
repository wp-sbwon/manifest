"""Conflict report file I/O. Separates storage from blueprint comparison."""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from manifest.core.logger import get_logger

logger = get_logger(__name__)


class ConflictReportStorage:
    """Load and save conflict report dicts to disk."""

    def __init__(self, conflicts_dir: Path):
        self.conflicts_dir = Path(conflicts_dir)
        self.conflicts_dir.mkdir(parents=True, exist_ok=True)

    def save(self, report_dict: Dict[str, Any]) -> Path:
        """Save report dict to conflict_{timestamp}_{task_id}.json."""
        timestamp = (report_dict.get("timestamp") or "").replace(":", "-").replace(".", "-")
        task_id = report_dict.get("task_id") or "unknown"
        filename = f"conflict_{timestamp}_{task_id}.json"
        path = self.conflicts_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
        return path

    def load(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Load report dict from file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.debug("load_conflict_report failed: %s", e)
            return None
