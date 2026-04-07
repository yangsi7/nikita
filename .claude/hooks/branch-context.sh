#!/usr/bin/env bash
# Informational: surface current branch context before edits
# Helps catch worktree cross-contamination early
# No set -e: this hook is intentionally always-exit-0 (informational only)

BRANCH=$(git branch --show-current 2>/dev/null || echo "detached")
WORKTREE=$(git rev-parse --show-toplevel 2>/dev/null || echo "unknown")
WORKTREE_NAME=$(basename "$WORKTREE")

# Only show context when NOT on master (edits on master are blocked by PR workflow)
if [[ "$BRANCH" != "master" && "$BRANCH" != "main" ]]; then
  echo "[branch: $BRANCH | worktree: $WORKTREE_NAME]" >&2
fi

exit 0
