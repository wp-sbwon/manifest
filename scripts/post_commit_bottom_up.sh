#!/usr/bin/env bash
# Post-commit hook: run bottom-up doc generation after every commit.
# Install: ln -sf ../../scripts/post_commit_bottom_up.sh .git/hooks/post-commit
#
# Refreshes blueprint_code.json from code. Process is always bottom-up.
# Does not block or fail the commit; errors are logged to stderr.

set -e

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

if ! command -v python3 &> /dev/null; then
    echo "post_commit_bottom_up: python3 not found, skipping" >&2
    exit 0
fi

if [ -f "venv/bin/activate" ]; then
    # shellcheck source=/dev/null
    source venv/bin/activate
fi

if [ ! -f "bin/run_bottom_up_docs.py" ]; then
    echo "post_commit_bottom_up: bin/run_bottom_up_docs.py not found" >&2
    exit 0
fi

export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
python3 bin/run_bottom_up_docs.py --project-root "$ROOT" 2>&1 | head -20
exit 0
