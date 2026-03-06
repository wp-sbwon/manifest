"""Header strip and tab bar content."""
from typing import Dict

from manifest.view.views_content import ACCENT_BLUE, status_label, status_color_tag


def _overall_status(comp_status: Dict[str, str]) -> str:
    """Derive a single overall status from per-component statuses."""
    statuses = list(comp_status.values())
    if any(s == "deviation" for s in statuses):
        return "deviation"
    if any(s == "partial" for s in statuses):
        return "partial"
    if all(s == "healthy" for s in statuses) and statuses:
        return "healthy"
    if all(s == "planned" for s in statuses):
        return "planned"
    return "partial"


def build_header_strip_content(
    comp_status: Dict[str, str],
    right_panel_differences: bool,
    time_str: str,
) -> str:
    """Header: Manifest View, Planning/Differences, STATUS, TIME."""
    planning_active = not right_panel_differences
    diff_active = right_panel_differences
    planning = "[bold white][ Planning ][/]" if planning_active else "[dim][ Planning ][/]"
    diff = "[bold red underline][ Differences ][/]" if diff_active else "[dim][ Differences ][/]"
    if comp_status:
        overall = _overall_status(comp_status)
        status_markup = f"[{status_color_tag(overall)}]{status_label(overall)}[/]"
    else:
        status_markup = "[dim]—[/]"
    return (
        f"[bold {ACCENT_BLUE}]Manifest View[/]  {planning}  {diff}     "
        f"STATUS: {status_markup}  TIME: [dim]{time_str}[/]"
    )


def build_tab_bar_content(current_view_value: str) -> str:
    """Tab bar: Diagram, Files, Timeline; current one highlighted. current_view_value is e.g. 'diagram', 'files'."""
    tabs = [
        ("1:DIAGRAM", "diagram"),
        ("2:FILES", "files"),
        ("3:TIMELINE", "timeline"),
    ]
    parts = []
    for label, key in tabs:
        if current_view_value == key:
            parts.append(f"[bold {ACCENT_BLUE}]{label}[/]")
        else:
            parts.append(f"[dim]{label}[/]")
    return "  ".join(parts)
