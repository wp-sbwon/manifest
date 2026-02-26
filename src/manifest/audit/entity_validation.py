"""
Validation for blueprint data. Normalize null to ""/[]/{}; ensure required keys.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from manifest.audit.entity_schema import empty_entity


def _normalize_value(value: Any) -> Any:
    """Recursively coerce null to default; ensure no None in output."""
    if value is None:
        return ""
    if isinstance(value, dict):
        return {k: _normalize_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    return value


_ENTITY_KEYS = (
    "id", "children", "dependencies", "narrative", "blueprint", "protocol", "profile",
    "governance", "symbol", "traits", "topology_actual", "preview", "outgoing_contracts",
)


def normalize_for_schema(data: Dict[str, Any]) -> Dict[str, Any]:
    """Idempotent: coerce null to defaults, ensure required keys exist."""
    if not isinstance(data, dict):
        return {}
    data = _normalize_value(data)

    if "version" not in data:
        data["version"] = "1.0"
    if "entities" not in data:
        data["entities"] = []
    if "root_id" not in data:
        data["root_id"] = ""

    entities = data.get("entities") or []
    normalized_entities = []
    for ent in entities:
        if not isinstance(ent, dict):
            continue
        ent = _normalize_value(ent)
        base = empty_entity(ent.get("id") or "")
        for key in _ENTITY_KEYS:
            if key not in ent or ent[key] is None:
                ent[key] = base[key]
            elif key == "outgoing_contracts":
                oc = []
                for c in ent.get("outgoing_contracts") or []:
                    if not isinstance(c, dict):
                        continue
                    oc.append({
                        "to": (c.get("to") or ""),
                        "type": (c.get("type") or "dependency"),
                        "file": (c.get("file") or ""),
                        "symbols": list(c.get("symbols") or []),
                    })
                ent["outgoing_contracts"] = oc
            elif isinstance(ent[key], dict):
                ent[key] = {**base.get(key, {}), **_normalize_value(ent[key])}
            elif isinstance(ent[key], list):
                ent[key] = list(ent[key])
        normalized_entities.append(ent)
    data["entities"] = normalized_entities

    return data


def _entity_ids(data: Dict[str, Any]) -> set:
    ids = set()
    for ent in data.get("entities") or []:
        if isinstance(ent, dict):
            eid = ent.get("id")
            if eid and isinstance(eid, str) and eid.strip():
                ids.add(eid.strip())
    return ids


def _validate_entity(data: Any, path: str, valid_ids: Optional[set] = None) -> List[str]:
    errors: List[str] = []
    if not isinstance(data, dict):
        errors.append(f"{path}: entity must be an object")
        return errors
    for key in _ENTITY_KEYS:
        if key not in data:
            errors.append(f"{path}: missing '{key}'")
        elif data[key] is None:
            errors.append(f"{path}: '{key}' must not be null")
    if "children" in data and not isinstance(data["children"], list):
        errors.append(f"{path}: 'children' must be an array")
    if "dependencies" in data and not isinstance(data["dependencies"], list):
        errors.append(f"{path}: 'dependencies' must be an array")
    if "outgoing_contracts" in data:
        oc = data.get("outgoing_contracts") or []
        if not isinstance(oc, list):
            errors.append(f"{path}: 'outgoing_contracts' must be an array")
        else:
            for i, c in enumerate(oc):
                if isinstance(c, dict):
                    if "to" not in c:
                        errors.append(f"{path}.outgoing_contracts[{i}]: missing 'to'")
                    if "type" not in c:
                        errors.append(f"{path}.outgoing_contracts[{i}]: missing 'type'")
    if valid_ids:
        for i, cid in enumerate(data.get("children") or []):
            ref = (cid if isinstance(cid, str) else "").strip()
            if ref and ref not in valid_ids:
                errors.append(f"{path}.children[{i}]: references non-existent entity '{ref}'")
        for i, dep in enumerate(data.get("dependencies") or []):
            ref = (dep if isinstance(dep, str) else (dep.get("id") or dep.get("to") or "") if isinstance(dep, dict) else "").strip()
            if ref and ref not in valid_ids:
                errors.append(f"{path}.dependencies[{i}]: references non-existent entity")
        for i, oc in enumerate(data.get("outgoing_contracts") or []):
            if isinstance(oc, dict):
                to_id = (oc.get("to") or "").strip()
                if to_id and not to_id.startswith("external-") and to_id not in valid_ids:
                    errors.append(f"{path}.outgoing_contracts[{i}]: 'to' references non-existent entity '{to_id}'")
    return errors


def validate_entity(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors = _validate_entity(data, "entity")
    return (len(errors) == 0, errors)


def _validate_blueprint_root(data: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if not isinstance(data, dict):
        return ["root must be an object"]
    if "version" not in data:
        errors.append("missing 'version'")
    if "entities" not in data:
        errors.append("missing 'entities'")
    elif not isinstance(data["entities"], list):
        errors.append("'entities' must be an array")
    valid_ids = _entity_ids(data)
    root_id = (data.get("root_id") or "").strip()
    if root_id:
        valid_ids = valid_ids | {root_id}
    for i, ent in enumerate(data.get("entities") or []):
        errors.extend(_validate_entity(ent, f"entities[{i}]", valid_ids=valid_ids))
    return errors


def validate_blueprint_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    data = normalize_for_schema(data)
    errors = _validate_blueprint_root(data)
    return (len(errors) == 0, errors)


def validate_blueprint_file(path: Path) -> Tuple[bool, List[str]]:
    path = Path(path)
    if not path.exists():
        return (False, [f"File not found: {path}"])
    try:
        import json
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return (False, [f"Failed to load JSON: {e}"])
    data = normalize_for_schema(data)
    errors = _validate_blueprint_root(data)
    return (len(errors) == 0, errors)
