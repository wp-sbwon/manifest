"""
Canonical schema for blueprint entities.

Persisted shape: version, root_id, entities. Each entity: id, children, dependencies,
narrative, blueprint, protocol, profile, governance, symbol, traits, topology_actual, preview,
outgoing_contracts. No nulls; use "" or []/{}.
"""
from typing import Any, Dict, List, Optional



# ---------------------------------------------------------------------------
# Root shape for blueprint JSON
# ---------------------------------------------------------------------------


def language_to_list(val: Any) -> List[str]:
    """Normalize profile.language to list of strings. Accepts raw value (string, list, or None)."""
    if val is None or val == "":
        return []
    if isinstance(val, list):
        return [x for x in val if x]
    return [val] if val else []


PROJECT_ROOT_ID = "PROJECT_ROOT"


def entity_display_name(e: Dict[str, Any], prefer_name_first: bool = False) -> str:
    """Display name: narrative.role, symbol, name, or id."""
    if not e:
        return ""
    narrative = (e.get("narrative") or {}) if isinstance(e.get("narrative"), dict) else {}
    role = (narrative.get("role") or "").strip()
    name = (e.get("name") or "").strip()
    symbol = (e.get("symbol") or "").strip() if isinstance(e.get("symbol"), str) else ""
    fallback = (e.get("id") or "").strip()
    if prefer_name_first:
        return name or role or symbol or fallback or ""
    if role:
        return role
    return symbol or name or fallback or ""


def get_root_entity(blueprint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return the root entity (id PROJECT_ROOT_ID) or None."""
    entities = blueprint.get("entities") or []
    for e in entities:
        if (e.get("id") or "") == PROJECT_ROOT_ID:
            return e
    return None


def top_layer_entities(blueprint: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return root's direct children (top-layer entities)."""
    root = get_root_entity(blueprint)
    if not root:
        return []
    child_ids = set(root.get("children") or [])
    entities = blueprint.get("entities") or []
    return [e for e in entities if (e.get("id") or "") in child_ids]


def _root_narrative(blueprint: Dict[str, Any]) -> Dict[str, str]:
    """Return root entity's narrative dict. Empty dict if no root."""
    root = get_root_entity(blueprint)
    if not root:
        return {}
    return (root.get("narrative") or {}) if isinstance(root.get("narrative"), dict) else {}


def mission_from_blueprint(blueprint: Dict[str, Any], default: str = "") -> str:
    """Root mission text. Returns stripped mission or default."""
    raw = (_root_narrative(blueprint).get("mission") or "").strip()
    return raw if raw else (default or "")


# ---------------------------------------------------------------------------
# Empty entity for defaults (no null)
# ---------------------------------------------------------------------------


def empty_outgoing_contracts() -> List[Dict[str, Any]]:
    return []


def empty_entity(id: str = "") -> Dict[str, Any]:
    """Entity with all keys present and empty defaults."""
    return {
        "id": id,
        "children": [],
        "dependencies": [],
        "narrative": {"role": "", "mission": ""},
        "blueprint": {"type": "FLOW", "topology": {}},
        "protocol": {"input": [], "output": []},
        "profile": {"language": [], "platform": "", "io_model": "", "state_model": ""},
        "governance": {"rules": [], "assertions": []},
        "symbol": "",
        "traits": [],
        "topology_actual": {"type": "", "map": []},
        "preview": "",
        "outgoing_contracts": empty_outgoing_contracts(),
    }


def empty_blueprint_root() -> Dict[str, Any]:
    """Root shape: version, root_id, entities."""
    return {
        "version": "1.0",
        "root_id": "",
        "entities": [],
    }
