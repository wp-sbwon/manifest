"""Build text tree from blueprint entities."""
from typing import Dict, Any, List

from manifest.audit.entity_schema import entity_display_name, get_root_entity


def _entity_tree_lines(blueprint: Dict[str, Any], entity_id: str, prefix: str, last: bool) -> List[str]:
    entities = {e.get("id"): e for e in (blueprint.get("entities") or []) if e.get("id")}
    entity = entities.get(entity_id)
    if not entity:
        return []
    name = entity_display_name(entity) or entity_id or "(root)"
    branch = "└── " if last else "├── "
    lines = [prefix + branch + name]
    child_ids = entity.get("children") or []
    for i, cid in enumerate(child_ids):
        is_last = i == len(child_ids) - 1
        add = "    " if last else "│   "
        lines.extend(_entity_tree_lines(blueprint, cid, prefix + add, is_last))
    return lines


def build_blueprint_text_tree(blueprint: Dict[str, Any]) -> List[str]:
    """Build text tree lines from blueprint."""
    entities = blueprint.get("entities") or []
    if not entities:
        return ["No entities"]
    root = get_root_entity(blueprint)
    root_id = root.get("id") if root else (entities[0].get("id") if entities else "")
    if not root_id:
        return ["No root"]
    root_entity = next((e for e in entities if (e.get("id") or "") == root_id), None)
    if not root_entity:
        return ["Root not in entities"]
    name = entity_display_name(root_entity) or root_id
    lines = [name]
    child_ids = root_entity.get("children") or []
    for i, cid in enumerate(child_ids):
        is_last = i == len(child_ids) - 1
        lines.extend(_entity_tree_lines(blueprint, cid, "", is_last))
    return lines
