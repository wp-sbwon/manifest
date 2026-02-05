"""
Canonical schema for recursive universal entities (Option B).

Blueprint.json and blueprint_code.json share this shape. No nulls;
use "" for strings, [] for lists, {} for objects. Used by writers
(agents, CodeExtractor) and readers (BlueprintLoader, view).
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
    """Recursive universal entity: id, children, dependencies, intent, reality."""
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
    """Per-entity validation (output only; not stored in plan/actual files)."""
    status: str = "planned"  # healthy | deviation | planned | partial
    deviations: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Root shape for blueprint.json and blueprint_code.json
# ---------------------------------------------------------------------------


def default_entities() -> List[Dict[str, Any]]:
    return []


def default_contracts() -> List[Dict[str, Any]]:
    return []


@dataclass
class BlueprintRoot:
    """Top-level shape for blueprint.json and blueprint_code.json."""
    version: str = "1.0"
    root_id: str = ""
    entities: List[Dict[str, Any]] = field(default_factory=default_entities)
    contracts: List[Dict[str, Any]] = field(default_factory=default_contracts)


# Root entity id used in blueprint/blueprint_code (plan and actual)
PROJECT_ROOT_ID = "PROJECT_ROOT"

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


def empty_entity(id: str = "") -> Dict[str, Any]:
    return {
        "id": id,
        "children": [],
        "dependencies": [],
        "intent": empty_intent(),
        "reality": empty_reality(),
    }


def empty_blueprint_root() -> Dict[str, Any]:
    return {
        "version": "1.0",
        "root_id": "",
        "entities": [],
        "contracts": [],
    }


# ---------------------------------------------------------------------------
# JSON Schema export for mechanical validation and docs
# ---------------------------------------------------------------------------


def entity_json_schema() -> Dict[str, Any]:
    """Return a JSON Schema for one entity (for validation/tooling)."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["id", "children", "dependencies", "intent", "reality"],
        "additionalProperties": True,
        "properties": {
            "id": {"type": "string"},
            "children": {"type": "array", "items": {"type": "string"}},
            "dependencies": {"type": "array", "items": {"type": "string"}},
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
    """Return a JSON Schema for blueprint/blueprint_code root (version, root_id, entities, contracts)."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["version", "entities", "contracts"],
        "additionalProperties": True,
        "properties": {
            "version": {"type": "string"},
            "root_id": {"type": "string"},
            "entities": {
                "type": "array",
                "items": entity_json_schema(),
            },
            "contracts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["from", "to", "type"],
                    "properties": {
                        "from": {"type": "string"},
                        "to": {"type": "string"},
                        "type": {"type": "string"},
                        "file": {"type": "string"},
                        "symbols": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
        },
    }
