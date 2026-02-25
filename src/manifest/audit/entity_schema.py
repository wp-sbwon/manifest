"""
Canonical schema for blueprint entities.

Persisted shape: version, root_id, entities. Each entity: id, children, dependencies,
narrative, blueprint, protocol, profile, governance, symbol, traits, topology_actual, preview,
outgoing_contracts. No nulls; use "" or []/{}.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ProtocolItem:
    """Single input or output in protocol; name/type for mechanical check."""
    name: str = ""
    type: str = ""
    req: bool = False


@dataclass
class TopologyMapItem:
    """One entry in topology map; area = [start_row, start_col, row_span, col_span]."""
    id: str = ""
    area: List[int] = field(default_factory=lambda: [0, 0, 1, 1])
    label: str = ""


# ---------------------------------------------------------------------------
# Entity shape (single set of fields for design and code blueprints)
# ---------------------------------------------------------------------------


@dataclass
class Entity:
    """Entity: id, structure, narrative/blueprint/governance, protocol/profile, symbol/traits/preview, contracts."""
    id: str = ""
    children: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    narrative: Dict[str, str] = field(default_factory=lambda: {"role": "", "mission": ""})
    blueprint: Dict[str, Any] = field(default_factory=lambda: {"type": "FLOW", "topology": {}})
    protocol: Dict[str, List[Dict[str, Any]]] = field(
        default_factory=lambda: {"input": [], "output": []}
    )
    profile: Dict[str, str] = field(
        default_factory=lambda: {"language": "", "platform": "", "io_model": "", "state_model": ""}
    )
    governance: Dict[str, List[str]] = field(
        default_factory=lambda: {"rules": [], "assertions": []}
    )
    symbol: str = ""
    traits: List[str] = field(default_factory=list)
    topology_actual: Dict[str, Any] = field(default_factory=lambda: {"type": "", "map": []})
    preview: str = ""
    outgoing_contracts: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Contract:
    """Edge between entities: from, to, type; optional file and symbols."""
    from_id: str = ""
    to_id: str = ""
    type: str = "dependency"
    file: str = ""
    symbols: List[str] = field(default_factory=list)


@dataclass
class Validation:
    """Per-entity validation result (status, deviations from view)."""
    status: str = "planned"
    deviations: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Root shape for blueprint JSON
# ---------------------------------------------------------------------------


def default_entities() -> List[Dict[str, Any]]:
    return []


@dataclass
class BlueprintRoot:
    """Root shape for blueprint JSON."""
    version: str = "1.0"
    root_id: str = ""
    entities: List[Dict[str, Any]] = field(default_factory=default_entities)


def contracts_from_entities(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Derive flat contract list from entities' outgoing_contracts."""
    out: List[Dict[str, Any]] = []
    for e in entities or []:
        eid = e.get("id") or ""
        for oc in e.get("outgoing_contracts") or []:
            if not isinstance(oc, dict):
                continue
            out.append({
                "from": eid,
                "to": oc.get("to") or "",
                "type": oc.get("type") or "dependency",
                "file": oc.get("file") or "",
                "symbols": list(oc.get("symbols") or []),
            })
    return out


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


def non_root_entities(blueprint: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return entities except the root."""
    entities = blueprint.get("entities") or []
    return [e for e in entities if (e.get("id") or "") != PROJECT_ROOT_ID]


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


def root_narrative(blueprint: Dict[str, Any]) -> Dict[str, str]:
    """Return root entity's narrative dict. Empty dict if no root."""
    root = get_root_entity(blueprint)
    if not root:
        return {}
    return (root.get("narrative") or {}) if isinstance(root.get("narrative"), dict) else {}


def mission_from_blueprint(blueprint: Dict[str, Any], default: str = "") -> str:
    """Root mission text. Returns stripped mission or default."""
    raw = (root_narrative(blueprint).get("mission") or "").strip()
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
        "profile": {"language": "", "platform": "", "io_model": "", "state_model": ""},
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
