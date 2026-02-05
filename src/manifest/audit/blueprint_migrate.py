"""
One-time migration: old blueprint.json / blueprint_code.json (flat components + contracts + zones)
to new format (entities with id, children, dependencies, intent, reality).

Run once per repo or on first load when legacy format is detected.
"""
import json
from pathlib import Path
from typing import Any, Dict, List

from manifest.audit.entity_schema import empty_intent, empty_reality, PROJECT_ROOT_ID
from manifest.audit.entity_validation import normalize_for_schema, validate_blueprint_file
from manifest.core.logger import get_logger

logger = get_logger(__name__)



def _component_to_entity_plan(comp: Dict[str, Any], dependencies: List[str]) -> Dict[str, Any]:
    """Convert old plan component to new entity (intent filled, reality empty)."""
    cid = comp.get("id") or ""
    intent = {
        "narrative": {
            "role": (comp.get("name") or cid or "")[:200],
            "mission": (comp.get("description") or "")[:500],
        },
        "blueprint": {"type": "FLOW", "topology": {}},
        "protocol": {
            "input": [],
            "output": [],
        },
        "profile": {"language": "", "platform": "", "io_model": "", "state_model": ""},
        "governance": {
            "rules": list(comp.get("project_rules") or []),
            "assertions": [],
        },
    }
    # Optional: parse interface string into protocol
    iface = comp.get("interface") or ""
    if iface:
        intent["protocol"]["input"] = [{"name": "interface", "type": "string", "req": False}]
    entity = {
        "id": cid,
        "children": [],
        "dependencies": dependencies,
        "intent": intent,
        "reality": empty_reality(),
    }
    entity["name"] = comp.get("name") or (intent["narrative"].get("role") or cid)
    return entity


def _component_to_entity_actual(comp: Dict[str, Any], dependencies: List[str]) -> Dict[str, Any]:
    """Convert old actual component to new entity (reality filled, intent empty)."""
    cid = comp.get("id") or ""
    traits = list(comp.get("side_effects") or [])
    if comp.get("complexity"):
        traits.append(f"complexity:{comp.get('complexity')}")
    reality = {
        "symbol": (comp.get("file") or comp.get("module_path") or "")[:500],
        "protocol": {
            "input": [],
            "output": [],
        },
        "profile": {"language": "", "platform": "", "io_model": "", "state_model": ""},
        "dependencies": list(comp.get("dependencies") or []),
        "traits": traits,
        "topology_actual": {"type": "", "map": []},
        "preview": "",
    }
    det = comp.get("detected_interface") or ""
    if det:
        reality["protocol"]["output"] = [{"name": "signature", "type": "string"}]
    entity = {
        "id": cid,
        "children": [],
        "dependencies": dependencies,
        "intent": empty_intent(),
        "reality": reality,
    }
    # Backward compat for comparator: preserve methods, attributes, file, name
    if comp.get("methods") is not None:
        entity["methods"] = comp["methods"]
    if comp.get("attributes") is not None:
        entity["attributes"] = comp["attributes"]
    entity["file"] = comp.get("file") or ""
    entity["name"] = comp.get("name") or cid
    return entity


def _dependencies_from_contracts(contracts: List[Dict[str, Any]], entity_ids: set) -> Dict[str, List[str]]:
    """Build per-entity dependencies from contracts (to_id list for each from_id)."""
    deps: Dict[str, List[str]] = {}
    for c in contracts or []:
        from_id = c.get("from") or ""
        to_id = c.get("to") or ""
        if not from_id or not to_id:
            continue
        if to_id.startswith("external-"):
            continue
        if to_id in entity_ids:
            deps.setdefault(from_id, []).append(to_id)
    return deps


def migrate_blueprint_data(data: Dict[str, Any], is_plan: bool) -> Dict[str, Any]:
    """
    Convert old blueprint dict (components, contracts, zones) to new format (entities, contracts).
    is_plan: True for blueprint.json (intent filled), False for blueprint_code.json (reality filled).
    """
    components = data.get("components") or []
    contracts = data.get("contracts") or []
    zones = data.get("zones") or {}

    entity_ids = {c.get("id") for c in components if c.get("id")}
    deps_map = _dependencies_from_contracts(contracts, entity_ids)

    entities: List[Dict[str, Any]] = []
    root_children: List[str] = []

    # Order: server, data, client, then any remaining
    for zone_name in ("server", "data", "client"):
        for cid in (zones.get(zone_name) or []):
            if cid in entity_ids:
                root_children.append(cid)
    for comp in components:
        cid = comp.get("id")
        if not cid:
            continue
        if cid not in root_children:
            root_children.append(cid)
        deps = deps_map.get(cid, [])
        if is_plan:
            entities.append(_component_to_entity_plan(comp, deps))
        else:
            entities.append(_component_to_entity_actual(comp, deps))

    # Prepend root entity
    root_entity = {
        "id": PROJECT_ROOT_ID,
        "children": root_children,
        "dependencies": [],
        "intent": empty_intent(),
        "reality": empty_reality(),
    }
    entities.insert(0, root_entity)

    # Normalize contracts to have "from", "to", "type"
    new_contracts = []
    for c in contracts:
        new_contracts.append({
            "from": c.get("from", ""),
            "to": c.get("to", ""),
            "type": c.get("type", "dependency"),
            "file": c.get("file", ""),
            "symbols": list(c.get("symbols") or []),
        })

    result = {
        "version": data.get("version", "1.0"),
        "root_id": PROJECT_ROOT_ID,
        "entities": entities,
        "contracts": new_contracts,
    }
    # Preserve optional metadata
    for key in ("source", "from_actual_code", "ground_truth", "last_updated", "extraction_method"):
        if key in data:
            result[key] = data[key]
    return normalize_for_schema(result)


def migrate_file(path: Path, is_plan: bool) -> bool:
    """
    Read file, migrate to new format, write back. Returns True if migrated, False if not legacy or error.
    """
    path = Path(path)
    if not path.exists():
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error("Failed to load %s: %s", path, e)
        return False
    if "entities" in data and "components" not in data:
        return False  # already new format
    if "components" not in data:
        return False
    migrated = migrate_blueprint_data(data, is_plan=is_plan)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(migrated, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error("Failed to write %s: %s", path, e)
        return False
    ok, errors = validate_blueprint_file(path)
    if not ok and errors:
        logger.warning("Validation after migrate had issues: %s", errors)
    logger.info("Migrated %s to new entity format", path)
    return True


def migrate_manifest_dir(manifest_dir: Path) -> Dict[str, bool]:
    """
    Migrate blueprint.json and blueprint_code.json in manifest_dir if they are legacy.
    Returns {"blueprint.json": True/False, "blueprint_code.json": True/False}.
    """
    manifest_dir = Path(manifest_dir)
    results = {}
    bp = manifest_dir / "blueprint.json"
    if bp.exists():
        results["blueprint.json"] = migrate_file(bp, is_plan=True)
    else:
        results["blueprint.json"] = False
    bpc = manifest_dir / "blueprint_code.json"
    if bpc.exists():
        results["blueprint_code.json"] = migrate_file(bpc, is_plan=False)
    else:
        results["blueprint_code.json"] = False
    return results


def main() -> int:
    """CLI: python -m manifest.audit.blueprint_migrate [--manifest-dir .manifest]"""
    import argparse
    parser = argparse.ArgumentParser(description="Migrate blueprint files to new entity format")
    parser.add_argument("--manifest-dir", type=Path, default=Path(".manifest"), help="Path to .manifest")
    args = parser.parse_args()
    manifest_dir = args.manifest_dir.resolve()
    if not manifest_dir.is_dir():
        print(f"Not a directory: {manifest_dir}", flush=True)
        return 1
    results = migrate_manifest_dir(manifest_dir)
    for name, done in results.items():
        print(f"  {name}: {'migrated' if done else 'skipped (already new or missing)'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
