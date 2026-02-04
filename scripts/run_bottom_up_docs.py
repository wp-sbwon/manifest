#!/usr/bin/env python3
"""
Run bottom-up doc generation: refresh blueprint_code.json and generate
intent_code.json / architecture_code.json using the OpenCode session as agent.

Called on every commit (post-commit hook) and optionally after GitManager.create_commit.
Process is always bottom-up: extract from code first, then infer higher-level docs via LLM.
"""
import argparse
import asyncio
import sys
from pathlib import Path

# Ensure project root is on path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))


def _refresh_blueprint_code(project_root: Path, manifest_dir: Path) -> bool:
    """Refresh blueprint_code.json from code. Returns True if updated."""
    try:
        from manifest.audit.monitoring.code_watcher import CodeWatcher
        watcher = CodeWatcher(project_root=project_root, manifest_dir=manifest_dir)
        return watcher.force_extract()
    except Exception as e:
        print(f"Warning: failed to refresh blueprint_code.json: {e}", file=sys.stderr)
        return False


async def _run_bottom_up_with_opencode(manifest_dir: Path, project_root: Path) -> bool:
    """Run LLM-based intent/architecture generation using OpenCode session. Returns True if successful."""
    try:
        from manifest.core.config import get_config_manager
        from manifest.core.state_manager import StateManager
        from manifest.runtime.agent.core.executor_factory import ExecutorFactory
        from manifest.audit.code.bottom_up_docs import generate_higher_level_docs_from_code
    except ImportError as e:
        print(f"Warning: cannot import manifest modules: {e}", file=sys.stderr)
        return False

    config_manager = get_config_manager()
    config_manager.manifest_dir = manifest_dir
    state_manager = StateManager(manifest_dir)
    backend = config_manager.get_setting("agent.execution_backend", "opencode")
    executor = ExecutorFactory.create_executor(config_manager, state_manager, backend=backend)

    # Only OpenCode adapter supports call_llm_once
    from manifest.runtime.opencode_llm_adapter import OpenCodeLLMAdapter
    if not isinstance(executor, OpenCodeLLMAdapter):
        print("Bottom-up higher-level docs require OpenCode backend; skipping LLM generation.", file=sys.stderr)
        return False

    async def llm_caller(prompt: str, context: dict) -> str:
        return await executor.call_llm_once(prompt, context)

    result = await generate_higher_level_docs_from_code(
        manifest_dir=manifest_dir,
        project_root=project_root,
        llm_caller=llm_caller,
        code_files=None,
    )
    if result.get("error"):
        print(f"Bottom-up docs LLM error: {result['error']}", file=sys.stderr)
        return False
    return True


def _write_project_metrics(manifest_dir: Path, project_root: Path) -> None:
    """Write project health (lint, coverage, size) to state.json. Part of bottom-up."""
    try:
        from manifest.audit.code.health_from_code import write_health_to_state
        write_health_to_state(manifest_dir)
    except Exception as e:
        print(f"Warning: failed to write project metrics: {e}", file=sys.stderr)


async def main(project_root: Path, manifest_dir: Path, skip_llm: bool = False) -> int:
    """Refresh blueprint_code and optionally generate intent_code/architecture_code. Returns exit code."""
    manifest_dir.mkdir(parents=True, exist_ok=True)
    updated = _refresh_blueprint_code(project_root, manifest_dir)
    if updated:
        print("Updated blueprint_code.json from code.", file=sys.stderr)
    _write_project_metrics(manifest_dir, project_root)
    if skip_llm:
        return 0
    ok = await _run_bottom_up_with_opencode(manifest_dir, project_root)
    return 0 if ok else 1


def main_sync() -> int:
    parser = argparse.ArgumentParser(description="Run bottom-up doc generation (blueprint_code + intent/architecture via OpenCode).")
    parser.add_argument("--project-root", type=Path, default=None, help="Project root (default: cwd)")
    parser.add_argument("--manifest-dir", type=Path, default=None, help="Manifest dir (default: project_root/.manifest)")
    parser.add_argument("--skip-llm", action="store_true", help="Only refresh blueprint_code.json; skip LLM generation")
    args = parser.parse_args()
    project_root = (args.project_root or Path.cwd()).resolve()
    manifest_dir = (args.manifest_dir or (project_root / ".manifest")).resolve()
    return asyncio.run(main(project_root, manifest_dir, skip_llm=args.skip_llm))


if __name__ == "__main__":
    sys.exit(main_sync())
