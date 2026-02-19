#!/usr/bin/env python3
"""
Bottom-up pipeline: CodeExtractor + opencode enricher → blueprint_code.json, blueprint_view.json, health_metrics.
Run on commit (GitManager or post-commit hook). Requires blueprint_design.json and opencode on PATH.
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
    from manifest.audit.monitoring.code_watcher import CodeWatcher
    watcher = CodeWatcher(project_root=project_root, manifest_dir=manifest_dir)
    return watcher.force_extract()


def _write_project_metrics(manifest_dir: Path, project_root: Path) -> None:
    try:
        from manifest.audit.code.health_from_code import write_health_to_state
        write_health_to_state(manifest_dir)
    except Exception as e:
        print(f"Warning: failed to write project metrics: {e}", file=sys.stderr)


def _refresh_blueprint_view(manifest_dir: Path) -> None:
    """Build and write blueprint_view.json (same keys as design/code; values = plan/actual + deviates)."""
    try:
        from manifest.view.entity_model import get_entities_for_view
        get_entities_for_view(manifest_dir)
    except Exception as e:
        print(f"Warning: failed to refresh blueprint_view: {e}", file=sys.stderr)


async def main(project_root: Path, manifest_dir: Path) -> int:
    manifest_dir.mkdir(parents=True, exist_ok=True)
    updated = _refresh_blueprint_code(project_root, manifest_dir)
    if updated:
        print("Updated blueprint_code from codebase.", file=sys.stderr)
    _refresh_blueprint_view(manifest_dir)
    _write_project_metrics(manifest_dir, project_root)
    return 0


def main_sync() -> int:
    parser = argparse.ArgumentParser(description="Run bottom-up: extraction + opencode enricher -> blueprint_code.")
    parser.add_argument("--project-root", type=Path, default=None, help="Project root (default: cwd)")
    parser.add_argument("--manifest-dir", type=Path, default=None, help="Manifest dir (default: project_root/.manifest)")
    args = parser.parse_args()
    project_root = (args.project_root or Path.cwd()).resolve()
    manifest_dir = (args.manifest_dir or (project_root / ".manifest")).resolve()
    return asyncio.run(main(project_root, manifest_dir))


if __name__ == "__main__":
    sys.exit(main_sync())
