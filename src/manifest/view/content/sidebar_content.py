"""Sidebar content: health summary and current view name."""
import re
from typing import Dict, Any

from manifest.view.views_content import ACCENT_BLUE


def get_sidebar_health_text(
    comp_status: Dict[str, str],
    metrics: Dict[str, Any],
) -> str:
    """Project Health panel text from comp_status and state health_metrics."""
    total = len(comp_status) or 1
    deviation_count = sum(1 for s in comp_status.values() if s in ("deviation", "partial"))
    pct = int(100 * deviation_count / total)
    dev_color = "yellow" if pct > 0 else "green"
    quality_str = metrics.get("code_quality") or "—"
    q = str(quality_str).lower()
    if q in ("excellent", "good", "ok"):
        quality_tag = "green"
    elif "issues" in q:
        n = re.search(r"(\d+)\s*issues", q)
        quality_tag = "yellow" if (n and int(n.group(1)) <= 20) else "red"
    else:
        quality_tag = "dim"
    cov_val = metrics.get("test_coverage")
    cov_str = f"{cov_val}%" if cov_val is not None else "—"
    size_str = metrics.get("binary_size") or "—"
    return (
        "[bold cyan]Project Health[/]\n"
        "[dim]─────────────────────[/]\n"
        f"  Total Deviation:  [{dev_color}]{pct}%[/]\n"
        f"  Code Quality:     [{quality_tag}]{quality_str}[/]\n"
        f"  Test Coverage:   [{ACCENT_BLUE}]{cov_str}[/]\n"
        f"  Binary Size:     [dim]{size_str}[/]"
    )


def get_sidebar_viz_text(view_name: str) -> str:
    """Name of current main view for sidebar."""
    return f"View: {view_name}"
