"""
Calculate implementation status from design vs code blueprints.

Returns node_statuses (planned/deviation/healthy/extra), node_deviations,
and parent_completions.
"""
from typing import Dict, Any, List

from manifest.audit.blueprint.blueprint_comparator import BlueprintComparator
from manifest.audit.blueprint.status_enums import ImplementationStatus
from manifest.audit.code.deviation_auditor import Severity
from manifest.audit.entity_schema import PROJECT_ROOT_ID, top_layer_entities

DEVIATION_COMPLETION_WEIGHT = 1.0


def calculate_implementation_status(
    top_down: Dict[str, Any],
    bottom_up: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Calculate implementation status for components (planned/deviation/healthy/extra).
    Parent completion: % of children healthy per root's direct children.
    """
    def _by_id(entities: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        return {
            ent["id"]: ent
            for ent in (entities or [])
            if (ent.get("id") or "") != PROJECT_ROOT_ID
        }

    td_entities = top_down.get("entities") or []
    bu_entities = bottom_up.get("entities") or []
    td_components_by_id = _by_id(td_entities)
    bu_components_by_id = _by_id(bu_entities)

    comparator = BlueprintComparator()
    node_statuses: Dict[str, str] = {}
    node_deviations: Dict[str, List[str]] = {}

    for comp_id, td_comp in td_components_by_id.items():
        bu_comp = bu_components_by_id.get(comp_id)
        if not bu_comp:
            node_statuses[comp_id] = ImplementationStatus.PLANNED.value
        else:
            conflicts = comparator.compare_entities([td_comp], [bu_comp])
            significant_conflicts = [
                c for c in conflicts
                if c.severity in [Severity.ERROR, Severity.WARNING]
            ]
            if significant_conflicts:
                node_statuses[comp_id] = ImplementationStatus.DEVIATION.value
                node_deviations[comp_id] = [c.message for c in significant_conflicts]
            else:
                node_statuses[comp_id] = ImplementationStatus.HEALTHY.value

    for comp_id in bu_components_by_id:
        if comp_id not in td_components_by_id:
            node_statuses[comp_id] = ImplementationStatus.EXTRA.value

    parent_completions: Dict[str, float] = {}
    for entity in top_layer_entities(top_down):
        parent_id = entity.get("id", "")
        child_ids = list(entity.get("children") or [])

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
        "parent_completions": parent_completions
    }
