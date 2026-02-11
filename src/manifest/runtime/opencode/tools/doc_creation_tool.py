"""
Doc creation tool: hierarchical blueprint from PRD.

Supports the flow: PRD first (via architect write_prd), then blueprint built
layer-by-layer. One agent writes layer 0 (root + top-level); for each entity
at that layer we spawn a layer writer that produces that entity's children;
merge fragments into blueprint_design.json. See docs/doc-creation-process.md.

Layer writers run as subprocesses (parallel within a layer); layer n+1 is
spawned only after all layer-n tasks in the same batch are completed.
"""
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from manifest.audit.entity_schema import (
    PROJECT_ROOT_ID,
    empty_entity,
    empty_blueprint_root,
    empty_intent,
    empty_reality,
    empty_outgoing_contracts,
)
from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
from manifest.core.logger import get_logger

# Optional cap for layer depth (can be passed in context; not enforced here)
DEFAULT_MAX_DEPTH = 10

logger = get_logger(__name__)

DOC_LAYER_WRITER_LOG = "doc_layer_writer_tasks.json"


def _default_layer_tasks() -> Dict[str, Any]:
    return {"tasks": [], "batches": {}, "version": "1.0"}


def _load_layer_tasks(path: Path) -> Dict[str, Any]:
    data = _default_layer_tasks()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
    data.setdefault("tasks", [])
    data.setdefault("batches", {})
    return data


def _save_layer_tasks(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _ensure_batch(
    data: Dict[str, Any],
    batch_id: str,
    layer_index: int,
    task_ids: List[str],
) -> None:
    data.setdefault("batches", {})
    data["batches"][batch_id] = {
        "layer_index": layer_index,
        "task_ids": list(task_ids),
        "next_layer_spawned": False,
    }


def merge_blueprint_fragment(
    blueprint: Dict[str, Any],
    parent_entity_id: str,
    child_entities: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Merge a list of child entities under parent. Returns new blueprint dict (does not save)."""
    entities = list(blueprint.get("entities") or [])
    id_to_idx: Dict[str, int] = {e.get("id") or "": i for i, e in enumerate(entities)}
    new_ids: List[str] = []
    for child in child_entities or []:
        cid = (child.get("id") or "").strip()
        if not cid:
            continue
        if cid not in id_to_idx:
            entities.append(child)
            id_to_idx[cid] = len(entities) - 1
        new_ids.append(cid)
    for i, e in enumerate(entities):
        if (e.get("id") or "") == parent_entity_id:
            existing = list(e.get("children") or [])
            merged = list(dict.fromkeys(existing + new_ids))
            entities[i] = {**e, "children": merged}
            break
    return {**blueprint, "entities": entities}


def build_layer_writer_context(
    manifest_dir: Path,
    parent_entity_id: str,
    layer_index: int,
    max_depth: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Build context for a single layer-writer task: full PRD + scoped blueprint only.

    Each sub-worker receives full PRD and scoped blueprint (path_from_root,
    parent_entity, sibling_ids, root_id, optional sibling_summaries). No full
    blueprint or full entities list is included.
    """
    manifest_dir = Path(manifest_dir)
    context: Dict[str, Any] = {
        "layer_index": layer_index,
        "max_depth": max_depth if max_depth is not None else DEFAULT_MAX_DEPTH,
    }

    # Full PRD
    prd_path = manifest_dir / "prd.json"
    prd: Dict[str, Any] = {}
    if prd_path.exists():
        try:
            with open(prd_path, "r", encoding="utf-8") as f:
                prd = json.load(f)
        except Exception as e:
            logger.debug("build_layer_writer_context: could not load PRD: %s", e)
    context["prd"] = prd

    # Blueprint: load only to compute scoped structure
    blueprint = BlueprintLoader.load_blueprint(manifest_dir)
    entities = list(blueprint.get("entities") or []) if blueprint else []
    id_to_entity: Dict[str, Dict[str, Any]] = {e.get("id") or "": e for e in entities if e.get("id")}
    root_id = (blueprint.get("root_id") or PROJECT_ROOT_ID) if blueprint else PROJECT_ROOT_ID

    # Parent map: child_id -> parent_id
    parent_of: Dict[str, str] = {}
    for e in entities:
        eid = e.get("id")
        if not eid:
            continue
        for cid in e.get("children") or []:
            parent_of[cid] = eid

    parent_entity = id_to_entity.get(parent_entity_id)
    if parent_entity is not None:
        context["parent_entity"] = parent_entity
    else:
        context["parent_entity"] = {}

    # Path from root to parent_entity_id (inclusive)
    path_from_root: List[str] = []
    cur = parent_entity_id
    while cur:
        path_from_root.append(cur)
        if cur == root_id:
            break
        cur = parent_of.get(cur)
    path_from_root.reverse()
    if path_from_root and path_from_root[0] != root_id:
        path_from_root.insert(0, root_id)

    # Sibling ids (same parent's children, excluding self)
    parent_id = parent_of.get(parent_entity_id)
    sibling_ids: List[str] = []
    if parent_id and parent_id in id_to_entity:
        sibling_ids = [
            cid for cid in (id_to_entity[parent_id].get("children") or [])
            if cid != parent_entity_id
        ]
    elif parent_entity_id == root_id:
        sibling_ids = []

    # Optional sibling summaries (id + role/mission)
    sibling_summaries: List[Dict[str, Any]] = []
    for sid in sibling_ids:
        ent = id_to_entity.get(sid)
        if not ent:
            sibling_summaries.append({"id": sid, "role": "", "mission": ""})
            continue
        intent = ent.get("intent") or {}
        narrative = intent.get("narrative") or {}
        if isinstance(narrative, dict):
            sibling_summaries.append({
                "id": sid,
                "role": narrative.get("role", ""),
                "mission": narrative.get("mission", ""),
            })
        else:
            sibling_summaries.append({"id": sid, "role": "", "mission": ""})

    context["blueprint_scope"] = {
        "path_from_root": path_from_root,
        "parent_id": parent_entity_id,
        "sibling_ids": sibling_ids,
        "root_id": root_id,
        "sibling_summaries": sibling_summaries,
    }
    return context


def start_blueprint_from_prd(manifest_dir: Path) -> Dict[str, Any]:
    """
    Load PRD and return a minimal blueprint (root only) plus metadata for layer-0.
    Layer-0 writer (separate agent/LLM) should produce root + top-level entities;
    then call spawn_layer_writer for each top-level entity.
    """
    manifest_dir = Path(manifest_dir)
    prd_path = manifest_dir / "prd.json"
    prd: Dict[str, Any] = {}
    if prd_path.exists():
        try:
            with open(prd_path, "r", encoding="utf-8") as f:
                prd = json.load(f)
        except Exception as e:
            logger.debug("start_blueprint_from_prd: could not load PRD: %s", e)
    root = dict(empty_blueprint_root())
    root["root_id"] = PROJECT_ROOT_ID
    root["entities"] = [empty_entity(PROJECT_ROOT_ID)]
    return {
        "ok": True,
        "blueprint": root,
        "prd_loaded": bool(prd),
        "next_spawns": [],
        "message": "Minimal blueprint (root only). Run layer-0 writer to add top-level entities, then spawn_layer_writer per entity.",
    }


def write_blueprint_layer(
    manifest_dir: Path,
    parent_entity_id: str,
    prd_excerpt: Optional[Dict[str, Any]] = None,
    current_blueprint: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Placeholder for layer writer output. In production, an LLM or agent uses
    parent_entity_id + prd_excerpt + current_blueprint to produce direct children.
    Returns { "ok": True, "children": [] }. Caller (layer writer agent) should
    replace "children" with actual entity dicts and call merge_blueprint_fragment.
    """
    manifest_dir = Path(manifest_dir)
    if current_blueprint is None:
        current_blueprint = BlueprintLoader.load_blueprint(manifest_dir)
    return {"ok": True, "children": []}


def spawn_layer_writer(
    manifest_dir: Path,
    parent_entity_id: str,
    context: Optional[Dict[str, Any]] = None,
    depth: Optional[int] = None,
    batch_id: Optional[str] = None,
    layer_index: Optional[int] = None,
    start_process: bool = False,
) -> Dict[str, Any]:
    """Record a doc-layer-writer task. Returns { ok, task_id, batch_id }. Optionally register batch and start subprocess."""
    manifest_dir = Path(manifest_dir)
    path = manifest_dir / DOC_LAYER_WRITER_LOG
    data = _load_layer_tasks(path)
    task_id = f"lw-{uuid.uuid4().hex[:12]}"
    task = {
        "task_id": task_id,
        "parent_entity_id": parent_entity_id,
        "context": context or {},
        "depth": depth if depth is not None else 0,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "status": "pending",
    }
    if batch_id is not None:
        task["batch_id"] = batch_id
    if layer_index is not None:
        task["layer_index"] = layer_index
    data["tasks"].append(task)
    if batch_id is not None and layer_index is not None:
        batch = data["batches"].get(batch_id)
        if batch is not None:
            batch.setdefault("task_ids", []).append(task_id)
        else:
            _ensure_batch(data, batch_id, layer_index, [task_id])
    _save_layer_tasks(path, data)
    if start_process:
        start_layer_writer_process(manifest_dir, task_id)
    logger.info("Doc layer writer task: parent=%s task_id=%s batch_id=%s", parent_entity_id, task_id, batch_id)
    return {"ok": True, "task_id": task_id, "batch_id": batch_id}


def start_layer_writer_process(manifest_dir: Path, task_id: str) -> Dict[str, Any]:
    """Start the layer-writer runner as a subprocess; return immediately (non-blocking)."""
    manifest_dir = Path(manifest_dir)
    repo_root = manifest_dir.resolve().parent
    script = repo_root / "scripts" / "run_doc_layer_writer.py"
    if not script.exists():
        return {"ok": False, "error": f"Runner script not found: {script}"}
    env = os.environ.copy()
    if "PYTHONPATH" not in env and (repo_root / "src").exists():
        env["PYTHONPATH"] = str(repo_root / "src")
    try:
        proc = subprocess.Popen(
            [sys.executable, str(script), "--manifest-dir", str(manifest_dir), "--task-id", task_id],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(repo_root),
            env=env,
        )
        return {"ok": True, "pid": proc.pid, "task_id": task_id}
    except Exception as e:
        logger.exception("start_layer_writer_process failed")
        return {"ok": False, "error": str(e)}


def _entities_at_layer(blueprint: Dict[str, Any], root_id: str, layer_index: int) -> List[Dict[str, Any]]:
    """Return entities at layer_index (0 = root only, 1 = root's children, etc.)."""
    entities = {e.get("id"): e for e in (blueprint.get("entities") or []) if e.get("id")}
    if layer_index == 0:
        root = entities.get(root_id)
        return [root] if root else []
    current = [entities.get(root_id)] if root_id in entities else []
    for _ in range(layer_index):
        next_layer = []
        for e in current:
            if not e:
                continue
            for cid in e.get("children") or []:
                if cid in entities:
                    next_layer.append(entities[cid])
        current = next_layer
    return current


def try_spawn_next_layer(manifest_dir: Path, batch_id: str) -> Dict[str, Any]:
    """
    If all tasks in batch are completed and next_layer_spawned is False,
    spawn one layer-writer task per entity at the next layer and start subprocesses.
    """
    path = Path(manifest_dir) / DOC_LAYER_WRITER_LOG
    data = _load_layer_tasks(path)
    batches = data.get("batches") or {}
    batch = batches.get(batch_id)
    if not batch or batch.get("next_layer_spawned"):
        return {"ok": True, "spawned": False, "reason": "batch_done_or_already_spawned"}
    task_ids = batch.get("task_ids") or []
    tasks = {t["task_id"]: t for t in data.get("tasks") or [] if t.get("task_id")}
    if not all((tasks.get(tid) or {}).get("status") == "completed" for tid in task_ids):
        return {"ok": True, "spawned": False, "reason": "batch_not_all_completed"}
    layer_index = batch.get("layer_index", 0) + 1
    design = BlueprintLoader.load_blueprint(manifest_dir)
    if not design or not design.get("entities"):
        batch["next_layer_spawned"] = True
        _save_layer_tasks(path, data)
        return {"ok": True, "spawned": False, "reason": "no_blueprint"}
    root_id = design.get("root_id") or PROJECT_ROOT_ID
    parent_ids = [t.get("parent_entity_id") for tid in task_ids for t in [tasks.get(tid)] if t and t.get("parent_entity_id")]
    id_to_entity = {e.get("id"): e for e in design.get("entities") or []}
    next_entity_ids = []
    for pid in parent_ids:
        ent = id_to_entity.get(pid)
        if not ent:
            continue
        for cid in ent.get("children") or []:
            if cid in id_to_entity and cid not in next_entity_ids:
                next_entity_ids.append(cid)
    if not next_entity_ids:
        batch["next_layer_spawned"] = True
        _save_layer_tasks(path, data)
        return {"ok": True, "spawned": False, "reason": "no_children"}
    new_batch_id = f"batch-{uuid.uuid4().hex[:12]}"
    _ensure_batch(data, new_batch_id, layer_index, [])
    for eid in next_entity_ids:
        ctx = build_layer_writer_context(manifest_dir, eid, layer_index)
        out = spawn_layer_writer(
            manifest_dir,
            eid,
            context=ctx,
            depth=layer_index,
            batch_id=new_batch_id,
            layer_index=layer_index,
        )
        if out.get("ok") and out.get("task_id"):
            start_layer_writer_process(manifest_dir, out["task_id"])
    batch["next_layer_spawned"] = True
    _save_layer_tasks(path, data)
    return {"ok": True, "spawned": True, "batch_id": new_batch_id, "task_count": len(next_entity_ids)}


def spawn_layer_writer_batch(
    manifest_dir: Path,
    parent_entity_ids: List[str],
    layer_index: int,
    context_map: Optional[Dict[str, Dict[str, Any]]] = None,
    start_processes: bool = True,
) -> Dict[str, Any]:
    """Create a batch and one task per parent; optionally start a subprocess for each (non-blocking)."""
    manifest_dir = Path(manifest_dir)
    batch_id = f"batch-{uuid.uuid4().hex[:12]}"
    path = manifest_dir / DOC_LAYER_WRITER_LOG
    data = _load_layer_tasks(path)
    _ensure_batch(data, batch_id, layer_index, [])
    task_ids = []
    context_map = context_map or {}
    for pid in parent_entity_ids:
        out = spawn_layer_writer(
            manifest_dir,
            pid,
            context=context_map.get(pid) or {},
            depth=layer_index,
            batch_id=batch_id,
            layer_index=layer_index,
        )
        if out.get("ok") and out.get("task_id"):
            task_ids.append(out["task_id"])
    if not task_ids:
        return {"ok": False, "error": "No tasks created", "batch_id": batch_id}
    if start_processes:
        for tid in task_ids:
            start_layer_writer_process(manifest_dir, tid)
    return {"ok": True, "batch_id": batch_id, "task_ids": task_ids}


def _start_recursive_expansion(manifest_dir: Path) -> Dict[str, Any]:
    """
    Entry point for recursive blueprint expansion. Same model as every other layer:
    ensure root-only blueprint, spawn one task for the root at layer_index=0 with
    build_layer_writer_context; the runner produces children, merges, then
    try_spawn_next_layer spawns layer 1, and so on. No separate layer-0 flow.
    """
    manifest_dir = Path(manifest_dir)
    design = BlueprintLoader.load_blueprint(manifest_dir)
    if not design.get("entities") or not any(e.get("id") == PROJECT_ROOT_ID for e in design.get("entities") or []):
        out = start_blueprint_from_prd(manifest_dir)
        if out.get("blueprint"):
            BlueprintLoader.save_blueprint(manifest_dir, out["blueprint"], backup=True)
    ctx = build_layer_writer_context(manifest_dir, PROJECT_ROOT_ID, 0)
    return spawn_layer_writer_batch(
        manifest_dir,
        [PROJECT_ROOT_ID],
        layer_index=0,
        context_map={PROJECT_ROOT_ID: ctx},
        start_processes=True,
    )


class DocCreationTool:
    """Tool for hierarchical doc creation: PRD → blueprint layer 0 → spawn layer writers → merge."""

    def __init__(self, manifest_dir: Optional[Path] = None):
        self.manifest_dir = (manifest_dir or Path(".manifest")).resolve()

    def run(
        self,
        action: str,
        parent_entity_id: Optional[str] = None,
        child_entities: Optional[List[Dict[str, Any]]] = None,
        prd_excerpt: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        depth: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Run a doc_creation action."""
        action = (action or "").strip().lower()
        if action == "start_blueprint_from_prd":
            out = start_blueprint_from_prd(self.manifest_dir)
            if out.get("blueprint"):
                BlueprintLoader.save_blueprint(self.manifest_dir, out["blueprint"], backup=True)
            return out
        if action == "write_blueprint_layer":
            if not parent_entity_id:
                return {"ok": False, "error": "parent_entity_id required"}
            return write_blueprint_layer(
                self.manifest_dir,
                parent_entity_id,
                prd_excerpt=prd_excerpt,
            )
        if action == "merge_blueprint_fragment":
            if not parent_entity_id or child_entities is None:
                return {"ok": False, "error": "parent_entity_id and child_entities required"}
            blueprint = BlueprintLoader.load_blueprint(self.manifest_dir)
            merged = merge_blueprint_fragment(blueprint, parent_entity_id, child_entities)
            if BlueprintLoader.save_blueprint(self.manifest_dir, merged, backup=True):
                return {"ok": True, "message": "Fragment merged and saved"}
            return {"ok": False, "error": "Failed to save blueprint"}
        if action == "spawn_layer_writer":
            if not parent_entity_id:
                return {"ok": False, "error": "parent_entity_id required"}
            out = spawn_layer_writer(
                self.manifest_dir,
                parent_entity_id,
                context=context,
                depth=depth,
                batch_id=context.get("batch_id") if context else None,
                layer_index=context.get("layer_index") if context else None,
                start_process=bool(context.get("start_process")) if context else False,
            )
            return out if out.get("ok") else {"ok": False, "error": out.get("error", "spawn failed")}
        if action == "spawn_layer_writer_batch":
            parent_ids = []
            if isinstance(context, dict) and context.get("parent_entity_ids"):
                parent_ids = list(context["parent_entity_ids"])
            elif isinstance(child_entities, list) and child_entities:
                if isinstance(child_entities[0], str):
                    parent_ids = child_entities
                else:
                    parent_ids = [e.get("id") for e in child_entities if isinstance(e, dict) and e.get("id")]
            if not parent_ids:
                return {"ok": False, "error": "context.parent_entity_ids or child_entities (list of ids or entity dicts) required"}
            return spawn_layer_writer_batch(
                self.manifest_dir,
                parent_ids,
                depth if depth is not None else 1,
                context_map=context.get("context_map") if isinstance(context, dict) else None,
                start_processes=bool(context.get("start_processes", True)) if isinstance(context, dict) else True,
            )
        if action == "run_layer_0":
            return _start_recursive_expansion(self.manifest_dir)
        return {"ok": False, "error": f"Unknown action: {action}. Valid: start_blueprint_from_prd, write_blueprint_layer, merge_blueprint_fragment, spawn_layer_writer, spawn_layer_writer_batch, run_layer_0"}
