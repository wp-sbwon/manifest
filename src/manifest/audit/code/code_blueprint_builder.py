"""
Bottom-up blueprint_code: CodeExtractor produces an outline; merge_design_and_extraction
combines design (narrative, governance) with extraction (symbol, protocol, dependencies) by exact ID.
"""
from pathlib import Path
from typing import Dict, Any, List

from manifest.audit.entity_schema import (
    PROJECT_ROOT_ID,
    empty_entity,
    language_to_list,
)
from manifest.audit.entity_validation import normalize_for_schema
from manifest.core.logger import get_logger

logger = get_logger(__name__)


def _fields_from_extracted(ent: Dict[str, Any]) -> Dict[str, Any]:
    """Symbol, protocol, profile, dependencies, traits, topology_actual, preview from extracted entity."""
    raw_profile = ent.get("profile") or {"language": [], "platform": "", "io_model": "", "state_model": ""}
    profile = {**raw_profile, "language": language_to_list(raw_profile.get("language"))}
    return {
        "symbol": ent.get("symbol") or "",
        "protocol": ent.get("protocol") or {"input": [], "output": []},
        "profile": profile,
        "dependencies": list(ent.get("dependencies") or []),
        "traits": list(ent.get("traits") or []),
        "topology_actual": ent.get("topology_actual") or {"type": "", "map": []},
        "preview": ent.get("preview") or "",
    }


def _normalize_symbol_for_match(symbol: str) -> str:
    """Path or dotted module to comparable form: dots, no .py."""
    s = (symbol or "").strip().replace("\\", "/")
    if s.endswith(".py"):
        s = s[:-3]
    return s.replace("/", ".").strip(".")


def _extraction_with_design_ids(
    design_blueprint: Dict[str, Any],
    extracted_blueprint: Dict[str, Any],
) -> Dict[str, Any]:
    """Rewrite extracted entity ids to design ids when symbol matches exactly. One-to-one."""
    design_entities = {e.get("id"): e for e in (design_blueprint.get("entities") or []) if e.get("id")}
    design_symbol_to_id = {}
    for eid, ent in design_entities.items():
        if eid == PROJECT_ROOT_ID:
            continue
        sym = _normalize_symbol_for_match(ent.get("symbol") or "")
        if sym and sym not in design_symbol_to_id:
            design_symbol_to_id[sym] = eid
    new_entities = []
    used_design_ids = set()
    for e in extracted_blueprint.get("entities") or []:
        eid = (e.get("id") or "").strip()
        if eid == PROJECT_ROOT_ID:
            new_entities.append(dict(e))
            continue
        symbol_norm = _normalize_symbol_for_match(e.get("symbol") or "")
        design_id = design_symbol_to_id.get(symbol_norm) if symbol_norm else None
        if design_id and design_id not in used_design_ids:
            used_design_ids.add(design_id)
            ent = dict(e)
            ent["id"] = design_id
            new_entities.append(ent)
        else:
            new_entities.append(dict(e))
    return {**extracted_blueprint, "entities": new_entities}


def merge_design_and_extraction(
    design_blueprint: Dict[str, Any],
    extracted_blueprint: Dict[str, Any],
) -> Dict[str, Any]:
    """Merge by exact ID only. Narrative and governance from design; mechanical fields from extraction.
    Includes design entities with no extraction match (planned). Includes extracted entities with no design id (orphans)."""
    design_entities = {e.get("id"): e for e in (design_blueprint.get("entities") or []) if e.get("id")}
    extracted_by_id = {
        (e.get("id") or "").strip(): e
        for e in (extracted_blueprint.get("entities") or [])
        if (e.get("id") or "").strip() and (e.get("id") or "").strip() != PROJECT_ROOT_ID
    }
    root_id = design_blueprint.get("root_id") or extracted_blueprint.get("root_id") or PROJECT_ROOT_ID
    design_ids = set(design_entities)
    code_entity_ids = set()

    entities: List[Dict[str, Any]] = []

    for eid, design_ent in design_entities.items():
        if eid == PROJECT_ROOT_ID:
            base = dict(empty_entity(eid))
            base["id"] = eid
            base["children"] = list(design_ent.get("children") or [])
            base["dependencies"] = list(design_ent.get("dependencies") or [])
            base["outgoing_contracts"] = list(design_ent.get("outgoing_contracts") or [])
            for key in ("narrative", "blueprint", "protocol", "profile", "governance", "symbol", "traits", "topology_actual", "preview"):
                base[key] = design_ent.get(key, base[key])
            entities.append(base)
            code_entity_ids.add(eid)
            continue
        ext = extracted_by_id.get(eid)
        if ext is None:
            base = dict(empty_entity(eid))
            base["id"] = eid
            base["children"] = list(design_ent.get("children") or [])
            base["dependencies"] = list(design_ent.get("dependencies") or [])
            base["outgoing_contracts"] = list(design_ent.get("outgoing_contracts") or [])
            for key in ("narrative", "blueprint", "protocol", "profile", "governance", "symbol", "traits", "topology_actual", "preview"):
                base[key] = design_ent.get(key, base[key])
            entities.append(base)
            code_entity_ids.add(eid)
            continue
        base = dict(empty_entity(eid))
        base["id"] = eid
        base["children"] = list(design_ent.get("children") or [])
        base["dependencies"] = list(design_ent.get("dependencies") or [])
        base["outgoing_contracts"] = list(design_ent.get("outgoing_contracts") or [])
        base["narrative"] = design_ent.get("narrative", base["narrative"])
        base["blueprint"] = design_ent.get("blueprint", base["blueprint"])
        base["governance"] = design_ent.get("governance", base["governance"])
        mech = _fields_from_extracted(ext)
        base["symbol"] = mech["symbol"]
        base["protocol"] = mech["protocol"]
        base["profile"] = mech["profile"]
        base["traits"] = mech["traits"]
        base["topology_actual"] = mech["topology_actual"]
        base["preview"] = mech["preview"]
        deps = mech["dependencies"]
        base["dependencies"] = [d for d in deps if (d if isinstance(d, str) else (d.get("to") or d.get("id") or "")) in design_ids]
        oc = ext.get("outgoing_contracts") or []
        base["outgoing_contracts"] = [c for c in oc if isinstance(c, dict) and (c.get("to") or "").strip() in design_ids]
        entities.append(base)
        code_entity_ids.add(eid)

    for ext_id, ext in extracted_by_id.items():
        if ext_id in design_ids:
            continue
        base = dict(empty_entity(ext_id))
        base["id"] = ext_id
        mech = _fields_from_extracted(ext)
        base["children"] = []
        base["dependencies"] = [d for d in mech["dependencies"] if isinstance(d, str) and d in (design_ids | code_entity_ids)]
        base["outgoing_contracts"] = [c for c in (ext.get("outgoing_contracts") or []) if isinstance(c, dict) and (c.get("to") or "").strip() in (design_ids | code_entity_ids)]
        base["narrative"] = {"role": "", "mission": ""}
        base["blueprint"] = {"type": "", "topology": {}}
        base["governance"] = {"rules": [], "assertions": []}
        base["symbol"] = mech["symbol"]
        base["protocol"] = mech["protocol"]
        base["profile"] = mech["profile"]
        base["traits"] = mech["traits"]
        base["topology_actual"] = mech["topology_actual"]
        base["preview"] = mech["preview"]
        entities.append(base)
        code_entity_ids.add(ext_id)

    code_entity_ids = {e.get("id") for e in entities if e.get("id")}
    for e in entities:
        children = e.get("children") or []
        e["children"] = [c for c in children if c in code_entity_ids]
        deps = e.get("dependencies") or []
        e["dependencies"] = [d for d in deps if (d if isinstance(d, str) else (d.get("to") or d.get("id") or "")) in code_entity_ids]
        oc = e.get("outgoing_contracts") or []
        e["outgoing_contracts"] = [c for c in oc if isinstance(c, dict) and (c.get("to") or "").strip() in code_entity_ids]

    root_first = [e for e in entities if (e.get("id") or "") == PROJECT_ROOT_ID]
    rest = [e for e in entities if (e.get("id") or "") != PROJECT_ROOT_ID]
    ordered = (root_first or []) + rest
    if not root_first and ordered:
        root_entity = dict(empty_entity(PROJECT_ROOT_ID))
        root_entity["id"] = PROJECT_ROOT_ID
        root_entity["children"] = [e["id"] for e in rest]
        ordered = [root_entity] + rest

    by_id = {e.get("id"): e for e in ordered if e.get("id")}
    for e in ordered:
        child_ids = e.get("children") or []
        if not child_ids:
            continue
        languages = set()
        for cid in child_ids:
            child = by_id.get(cid)
            if child:
                languages.update(language_to_list((child.get("profile") or {}).get("language")))
        if languages:
            prof = dict(e.get("profile") or {})
            prof["language"] = sorted(languages)
            e["profile"] = prof

    for e in ordered:
        prof = dict(e.get("profile") or {})
        prof["language"] = language_to_list((e.get("profile") or {}).get("language"))
        e["profile"] = prof

    return normalize_for_schema({
        "version": design_blueprint.get("version") or "1.0",
        "root_id": root_id,
        "entities": ordered,
    })


def build_code_blueprint(
    project_root: Path,
    manifest_dir: Path,
    design_blueprint: Dict[str, Any],
    extracted_blueprint: Dict[str, Any],
) -> Dict[str, Any]:
    """Produce blueprint_code by deterministic merge: map extraction to design ids by symbol, then exact-ID merge."""
    extracted_mapped = _extraction_with_design_ids(design_blueprint, extracted_blueprint)
    result = merge_design_and_extraction(design_blueprint, extracted_mapped)
    for e in result.get("entities") or []:
        prof = dict(e.get("profile") or {})
        prof["language"] = language_to_list((e.get("profile") or {}).get("language"))
        e["profile"] = prof
    return result
