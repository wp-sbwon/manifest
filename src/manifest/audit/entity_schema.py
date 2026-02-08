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


def entity_display_name(e: Dict[str, Any]) -> str:
    """Display name: role, symbol, name, or id."""
    if not e:
        return ""
    n = (e.get("intent") or {}).get("narrative") or {}
    role = n.get("role") if isinstance(n, dict) else ""
    if role:
        return role
    return (e.get("reality") or {}).get("symbol") or e.get("name") or e.get("id") or ""


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
    """Return top-layer entities (root's children). Layer 0 = features."""
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


def mission_from_blueprint(blueprint: Dict[str, Any], fallback: str = "") -> str:
    """Root mission text for display. Returns stripped mission or fallback."""
    raw = (root_intent(blueprint).get("narrative") or {}).get("mission") or ""
    out = (raw or "").strip()
    return out if out else (fallback or "")


def goals_from_blueprint(blueprint: Dict[str, Any]) -> List[Any]:
    """Root goals list for display. Returns list of goal dicts or strings; empty list if none."""
    goals = root_intent(blueprint).get("goals")
    if goals is None or not isinstance(goals, list):
        return []
    return goals


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


# ---------------------------------------------------------------------------
# JSON Schema export for mechanical validation and docs
# ---------------------------------------------------------------------------


def entity_json_schema() -> Dict[str, Any]:
    """Return a JSON Schema for one entity (for validation/tooling)."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["id", "children", "dependencies", "intent", "reality", "outgoing_contracts"],
        "additionalProperties": True,
        "properties": {
            "id": {"type": "string"},
            "children": {"type": "array", "items": {"type": "string"}},
            "dependencies": {"type": "array", "items": {"type": "string"}},
            "outgoing_contracts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string"},
                        "type": {"type": "string"},
                        "file": {"type": "string"},
                        "symbols": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
            "intent": {
                "type": "object",
                "required": ["narrative", "blueprint", "protocol", "profile", "governance"],
                "properties": {
                    "narrative": {
                        "type": "object",
                        "properties": {"role": {"type": "string"}, "mission": {"type": "string"}},
                    },
                    "blueprint": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["GRID", "STACK", "FLOW"]},
                            "topology": {"type": "object"},
                        },
                    },
                    "protocol": {
                        "type": "object",
                        "properties": {
                            "input": {"type": "array", "items": {"type": "object"}},
                            "output": {"type": "array", "items": {"type": "object"}},
                        },
                    },
                    "profile": {"type": "object"},
                    "governance": {
                        "type": "object",
                        "properties": {
                            "rules": {"type": "array", "items": {"type": "string"}},
                            "assertions": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
            },
            "reality": {
                "type": "object",
                "required": [
                    "symbol", "protocol", "profile", "dependencies", "traits",
                    "topology_actual", "preview",
                ],
                "properties": {
                    "symbol": {"type": "string"},
                    "protocol": {"type": "object"},
                    "profile": {"type": "object"},
                    "dependencies": {"type": "array", "items": {"type": "string"}},
                    "traits": {"type": "array", "items": {"type": "string"}},
                    "topology_actual": {"type": "object"},
                    "preview": {"type": "string"},
                },
            },
        },
    }


def blueprint_root_json_schema() -> Dict[str, Any]:
    """Return a JSON Schema for blueprint/blueprint_code root (version, root_id, entities)."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["version", "entities"],
        "additionalProperties": True,
        "properties": {
            "version": {"type": "string"},
            "root_id": {"type": "string"},
            "entities": {
                "type": "array",
                "items": entity_json_schema(),
            },
        },
    }
