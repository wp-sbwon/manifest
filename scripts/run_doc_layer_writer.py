#!/usr/bin/env python3
"""
Run a single doc layer-writer task: produce children for a parent entity and merge into blueprint.

Usage:
  PYTHONPATH=src python scripts/run_doc_layer_writer.py --manifest-dir .manifest --parent PROJECT_ROOT --layer 0

Per doc-creation-context-plan.md: each task receives parent entity, PRD excerpt, path from root,
and sibling IDs. OpenCode (or stub) produces that layer's children. Result is merged into
blueprint_design.json; next layer tasks are spawned for each child.
"""
import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from manifest.opencode.layer_writer import (
    build_layer_writer_context,
    merge_children_into_blueprint,
    try_spawn_next_layer,
    write_blueprint_layer,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run doc layer-writer: produce children for parent entity and merge into blueprint."
    )
    parser.add_argument("--manifest-dir", required=True, type=Path, help="Path to .manifest directory")
    parser.add_argument("--parent", help="Parent entity ID (e.g. PROJECT_ROOT, cli)")
    parser.add_argument("--layer", type=int, help="Layer index (0 = root's children)")
    parser.add_argument("--layer-0", action="store_true", help="Shorthand: run layer 0 (root's children)")
    parser.add_argument("--max-depth", type=int, default=None, help="Max layer depth")
    args = parser.parse_args()

    if args.layer_0:
        args.parent = "PROJECT_ROOT"
        args.layer = 0
    if args.parent is None or args.layer is None:
        parser.error("--parent and --layer required, or use --layer-0")

    manifest_dir = Path(args.manifest_dir).resolve()
    if not manifest_dir.exists():
        print(f"Manifest dir not found: {manifest_dir}", file=sys.stderr)
        return 1

    project_root = manifest_dir.parent

    try:
        ctx = build_layer_writer_context(
            manifest_dir,
            args.parent,
            args.layer,
            max_depth=args.max_depth,
        )
    except ValueError as e:
        print(f"Context build failed: {e}", file=sys.stderr)
        return 1

    try:
        result = write_blueprint_layer(ctx, project_root, manifest_dir)
    except RuntimeError as e:
        print(f"Layer writer failed: {e}", file=sys.stderr)
        return 1

    children = result.get("children") or []
    if children:
        if not merge_children_into_blueprint(manifest_dir, args.parent, children):
            print("Failed to merge children into blueprint", file=sys.stderr)
            return 1
        try_spawn_next_layer(
            manifest_dir,
            project_root,
            args.parent,
            args.layer,
            children,
            max_depth=args.max_depth,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
