"""
Render diagram from spec + config. Data-driven: layout follows spec.layout_type and spec.layout_topology.

Same schema for front/back; renderer draws according to data (STACK / FLOW / GRID from intent.blueprint).
"""

from typing import Dict, Any, List, Optional


def _status_color(status: str, config: Dict[str, Any]) -> str:
    """Status color from config.colors.status[status] or fallback."""
    colors = config.get("colors") or {}
    status_colors = colors.get("status") or {}
    key = (status or "").strip().lower()
    return status_colors.get(key) or status_colors.get("planned") or "#8b949e"


def _type_color(node_type: str, config: Dict[str, Any]) -> str:
    colors = config.get("colors") or {}
    return colors.get(node_type) or "#58a6ff"


def render_diagram(spec: Dict[str, Any], config: Dict[str, Any]) -> str:
    """Render from spec { title, nodes, edges, layout_type, layout_topology }. Layout is data-driven."""
    nodes: List[Dict[str, Any]] = spec.get("nodes") or []
    edges: List[Dict[str, str]] = spec.get("edges") or []
    layout_type: str = (spec.get("layout_type") or "STACK").strip().upper()
    if layout_type not in ("FLOW", "GRID", "STACK"):
        layout_type = "STACK"
    layout_topology: Dict[str, Any] = spec.get("layout_topology") or {}
    if not isinstance(layout_topology, dict):
        layout_topology = {}

    if not nodes:
        return "  (no nodes)"

    title = spec.get("title") or config.get("title") or "ARCHITECTURE FLOW"
    box_width = config.get("box_width") or 28
    S = "■"
    gateway_color = _type_color("gateway", config)
    module_color = _type_color("module", config)
    method_color = _type_color("method", config)

    id_to_label = {n.get("id") or "": (n.get("label") or n.get("id") or "?") for n in nodes}
    from_to_targets: Dict[str, List[str]] = {}
    for e in edges:
        from_id = e.get("from") or ""
        to_id = e.get("to") or ""
        if from_id and to_id:
            from_to_targets.setdefault(from_id, []).append(id_to_label.get(to_id, to_id))

    lines: List[str] = []
    lines.append(f"[white]  ┌{'─' * (box_width + 2)}┐[/]")
    lines.append(f"[white]  │  {title[:box_width-2]:<{box_width-2}}│[/]")
    lines.append(f"[white]  └{'─' * (box_width + 2)}┘[/]")

    if layout_type == "GRID" and layout_topology.get("map"):
        lines.extend(_render_grid(nodes, layout_topology, config, S, module_color, method_color))
    elif layout_type == "FLOW":
        lines.extend(_render_flow(nodes, from_to_targets, config, S, gateway_color, module_color, method_color))
    else:
        lines.extend(_render_stack(nodes, from_to_targets, config, S, gateway_color, module_color, method_color, box_width))

    return "\n".join(lines)


def _render_stack(
    nodes: List[Dict[str, Any]],
    from_to_targets: Dict[str, List[str]],
    config: Dict[str, Any],
    S: str,
    gateway_color: str,
    module_color: str,
    method_color: str,
    box_width: int,
) -> List[str]:
    """STACK: vertical list of L1 nodes, each with optional row of L2 and flow line."""
    lines: List[str] = []

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

    def flow_line(target_labels: List[str]) -> None:
        if not target_labels:
            return
        short = [t[:12] for t in target_labels[:5]]
        lines.append(f"  [dim]──► [/][cyan]{', '.join(short)}[/]")

    for i, node in enumerate(nodes):
        nid = node.get("id") or ""
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
        flow_line(from_to_targets.get(nid, []))
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
    return lines


def _render_flow(
    nodes: List[Dict[str, Any]],
    from_to_targets: Dict[str, List[str]],
    config: Dict[str, Any],
    S: str,
    gateway_color: str,
    module_color: str,
    method_color: str,
) -> List[str]:
    """FLOW: L1 as horizontal row with ──► between boxes; then ▼ and each node's row below."""
    lines: List[str] = []
    node_w = 14
    arrow_gap = " ──► "
    id_to_node = {n.get("id") or "": n for n in nodes}
    st_colors = [_status_color(n.get("status") or "planned", config) for n in nodes]
    labels = [(n.get("label") or n.get("id") or "?")[:node_w - 4] for n in nodes]
    parts = []
    for i, (node, lbl) in enumerate(zip(nodes, labels)):
        st = st_colors[i]
        parts.append(f"[{module_color}]┌{'─' * (node_w-2)}┐[/]")
    lines.append("  " + arrow_gap.join(parts))
    parts = []
    for i, (node, lbl) in enumerate(zip(nodes, labels)):
        st = st_colors[i]
        parts.append(f"[{module_color}]│ [/][{st}]{S}[/] [{module_color}]{lbl:<{node_w-6}}│[/]")
    lines.append("  " + arrow_gap.join(parts))
    parts = []
    for node in nodes:
        parts.append(f"[{module_color}]└{'─' * (node_w-2)}┘[/]")
    lines.append("  " + arrow_gap.join(parts))
    lines.append(" " * 6 + " ".join("▼".center(node_w + len(arrow_gap) // 2) for _ in nodes))
    for i, node in enumerate(nodes):
        row = node.get("row") or []
        if row:
            tw = max(8, min(10, max(len(t.get("label") or "?") for t in row) + 2))
            seg = " ".join(
                f"[{method_color}]│[/][{_status_color(t.get('status') or 'planned', config)}]{S}[/] [{method_color}]{(t.get('label') or '?')[:tw-4]:<{tw-4}}│[/]"
                for t in row
            )
            pad = (node_w + len(arrow_gap)) * i
            lines.append("  " + " " * pad + seg)
    return lines


def _render_grid(
    nodes: List[Dict[str, Any]],
    layout_topology: Dict[str, Any],
    config: Dict[str, Any],
    S: str,
    module_color: str,
    method_color: str,
) -> List[str]:
    """GRID: place L1 nodes by topology.map (id -> area [row, col, row_span, col_span])."""
    lines: List[str] = []
    dims = layout_topology.get("dimensions") or {}
    rows = max(1, int(dims.get("rows") or 1))
    cols = max(1, int(dims.get("cols") or 1))
    map_list = layout_topology.get("map") or []
    if not isinstance(map_list, list):
        map_list = []
    id_to_node = {n.get("id") or "": n for n in nodes}
    cell_w = 12
    grid: List[List[Optional[str]]] = [[None] * cols for _ in range(rows)]
    for item in map_list:
        if not isinstance(item, dict):
            continue
        nid = item.get("id") or ""
        area = item.get("area")
        if not area or len(area) < 2 or nid not in id_to_node:
            continue
        r, c = int(area[0]), int(area[1])
        if 0 <= r < rows and 0 <= c < cols:
            grid[r][c] = nid
    for r in range(rows):
        line_parts = []
        for c in range(cols):
            nid = grid[r][c]
            if nid and nid in id_to_node:
                node = id_to_node[nid]
                label = (node.get("label") or node.get("id") or "?")[:cell_w - 4]
                st = _status_color(node.get("status") or "planned", config)
                line_parts.append(f"[{module_color}]┌{'─' * (cell_w-2)}┐[/]")
            else:
                line_parts.append(" " * cell_w)
        lines.append("  " + " ".join(line_parts))
        line_parts = []
        for c in range(cols):
            nid = grid[r][c]
            if nid and nid in id_to_node:
                node = id_to_node[nid]
                label = (node.get("label") or node.get("id") or "?")[:cell_w - 4]
                st = _status_color(node.get("status") or "planned", config)
                line_parts.append(f"[{module_color}]│ [/][{st}]{S}[/] [{module_color}]{label:<{cell_w-6}}│[/]")
            else:
                line_parts.append(" " * cell_w)
        lines.append("  " + " ".join(line_parts))
        line_parts = []
        for c in range(cols):
            nid = grid[r][c]
            if nid and nid in id_to_node:
                line_parts.append(f"[{module_color}]└{'─' * (cell_w-2)}┘[/]")
            else:
                line_parts.append(" " * cell_w)
        lines.append("  " + " ".join(line_parts))
    return lines
