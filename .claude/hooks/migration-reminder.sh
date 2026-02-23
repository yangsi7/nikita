#!/usr/bin/env bash
# PostToolUse Hook — Remind to create migration after model file edits
set -e

INPUT=$(cat)

TOOL=$(echo "$INPUT" | jq -r '.tool_name')
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Only trigger for Write/Edit/MultiEdit
if [[ "$TOOL" != "Write" && "$TOOL" != "Edit" && "$TOOL" != "MultiEdit" ]]; then
    exit 0
fi

# Only trigger for SQLAlchemy model files
if [[ ! "$FILE_PATH" =~ nikita/db/models/.*\.py$ ]]; then exit 0; fi

# Skip __init__.py and base.py
BASENAME=$(basename "$FILE_PATH")
if [[ "$BASENAME" == "__init__.py" || "$BASENAME" == "base.py" ]]; then exit 0; fi

jq -n --arg file "$BASENAME" '{
    hookSpecificOutput: {
      hookEventName: "PostToolUse",
      additionalContext: ("DB Model Changed: " + $file + ". If columns were added/changed, create a migration for BOTH local and production Supabase.")
    },
    suppressOutput: false
  }'

exit 0
