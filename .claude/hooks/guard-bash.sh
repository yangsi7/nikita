#!/usr/bin/env bash
# Guard: Bash command safety checks (PreToolUse hook)
# Merged from guard-deploy.sh + guard-push.sh
#
# Checks:
#   1. Block --min-instances on gcloud run deploy (must scale to zero)
#   2. Block git add of sensitive files (.env, credentials, keys)
#   3. Warn (non-blocking) before git push — run CI checks if available
#
# Requires: jq
# Spawned only for: gcloud run deploy, git add, git push (via `if` field)

set -e

INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)

[ -z "$CMD" ] && exit 0

# --- Guard 1: Block --min-instances on Cloud Run deploy ---
if echo "$CMD" | grep -q 'gcloud run deploy'; then
    if echo "$CMD" | grep -q '\-\-min-instances'; then
        echo "BLOCKED: --min-instances is forbidden. Cloud Run must scale to zero." >&2
        exit 2
    fi
fi

# --- Guard 2: Block git add of sensitive files ---
if echo "$CMD" | grep -q 'git add'; then
    if echo "$CMD" | grep -qE '\.env|credentials|\.key|\.pem|secrets'; then
        echo "BLOCKED: Cannot git add sensitive files (.env, credentials, keys). Review manually." >&2
        exit 2
    fi
fi

# --- Guard 3: Warn before git push (non-blocking) ---
if echo "$CMD" | grep -qE '^git push'; then
    # Run CI checks if script exists, but don't block push
    if [ -x "$CLAUDE_PROJECT_DIR/scripts/ci-check.sh" ]; then
        if ! "$CLAUDE_PROJECT_DIR/scripts/ci-check.sh" --backend-only --quick 2>/dev/null; then
            echo "WARNING: Pre-push CI checks failed. Consider fixing before push." >&2
            # Non-blocking — exit 0 to allow push
        fi
    fi
fi

exit 0
