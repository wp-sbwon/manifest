"""
Render diagram from diagram spec (formatted JSON) and config. No hardcoded colors.

Renderer takes: spec (from builder or loaded from file) + config (from config_loader).
All colors and box_width come from config.
"""

from typing import Dict, Any, List


def _status_color(status: str, config: Dict[str, Any]) -> str:
    """Status color from config.colors.status[status] or fallback. Status normalized to lowercase."""
    colors = config.get("colors") or {}
    status_colors = colors.get("status") or {}
    key = (status or "").strip().lower()
    return status_colors.get(key) or status_colors.get("planned") or "#8b949e"


def _type_color(node_type: str, config: Dict[str, Any]) -> str:
    colors = config.get("colors") or {}
    return colors.get(node_type) or "#58a6ff"


def render_diagram(spec: Dict[str, Any], config: Dict[str, Any]) -> str:
    """Render diagram from spec { title, nodes } and config (title, box_width, colors)."""
    nodes: List[Dict[str, Any]] = spec.get("nodes") or []
    if not nodes:
        return "  (no nodes)"

    title = spec.get("title") or config.get("title") or "ARCHITECTURE FLOW"
    box_width = config.get("box_width") or 28
    S = "■"

    lines: List[str] = []
    lines.append(f"[white]  ┌{'─' * (box_width + 2)}┐[/]")
    lines.append(f"[white]  │  {title[:box_width-2]:<{box_width-2}}│[/]")
    lines.append(f"[white]  └{'─' * (box_width + 2)}┘[/]")

    def box_one(label: str, status: str, color: str, w: int = 24) -> None:
        st_color = _status_color(status, config)
        w = min(box_width + 2, max(w, len(label) + 6, 12))
        top = "  ┌" + "─" * (w - 2) + "┐"
        mid = f"  [{color}]│ [/][{st_color}]{S}[/] [{color}]{label[:w-6]:<{w-6}}│[/]"
        bot = "  └" + "─" * (w - 2) + "┘"
        lines.append(f"  [{color}]{top}[/]")
        lines.append(mid)
        lines.append(f"  [{color}]{bot}[/]")

    def arrow_down() -> None:
        lines.append(" " * 6 + "│")
        lines.append(" " * 6 + "▼")

    gateway_color = _type_color("gateway", config)
    module_color = _type_color("module", config)
    method_color = _type_color("method", config)

    for i, node in enumerate(nodes):
        node_type = node.get("type") or "gateway"
        label = node.get("label") or "?"
        status = node.get("status") or "planned"
        methods = node.get("methods")
        row = node.get("row")

        if not methods and not row:
            color = gateway_color if node_type == "gateway" else module_color
            box_one(label, status, color)
        elif methods:
            mw = max(10, min(14, max(len(m.get("label") or "?") for m in methods) + 6))
            total_w = mw * len(methods) + max(0, len(methods) - 1) * 2
            st_color = _status_color(status, config)
            lines.append(f"  [{module_color}]┌{'─' * (total_w + 2)}┐[/]")
            lines.append(f"  [{module_color}]│ [/][{st_color}]{S}[/] [{module_color}]{label[:total_w-4]:<{total_w-4}}│[/]")
            lines.append(f"  [{module_color}]├{'─' * (total_w + 2)}┤[/]")
            parts_top = []
            parts_mid = []
            parts_bot = []
            for m in methods:
                ml = (m.get("label") or "?")[:mw-6]
                ms = m.get("status") or "planned"
                mst = _status_color(ms, config)
                parts_top.append(f"[{method_color}]┌{'─' * (mw-2)}┐[/]")
                parts_mid.append(f"[{method_color}]│ [/][{mst}]{S}[/] [{method_color}]{ml:<{mw-6}}│[/]")
                parts_bot.append(f"[{method_color}]└{'─' * (mw-2)}┘[/]")
            lines.append(f"  [{module_color}]│ [/]" + " ".join(parts_top) + f" [{module_color}]│[/]")
            lines.append(f"  [{module_color}]│ [/]" + " ".join(parts_mid) + f" [{module_color}]│[/]")
            lines.append(f"  [{module_color}]│ [/]" + " ".join(parts_bot) + f" [{module_color}]│[/]")
            lines.append(f"  [{module_color}]└{'─' * (total_w + 2)}┘[/]")
        else:
            color = gateway_color if node_type == "gateway" else module_color
            box_one(label, status, color)

        if row:
            arrow_down()
            tw = max(8, min(12, max(len(t.get("label") or "?") for t in row) + 4))
            parts_top = []
            parts_mid = []
            parts_bot = []
            for t in row:
                tl = (t.get("label") or "?")[:tw-4]
                ts = t.get("status") or "planned"
                tst = _status_color(ts, config)
                parts_top.append(f"[{method_color}]┌{'─' * (tw-2)}┐[/]")
                parts_mid.append(f"[{method_color}]│[/][{tst}]{S}[/] [{method_color}]{tl:<{tw-4}}│[/]")
                parts_bot.append(f"[{method_color}]└{'─' * (tw-2)}┘[/]")
            lines.append("  " + " ".join(parts_top))
            lines.append("  " + " ".join(parts_mid))
            lines.append("  " + " ".join(parts_bot))
            arrow_down()

        if i < len(nodes) - 1:
            arrow_down()
    return "\n".join(lines)
