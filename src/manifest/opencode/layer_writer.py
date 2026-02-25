"""
Layer-by-layer blueprint writer: build context per layer; opencode produces children.

Per doc-creation-context-plan.md: each layer gets parent entity, PRD excerpt,
path from root, and sibling IDs.
"""
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_entity
from manifest.audit.entity_validation import normalize_for_schema, validate_blueprint_data
from manifest.core.logger import get_logger
from manifest.io.blueprint_io import load_blueprint
from manifest.io.prd_io import load_prd
from manifest.opencode.run_helpers import (
    extract_json_from_text,
    parse_opencode_stdout,
)

logger = get_logger(__name__)


def _path_from_root(blueprint: Dict[str, Any], entity_id: str) -> List[str]:
    """Compute path from root to entity. Returns [root_id, ...] or [] if not found."""
    entities_by_id = {e.get("id"): e for e in (blueprint.get("entities") or []) if e.get("id")}
    if entity_id not in entities_by_id:
        return []

    def _find_path(eid: str, visited: set) -> Optional[List[str]]:
        if eid in visited:
            return None
        visited.add(eid)
        if eid == PROJECT_ROOT_ID:
            return [eid]
        for parent_id, ent in entities_by_id.items():
            children = ent.get("children") or []
            if eid in children:
                sub = _find_path(parent_id, visited)
                if sub is not None:
                    return sub + [eid]
        return None

    out = _find_path(entity_id, set())
    return out if out else []


def _sibling_ids(blueprint: Dict[str, Any], entity_id: str) -> List[str]:
    """Return sibling entity IDs (parent's other children)."""
    entities_by_id = {e.get("id"): e for e in (blueprint.get("entities") or []) if e.get("id")}
    for parent_id, ent in entities_by_id.items():
        children = ent.get("children") or []
        if entity_id in children:
            return [c for c in children if c != entity_id]
    return []


def build_layer_writer_context(
    manifest_dir: Path,
    parent_entity_id: str,
    layer_index: int,
    *,
    max_depth: Optional[int] = None,
    max_context_tokens: int = 12000,
) -> Dict[str, Any]:
    """
    Build context dict: blueprint, PRD, parent entity, path from root, sibling IDs.
    Returns dict with layer_index, max_depth, parent_entity, prd_excerpt, blueprint_excerpt.
    """
    manifest_dir = Path(manifest_dir)
    blueprint = load_blueprint(manifest_dir)
    prd_excerpt = load_prd(manifest_dir)

    entities = blueprint.get("entities") or []
    parent = next((e for e in entities if (e.get("id") or "") == parent_entity_id), None)
    if not parent:
        raise ValueError(f"Parent entity '{parent_entity_id}' not found in blueprint")

    path_from_root = _path_from_root(blueprint, parent_entity_id)
    sibling_ids = _sibling_ids(blueprint, parent_entity_id)
    root_id = blueprint.get("root_id") or PROJECT_ROOT_ID

    return {
        "layer_index": layer_index,
        "max_depth": max_depth if max_depth is not None else 10,
        "parent_entity": parent,
        "prd_excerpt": {
            "title": prd_excerpt.get("title", ""),
            "mission": prd_excerpt.get("mission", ""),
            "sections": list(prd_excerpt.get("sections") or []),
        },
        "blueprint_excerpt": {
            "path_from_root": path_from_root,
            "parent_id": parent_entity_id,
            "sibling_ids": sibling_ids,
            "root_id": root_id,
        },
    }


LAYER_WRITER_PROMPT = (
    "Read the blueprint layer context from the attached file context.json. "
    "Produce a JSON object with a 'children' array of entity objects (id, narrative, profile, children, etc.). "
    "Return empty children [] when no further breakdown is needed. "
    "Output ONLY valid JSON, no markdown or explanation."
)


def write_blueprint_layer(
    context: Dict[str, Any],
    project_root: Path,
    manifest_dir: Path,
) -> Dict[str, Any]:
    """
    Produce children for the parent entity via opencode.

    Returns dict with 'children' (list of entity dicts); empty if stub mode or no output.
    Raises if opencode fails and stub is off.
    """
    project_root = Path(project_root)
    manifest_dir = Path(manifest_dir)

    if os.environ.get("MANIFEST_LAYER_WRITER_STUB") == "1":
        logger.info("Layer writer stub mode: returning empty children")
        return {"children": []}

    opencode_path = shutil.which("opencode")
    if not opencode_path:
        raise RuntimeError(
            "opencode not on PATH. "
            "Layer writing requires opencode. "
            "Set MANIFEST_LAYER_WRITER_STUB=1 to run pipeline without OpenCode."
        )

    with tempfile.TemporaryDirectory(prefix="manifest_layer_") as tmp:
        context_path = Path(tmp) / "context.json"
        with open(context_path, "w", encoding="utf-8") as f:
            json.dump(context, f, indent=2, ensure_ascii=False)

        cmd = [
            opencode_path,
            "run",
            LAYER_WRITER_PROMPT,
            "--agent", "layer-writer",
            "--dir", str(project_root.resolve()),
            "--format", "json",
            "-f", str(context_path.resolve()),
        ]

        timeout = int(os.environ.get("MANIFEST_LAYER_TIMEOUT", "120"))
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(project_root),
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"Layer writer timed out after {timeout}s. "
                "Set MANIFEST_LAYER_TIMEOUT for larger projects."
            )
        except FileNotFoundError:
            raise RuntimeError("opencode not found on PATH")

        if result.returncode != 0:
            stderr = ((result.stdout or "") + (result.stderr or "")).strip()
            excerpt = stderr[:400].replace("\n", " ") if stderr else ""
            raise RuntimeError(
                f"Layer writer failed (exit {result.returncode}). "
                f"Output: {excerpt}. "
                "Set MANIFEST_LAYER_WRITER_STUB=1 to skip."
            )

        merged = parse_opencode_stdout(result.stdout or "")
        if not merged:
            return {"children": []}

        try:
            data = extract_json_from_text(merged)
        except (json.JSONDecodeError, KeyError):
            return {"children": []}

        children = data.get("children") if isinstance(data, dict) else []
        if not isinstance(children, list):
            children = []

        normalized_children: List[Dict[str, Any]] = []
        for c in children:
            if isinstance(c, dict) and "id" in c:
                normalized_children.append({**empty_entity(c.get("id", "")), **c})
            elif isinstance(c, dict):
                normalized_children.append(dict(c))

        return {"children": normalized_children}


def merge_children_into_blueprint(
    manifest_dir: Path,
    parent_entity_id: str,
    children: List[Dict[str, Any]],
) -> bool:
    """
    Merge new children into blueprint_design.json: update parent's children list
    and append child entities. Returns True on success.
    """
    from manifest.io.blueprint_io import save_blueprint

    manifest_dir = Path(manifest_dir)
    blueprint = load_blueprint(manifest_dir)
    entities = list(blueprint.get("entities") or [])
    by_id = {e.get("id"): e for e in entities if e.get("id")}

    child_ids = []
    for c in children:
        if not isinstance(c, dict):
            continue
        eid = (c.get("id") or "").strip()
        if not eid or eid == PROJECT_ROOT_ID:
            continue
        child_ids.append(eid)
        if eid not in by_id:
            entities.append(normalize_for_schema(dict(c)))
            by_id[eid] = entities[-1]

    if not child_ids:
        return True

    parent = by_id.get(parent_entity_id)
    if not parent:
        return False

    existing = set(parent.get("children") or [])
    for cid in child_ids:
        existing.add(cid)
    parent["children"] = sorted(existing)

    data = {**blueprint, "entities": entities}
    valid, _ = validate_blueprint_data(normalize_for_schema(data))
    if not valid:
        return False
    return save_blueprint(manifest_dir, data)


DEFAULT_MAX_CONCURRENCY = 4


def try_spawn_next_layer(
    manifest_dir: Path,
    project_root: Path,
    parent_entity_id: str,
    layer_index: int,
    children: List[Dict[str, Any]],
    *,
    max_depth: Optional[int] = None,
    max_concurrency: Optional[int] = None,
) -> List[Tuple[str, int]]:
    """
    After a layer completes, spawn the layer-writer process for each child.

    Limits concurrent processes via max_concurrency (env MANIFEST_LAYER_MAX_CONCURRENCY).
    Returns list of (child_id, next_layer_index) for spawned tasks.
    """
    manifest_dir = Path(manifest_dir)
    project_root = Path(project_root)
    next_layer = layer_index + 1
    if max_depth is not None and next_layer > max_depth:
        logger.info("Layer writer: max_depth=%s reached, not spawning layer %d", max_depth, next_layer)
        return []

    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    script = repo_root / "bin" / "run_doc_layer_writer.py"
    if not script.exists():
        logger.warning("bin/run_doc_layer_writer.py not found; skipping spawn")
        return []

    limit = max_concurrency
    if limit is None:
        limit = int(os.environ.get("MANIFEST_LAYER_MAX_CONCURRENCY", str(DEFAULT_MAX_CONCURRENCY)))
    limit = max(1, limit)

    child_ids: List[str] = []
    for c in children:
        if not isinstance(c, dict):
            continue
        cid = (c.get("id") or "").strip()
        if cid and cid != PROJECT_ROOT_ID:
            child_ids.append(cid)

    spawned: List[Tuple[str, int]] = []
    procs: List[subprocess.Popen] = []
    for i, cid in enumerate(child_ids):
        if len(procs) >= limit:
            for p in procs:
                try:
                    p.wait(timeout=300)
                except subprocess.TimeoutExpired:
                    logger.warning("Layer writer process timed out (300s), continuing")
            procs = []
        try:
            env = os.environ.copy()
            env["PYTHONPATH"] = str(repo_root / "src")
            proc = subprocess.Popen(
                ["python", str(script), "--manifest-dir", str(manifest_dir), "--parent", cid, "--layer", str(next_layer)],
                cwd=str(project_root),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            procs.append(proc)
            spawned.append((cid, next_layer))
        except Exception as e:
            logger.warning("Spawn layer writer for %s failed: %s", cid, e)
    for p in procs:
        try:
            p.wait(timeout=1)
        except subprocess.TimeoutExpired:
            pass
    return spawned
