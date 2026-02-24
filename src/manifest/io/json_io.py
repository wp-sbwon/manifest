"""Read JSON with default on missing or error."""
import json
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from manifest.core.logger import get_logger


def read_json_or_default(
    path: Path,
    default: Dict[str, Any],
    *,
    normalize: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    logger: Optional[Any] = None,
) -> Dict[str, Any]:
    """Load JSON from path; return default (copy) if missing or on error. Optionally normalize and log."""
    path = Path(path)
    if not path.exists():
        return dict(default)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        if logger is not None:
            logger.error("Error loading %s: %s", path, e, exc_info=True)
        return dict(default)
    if normalize is not None:
        data = normalize(data)
    return data
