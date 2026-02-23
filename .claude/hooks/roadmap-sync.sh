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

# Extract spec number (POSIX-compatible — no grep -oP on macOS)
SPEC_NUM=$(echo "$FILE_PATH" | sed -n 's|.*specs/\([0-9]\{3\}\).*|\1|p')
if [ -z "$SPEC_NUM" ]; then
    exit 0  # Not a recognizable spec path
fi
ARTIFACT=$(basename "$FILE_PATH")

jq -n \
  --arg spec "$SPEC_NUM" \
  --arg artifact "$ARTIFACT" \
  '{
    hookSpecificOutput: {
      hookEventName: "PostToolUse",
      additionalContext: ("Spec " + $spec + " artifact updated (" + $artifact + "). Remember to run `/roadmap sync` to keep ROADMAP.md current.")
    },
    suppressOutput: false
  }'

exit 0
