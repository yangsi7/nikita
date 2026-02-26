#!/usr/bin/env bash
# scripts/ci-check.sh — Local CI gate (mirrors backend-ci.yml + portal-ci.yml)
# Usage: ./scripts/ci-check.sh [--backend-only] [--quick]
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FAILURES=0
BACKEND_ONLY=false
QUICK=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --backend-only) BACKEND_ONLY=true; shift ;;
        --quick) QUICK=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# --- Backend Tests ---
echo "=== Backend CI ==="
cd "$PROJECT_DIR"

if [ "$QUICK" = "true" ]; then
    echo "Running pytest (quick: fail-fast, short tracebacks)..."
    pytest tests/ -x -q \
        --ignore=tests/e2e --ignore=tests/db/integration \
        --ignore=tests/integration --ignore=tests/smoke \
        --tb=short || FAILURES=$((FAILURES + 1))
else
    echo "Running pytest (full CI mode)..."
    pytest tests/ -x -q \
        --ignore=tests/e2e --ignore=tests/db/integration \
        --ignore=tests/integration --ignore=tests/smoke || FAILURES=$((FAILURES + 1))
fi

# --- Portal Tests (skip if --backend-only) ---
if [ "$BACKEND_ONLY" != "true" ]; then
    echo ""
    echo "=== Portal CI ==="
    cd "$PROJECT_DIR/portal"

    # Source nvm for Node 22
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
    nvm use 22 2>/dev/null || true

    echo "Running npm test:ci..."
    npm run test:ci || FAILURES=$((FAILURES + 1))

    echo "Running ESLint..."
    npm run lint || FAILURES=$((FAILURES + 1))

    echo "Running type-check..."
    npm run type-check || FAILURES=$((FAILURES + 1))

    if [ "$QUICK" != "true" ]; then
        echo "Running build check..."
        NEXT_PUBLIC_SUPABASE_URL=https://example.supabase.co \
        NEXT_PUBLIC_SUPABASE_ANON_KEY=dummy-key-for-ci \
        NEXT_PUBLIC_API_URL=https://example.run.app \
        npm run build || FAILURES=$((FAILURES + 1))
    fi
fi

# --- Summary ---
echo ""
if [ $FAILURES -eq 0 ]; then
    echo "All CI checks passed!"
    exit 0
else
    echo "$FAILURES CI check(s) failed. Fix before pushing."
    exit 1
fi
