#!/bin/bash
# Pre-push hook to check CI status before allowing push
# This helps catch CI failures early

set -e

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Check CI status using Python script
cd "$PROJECT_ROOT"

# Activate venv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run CI status check
python scripts/check_ci_status.py
CI_EXIT_CODE=$?

if [ $CI_EXIT_CODE -ne 0 ]; then
    echo ""
    echo "⚠️  Warning: CI check failed or CI is currently failing"
    echo "   You can still push, but CI may fail"
    echo "   To skip this check, use: git push --no-verify"
    read -p "Continue with push? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

exit 0
