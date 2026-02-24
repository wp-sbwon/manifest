"""
Layer-by-layer blueprint writer: build context for each layer, invoke OpenCode to produce children.

Per doc-creation-context-plan.md: each layer receives parent entity, PRD excerpt,
path from root, and sibling IDs. OpenCode produces that layer's children.
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
from manifest.io.json_io import read_json_or_default

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
    Build the context dict for a layer-writer task.

    Loads blueprint and PRD, finds parent entity, path from root, sibling IDs.
    Returns dict: layer_index, max_depth, parent_entity, prd_excerpt, blueprint_excerpt.
    """
    manifest_dir = Path(manifest_dir)
    blueprint = load_blueprint(manifest_dir)
    prd_path = manifest_dir / "prd.json"
    prd_excerpt = read_json_or_default(prd_path, {"title": "", "sections": []})

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
        "prd_excerpt": {"title": prd_excerpt.get("title", ""), "sections": list(prd_excerpt.get("sections") or [])},
        "blueprint_excerpt": {
            "path_from_root": path_from_root,
            "parent_id": parent_entity_id,
            "sibling_ids": sibling_ids,
            "root_id": root_id,
        },
    }


def write_blueprint_layer(
    context: Dict[str, Any],
    project_root: Path,
    manifest_dir: Path,
) -> Dict[str, Any]:
    """
    Invoke OpenCode to produce children for the parent entity.

    Returns dict with keys: children (list of entity dicts), or empty children if
    OpenCode returns none / stub mode. Raises if OpenCode fails and stub mode is off.
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
            "Layer writing requires opencode with write-blueprint-layer support. "
            "Set MANIFEST_LAYER_WRITER_STUB=1 to run pipeline without OpenCode."
        )

    with tempfile.TemporaryDirectory(prefix="manifest_layer_") as tmp:
        context_path = Path(tmp) / "context.json"
        output_path = Path(tmp) / "children.json"
        with open(context_path, "w", encoding="utf-8") as f:
            json.dump(context, f, indent=2, ensure_ascii=False)

        env = os.environ.copy()
        env["MANIFEST_LAYER_CONTEXT"] = str(context_path)
        env["MANIFEST_LAYER_OUTPUT"] = str(output_path)
        cmd = [
            opencode_path,
            str(project_root),
            "write-blueprint-layer",
            "--context", str(context_path),
            "--output", str(output_path),
        ]

        timeout = int(os.environ.get("MANIFEST_LAYER_TIMEOUT", "120"))
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(project_root),
                env=env,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"opencode write-blueprint-layer timed out after {timeout}s. "
                "Set MANIFEST_LAYER_TIMEOUT for larger projects."
            )
        except FileNotFoundError:
            raise RuntimeError("opencode not found on PATH")

        if result.returncode != 0:
            stderr = ((result.stdout or "") + (result.stderr or "")).strip()
            excerpt = stderr[:400].replace("\n", " ") if stderr else ""
            raise RuntimeError(
                f"opencode write-blueprint-layer failed (exit {result.returncode}). "
                f"Output: {excerpt}. "
                "OpenCode may not support write-blueprint-layer yet. Set MANIFEST_LAYER_WRITER_STUB=1 to skip."
            )

        if not output_path.exists():
            return {"children": []}

        try:
            with open(output_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"opencode wrote invalid JSON: {e}")

        children = raw.get("children") if isinstance(raw, dict) else []
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
    spawn_script: Optional[Path] = None,
) -> List[Tuple[str, int]]:
    """
    After a layer completes, spawn tasks for each child.

    For each child entity, spawns run_doc_layer_writer.py. Limits concurrent
    processes via max_concurrency (env MANIFEST_LAYER_MAX_CONCURRENCY).
    Returns list of (child_id, next_layer_index) for spawned tasks.
    """
    manifest_dir = Path(manifest_dir)
    project_root = Path(project_root)
    next_layer = layer_index + 1
    if max_depth is not None and next_layer > max_depth:
        logger.info("Layer writer: max_depth=%s reached, not spawning layer %d", max_depth, next_layer)
        return []

    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    script = spawn_script or (repo_root / "scripts" / "run_doc_layer_writer.py")
    if not script.exists():
        logger.warning("run_doc_layer_writer.py not found; skipping spawn")
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


def run_layer_0(manifest_dir: Path, project_root: Path) -> bool:
    """
    Run the layer-0 writer (root's direct children). Merges result and spawns layer 1.

    Returns True if successful. Requires blueprint with root and optionally prd.json.
    """
    manifest_dir = Path(manifest_dir)
    project_root = Path(project_root)
    blueprint = load_blueprint(manifest_dir)
    root = next(
        (e for e in (blueprint.get("entities") or []) if (e.get("id") or "") == PROJECT_ROOT_ID),
        None,
    )
    if not root:
        raise ValueError("Blueprint has no PROJECT_ROOT entity")

    ctx = build_layer_writer_context(manifest_dir, PROJECT_ROOT_ID, 0)
    result = write_blueprint_layer(ctx, project_root, manifest_dir)
    children = result.get("children") or []

    if not children:
        return True

    if not merge_children_into_blueprint(manifest_dir, PROJECT_ROOT_ID, children):
        return False

    try_spawn_next_layer(manifest_dir, project_root, PROJECT_ROOT_ID, 0, children)
    return True
