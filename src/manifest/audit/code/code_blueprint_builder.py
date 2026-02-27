"""
Bottom-up blueprint_code: CodeExtractor produces an outline of actual code; the LLM agent reads that
outline, the actual code, and blueprint_design (guide only), and produces blueprint_code. Result must
be based on actual code only; entities not present in the code must not appear in blueprint_code.
"""
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

from manifest.audit.entity_schema import (
    PROJECT_ROOT_ID,
    empty_entity,
    entity_display_name,
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


def _normalize_for_match(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"[\s_\-\.]+", "", (s or "").lower())


def _module_path_from_extracted_id(eid: str) -> str:
    if not eid or not eid.startswith("comp-"):
        return ""
    rest = eid[5:]
    idx = rest.rfind("-")
    if idx <= 0:
        return rest.replace("-", ".")
    return rest[:idx].replace("-", ".")


def _tokens_for_match(s: str) -> set:
    if not s:
        return set()
    normalized = _normalize_for_match(s)
    parts = re.split(r"(?=[A-Z])|[\s_\-\.]+", s)
    tokens = {_normalize_for_match(p) for p in parts if p}
    if normalized:
        tokens.add(normalized)
    return tokens


def _design_id_as_path_segment(design_id: str) -> str:
    return design_id.replace("_", ".")


def _segment_matches(s: str, design_norm: str) -> bool:
    if not design_norm:
        return False
    segments = re.split(r"[\s_\-\.]+", (s or "").lower())
    norm_segments = [_normalize_for_match(seg) for seg in segments if seg]
    return design_norm in norm_segments


def _find_best_extracted_match(
    design_id: str,
    design_ent: Dict[str, Any],
    extracted_list: List[Dict[str, Any]],
    extracted_by_exact: Dict[str, Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    name = (entity_display_name(design_ent) or "").strip().lower()
    ext = extracted_by_exact.get(design_id) or extracted_by_exact.get(name)
    if ext:
        return ext
    design_norm = _normalize_for_match(design_id)
    design_tokens = _tokens_for_match(design_id) | _tokens_for_match(name)
    role = ((design_ent.get("narrative") or {}).get("role") or "").strip()
    design_tokens |= _tokens_for_match(role)
    design_path_seg = _design_id_as_path_segment(design_id)
    candidates: List[tuple] = []
    for e in extracted_list:
        eid = (e.get("id") or "").strip()
        disp = (entity_display_name(e) or "").strip()
        mod_path = _module_path_from_extracted_id(eid)
        symbol = (e.get("symbol") or "").strip()
        mod_segments = mod_path.split(".")
        mod_segments_underscore = mod_path.replace(".", "_").split("_")
        if design_path_seg and design_path_seg in mod_segments:
            candidates.append((e, 3, "path"))
        elif design_id and design_id in mod_segments_underscore:
            candidates.append((e, 3, "path"))
        elif design_norm and _segment_matches(disp, design_norm):
            candidates.append((e, 2, "partial_name"))
        elif design_norm and _segment_matches(eid, design_norm):
            candidates.append((e, 2, "partial_id"))
        elif design_norm and _segment_matches(symbol, design_norm):
            candidates.append((e, 2, "partial_symbol"))
        else:
            ext_tokens = _tokens_for_match(eid) | _tokens_for_match(disp) | _tokens_for_match(symbol)
            overlap = len(design_tokens & ext_tokens)
            if overlap > 0:
                candidates.append((e, 1, overlap))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (-x[1], -(x[2] if isinstance(x[2], int) else 0)))
    return candidates[0][0]


def _extracted_by_exact(extracted_entities: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    by_exact: Dict[str, Dict[str, Any]] = {}
    for e in extracted_entities:
        name = (entity_display_name(e) or "").strip().lower()
        if name:
            by_exact[name] = e
        eid = (e.get("id") or "").strip()
        if eid and eid != PROJECT_ROOT_ID:
            by_exact[eid] = e
    return by_exact


def _extraction_with_design_id_hints(
    design_blueprint: Dict[str, Any],
    extracted_blueprint: Dict[str, Any],
) -> Dict[str, Any]:
    """Add design_id to each extracted entity when it matches a design entity, so the agent can use design naming."""
    design_entities = {e.get("id"): e for e in (design_blueprint.get("entities") or []) if e.get("id")}
    extracted_list = [e for e in (extracted_blueprint.get("entities") or []) if (e.get("id") or "") != PROJECT_ROOT_ID]
    extracted_by_exact = _extracted_by_exact(extracted_list)
    extracted_to_design: Dict[str, str] = {}
    for eid, design_ent in design_entities.items():
        if eid == PROJECT_ROOT_ID:
            continue
        ext = _find_best_extracted_match(eid, design_ent, extracted_list, extracted_by_exact)
        if ext:
            ext_id = (ext.get("id") or "").strip()
            if ext_id and ext_id not in extracted_to_design:
                extracted_to_design[ext_id] = eid
    new_entities = [dict(e) for e in (extracted_blueprint.get("entities") or [])]
    for ent in new_entities:
        eid = (ent.get("id") or "").strip()
        if eid in extracted_to_design:
            ent["design_id"] = extracted_to_design[eid]
    return {**extracted_blueprint, "entities": new_entities}


def merge_design_and_extraction(
    design_blueprint: Dict[str, Any],
    extracted_blueprint: Dict[str, Any],
) -> Dict[str, Any]:
    """Match design entity ids to extracted entities; output root and matched entities with fields from extraction. Used by tests."""
    design_entities = {e.get("id"): e for e in (design_blueprint.get("entities") or []) if e.get("id")}
    extracted_list = [e for e in (extracted_blueprint.get("entities") or []) if (e.get("id") or "") != PROJECT_ROOT_ID]
    extracted_by_exact = _extracted_by_exact(extracted_list)
    root_id = design_blueprint.get("root_id") or extracted_blueprint.get("root_id") or PROJECT_ROOT_ID
    used_extracted: set = set()

    def pick_extracted(eid: str, design_ent: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ext = _find_best_extracted_match(eid, design_ent, extracted_list, extracted_by_exact)
        if ext and id(ext) not in used_extracted:
            used_extracted.add(id(ext))
            return ext
        if eid != PROJECT_ROOT_ID:
            design_name = entity_display_name(design_ent) or design_ent.get("name") or eid
            logger.warning(
                "Fuzzy match failed for design entity %s (%s): no extracted match",
                eid, design_name,
            )
        return None

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
            continue
        ext = pick_extracted(eid, design_ent)
        if ext is None:
            continue
        base = dict(empty_entity(eid))
        base["id"] = eid
        base["children"] = list(design_ent.get("children") or [])
        base["dependencies"] = list(design_ent.get("dependencies") or [])
        base["outgoing_contracts"] = list(design_ent.get("outgoing_contracts") or [])
        for key in ("narrative", "blueprint", "protocol", "profile", "governance", "symbol", "traits", "topology_actual", "preview"):
            base[key] = design_ent.get(key, base[key])
        mech = _fields_from_extracted(ext)
        base["symbol"] = mech["symbol"]
        base["protocol"] = mech["protocol"]
        base["profile"] = mech["profile"]
        deps = mech["dependencies"]
        design_ids = set(design_entities)
        mapped = []
        for d in deps:
            if d in design_ids:
                mapped.append(d)
            else:
                head = (d.split(".")[0] if isinstance(d, str) else "").strip()
                if head in design_ids and head not in mapped:
                    mapped.append(head)
        base["dependencies"] = mapped
        base["traits"] = mech["traits"]
        base["topology_actual"] = mech["topology_actual"]
        base["preview"] = mech["preview"]
        entities.append(base)

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

    # Aggregate profile.language from children for every entity that has children (root and parents).
    # Language is a list so a system can have multiple languages (e.g. frontend JS, backend Python).
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

    # Normalize every entity's profile.language to list (string or list accepted).
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
    """
    Produce blueprint_code: agent reads extraction outline + actual code + design (guide only).
    Result is based on actual code; entities not present in code must not appear in blueprint_code.
    Extraction is augmented with design_id per entity when matched so top-down and bottom-up use the same names.
    """
    from manifest.opencode.code_blueprint_enricher import enrich_code_blueprint

    extraction_with_hints = _extraction_with_design_id_hints(design_blueprint, extracted_blueprint)
    result = enrich_code_blueprint(
        design_blueprint, extraction_with_hints, project_root, manifest_dir
    )
    for e in result.get("entities") or []:
        prof = dict(e.get("profile") or {})
        prof["language"] = language_to_list((e.get("profile") or {}).get("language"))
        e["profile"] = prof
    return result
