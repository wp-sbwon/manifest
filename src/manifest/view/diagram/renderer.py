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


def render_diagram(spec: Dict[str, Any], config: Dict[str, Any]) -> str:
    """Render from spec { title, nodes, layout_type, layout_topology }."""
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
    lines.append(f"[{node_color}]  ┌{'─' * (box_width + 2)}┐[/]")
    lines.append(f"[{node_color}]  │  {title[:box_width-2]:<{box_width-2}}│[/]")
    lines.append(f"[{node_color}]  └{'─' * (box_width + 2)}┘[/]")

    if layout_type == "GRID" and layout_topology.get("map"):
        lines.extend(_render_grid(nodes, layout_topology, config, S, node_color, child_color))
    else:
        lines.extend(_render_simple_flow(nodes, config, S, node_color, child_color))

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
) -> List[str]:
    """Flow of L1 boxes; L2 as plain text inside each box (no nested box structure)."""
    arrow = " ──► "
    min_w, max_w = 12, 28
    lines: List[str] = []
    boxes: List[tuple] = []
    for node in nodes:
        label = (node.get("label") or node.get("id") or "?")
        status = node.get("status") or "planned"
        st_color = _status_color(status, config)
        l2_list = _l2_labels(node)
        l2_line = ", ".join((t or "?")[:14] for t in l2_list[:8]) if l2_list else "—"
        w = max(min_w, min(max_w, max(len(label) + 6, len(l2_line) + 4)))
        boxes.append((label, st_color, l2_line, w))
    parts = [f"[{node_color}]┌{'─' * (w - 2)}┐[/]" for (_, _, _, w) in boxes]
    lines.append("  " + arrow.join(parts))
    parts = [f"[{node_color}]│ [/][{st_color}]{S}[/] [{node_color}]{label[:w-6]:<{w-6}}│[/]" for (label, st_color, _, w) in boxes]
    lines.append("  " + arrow.join(parts))
    parts = [f"[{child_color}]│ {l2_line[:w-4]:<{w-4}}│[/]" for (_, _, l2_line, w) in boxes]
    lines.append("  " + arrow.join(parts))
    parts = [f"[{node_color}]└{'─' * (w - 2)}┘[/]" for (_, _, _, w) in boxes]
    lines.append("  " + arrow.join(parts))
    return lines


def _render_grid(
    nodes: List[Dict[str, Any]],
    layout_topology: Dict[str, Any],
    config: Dict[str, Any],
    S: str,
    node_color: str,
    child_color: str,
) -> List[str]:
    """GRID: place L1 nodes by topology.map."""
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
                line_parts.append(f"[{node_color}]┌{'─' * (cell_w-2)}┐[/]")
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
                line_parts.append(f"[{node_color}]│ [/][{st}]{S}[/] [{node_color}]{label:<{cell_w-6}}│[/]")
            else:
                line_parts.append(" " * cell_w)
        lines.append("  " + " ".join(line_parts))
        line_parts = []
        for c in range(cols):
            nid = grid[r][c]
            if nid and nid in id_to_node:
                line_parts.append(f"[{node_color}]└{'─' * (cell_w-2)}┘[/]")
            else:
                line_parts.append(" " * cell_w)
        lines.append("  " + " ".join(line_parts))
    return lines
