"""
Render diagram from spec + config. Data-driven: layout follows spec.layout_type and spec.layout_topology.
"""

from typing import Dict, Any, List, Optional


def _status_color(status: str, config: Dict[str, Any]) -> str:
    """Status color from config.colors.status[status] or default."""
    colors = config.get("colors") or {}
    status_colors = colors.get("status") or {}
    key = (status or "").strip().lower()
    return status_colors.get(key) or status_colors.get("planned") or "#8b949e"


def _entity_color(key: str, config: Dict[str, Any]) -> str:
    """'entity' for L1 nodes, 'child' for row items."""
    colors = config.get("colors") or {}
    return colors.get(key) or "#58a6ff"


def render_diagram(
    spec: Dict[str, Any],
    config: Dict[str, Any],
    selected_node_id: Optional[str] = None,
) -> str:
    """Render from spec { title, nodes, layout_type, layout_topology }. Selected node box in magenta."""
    nodes: List[Dict[str, Any]] = spec.get("nodes") or []
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
    node_color = _entity_color("entity", config)
    child_color = _entity_color("child", config)

    lines: List[str] = []
    # Legend (top-left): status meanings
    leg_planned = _status_color("planned", config)
    leg_healthy = _status_color("healthy", config)
    leg_partial = _status_color("partial", config)
    leg_deviation = _status_color("deviation", config)
    legend = (
        f"[dim]Status: [/]"
        f"[{leg_planned}]{S}[/] Planned  "
        f"[{leg_healthy}]{S}[/] Healthy  "
        f"[{leg_partial}]{S}[/] Partial  "
        f"[{leg_deviation}]{S}[/] Deviation"
    )
    lines.append(legend)
    lines.append("")
    lines.append(f"[{node_color}]  ┌{'─' * (box_width + 2)}┐[/]")
    lines.append(f"[{node_color}]  │  {title[:box_width-2]:<{box_width-2}}│[/]")
    lines.append(f"[{node_color}]  └{'─' * (box_width + 2)}┘[/]")

    use_arrows = layout_type == "FLOW"
    if layout_type == "GRID" and layout_topology.get("map"):
        lines.extend(
            _render_grid(
                nodes, layout_topology, config, S, node_color, child_color,
                selected_node_id=selected_node_id,
            )
        )
    else:
        lines.extend(
            _render_simple_flow(
                nodes, config, S, node_color, child_color,
                selected_node_id=selected_node_id,
                use_arrows=use_arrows,
            )
        )

    return "\n".join(lines)


def _l2_labels(node: Dict[str, Any]) -> List[str]:
    """L2 labels from node row or methods (for display inside L1)."""
    row = node.get("row") or []
    methods = node.get("methods") or []
    if row:
        return [(t.get("label") or t.get("id") or "?") for t in row]
    if methods:
        return [(m.get("label") or m.get("id") or "?") for m in methods]
    return []


def _render_simple_flow(
    nodes: List[Dict[str, Any]],
    config: Dict[str, Any],
    S: str,
    node_color: str,
    child_color: str,
    selected_node_id: Optional[str] = None,
    use_arrows: bool = True,
) -> List[str]:
    """Flow of L1 boxes; L2 as plain text inside each box. Selected box in magenta. Arrows only if use_arrows."""
    arrow = " ──► "
    spacer = "     "  # same visual width as arrow; used on non-arrow rows
    selected_color = "#ff00ff"  # magenta for selected box
    min_w, max_w = 12, 28
    lines: List[str] = []
    boxes: List[tuple] = []  # (nid, label, st_color, l2_line, w)
    for node in nodes:
        nid = node.get("id")
        label = (node.get("label") or nid or "?")
        status = node.get("status") or "planned"
        st_color = _status_color(status, config)
        l2_list = _l2_labels(node)
        l2_line = ", ".join((t or "?")[:14] for t in l2_list[:8]) if l2_list else "—"
        w = max(min_w, min(max_w, max(len(label) + 6, len(l2_line) + 4)))
        boxes.append((nid, label, st_color, l2_line, w))
    # Per-box border/label color: magenta when selected
    def box_color(nid: Optional[str]) -> str:
        return selected_color if (selected_node_id and nid == selected_node_id) else node_color
    def row_child_color(nid: Optional[str]) -> str:
        return selected_color if (selected_node_id and nid == selected_node_id) else child_color
    # Top border: no arrow
    parts = [f"[{box_color(nid)}]┌{'─' * (w - 2)}┐[/]" for (nid, _, _, _, w) in boxes]
    lines.append("  " + spacer.join(parts))
    # Label row: arrow between boxes only when use_arrows (FLOW with edges); else spacer
    sep = arrow if use_arrows else spacer
    parts = [
        f"[{box_color(nid)}]│ [/][{st_color}]{S}[/] [{box_color(nid)}]{label[:w-6]:<{w-6}}│[/]"
        for (nid, label, st_color, _, w) in boxes
    ]
    lines.append("  " + sep.join(parts))
    # L2 row: no arrow
    parts = [f"[{row_child_color(nid)}]│ {l2_line[:w-4]:<{w-4}}│[/]" for (nid, _, _, l2_line, w) in boxes]
    lines.append("  " + spacer.join(parts))
    # Bottom border: no arrow
    parts = [f"[{box_color(nid)}]└{'─' * (w - 2)}┘[/]" for (nid, _, _, _, w) in boxes]
    lines.append("  " + spacer.join(parts))
    return lines


def _render_grid(
    nodes: List[Dict[str, Any]],
    layout_topology: Dict[str, Any],
    config: Dict[str, Any],
    S: str,
    node_color: str,
    child_color: str,
    selected_node_id: Optional[str] = None,
) -> List[str]:
    """GRID: place L1 nodes by topology.map. Selected cell in magenta."""
    selected_color = "#ff00ff"  # magenta
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
                color = selected_color if nid == selected_node_id else node_color
                line_parts.append(f"[{color}]┌{'─' * (cell_w-2)}┐[/]")
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
                color = selected_color if nid == selected_node_id else node_color
                line_parts.append(f"[{color}]│ [/][{st}]{S}[/] [{color}]{label:<{cell_w-6}}│[/]")
            else:
                line_parts.append(" " * cell_w)
        lines.append("  " + " ".join(line_parts))
        line_parts = []
        for c in range(cols):
            nid = grid[r][c]
            if nid and nid in id_to_node:
                color = selected_color if nid == selected_node_id else node_color
                line_parts.append(f"[{color}]└{'─' * (cell_w-2)}┘[/]")
            else:
                line_parts.append(" " * cell_w)
        lines.append("  " + " ".join(line_parts))
    return lines
