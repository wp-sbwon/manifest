"""Build diagram spec from tree (root_id, children) and comp_status."""

from typing import Dict, Any, List, Optional, Set


def is_app_component(node: Dict[str, Any]) -> bool:
    """Return True if node is app code (exclude test components)."""
    cid = (node.get("id") or "")
    name = (node.get("name") or "")
    module_path = (node.get("module_path") or "")
    if cid.startswith("comp-tests.") or module_path.startswith("tests."):
        return False
    if isinstance(name, str) and name.startswith("test_"):
        return False
    return True


def _node_label(node: Dict[str, Any]) -> str:
    """Label for node: name, or intent.narrative.role, or reality.symbol, or id."""
    name = (node.get("name") or "").strip()
    if name:
        return name
    role = ((node.get("intent") or {}).get("narrative") or {}).get("role") or ""
    if role:
        return role.strip()
    symbol = (node.get("reality") or {}).get("symbol") or ""
    if symbol:
        return symbol.strip()
    return (node.get("id") or "?").strip()


def _status_for(comp_status: Dict[str, str], comp_id: str) -> str:
    return comp_status.get(comp_id, "planned")


def build_flat_diagram_spec(
    node_list: List[Dict[str, Any]],
    comp_status: Dict[str, str],
    title: str = "ARCHITECTURE FLOW",
) -> Dict[str, Any]:
    """Build flat spec (one diagram node per item in list)."""
    nodes = []
    for node in node_list:
        nid = node.get("id") or ""
        nodes.append({
            "type": "module",
            "label": _node_label(node),
            "status": _status_for(comp_status, nid),
            "node_id": nid,
        })
    return {"title": title, "nodes": nodes}


def _tree_order(
    nodes: List[Dict[str, Any]],
    contracts: List[Dict[str, Any]],
    root_id: str,
    filter_app_only: bool = True,
) -> List[Dict[str, Any]]:
    """Order nodes by tree: root_id then children recursively."""
    id_to_node = {n.get("id"): n for n in nodes if n.get("id")}
    ordered: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    def walk(nid: str) -> None:
        if not nid or nid in seen or nid not in id_to_node:
            return
        node = id_to_node[nid]
        if filter_app_only and not is_app_component(node):
            return
        seen.add(nid)
        ordered.append(node)
        for cid in node.get("children") or []:
            walk(cid)

    walk(root_id)
    for nid, node in id_to_node.items():
        if nid not in seen and (not filter_app_only or is_app_component(node)):
            ordered.append(node)
    return ordered[:14]


def _flat_spec_from_tree(
    nodes: List[Dict[str, Any]],
    contracts: List[Dict[str, Any]],
    comp_status: Dict[str, str],
    root_id: str = "PROJECT_ROOT",
    title: Optional[str] = "ARCHITECTURE FLOW",
    filter_app_only: bool = True,
) -> Dict[str, Any]:
    """Build flat diagram spec from tree (root_id, children)."""
    ordered = _tree_order(nodes, contracts, root_id, filter_app_only=filter_app_only)
    return build_flat_diagram_spec(ordered, comp_status, title=title or "ARCHITECTURE FLOW")


def build_diagram_spec(
    nodes: List[Dict[str, Any]],
    comp_status: Dict[str, str],
    root_id: str = "PROJECT_ROOT",
    title: Optional[str] = "ARCHITECTURE FLOW",
    filter_app_only: bool = True,
) -> Dict[str, Any]:
    """
    Layer 1: direct children of root_id (structured). Layer 2: under each L1 node, a row of its children.
    Returns spec with nodes[].row; each node has id and _data for selection.
    """
    id_to_node = {n.get("id"): n for n in nodes if n.get("id")}
    root = id_to_node.get(root_id)
    if not root:
        return {"title": title or "ARCHITECTURE FLOW", "root_id": root_id, "nodes": []}
    child_ids = [cid for cid in (root.get("children") or []) if cid in id_to_node]
    if filter_app_only:
        child_ids = [cid for cid in child_ids if is_app_component(id_to_node[cid])]
    out_nodes: List[Dict[str, Any]] = []
    for cid in child_ids:
        node = id_to_node[cid]
        row_nodes = [id_to_node[tid] for tid in (node.get("children") or []) if tid in id_to_node]
        if filter_app_only:
            row_nodes = [n for n in row_nodes if is_app_component(n)]
        row = [
            {
                "label": _node_label(n),
                "status": _status_for(comp_status, n.get("id") or ""),
                "id": n.get("id") or "",
                "_data": n,
            }
            for n in row_nodes
        ]
        out_nodes.append({
            "type": "module",
            "label": _node_label(node),
            "status": _status_for(comp_status, cid),
            "id": cid,
            "_data": node,
            "row": row,
        })
    return {
        "title": title or "ARCHITECTURE FLOW",
        "root_id": root_id,
        "nodes": out_nodes,
    }
