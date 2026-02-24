"""
Build blueprint_code from design structure and code extraction; enrich intent via opencode.
Output has same schema and entity ids as design.
"""
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

from manifest.audit.entity_schema import (
    PROJECT_ROOT_ID,
    empty_intent,
    empty_reality,
    entity_display_name,
)
from manifest.audit.entity_validation import normalize_for_schema
from manifest.core.logger import get_logger

logger = get_logger(__name__)


def _reality_from_entity(ent: Dict[str, Any]) -> Dict[str, Any]:
    r = ent.get("reality") or {}
    return {
        "symbol": r.get("symbol") or "",
        "protocol": r.get("protocol") or {"input": [], "output": []},
        "profile": r.get("profile") or {"language": "", "platform": "", "io_model": "", "state_model": ""},
        "dependencies": list(r.get("dependencies") or []),
        "traits": list(r.get("traits") or []),
        "topology_actual": r.get("topology_actual") or {"type": "", "map": []},
        "preview": r.get("preview") or "",
    }


def _normalize_for_match(s: str) -> str:
    """Lowercase, collapse separators and spaces for fuzzy matching."""
    if not s:
        return ""
    out = re.sub(r"[\s_\-\.]+", "", (s or "").lower())
    return out


def _module_path_from_extracted_id(eid: str) -> str:
    """Extract module path from ids like comp-src.manifest.cli.parser-ParseArgs."""
    if not eid or not eid.startswith("comp-"):
        return ""
    rest = eid[5:]
    idx = rest.rfind("-")
    if idx <= 0:
        return rest.replace("-", ".")
    return rest[:idx].replace("-", ".")


def _tokens_for_match(s: str) -> set:
    """Tokenize: split on non-alnum, camelCase, lowercase."""
    if not s:
        return set()
    normalized = _normalize_for_match(s)
    parts = re.split(r"(?=[A-Z])|[\s_\-\.]+", s)
    tokens = set()
    for p in parts:
        if p:
            tokens.add(_normalize_for_match(p))
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
    """
    Find best extracted entity for a design entity using multiple heuristics.
    Order: exact id/name, module path suffix, normalized partial, token overlap.
    """
    name = (entity_display_name(design_ent) or "").strip().lower()
    ext = extracted_by_exact.get(design_id) or extracted_by_exact.get(name)
    if ext:
        return ext

    design_norm = _normalize_for_match(design_id)
    design_tokens = _tokens_for_match(design_id) | _tokens_for_match(name)
    role = ((design_ent.get("intent") or {}).get("narrative") or {}).get("role") or ""
    design_tokens |= _tokens_for_match(role)
    design_path_seg = _design_id_as_path_segment(design_id)

    candidates: List[tuple] = []
    for e in extracted_list:
        eid = (e.get("id") or "").strip()
        disp = (entity_display_name(e) or "").strip()
        mod_path = _module_path_from_extracted_id(eid)
        symbol = (e.get("reality") or {}).get("symbol") or ""

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


def merge_design_and_extraction(
    design_blueprint: Dict[str, Any],
    extracted_blueprint: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build code blueprint with same root_id and entity ids/children as design;
    reality from extraction. Match by exact id/name, then module path suffix,
    normalized partial name, and token overlap.
    """
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
        return None

    entities: List[Dict[str, Any]] = []
    for eid, design_ent in design_entities.items():
        ext = pick_extracted(eid, design_ent) if eid != PROJECT_ROOT_ID else None
        if eid == PROJECT_ROOT_ID:
            reality = empty_reality()
            intent = design_ent.get("intent") or empty_intent()
        else:
            intent = empty_intent()
            if ext:
                reality = _reality_from_entity(ext)
                reality["dependencies"] = list(ext.get("dependencies") or (ext.get("reality") or {}).get("dependencies") or [])
            else:
                reality = empty_reality()

        entities.append({
            "id": eid,
            "children": list(design_ent.get("children") or []),
            "dependencies": list(design_ent.get("dependencies") or []),
            "intent": intent,
            "reality": reality,
            "outgoing_contracts": list(design_ent.get("outgoing_contracts") or []),
        })

    root_first = [e for e in entities if (e.get("id") or "") == PROJECT_ROOT_ID]
    rest = [e for e in entities if (e.get("id") or "") != PROJECT_ROOT_ID]
    ordered = (root_first or []) + rest
    if not root_first and ordered:
        root_entity = {
            "id": PROJECT_ROOT_ID,
            "children": [e["id"] for e in rest],
            "dependencies": [],
            "intent": empty_intent(),
            "reality": empty_reality(),
            "outgoing_contracts": [],
        }
        ordered = [root_entity] + rest

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
    Produce blueprint_code: same schema and ids as design; reality from extraction; intent from opencode.
    """
    from manifest.opencode.code_blueprint_enricher import enrich_code_blueprint

    code_draft = merge_design_and_extraction(design_blueprint, extracted_blueprint)
    return enrich_code_blueprint(design_blueprint, code_draft, project_root, manifest_dir)
