"""Shared helpers for building minimal blueprints in tests."""
from typing import List


def minimal_blueprint(children: List[str]) -> dict:
    """Normalized blueprint with root and one entity per child id (empty intent/reality)."""
    from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_entity, empty_intent, empty_reality
    from manifest.audit.entity_validation import normalize_for_schema

    root = dict(empty_entity(PROJECT_ROOT_ID))
    root["children"] = list(children)
    root["intent"] = dict(empty_intent())
    root["reality"] = dict(empty_reality())
    entities = [root]
    for eid in children:
        e = dict(empty_entity(eid))
        e["children"] = []
        e["intent"] = dict(empty_intent())
        e["reality"] = dict(empty_reality())
        entities.append(e)
    return normalize_for_schema({"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": entities})
