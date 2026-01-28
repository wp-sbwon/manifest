#!/bin/bash
# Pre-push hook: run CI-equivalent checks before push.
# Install: ln -sf ../../scripts/pre_push_ci_check.sh .git/hooks/pre-push
# Or use pre-commit: pre-commit run --hook-stage pre-push
#
# Runs scripts/check_ci_status.py (local readiness + same pytest as CI + optional remote status).

set -e

echo "🔍 Running CI-equivalent checks before push..."

if ! command -v python3 &> /dev/null; then
    echo "⚠️  python3 not found, skipping CI checks"
    exit 0
fi

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

if [ ! -f "scripts/check_ci_status.py" ]; then
    echo "⚠️  scripts/check_ci_status.py not found"
    exit 0
fi

PYTHONPATH=src python3 scripts/check_ci_status.py || {
    echo ""
    echo "⚠️  CI checks failed. Fix issues before pushing, or push with: git push --no-verify"
    exit 1
}

echo "✅ Pre-push CI checks passed"
