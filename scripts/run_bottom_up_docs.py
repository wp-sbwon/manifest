#!/usr/bin/env python3
"""
Run bottom-up: refresh blueprint_code.json from code and write project metrics.

Called on every commit (post-commit hook) and optionally after GitManager.create_commit.
"""
import argparse
import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))


def _refresh_blueprint_code(project_root: Path, manifest_dir: Path) -> bool:
    """Refresh blueprint_code.json from codebase. Returns True if updated."""
    try:
        from manifest.audit.monitoring.code_watcher import CodeWatcher
        watcher = CodeWatcher(project_root=project_root, manifest_dir=manifest_dir)
        return watcher.force_extract()
    except Exception as e:
        print(f"Warning: failed to refresh blueprint_code: {e}", file=sys.stderr)
        return False


def _write_project_metrics(manifest_dir: Path, project_root: Path) -> None:
    """Write project health (lint, coverage, size) to state.json."""
    try:
        from manifest.audit.code.health_from_code import write_health_to_state
        write_health_to_state(manifest_dir)
    except Exception as e:
        print(f"Warning: failed to write project metrics: {e}", file=sys.stderr)


async def main(project_root: Path, manifest_dir: Path, skip_llm: bool = False) -> int:
    """Refresh blueprint_code and write project metrics. Returns exit code."""
    manifest_dir.mkdir(parents=True, exist_ok=True)
    updated = _refresh_blueprint_code(project_root, manifest_dir)
    if updated:
        print("Updated blueprint_code from codebase.", file=sys.stderr)
    _write_project_metrics(manifest_dir, project_root)
    return 0


def main_sync() -> int:
    parser = argparse.ArgumentParser(description="Run bottom-up: refresh blueprint_code from code.")
    parser.add_argument("--project-root", type=Path, default=None, help="Project root (default: cwd)")
    parser.add_argument("--manifest-dir", type=Path, default=None, help="Manifest dir (default: project_root/.manifest)")
    parser.add_argument("--skip-llm", action="store_true", help="Ignored; kept for CLI compatibility")
    args = parser.parse_args()
    project_root = (args.project_root or Path.cwd()).resolve()
    manifest_dir = (args.manifest_dir or (project_root / ".manifest")).resolve()
    return asyncio.run(main(project_root, manifest_dir, skip_llm=args.skip_llm))


if __name__ == "__main__":
    sys.exit(main_sync())
