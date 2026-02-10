"""Mechanical comparison of two values (for future use)."""
from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class DocDiff:
    """A single difference between two values."""
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
