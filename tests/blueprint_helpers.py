"""Shared helpers for building minimal blueprints in tests."""
from typing import List


def minimal_blueprint(children: List[str]) -> dict:
    """Normalized blueprint with root and one entity per child id (unified schema)."""
    from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_entity
    from manifest.audit.entity_validation import normalize_for_schema

    root = dict(empty_entity(PROJECT_ROOT_ID))
    root["children"] = list(children)
    entities = [root]
    for eid in children:
        e = dict(empty_entity(eid))
        e["children"] = []
        entities.append(e)
    return normalize_for_schema({"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": entities})
