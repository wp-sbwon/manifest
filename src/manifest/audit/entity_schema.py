"""
Canonical schema for recursive universal entities.

Persisted shape: version, root_id, entities. Each entity: id, children,
dependencies, intent, reality, outgoing_contracts. No nulls; use "" or []/{}.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Protocol and nested intent/reality structures (doc §1.1)
# ---------------------------------------------------------------------------


@dataclass
class ProtocolItem:
    """Single input or output in protocol; name/type for mechanical check."""
    name: str = ""
    type: str = ""
    req: bool = False  # for input items only


@dataclass
class Narrative:
    """Intent narrative: role and mission."""
    role: str = ""
    mission: str = ""


@dataclass
class TopologyMapItem:
    """One entry in topology map; area = [start_row, start_col, row_span, col_span]."""
    id: str = ""
    area: List[int] = field(default_factory=lambda: [0, 0, 1, 1])
    label: str = ""


@dataclass
class Topology:
    """Blueprint topology: dimensions and map."""
    dimensions: Dict[str, int] = field(default_factory=lambda: {"rows": 12, "cols": 12})
    map: List[TopologyMapItem] = field(default_factory=list)


@dataclass
class BlueprintIntent:
    """Intent blueprint: type (GRID|STACK|FLOW) and topology."""
    type: str = "FLOW"
    topology: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Profile:
    """Profile: language, platform, io_model, state_model."""
    language: str = ""
    platform: str = ""
    io_model: str = ""
    state_model: str = ""


@dataclass
class Governance:
    """Governance: rules and assertions."""
    rules: List[str] = field(default_factory=list)
    assertions: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Intent (plan side) and Reality (actual side) — same key set per entity
# ---------------------------------------------------------------------------


@dataclass
class Intent:
    """Entity intent: narrative, blueprint, protocol, profile, governance."""
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


@dataclass
class Reality:
    """Entity reality: symbol, protocol, profile, dependencies, traits, topology_actual, preview."""
    symbol: str = ""
    protocol: Dict[str, List[Dict[str, Any]]] = field(
        default_factory=lambda: {"input": [], "output": []}
    )
    profile: Dict[str, str] = field(
        default_factory=lambda: {"language": "", "platform": "", "io_model": "", "state_model": ""}
    )
    dependencies: List[str] = field(default_factory=list)
    traits: List[str] = field(default_factory=list)
    topology_actual: Dict[str, Any] = field(default_factory=lambda: {"type": "", "map": []})
    preview: str = ""


# ---------------------------------------------------------------------------
# Entity and root shape
# ---------------------------------------------------------------------------


@dataclass
class Entity:
    """Recursive entity: id, children, dependencies, intent, reality, outgoing_contracts."""
    id: str = ""
    children: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    intent: Dict[str, Any] = field(default_factory=lambda: {
        "narrative": {"role": "", "mission": ""},
        "blueprint": {"type": "FLOW", "topology": {}},
        "protocol": {"input": [], "output": []},
        "profile": {"language": "", "platform": "", "io_model": "", "state_model": ""},
        "governance": {"rules": [], "assertions": []},
    })
    reality: Dict[str, Any] = field(default_factory=lambda: {
        "symbol": "",
        "protocol": {"input": [], "output": []},
        "profile": {"language": "", "platform": "", "io_model": "", "state_model": ""},
        "dependencies": [],
        "traits": [],
        "topology_actual": {"type": "", "map": []},
        "preview": "",
    })
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
    """Per-entity validation result."""
    status: str = "planned"
    deviations: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Root shape for blueprint_design.json and blueprint_code.json
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


# Root entity id used in blueprint/blueprint_code (plan and actual)
PROJECT_ROOT_ID = "PROJECT_ROOT"


def entity_display_name(e: Dict[str, Any], prefer_name_first: bool = False) -> str:
    """Display name: role, symbol, name, or id. If prefer_name_first, name is tried before role."""
    if not e:
        return ""
    n = (e.get("intent") or {}).get("narrative") or {}
    role = (n.get("role") or "").strip() if isinstance(n, dict) else ""
    name = (e.get("name") or "").strip()
    symbol = (e.get("reality") or {}).get("symbol") or ""
    if isinstance(symbol, str):
        symbol = symbol.strip()
    else:
        symbol = ""
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
    """Return root's direct children (top-layer entities). No explicit type (e.g. modules)."""
    root = get_root_entity(blueprint)
    if not root:
        return []
    child_ids = set(root.get("children") or [])
    entities = blueprint.get("entities") or []
    return [e for e in entities if (e.get("id") or "") in child_ids]


def root_intent(blueprint: Dict[str, Any]) -> Dict[str, Any]:
    """Return root entity's intent dict. Empty dict if no root."""
    root = get_root_entity(blueprint)
    if not root:
        return {}
    return root.get("intent") or {}


def mission_from_blueprint(blueprint: Dict[str, Any], default: str = "") -> str:
    """Root mission text. Returns stripped mission or default."""
    raw = (root_intent(blueprint).get("narrative") or {}).get("mission") or ""
    out = (raw or "").strip()
    return out if out else (default or "")


# ---------------------------------------------------------------------------
# Empty entity / intent / reality for defaults (no null)
# ---------------------------------------------------------------------------


def empty_intent() -> Dict[str, Any]:
    return {
        "narrative": {"role": "", "mission": ""},
        "blueprint": {"type": "FLOW", "topology": {}},
        "protocol": {"input": [], "output": []},
        "profile": {"language": "", "platform": "", "io_model": "", "state_model": ""},
        "governance": {"rules": [], "assertions": []},
    }


def empty_reality() -> Dict[str, Any]:
    return {
        "symbol": "",
        "protocol": {"input": [], "output": []},
        "profile": {"language": "", "platform": "", "io_model": "", "state_model": ""},
        "dependencies": [],
        "traits": [],
        "topology_actual": {"type": "", "map": []},
        "preview": "",
    }


def empty_outgoing_contracts() -> List[Dict[str, Any]]:
    """Returns an empty list."""
    return []


def empty_entity(id: str = "") -> Dict[str, Any]:
    return {
        "id": id,
        "children": [],
        "dependencies": [],
        "intent": empty_intent(),
        "reality": empty_reality(),
        "outgoing_contracts": empty_outgoing_contracts(),
    }


def empty_blueprint_root() -> Dict[str, Any]:
    """Root shape: version, root_id, entities."""
    return {
        "version": "1.0",
        "root_id": "",
        "entities": [],
    }
