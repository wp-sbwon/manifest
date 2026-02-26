"""Build diagram spec from tree (root_id, children), comp_status, and edges from outgoing_contracts."""

from typing import Dict, Any, List, Optional, Set, Tuple

from manifest.audit.entity_schema import PROJECT_ROOT_ID, entity_display_name
from manifest.core.logger import get_logger
from manifest.view.constants import DEFAULT_DIAGRAM_TITLE, DEFAULT_MAX_TREE_NODES

logger = get_logger(__name__)


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
    """Label for diagram node (name preferred)."""
    return entity_display_name(node, prefer_name_first=True) or (node.get("id") or "?").strip()


def _status_for(comp_status: Dict[str, str], comp_id: str) -> str:
    return comp_status.get(comp_id, "planned")


def _tree_order(
    nodes: List[Dict[str, Any]],
    contracts: List[Dict[str, Any]],
    root_id: str,
    filter_app_only: bool = True,
    max_nodes: int = DEFAULT_MAX_TREE_NODES,
) -> List[Dict[str, Any]]:
    """Order nodes by tree: root_id then children recursively. Capped at max_nodes for layout sanity."""
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
    if len(ordered) > max_nodes:
        logger.info("Diagram: capping at %d nodes (had %d); set diagram_config max_tree_nodes to override.", max_nodes, len(ordered))
        return ordered[:max_nodes]
    return ordered


def _edges_for_layer(entities: List[Dict[str, Any]], layer_ids: Set[str]) -> List[Dict[str, str]]:
    """Edges (from, to) from entities' outgoing_contracts where both endpoints are in layer_ids."""
    edges: List[Dict[str, str]] = []
    for e in entities or []:
        from_id = (e.get("id") or "").strip()
        if from_id not in layer_ids:
            continue
        for oc in e.get("outgoing_contracts") or []:
            if not isinstance(oc, dict):
                continue
            to_id = (oc.get("to") or "").strip()
            if to_id in layer_ids and to_id != from_id:
                edges.append({"from": from_id, "to": to_id})
    return edges


def build_diagram_spec(
    nodes: List[Dict[str, Any]],
    comp_status: Dict[str, str],
    root_id: str = PROJECT_ROOT_ID,
    title: Optional[str] = DEFAULT_DIAGRAM_TITLE,
    filter_app_only: bool = True,
) -> Dict[str, Any]:
    """
    Root's direct children as main row; each node's children as a sub-row.
    Edges from outgoing_contracts. Returns spec with nodes[].row, edges.
    """
    id_to_node = {n.get("id"): n for n in nodes if n.get("id")}
    root = id_to_node.get(root_id)
    if not root:
        return {"title": title or DEFAULT_DIAGRAM_TITLE, "root_id": root_id, "nodes": [], "edges": []}
    child_ids = [cid for cid in (root.get("children") or []) if cid in id_to_node]
    if filter_app_only:
        child_ids = [cid for cid in child_ids if is_app_component(id_to_node[cid])]
    layer_id_set: Set[str] = set(child_ids)
    edges = _edges_for_layer(nodes, layer_id_set)
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

    layout_type = "STACK"
    layout_topology: Dict[str, Any] = {}
    root_blueprint = root.get("blueprint") or {}
    if isinstance(root_blueprint, dict):
        layout_type = (root_blueprint.get("type") or "STACK").strip().upper()
        if layout_type not in ("FLOW", "GRID", "STACK"):
            layout_type = "STACK"
        layout_topology = root_blueprint.get("topology") or {}
        if not isinstance(layout_topology, dict):
            layout_topology = {}
    # No arrows when there is no flow between nodes (e.g. siblings add/sub/mul).
    if layout_type == "FLOW" and not edges:
        layout_type = "STACK"

    return {
        "title": title or DEFAULT_DIAGRAM_TITLE,
        "root_id": root_id,
        "nodes": out_nodes,
        "edges": edges,
        "layout_type": layout_type,
        "layout_topology": layout_topology,
    }
