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
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _refresh_blueprint_code(project_root: Path, manifest_dir: Path) -> bool:
    from manifest.audit.monitoring.code_watcher import CodeWatcher
    watcher = CodeWatcher(project_root=project_root, manifest_dir=manifest_dir)
    return watcher.force_extract()


def _write_project_metrics(manifest_dir: Path, project_root: Path) -> bool:
    try:
        from manifest.audit.code.health_from_code import write_health_to_state
        return write_health_to_state(manifest_dir)
    except Exception as e:
        print(f"Warning: failed to write project metrics: {e}", file=sys.stderr)
        return False


def _refresh_blueprint_view(manifest_dir: Path) -> bool:
    """Build and write blueprint_view.json (same keys as design/code; values = plan/actual + deviates)."""
    try:
        from manifest.view.entity_model import get_entities_for_view
        data = get_entities_for_view(manifest_dir)
        return data.get("view_write_ok", True)
    except Exception as e:
        print(f"Warning: failed to refresh blueprint_view: {e}", file=sys.stderr)
        return False


async def main(project_root: Path, manifest_dir: Path) -> int:
    manifest_dir.mkdir(parents=True, exist_ok=True)
    try:
        updated = _refresh_blueprint_code(project_root, manifest_dir)
    except RuntimeError as e:
        print(
            f"Error: OpenCode enrichment failed. {e}\n"
            "Check that opencode is installed and on PATH, and that the project parses correctly.",
            file=sys.stderr,
        )
        return 1
    except Exception as e:
        print(f"Error: bottom-up extraction failed: {e}", file=sys.stderr)
        return 1
    if not updated:
        print("Bottom-up extraction did not produce an update.", file=sys.stderr)
        return 1
    print("Updated blueprint_code from codebase.", file=sys.stderr)
    view_ok = _refresh_blueprint_view(manifest_dir)
    metrics_ok = _write_project_metrics(manifest_dir, project_root)
    if not view_ok:
        print("Error: failed to write blueprint_view.json", file=sys.stderr)
        return 1
    if not metrics_ok:
        print("Error: failed to write project metrics to state.json", file=sys.stderr)
        return 1
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
