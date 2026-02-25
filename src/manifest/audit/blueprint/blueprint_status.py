"""
Implementation status derived from blueprint view (design vs code comparison).
"""
from typing import Dict, Any, List

from manifest.audit.blueprint.view_schema import build_view_schema
from manifest.audit.blueprint.status_enums import ImplementationStatus
from manifest.audit.entity_schema import PROJECT_ROOT_ID, top_layer_entities

DEVIATION_COMPLETION_WEIGHT = 1.0


def calculate_implementation_status(
    top_down: Dict[str, Any],
    bottom_up: Dict[str, Any],
) -> Dict[str, Any]:
    """Derive node_statuses and parent_completions from view (comparison of design and code)."""
    view_schema = build_view_schema(top_down, bottom_up)
    node_statuses: Dict[str, str] = {}
    node_deviations: Dict[str, List[str]] = {}
    for ve in view_schema.get("entities") or []:
        eid = ve.get("id")
        if eid:
            v = ve.get("validation") or {}
            node_statuses[eid] = v.get("status") or ImplementationStatus.PLANNED.value
            node_deviations[eid] = list(v.get("deviations") or [])

    parent_completions: Dict[str, float] = {}
    for entity in top_layer_entities(top_down):
        parent_id = entity.get("id", "")
        child_ids = list(entity.get("children") or [])
        if not parent_id:
            continue
        if not child_ids:
            parent_completions[parent_id] = 0.0
            continue
        healthy_count = 0
        total_count = len(child_ids)
        for ent_id in child_ids:
            status = node_statuses.get(ent_id, ImplementationStatus.PLANNED.value)
            if status == ImplementationStatus.HEALTHY.value:
                healthy_count += 1
            elif status == ImplementationStatus.DEVIATION.value:
                healthy_count += DEVIATION_COMPLETION_WEIGHT
        if total_count > 0:
            completion = (healthy_count / total_count) * 100
            parent_completions[parent_id] = round(completion, 1)
        else:
            parent_completions[parent_id] = 0.0

    return {
        "node_statuses": node_statuses,
        "node_deviations": node_deviations,
        "parent_completions": parent_completions,
    }
