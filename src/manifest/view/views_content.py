"""
Stateless view content builders. Pure functions returning strings or Rich renderables.
"""
from typing import Dict, Any, Optional, List

from manifest.audit.blueprint.status_enums import ImplementationStatus
from manifest.audit.entity_schema import PROJECT_ROOT_ID, entity_display_name
from manifest.core.logger import get_logger

logger = get_logger(__name__)

ACCENT_BLUE = "bright_blue"


def entities_for_display(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Flat dicts with id, name, file, type, methods."""
    out: List[Dict[str, Any]] = []
    for e in entities or []:
        if (e.get("id") or "") == PROJECT_ROOT_ID:
            continue
        name = entity_display_name(e) or "?"
        file_path = e.get("symbol") or e.get("file", "")
        parts = (file_path or "").replace("\\", "/").split("/")
        module_path = "/".join(parts[:-1]) if len(parts) > 1 else (parts[0] if parts else "")
        out.append({
            "id": e.get("id"),
            "name": name,
            "file": file_path,
            "module_path": module_path,
            "type": e.get("type", "?"),
            "methods": e.get("methods", []),
            "attributes": e.get("attributes", []),
            "line": e.get("line"),
            "algorithm": e.get("algorithm"),
            "design_pattern": e.get("design_pattern"),
            "complexity": e.get("complexity"),
            "notes": e.get("notes"),
        })
    return out


def status_label(status: str) -> str:
    if status in (ImplementationStatus.HEALTHY.value, "implemented"):
        return "Healthy"
    if status in (ImplementationStatus.PLANNED.value, "design_only"):
        return "Planned"
    if status == ImplementationStatus.PARTIAL.value:
        return "Partial"
    if status in (ImplementationStatus.DEVIATION.value, "drift"):
        return "Deviation"
    if status == ImplementationStatus.EXTRA.value:
        return "Extra"
    return status


def status_color_tag(status: str) -> str:
    if status in (ImplementationStatus.HEALTHY.value, "implemented"):
        return "green"
    if status in (ImplementationStatus.PLANNED.value, "design_only"):
        return "grey70"
    if status == ImplementationStatus.PARTIAL.value:
        return "yellow"
    if status in (ImplementationStatus.DEVIATION.value, "drift"):
        return "red"
    if status == ImplementationStatus.EXTRA.value:
        return "cyan"
    return "white"


def status_label_markup(status: str, text: Optional[str] = None) -> str:
    plain = text if text is not None else status_label(status)
    tag = status_color_tag(status)
    return f"[{tag}]{plain}[/]"
