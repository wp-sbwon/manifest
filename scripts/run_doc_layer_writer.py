#!/usr/bin/env python3
"""
Run a single doc layer-writer task: load task, produce children, merge, mark completed,
then try to spawn the next layer if this task is part of a completed batch.

Invoked as a subprocess by doc_creation tool (non-blocking). Usage:
  python scripts/run_doc_layer_writer.py --manifest-dir <path> --task-id <task_id>
"""
import argparse
import json
import sys
from pathlib import Path

# So manifest loggers (StreamHandler(sys.stdout)) write to stderr; we print JSON to real stdout
_stdout_for_json = sys.stdout
sys.stdout = sys.stderr

# Ensure repo src is on path when run as script
_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
from manifest.runtime.opencode.tools.doc_creation_tool import (
    _load_layer_tasks,
    _save_layer_tasks,
    DOC_LAYER_WRITER_LOG,
    merge_blueprint_fragment,
    try_spawn_next_layer,
    write_blueprint_layer,
)


def _produce_children(
    manifest_dir: Path,
    parent_entity_id: str,
    context: dict,
    layer_index: int = 0,
) -> list:
    """
    Produce child entities for the parent. Uses task context (full PRD + scoped
    blueprint when provided). Empty children are allowed (no placeholder).
    Same behavior for all layers: no layer-0-specific logic.
    """
    # Use PRD from context; if missing, try loading from manifest (same for any layer)
    prd = context.get("prd") if isinstance(context, dict) else {}
    if not prd:
        prd_path = manifest_dir / "prd.json"
        if prd_path.exists():
            try:
                with open(prd_path, "r", encoding="utf-8") as f:
                    prd = json.load(f)
            except Exception:
                pass
        if prd and isinstance(context, dict):
            context = dict(context)
            context["prd"] = prd

    blueprint = BlueprintLoader.load_blueprint(manifest_dir)
    out = write_blueprint_layer(manifest_dir, parent_entity_id, prd_excerpt=context, current_blueprint=blueprint)
    children = out.get("children") or []
    return children


def run_task(manifest_dir: Path, task_id: str) -> dict:
    """Load task, produce children, merge, mark completed, try spawn next layer."""
    manifest_dir = Path(manifest_dir)
    path = manifest_dir / DOC_LAYER_WRITER_LOG
    data = _load_layer_tasks(path)
    tasks = data.get("tasks") or []
    task = next((t for t in tasks if t.get("task_id") == task_id), None)
    if not task:
        return {"ok": False, "error": f"Task not found: {task_id}"}
    if task.get("status") == "completed":
        batch_id = task.get("batch_id")
        if batch_id:
            try_spawn_next_layer(manifest_dir, batch_id)
        return {"ok": True, "message": "Already completed", "task_id": task_id}

    parent_entity_id = task.get("parent_entity_id")
    if not parent_entity_id:
        task["status"] = "failed"
        task["error"] = "Missing parent_entity_id"
        _save_layer_tasks(path, data)
        return {"ok": False, "error": "Missing parent_entity_id", "task_id": task_id}

    context = task.get("context") or {}
    layer_index = task.get("layer_index", 0)
    children = _produce_children(manifest_dir, parent_entity_id, context, layer_index=layer_index)
    blueprint = BlueprintLoader.load_blueprint(manifest_dir)
    merged = merge_blueprint_fragment(blueprint, parent_entity_id, children)
    if not BlueprintLoader.save_blueprint(manifest_dir, merged, backup=True):
        task["status"] = "failed"
        task["error"] = "Save failed"
        _save_layer_tasks(path, data)
        return {"ok": False, "error": "Failed to save blueprint", "task_id": task_id}

    task["status"] = "completed"
    _save_layer_tasks(path, data)

    batch_id = task.get("batch_id")
    if batch_id:
        try_spawn_next_layer(manifest_dir, batch_id)
    return {"ok": True, "task_id": task_id, "batch_id": batch_id, "children_count": len(children)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one doc layer-writer task")
    parser.add_argument("--manifest-dir", type=Path, required=True, help="Path to .manifest")
    parser.add_argument("--task-id", required=True, help="Task ID from doc_layer_writer_tasks.json")
    args = parser.parse_args()
    result = run_task(args.manifest_dir, args.task_id)
    print(json.dumps(result, indent=2), file=_stdout_for_json)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
