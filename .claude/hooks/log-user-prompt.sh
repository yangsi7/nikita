#!/bin/bash
# Log user prompt submissions to event-stream.md

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
PROMPT=$(echo "$INPUT" | jq -r '.prompt')
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

# Truncate long prompts for logging
PROMPT_PREVIEW=$(echo "$PROMPT" | head -c 100)
if [ ${#PROMPT} -gt 100 ]; then
    PROMPT_PREVIEW="${PROMPT_PREVIEW}..."
fi

echo "[$TIMESTAMP] [$SESSION_ID] Message - User: $PROMPT_PREVIEW" >> "$CLAUDE_PROJECT_DIR/event-stream.md"

exit 0
