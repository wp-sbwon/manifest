#!/usr/bin/env python3
"""
Check GitHub Actions CI status.

This script checks the status of the latest GitHub Actions workflow run
and reports any failures. Can be run manually or integrated into pre-push hooks.

Also runs local CI checks to catch issues before pushing.
"""
import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


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
        # Format: https://github.com/owner/repo.git or git@github.com:owner/repo.git
        if "github.com" in url:
            if url.startswith("https://"):
                parts = url.replace("https://github.com/", "").replace(".git", "").split("/")
            elif url.startswith("git@"):
                parts = url.replace("git@github.com:", "").replace(".git", "").split("/")
            else:
                return None

            if len(parts) >= 2:
                return {"owner": parts[0], "repo": parts[1]}
    except Exception:
        pass

    return None


def get_github_token() -> Optional[str]:
    """Get GitHub token from environment or git config.

    Returns:
        GitHub token or None if not found.
    """
    # Check environment variable
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        return token

    # Try to get from gh CLI
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except Exception:
        pass

    return None


def check_workflow_status(
    owner: str,
    repo: str,
    branch: str = "dev",
    token: Optional[str] = None
) -> Dict[str, Any]:
    """Check the status of the latest workflow run for a branch.

    Args:
        owner: GitHub repository owner.
        repo: Repository name.
        branch: Branch name to check.
        token: Optional GitHub token for authentication.

    Returns:
        Dictionary with workflow status information.
    """
    if not HTTPX_AVAILABLE:
        return {
            "error": "httpx not available",
            "message": "Install httpx to check CI status: pip install httpx"
        }

    if not token:
        return {
            "error": "no_token",
            "message": "GitHub token not found. Set GITHUB_TOKEN env var or use 'gh auth login'"
        }

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {token}"
    }

    # Get latest workflow run for the branch
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs"
    params = {"branch": branch, "per_page": 1}

    try:
        import httpx
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, headers=headers, params=params)
            if response.status_code != 200:
                return {
                    "error": f"api_error_{response.status_code}",
                    "message": f"GitHub API error: {response.text}"
                }

            data = response.json()
            runs = data.get("workflow_runs", [])

            if not runs:
                return {
                    "status": "no_runs",
                    "message": f"No workflow runs found for branch '{branch}'"
                }

            latest_run = runs[0]
            return {
                "status": latest_run.get("status"),  # queued, in_progress, completed
                "conclusion": latest_run.get("conclusion"),  # success, failure, cancelled, etc.
                "workflow_name": latest_run.get("name"),
                "created_at": latest_run.get("created_at"),
                "updated_at": latest_run.get("updated_at"),
                "html_url": latest_run.get("html_url"),
                "run_number": latest_run.get("run_number")
            }
    except Exception as e:
        return {
            "error": "exception",
            "message": str(e)
        }


# Single startup test only. Full test suite is archived under tests/archive/.
CI_TEST_CMD = [
    "pytest", "tests/test_startup.py", "-v",
]
CI_TEST_TIMEOUT_SEC = 60


def run_ci_equivalent_tests() -> bool:
    """Run the same test command as CI. Returns True if all tests pass."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parent.parent / "src")
    try:
        r = subprocess.run(
            CI_TEST_CMD,
            env=env,
            cwd=Path(__file__).parent.parent,
            timeout=CI_TEST_TIMEOUT_SEC,
            capture_output=False,
        )
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        print("❌ Local CI tests timed out (script limit {:.0f}s).".format(CI_TEST_TIMEOUT_SEC))
        return False
    except FileNotFoundError:
        print("❌ pytest not found. Install test deps: pip install -r requirements.txt pytest pytest-timeout")
        return False


def main():
    """Main entry point."""
    # First, run local CI checks
    try:
        from manifest.core.ci_monitor import verify_ci_readiness
        local_check = verify_ci_readiness()

        if not local_check["ready"]:
            print("❌ Local CI checks failed!")
            if not local_check["imports"]["success"]:
                print("  Import errors:")
                for k, v in local_check["imports"]["results"].items():
                    if "FAILED" in v:
                        print(f"    {k}: {v}")
            if not local_check["syntax"]["success"]:
                print("  Syntax errors detected")
            print("  Fix these issues before pushing!")
            sys.exit(1)
        else:
            print("✅ Local CI checks passed")
    except Exception as e:
        print(f"⚠️  Could not run local CI checks: {e}")
        # Continue to GitHub status check

    # Run same tests as GitHub Actions so we catch failures before push
    print("Running startup test (pytest tests/test_startup.py)...")
    if not run_ci_equivalent_tests():
        print("❌ Local CI-equivalent tests failed. Fix before pushing.")
        sys.exit(1)
    print("✅ CI-equivalent tests passed")

    # Get current branch
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        current_branch = result.stdout.strip()
    except Exception:
        current_branch = "dev"

    # Get repo info
    repo_info = get_github_repo_info()
    if not repo_info:
        print("⚠️  Not a GitHub repository, skipping remote CI check")
        sys.exit(0)

    # Get token
    token = get_github_token()
    if not token:
        print("⚠️  GitHub token not found. Install 'gh' CLI and run 'gh auth login'")
        print("   Or set GITHUB_TOKEN environment variable")
        print("   Skipping remote CI status check...")
        sys.exit(0)

    # Check workflow status
    status = check_workflow_status(
        repo_info["owner"],
        repo_info["repo"],
        current_branch,
        token
    )

    if "error" in status:
        print(f"⚠️  Could not check remote CI status: {status.get('message')}")
        sys.exit(0)

    if status.get("status") == "completed":
        conclusion = status.get("conclusion")
        workflow_name = status.get("workflow_name", "Unknown")
        run_number = status.get("run_number", "?")
        html_url = status.get("html_url", "")

        if conclusion == "success":
            print(f"✅ Remote CI passed: {workflow_name} (run #{run_number})")
            sys.exit(0)
        elif conclusion == "failure":
            print(f"❌ Remote CI failed: {workflow_name} (run #{run_number})")
            if html_url:
                print(f"   View details: {html_url}")
            print("\n⚠️  CI is failing! Fix the issues before pushing.")
            print("   You can still push with: git push --no-verify")
            print("   But it's recommended to check GitHub Actions first.")
            sys.exit(1)
        else:
            print(f"⚠️  Remote CI {conclusion}: {workflow_name} (run #{run_number})")
            sys.exit(0)
    elif status.get("status") == "in_progress":
        print(f"⏳ Remote CI running: {status.get('workflow_name', 'Unknown')} (run #{status.get('run_number', '?')})")
        sys.exit(0)
    else:
        print(f"ℹ️  Remote CI status: {status.get('status', 'unknown')}")
        sys.exit(0)


if __name__ == "__main__":
    main()
