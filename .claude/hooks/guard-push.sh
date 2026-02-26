#!/usr/bin/env bash
# Guard: Run CI checks before git push (Claude Code PreToolUse hook)
# Bypass: git push --no-verify (handled by Claude Code, not this script)
set -e

CMD=$(echo "$CLAUDE_TOOL_INPUT" | jq -r '.command // empty' 2>/dev/null)

# Only intercept git push commands
if echo "$CMD" | grep -qE '^git push'; then
    echo "Running pre-push CI gate..." >&2
    "$CLAUDE_PROJECT_DIR/scripts/ci-check.sh" --backend-only --quick >&2
    EXIT=$?
    if [ $EXIT -ne 0 ]; then
        echo '{"decision":"block","reason":"Pre-push CI checks failed. Fix tests before pushing."}'
        exit 0
    fi
fi

echo '{"decision":"allow"}'
