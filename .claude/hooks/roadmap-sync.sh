#!/usr/bin/env bash
# PostToolUse Hook — Remind to sync ROADMAP.md after spec artifact writes
# Lightweight: just an echo reminder, not auto-edit

set -e

INPUT=$(cat)

TOOL=$(echo "$INPUT" | jq -r '.tool_name')
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Only trigger on Write/Edit to spec files
if [[ "$TOOL" != "Write" && "$TOOL" != "Edit" && "$TOOL" != "MultiEdit" ]]; then
    exit 0
fi

# Only trigger for spec artifact files
if [[ ! "$FILE_PATH" =~ specs/[0-9]{3}-.*/((spec|plan|tasks|audit-report)\.md)$ ]]; then
    exit 0
fi

# Extract spec number
SPEC_NUM=$(echo "$FILE_PATH" | grep -oP 'specs/\K[0-9]{3}')
ARTIFACT=$(basename "$FILE_PATH")

cat << EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "Spec ${SPEC_NUM} artifact updated (${ARTIFACT}). Remember to run \`/roadmap sync\` to keep ROADMAP.md current."
  },
  "suppressOutput": false
}
EOF

exit 0
