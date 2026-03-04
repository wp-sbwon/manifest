#!/usr/bin/env python3
"""
Run test-implementer for a single entity: fill test stub logic via opencode agent.

Usage:
  PYTHONPATH=src python bin/run_test_implementer.py --manifest-dir .manifest --entity cli
"""
import argparse
import json
import logging
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from manifest.opencode.test_implementer import (
    build_test_implementer_context,
    implement_test_stubs,
)

# Redirect all manifest loggers to stderr so stdout stays clean JSON
for _handler in logging.getLogger().handlers + [
    h for name in logging.Logger.manager.loggerDict
    for h in logging.getLogger(name).handlers
    if isinstance(h, logging.StreamHandler) and h.stream is sys.stdout
]:
    if isinstance(_handler, logging.StreamHandler) and _handler.stream is sys.stdout:
        _handler.stream = sys.stderr


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run test-implementer: fill test stub logic for an entity."
    )
    parser.add_argument("--manifest-dir", required=True, type=Path, help="Path to .manifest directory")
    parser.add_argument("--entity", required=True, help="Entity ID (e.g. cli, engine)")
    args = parser.parse_args()

    manifest_dir = Path(args.manifest_dir).resolve()
    if not manifest_dir.exists():
        print(f"Manifest dir not found: {manifest_dir}", file=sys.stderr)
        return 1

    project_root = manifest_dir.parent

    try:
        ctx = build_test_implementer_context(manifest_dir, args.entity, project_root)
    except ValueError as e:
        print(f"Context build failed: {e}", file=sys.stderr)
        return 1

    try:
        result = implement_test_stubs(ctx, project_root)
    except RuntimeError as e:
        print(f"Test implementer failed: {e}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
