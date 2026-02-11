"""
Fixed PRD JSON schema and validation.

Versioning is timestamp-based only (created_at, updated_at). No numeric version field.
"""
from typing import Any, Dict, List, Tuple
from datetime import datetime, timezone


# Required top-level keys per fixed PRD structure (align with .rules/prd-template.md)
REQUIRED_KEYS = (
    "title",
    "overview",
    "user_flows",
    "technical_constraints",
    "success_criteria",
    "architecture_requirements",
    "dependencies",
    "created_at",
    "updated_at",
)

# Key -> allowed JSON types: "string", "object", "array"
KEY_TYPES: Dict[str, str] = {
    "title": "string",
    "overview": "object",
    "user_flows": "array",
    "technical_constraints": "object",
    "success_criteria": "object",
    "architecture_requirements": "object",
    "dependencies": "array",
    "created_at": "string",
    "updated_at": "string",
}


def _is_valid_iso_timestamp(s: Any) -> bool:
    """Return True if s looks like an ISO timestamp string."""
    if not isinstance(s, str) or not s.strip():
        return False
    try:
        datetime.fromisoformat(s.replace("Z", "+00:00"))
        return True
    except Exception:
        return False


def validate_prd(prd: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate PRD against the fixed schema.

    Versioning is timestamp-based: created_at and updated_at are required.
    No numeric version field.

    Returns:
        (valid, list of error messages). valid is True only when errors is empty.
    """
    errors: List[str] = []
    if not isinstance(prd, dict):
        return False, ["PRD must be a JSON object"]

    for key in REQUIRED_KEYS:
        if key not in prd:
            errors.append(f"Missing required key: {key}")
            continue
        val = prd[key]
        expected = KEY_TYPES.get(key, "string")
        if expected == "string":
            if not isinstance(val, str):
                errors.append(f"'{key}' must be a string")
            elif key in ("created_at", "updated_at") and not _is_valid_iso_timestamp(val):
                errors.append(f"'{key}' must be an ISO timestamp string")
        elif expected == "object":
            if not isinstance(val, dict):
                errors.append(f"'{key}' must be an object")
        elif expected == "array":
            if not isinstance(val, list):
                errors.append(f"'{key}' must be an array")

    if "version" in prd:
        errors.append("PRD must not include a numeric 'version' field; use created_at/updated_at for versioning")

    return (len(errors) == 0, errors)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def normalize_prd(prd: Dict[str, Any]) -> Dict[str, Any]:
    """Fill missing required keys with empty defaults so older PRDs can load.

    Sets created_at/updated_at to now if missing. Does not validate;
    call validate_prd after normalize if you need to ensure validity.
    """
    if not isinstance(prd, dict):
        return prd
    out = dict(prd)
    now = _now_iso()
    defaults: Dict[str, Any] = {
        "title": out.get("title", ""),
        "overview": out.get("overview", {}),
        "user_flows": out.get("user_flows", []),
        "technical_constraints": out.get("technical_constraints", {}),
        "success_criteria": out.get("success_criteria", {}),
        "architecture_requirements": out.get("architecture_requirements", {}),
        "dependencies": out.get("dependencies", []),
        "created_at": out.get("created_at", now),
        "updated_at": out.get("updated_at", now),
    }
    for key, default in defaults.items():
        if key not in out:
            out[key] = default
    # Remove legacy numeric version if present
    out.pop("version", None)
    return out
