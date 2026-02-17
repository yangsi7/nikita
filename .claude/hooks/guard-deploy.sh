#!/bin/bash
# Guard: Block --min-instances on gcloud run deploy (must scale to zero)
# Also block git add of .env* and credential files

TOOL_INPUT="$CLAUDE_TOOL_INPUT"

# Check for --min-instances in gcloud run deploy commands
if echo "$TOOL_INPUT" | jq -r '.command // empty' 2>/dev/null | grep -q 'gcloud run deploy'; then
    if echo "$TOOL_INPUT" | jq -r '.command // empty' 2>/dev/null | grep -q '\-\-min-instances'; then
        echo "BLOCKED: --min-instances is forbidden. Cloud Run must scale to zero." >&2
        exit 2
    fi
fi

# Check for git add of sensitive files
if echo "$TOOL_INPUT" | jq -r '.command // empty' 2>/dev/null | grep -q 'git add'; then
    CMD=$(echo "$TOOL_INPUT" | jq -r '.command // empty' 2>/dev/null)
    if echo "$CMD" | grep -qE '\.env|credentials|\.key|\.pem|secrets'; then
        echo "BLOCKED: Cannot git add sensitive files (.env, credentials, keys). Review manually." >&2
        exit 2
    fi
fi

exit 0
