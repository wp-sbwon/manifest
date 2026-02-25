"""Load and save PRD JSON (fixed format: title, mission, sections)."""
import json
from pathlib import Path
from typing import Any, Dict, List

from manifest.audit.blueprint.manifest_filenames import PRD_FILE


def _normalize_prd(data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure fixed shape: title, mission, sections (list of {heading, content})."""
    title = (data.get("title") or "").strip() if isinstance(data.get("title"), str) else ""
    mission = (data.get("mission") or "").strip() if isinstance(data.get("mission"), str) else ""
    raw_sections = data.get("sections")
    if not isinstance(raw_sections, list):
        raw_sections = []
    sections: List[Dict[str, Any]] = []
    for s in raw_sections:
        if isinstance(s, dict):
            sections.append({
                "heading": (s.get("heading") or "").strip() if isinstance(s.get("heading"), str) else "",
                "content": (s.get("content") or "").strip() if isinstance(s.get("content"), str) else "",
            })
    return {"title": title, "mission": mission, "sections": sections}


def load_prd(manifest_dir: Path) -> Dict[str, Any]:
    """Load prd.json; return normalized default if missing."""
    path = Path(manifest_dir) / PRD_FILE
    if not path.exists():
        return _normalize_prd({})
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return _normalize_prd({})
    return _normalize_prd(data if isinstance(data, dict) else {})


def save_prd(manifest_dir: Path, data: Dict[str, Any]) -> bool:
    """Validate and save prd.json in fixed format. Returns True on success."""
    manifest_dir = Path(manifest_dir)
    normalized = _normalize_prd(data)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    path = manifest_dir / PRD_FILE
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(normalized, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False
