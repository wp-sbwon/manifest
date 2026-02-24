import json
from pathlib import Path
from typing import Dict, Any, List

from manifest.core.logger import get_logger

logger = get_logger(__name__)

DESIGN_HISTORY_FILE = "design_history.json"
MAX_ENTRIES = 200


def get_design_history(manifest_dir: Path) -> List[Dict[str, Any]]:
    path = Path(manifest_dir) / DESIGN_HISTORY_FILE
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        entries = data.get("entries", [])
        return list(reversed(entries[-MAX_ENTRIES:]))
    except Exception as e:
        logger.warning("design_history load failed (%s): %s", path, e, exc_info=True)
        return []
