"""
Mechanical validation for blueprint data.

Normalize null to ""/[]/{}; ensure required keys. Use on read and before write.
"""
from pathlib import Path
from typing import Any, Dict, List, Tuple

from manifest.schema.entity_schema import empty_intent, empty_reality, empty_outgoing_contracts


def _normalize_value(value: Any) -> Any:
    """Recursively coerce null to default; ensure no None in output."""
    if value is None:
        return ""
    if isinstance(value, dict):
        return {k: _normalize_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    return value


def normalize_for_schema(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Idempotent: coerce null to defaults, ensure required keys exist.
    Use on read so downstream code never sees null or missing keys.
    """
    if not isinstance(data, dict):
        return {}
    data = _normalize_value(data)

    # Ensure required root keys
    if "version" not in data:
        data["version"] = "1.0"
    if "entities" not in data:
        data["entities"] = []
    if "root_id" not in data:
        data["root_id"] = ""

    # Normalize each entity
    entities = data.get("entities") or []
    normalized_entities = []
    for ent in entities:
        if not isinstance(ent, dict):
            continue
        ent = _normalize_value(ent)
        if "id" not in ent:
            ent["id"] = ""
        if "children" not in ent:
            ent["children"] = []
        if "dependencies" not in ent:
            ent["dependencies"] = []
        if "intent" not in ent or not isinstance(ent["intent"], dict):
            ent["intent"] = empty_intent()
        else:
            ent["intent"] = _normalize_value(ent["intent"])
        if "reality" not in ent or not isinstance(ent["reality"], dict):
            ent["reality"] = empty_reality()
        else:
            ent["reality"] = _normalize_value(ent["reality"])
        if "outgoing_contracts" not in ent or not isinstance(ent.get("outgoing_contracts"), list):
            ent["outgoing_contracts"] = empty_outgoing_contracts()
        else:
            oc = []
            for c in ent["outgoing_contracts"]:
                if not isinstance(c, dict):
                    continue
                c = _normalize_value(c)
                oc.append({
                    "to": c.get("to") or "",
                    "type": c.get("type") or "dependency",
                    "file": c.get("file") or "",
                    "symbols": list(c.get("symbols") or []),
                })
            ent["outgoing_contracts"] = oc
        normalized_entities.append(ent)
    data["entities"] = normalized_entities

    return data


def _validate_entity(data: Any, path: str) -> List[str]:
    """Validate one entity; return list of error messages."""
    errors: List[str] = []
    if not isinstance(data, dict):
        errors.append(f"{path}: entity must be an object")
        return errors
    if "id" not in data:
        errors.append(f"{path}: missing 'id'")
    if "children" not in data:
        errors.append(f"{path}: missing 'children'")
    elif not isinstance(data["children"], list):
        errors.append(f"{path}: 'children' must be an array")
    if "dependencies" not in data:
        errors.append(f"{path}: missing 'dependencies'")
    elif not isinstance(data["dependencies"], list):
        errors.append(f"{path}: 'dependencies' must be an array")
    if "intent" not in data:
        errors.append(f"{path}: missing 'intent'")
    elif not isinstance(data["intent"], dict):
        errors.append(f"{path}: 'intent' must be an object")
    if "reality" not in data:
        errors.append(f"{path}: missing 'reality'")
    elif not isinstance(data["reality"], dict):
        errors.append(f"{path}: 'reality' must be an object")
    if "outgoing_contracts" not in data:
        errors.append(f"{path}: missing 'outgoing_contracts'")
    elif not isinstance(data["outgoing_contracts"], list):
        errors.append(f"{path}: 'outgoing_contracts' must be an array")
    else:
        for i, oc in enumerate(data.get("outgoing_contracts") or []):
            if isinstance(oc, dict):
                if "to" not in oc:
                    errors.append(f"{path}.outgoing_contracts[{i}]: missing 'to'")
                if "type" not in oc:
                    errors.append(f"{path}.outgoing_contracts[{i}]: missing 'type'")
    # No nulls
    for key in ("id", "children", "dependencies", "intent", "reality", "outgoing_contracts"):
        if key in data and data[key] is None:
            errors.append(f"{path}: '{key}' must not be null")
    return errors


def validate_entity(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate one entity against the canonical schema.
    Returns (valid, list of error messages).
    """
    errors = _validate_entity(data, "entity")
    return (len(errors) == 0, errors)


def _validate_blueprint_root(data: Dict[str, Any]) -> List[str]:
    """Validate root and all entities."""
    errors: List[str] = []
    if not isinstance(data, dict):
        return ["root must be an object"]
    if "version" not in data:
        errors.append("missing 'version'")
    if "entities" not in data:
        errors.append("missing 'entities'")
    elif not isinstance(data["entities"], list):
        errors.append("'entities' must be an array")
    for i, ent in enumerate(data.get("entities") or []):
        errors.extend(_validate_entity(ent, f"entities[{i}]"))
    return errors


def validate_blueprint_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate a blueprint/blueprint_code dict (already loaded).
    Returns (valid, list of error messages).
    """
    data = normalize_for_schema(data)
    errors = _validate_blueprint_root(data)
    return (len(errors) == 0, errors)


def validate_blueprint_file(path: Path) -> Tuple[bool, List[str]]:
    """
    Load JSON from path, normalize, then validate root and each entity.
    Returns (valid, list of error messages).
    """
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


def validate_blueprint_code_file(path: Path) -> Tuple[bool, List[str]]:
    """
    Same as validate_blueprint_file (same schema for plan and actual).
    Returns (valid, list of error messages).
    """
    return validate_blueprint_file(path)
