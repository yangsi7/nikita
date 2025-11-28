#!/bin/bash
# Log session start event to event-stream.md and save session ID

# Read JSON input from stdin
INPUT=$(cat)

# Extract session_id and source using jq
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
SOURCE=$(echo "$INPUT" | jq -r '.source')
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

# Append to event-stream.md
echo "[$TIMESTAMP] [$SESSION_ID] SessionStart - Session started from $SOURCE" >> "$CLAUDE_PROJECT_DIR/event-stream.md"

# Write session ID to .session-id file for access during session
echo "$SESSION_ID" > "$CLAUDE_PROJECT_DIR/.session-id"

# Output additional context for Claude
cat <<EOF
Session initialized: $SESSION_ID
Started from: $SOURCE
Event logging enabled to event-stream.md
Session ID available at .session-id
EOF

exit 0
