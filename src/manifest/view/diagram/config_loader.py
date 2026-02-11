"""Load diagram config from manifest_dir or package default."""
import json
from pathlib import Path
from typing import Dict, Any, Optional

from manifest.core.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_CONFIG: Dict[str, Any] = {}


def _get_package_default_config() -> Dict[str, Any]:
    global _DEFAULT_CONFIG
    if _DEFAULT_CONFIG:
        return _DEFAULT_CONFIG
    try:
        pkg_dir = Path(__file__).resolve().parent
        config_path = pkg_dir / "diagram_config.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                _DEFAULT_CONFIG = json.load(f)
    except Exception as e:
        logger.debug("Could not load default diagram config: %s", e)
        _DEFAULT_CONFIG = {
            "title": "ARCHITECTURE FLOW",
            "box_width": 28,
            "colors": {
                "entity": "#58a6ff",
                "child": "#7ee8fa",
                "selected": "#ff00ff",
                "status": {
                    "healthy": "green",
                    "planned": "#8b949e",
                    "partial": "yellow",
                    "deviation": "red",
                },
            },
        }
    return _DEFAULT_CONFIG


def load_diagram_config(manifest_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Load diagram_config.json from manifest_dir if present, else package default. Always merge default colors so diagram never loses colors."""
    default = _get_package_default_config()
    manifest_dir = manifest_dir or Path.cwd()
    config_path = Path(manifest_dir) / "diagram_config.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            colors = loaded.get("colors") or {}
            if not colors or not isinstance(colors, dict):
                loaded["colors"] = default.get("colors") or {}
            else:
                default_status = (default.get("colors") or {}).get("status") or {}
                status = colors.get("status")
                if not status and default_status:
                    colors = {**colors, "status": default_status}
                for k in ("entity", "child", "selected"):
                    if not colors.get(k) and (default.get("colors") or {}).get(k):
                        colors[k] = (default.get("colors") or {})[k]
                loaded["colors"] = colors
            return loaded
        except Exception as e:
            logger.debug("Could not load diagram config from %s: %s", config_path, e)
    return default.copy()
