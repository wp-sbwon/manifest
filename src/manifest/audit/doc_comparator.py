"""
Mechanical comparison of intent and architecture docs (same format from top-down and bottom-up).

Compares top-down vs bottom-up produced docs field-by-field; returns list of differences.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List

from manifest.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DocDiff:
    """A single difference between top-down and bottom-up doc (intent or architecture)."""
    path: str
    message: str
    top_value: Any = None
    bottom_value: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "message": self.message,
            "top_value": self.top_value,
            "bottom_value": self.bottom_value,
        }


def _deep_diff(path: str, top: Any, bottom: Any, diffs: List[DocDiff]) -> None:
    """Recursively compare two values and append differences to diffs."""
    if type(top) != type(bottom):
        diffs.append(DocDiff(
            path=path,
            message=f"Type mismatch: top={type(top).__name__}, bottom={type(bottom).__name__}",
            top_value=top,
            bottom_value=bottom,
        ))
        return
    if isinstance(top, dict):
        all_keys = set(top.keys()) | set(bottom.keys())
        for k in all_keys:
            p = f"{path}.{k}" if path else k
            if k not in top:
                diffs.append(DocDiff(path=p, message="In bottom-up only", bottom_value=bottom.get(k)))
            elif k not in bottom:
                diffs.append(DocDiff(path=p, message="In top-down only", top_value=top.get(k)))
            else:
                _deep_diff(p, top[k], bottom[k], diffs)
        return
    if isinstance(top, list):
        if len(top) != len(bottom):
            diffs.append(DocDiff(
                path=path,
                message=f"List length: top={len(top)}, bottom={len(bottom)}",
                top_value=top,
                bottom_value=bottom,
            ))
        for i in range(min(len(top), len(bottom))):
            _deep_diff(f"{path}[{i}]", top[i], bottom[i], diffs)
        return
    if top != bottom:
        diffs.append(DocDiff(path=path, message="Value mismatch", top_value=top, bottom_value=bottom))


def compare_intent(top: Dict[str, Any], bottom: Dict[str, Any]) -> List[DocDiff]:
    """Mechanically compare top-down intent vs bottom-up intent (same schema)."""
    diffs: List[DocDiff] = []
    _deep_diff("", top or {}, bottom or {}, diffs)
    return diffs


def compare_architecture(top: Dict[str, Any], bottom: Dict[str, Any]) -> List[DocDiff]:
    """Mechanically compare top-down architecture vs bottom-up architecture (same schema)."""
    diffs: List[DocDiff] = []
    # Normalize: ignore last_updated and source for comparison (they will differ)
    t = {k: v for k, v in (top or {}).items() if k not in ("last_updated", "source", "ground_truth")}
    b = {k: v for k, v in (bottom or {}).items() if k not in ("last_updated", "source", "ground_truth")}
    _deep_diff("", t, b, diffs)
    return diffs
