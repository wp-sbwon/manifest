"""Sidebar content: health summary (status distribution + assertion proof rate) and current view name."""
from typing import Dict, Any


def get_sidebar_health_text(
    comp_status: Dict[str, str],
    test_results: Dict[str, Any],
) -> str:
    """Project Health panel: status distribution and assertion proof rate."""
    # Status distribution
    counts = {"healthy": 0, "planned": 0, "partial": 0, "deviation": 0, "extra": 0}
    for s in comp_status.values():
        key = s if s in counts else "planned"
        counts[key] += 1

    status_lines = []
    labels = [
        ("healthy", "green", "Healthy"),
        ("planned", "grey70", "Planned"),
        ("partial", "yellow", "Partial"),
        ("deviation", "red", "Deviation"),
        ("extra", "cyan", "Extra"),
    ]
    for key, color, label in labels:
        n = counts[key]
        if n > 0:
            status_lines.append(f"  [{color}]{label}: {n}[/]")

    # Assertion proof rate
    total_assertions = 0
    implemented = 0
    for tests in (test_results or {}).values():
        if not isinstance(tests, list):
            continue
        for t in tests:
            total_assertions += 1
            if t.get("status") == "implemented":
                implemented += 1
    if total_assertions > 0:
        pct = int(100 * implemented / total_assertions)
        proof_color = "green" if pct == 100 else ("yellow" if pct >= 50 else "red")
        proof_line = f"  [{proof_color}]{implemented}/{total_assertions} ({pct}%)[/]"
    else:
        proof_line = "  [dim]No assertions[/]"

    return (
        "[bold cyan]Project Health[/]\n"
        "[dim]─────────────────────[/]\n"
        + "\n".join(status_lines) + "\n"
        "[dim]─────────────────────[/]\n"
        "  [bold]Assertion proof rate[/]\n"
        + proof_line
    )


def get_sidebar_viz_text(view_name: str) -> str:
    """Name of current main view for sidebar."""
    return f"View: {view_name}"
