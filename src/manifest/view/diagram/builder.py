"""Build diagram spec from architecture + blueprint + comp_status."""

from typing import Dict, Any, List, Optional, Set


def is_app_component(comp: Dict[str, Any]) -> bool:
    """Return True if component is app code (exclude test components)."""
    cid = (comp.get("id") or "")
    name = (comp.get("name") or "")
    module_path = (comp.get("module_path") or "")
    if cid.startswith("comp-tests.") or module_path.startswith("tests."):
        return False
    if isinstance(name, str) and name.startswith("test_"):
        return False
    return True


def _order_components_by_flow(
    components: List[Dict[str, Any]],
    contracts: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    id_to_comp = {c.get("id"): c for c in components if c.get("id")}
    ordered: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for contract in contracts or []:
        for cid in (contract.get("from"), contract.get("to")):
            if cid and cid not in seen and cid in id_to_comp:
                ordered.append(id_to_comp[cid])
                seen.add(cid)
    for c in components:
        cid = c.get("id")
        if cid and cid not in seen:
            ordered.append(c)
    return ordered[:14]


def order_components_for_diagram(
    components: List[Dict[str, Any]],
    contracts: List[Dict[str, Any]],
    blueprint: Dict[str, Any],
    filter_app_only: bool = True,
) -> List[Dict[str, Any]]:
    """Order components by zones or contract flow; optionally filter to app-only."""
    if filter_app_only:
        components = [c for c in components if is_app_component(c)]
    zones = blueprint.get("zones") or {}
    server_ids = zones.get("server") or zones.get("data") or []
    if server_ids:
        id_to_comp = {c.get("id"): c for c in components if c.get("id")}
        ordered = [id_to_comp[cid] for cid in server_ids if cid in id_to_comp]
        seen = {c.get("id") for c in ordered}
        for c in components:
            if c.get("id") and c.get("id") not in seen:
                ordered.append(c)
        return ordered[:14]
    return _order_components_by_flow(components, contracts) if contracts else components[:14]


def _component_label(comp: Dict[str, Any]) -> str:
    return (comp.get("name") or comp.get("id") or "?").strip()


def _status_for(comp_status: Dict[str, str], comp_id: str) -> str:
    return comp_status.get(comp_id, "planned")


def _aggregate_status(statuses: List[str]) -> str:
    if any(s == "deviation" for s in statuses):
        return "deviation"
    if any(s == "partial" for s in statuses):
        return "partial"
    if all(s == "healthy" for s in statuses):
        return "healthy"
    return "planned"


def build_diagram_spec(
    architecture: Dict[str, Any],
    blueprint: Dict[str, Any],
    comp_status: Dict[str, str],
    title: Optional[str] = None,
) -> Dict[str, Any]:
    """Build spec { title, nodes } from architecture.features and blueprint."""
    features = architecture.get("features") or []
    components_by_id = {c.get("id"): c for c in (blueprint.get("components") or []) if c.get("id")}

    nodes: List[Dict[str, Any]] = []
    for feat in features:
        if not isinstance(feat, dict):
            continue
        comp_ids = feat.get("components") or []
        comps = [components_by_id[cid] for cid in comp_ids if cid in components_by_id]
        if not comps:
            continue

        label = (feat.get("name") or feat.get("id") or "?").strip()
        node_type = (feat.get("type") or "").strip().lower() or ("gateway" if len(comps) == 1 else "module")

        if len(comps) == 1:
            c = comps[0]
            cid = c.get("id") or ""
            nodes.append({
                "type": "gateway" if node_type == "gateway" else "module",
                "label": label,
                "status": _status_for(comp_status, cid),
                "component_id": cid,
            })
        else:
            method_statuses = [_status_for(comp_status, c.get("id") or "") for c in comps]
            nodes.append({
                "type": "module",
                "label": label,
                "status": _aggregate_status(method_statuses),
                "methods": [
                    {
                        "label": _component_label(c),
                        "status": _status_for(comp_status, c.get("id") or ""),
                        "component_id": c.get("id") or "",
                    }
                    for c in comps
                ],
            })

    return {
        "title": title or (architecture.get("diagram_title") or "ARCHITECTURE FLOW"),
        "nodes": nodes,
    }


def build_flat_diagram_spec(
    comp_list: List[Dict[str, Any]],
    comp_status: Dict[str, str],
    title: str = "ARCHITECTURE FLOW",
) -> Dict[str, Any]:
    """Build flat spec (one node per component) when architecture has no features."""
    nodes = []
    for c in comp_list:
        cid = c.get("id") or ""
        nodes.append({
            "type": "module",
            "label": _component_label(c),
            "status": _status_for(comp_status, cid),
            "component_id": cid,
        })
    return {"title": title, "nodes": nodes}


def _entity_tree_order(
    entities: List[Dict[str, Any]],
    contracts: List[Dict[str, Any]],
    root_id: str,
    filter_app_only: bool = True,
) -> List[Dict[str, Any]]:
    """Order entities by tree: root_id then children recursively; fallback to contract flow."""
    id_to_ent = {e.get("id"): e for e in entities if e.get("id")}
    ordered: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    def walk(eid: str) -> None:
        if not eid or eid in seen or eid not in id_to_ent:
            return
        ent = id_to_ent[eid]
        if filter_app_only and not is_app_component(ent):
            return
        seen.add(eid)
        ordered.append(ent)
        for cid in ent.get("children") or []:
            walk(cid)

    walk(root_id)
    # Append any remaining (e.g. not under root)
    for eid, ent in id_to_ent.items():
        if eid not in seen and (not filter_app_only or is_app_component(ent)):
            ordered.append(ent)
    return ordered[:14]


def build_diagram_spec_from_entities(
    entities: List[Dict[str, Any]],
    contracts: List[Dict[str, Any]],
    comp_status: Dict[str, str],
    root_id: str = "PROJECT_ROOT",
    title: Optional[str] = "ARCHITECTURE FLOW",
    filter_app_only: bool = True,
) -> Dict[str, Any]:
    """Build diagram spec from entity tree (root_id, children) and contracts. Uses FLOW ordering."""
    ordered = _entity_tree_order(entities, contracts, root_id, filter_app_only=filter_app_only)
    return build_flat_diagram_spec(ordered, comp_status, title=title or "ARCHITECTURE FLOW")
