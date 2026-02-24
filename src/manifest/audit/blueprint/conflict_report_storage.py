"""Conflict report file I/O. Separates storage from blueprint comparison."""

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple

from manifest.core.logger import get_logger

logger = get_logger(__name__)

TERMINAL_STATUSES: Tuple[str, ...] = ("resolved", "rejected")


class ConflictReportStorage:
    def __init__(self, conflicts_dir: Path):
        self.conflicts_dir = Path(conflicts_dir)
        self.conflicts_dir.mkdir(parents=True, exist_ok=True)

    def save(self, report_dict: Dict[str, Any]) -> Path:
        timestamp = (report_dict.get("timestamp") or "").replace(":", "-").replace(".", "-")
        task_id = report_dict.get("task_id") or "unknown"
        filename = f"conflict_{timestamp}_{task_id}.json"
        path = self.conflicts_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
        return path

    def load(self, file_path: Path) -> Optional[Dict[str, Any]]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.debug("load_conflict_report failed: %s", e)
            return None

    def prune(self, max_age_days: int = 30, terminal_statuses: Sequence[str] = TERMINAL_STATUSES) -> int:
        cut = time.time() - max_age_days * 86400
        removed = 0
        for path in self.conflicts_dir.glob("conflict_*.json"):
            try:
                if path.stat().st_mtime >= cut:
                    continue
                data = self.load(path)
                if data and (data.get("status") or "") in terminal_statuses:
                    path.unlink()
                    removed += 1
            except OSError as e:
                logger.warning("prune skip %s: %s", path, e)
        return removed
