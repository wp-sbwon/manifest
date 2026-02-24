"""Header strip and tab bar content."""
from typing import Dict

from manifest.view.views_content import ACCENT_BLUE


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
        deviation_n = sum(1 for s in comp_status.values() if s == "deviation")
        partial_n = sum(1 for s in comp_status.values() if s == "partial")
        healthy_n = sum(1 for s in comp_status.values() if s == "healthy")
        planned_n = sum(1 for s in comp_status.values() if s == "planned")
        if deviation_n > 0:
            status_label, status_tag = "Deviation", "red"
        elif partial_n > 0:
            status_label, status_tag = "Partial", "yellow"
        elif healthy_n == len(comp_status) and len(comp_status) > 0:
            status_label, status_tag = "Healthy", "green"
        elif planned_n == len(comp_status):
            status_label, status_tag = "Planned", "grey70"
        else:
            status_label, status_tag = "Partial", "yellow"
        status_markup = f"[{status_tag}]{status_label}[/]"
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
        if current_view_value == key or (key == "timeline" and current_view_value == "history"):
            parts.append(f"[bold {ACCENT_BLUE}]{label}[/]")
        else:
            parts.append(f"[dim]{label}[/]")
    return "  ".join(parts)
