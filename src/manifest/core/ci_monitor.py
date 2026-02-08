"""
CI/CD monitoring and failure detection.

This module provides utilities to check GitHub Actions CI status and detect
failures automatically. It can be integrated into development workflows to
alert when CI is failing.
"""
import os
import subprocess
import json
from pathlib import Path
from typing import Optional, Dict, Any
from manifest.core.logger import get_logger

logger = get_logger(__name__)


def get_github_repo_info() -> Optional[Dict[str, str]]:
    """Get GitHub repository information from git remote.

    Returns:
        Dictionary with 'owner' and 'repo' keys, or None if not a GitHub repo.
    """
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True
        )
        url = result.stdout.strip()

        # Parse GitHub URL
        if "github.com" in url:
            if url.startswith("https://"):
                parts = url.replace("https://github.com/", "").replace(".git", "").split("/")
            elif url.startswith("git@"):
                parts = url.replace("git@github.com:", "").replace(".git", "").split("/")
            else:
                return None

            if len(parts) >= 2:
                return {"owner": parts[0], "repo": parts[1]}
    except Exception as e:
        logger.debug("get_github_repo_info failed: %s", e)

    return None


def check_ci_status_local() -> Dict[str, Any]:
    """Check CI status by running local tests (simulating CI).

    This runs the same tests that CI runs to catch failures early.

    Returns:
        Dictionary with test results.
    """
    try:
        # Run tests in CI-like environment
        env = os.environ.copy()
        env["PYTHONPATH"] = "src"

        result = subprocess.run(
            ["python", "-m", "pytest", "tests/", "-q", "--tb=short"],
            capture_output=True,
            text=True,
            env=env,
            cwd=Path.cwd()
        )

        return {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def check_imports() -> Dict[str, Any]:
    """Check if all critical imports work (like CI lint check).

    Returns:
        Dictionary with import check results.
    """
    imports_to_check = [
        ("manifest.__main__", "main"),
        ("manifest.launcher", "main"),
        ("manifest.view.app", "ManifestViewApp"),
        ("manifest.core.state_manager", "StateManager"),
        ("manifest.agents.agent_coordinator", "AgentCoordinator"),
        ("manifest.bridge.agent_bridge", "AgentBridge"),
        ("manifest.runtime.agent.core", "ExecutorFactory"),
    ]

    results = {}
    all_passed = True

    for module_name, attr_name in imports_to_check:
        try:
            module = __import__(module_name, fromlist=[attr_name])
            obj = getattr(module, attr_name)
            results[f"{module_name}.{attr_name}"] = "OK"
            if attr_name == "ManifestViewApp" and hasattr(obj, "compose"):
                if not callable(getattr(obj, "compose")):
                    results[f"{module_name}.{attr_name}.compose"] = "FAILED: compose not callable"
                    all_passed = False
        except Exception as e:
            results[f"{module_name}.{attr_name}"] = f"FAILED: {e}"
            all_passed = False

    return {
        "success": all_passed,
        "results": results
    }


def verify_ci_readiness() -> Dict[str, Any]:
    """Verify that code is ready for CI (all checks pass locally).

    This runs the same checks that CI runs to catch issues before pushing.

    Returns:
        Dictionary with verification results.
    """
    # Check imports
    import_results = check_imports()

    # Check syntax (simplified - just check a few key files)
    syntax_ok = True
    key_files = [
        "src/manifest/runtime/agent/core/__init__.py",
        "src/manifest/runtime/agent/core/executor_factory.py",
        "src/manifest/runtime/opencode_llm_adapter.py",
        "src/manifest/bridge/agent_bridge.py",
    ]

    for file_path in key_files:
        path = Path(file_path)
        if path.exists():
            try:
                compile(open(path).read(), str(path), "exec")
            except SyntaxError as e:
                logger.error(f"Syntax error in {file_path}: {e}")
                syntax_ok = False

    return {
        "imports": import_results,
        "syntax": {"success": syntax_ok},
        "ready": import_results["success"] and syntax_ok
    }
