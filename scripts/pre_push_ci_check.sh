#!/bin/bash
# Pre-push hook to check CI status before pushing
# This prevents pushing code when CI is failing

set -e

echo "🔍 Checking CI status before push..."

# Run local CI checks first
if command -v python3 &> /dev/null; then
    # Check if we're in a venv or need to activate it
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    fi

    # Run CI readiness check
    PYTHONPATH=src python3 -c "
from manifest.core.ci_monitor import verify_ci_readiness
import sys
result = verify_ci_readiness()
if not result['ready']:
    print('❌ Local CI checks failed!')
    if not result.get('imports', {}).get('success'):
        print('  Import errors detected')
    if not result.get('syntax', {}).get('success'):
        print('  Syntax errors detected')
    print('Fix these issues before pushing!')
    sys.exit(1)
else:
    print('✅ Local CI checks passed')
" || exit 1

    # Check GitHub CI status if token is available
    if [ -f "scripts/check_ci_status.py" ]; then
        python3 scripts/check_ci_status.py || {
            echo "⚠️  CI status check failed or CI is failing"
            echo "   You can still push with: git push --no-verify"
            echo "   But it's recommended to fix CI issues first"
            read -p "Continue with push anyway? (y/N) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        }
    fi
else
    echo "⚠️  Python3 not found, skipping CI checks"
fi

echo "✅ Pre-push checks passed"
