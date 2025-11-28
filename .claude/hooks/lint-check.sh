#!/bin/bash
# PostToolUse hook: Lint validation for edited files
# Validates markdown, shell scripts, and JSON files

set -euo pipefail

# Read JSON input from stdin
INPUT=$(cat)

# Extract tool information
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
TOOL_INPUT=$(echo "$INPUT" | jq -r '.tool_input // {}')
FILE_PATH=$(echo "$TOOL_INPUT" | jq -r '.file_path // empty')

# Only process Write and Edit tools with file paths
if [[ "$TOOL_NAME" != "Write" && "$TOOL_NAME" != "Edit" && "$TOOL_NAME" != "MultiEdit" ]]; then
    exit 0
fi

if [[ -z "$FILE_PATH" || "$FILE_PATH" == "null" ]]; then
    exit 0
fi

# Skip if file doesn't exist
if [[ ! -f "$FILE_PATH" ]]; then
    exit 0
fi

# Get file extension
EXT="${FILE_PATH##*.}"

# Lint checks based on file type
case "$EXT" in
    md|markdown)
        # Markdown lint: Check for trailing whitespace
        if grep -q '[[:space:]]$' "$FILE_PATH" 2>/dev/null; then
            echo "✓ Markdown file checked: $FILE_PATH" >&2
            echo "  Note: File contains trailing whitespace (non-blocking)" >&2
        else
            echo "✓ Markdown file checked: $FILE_PATH" >&2
        fi
        ;;

    sh|bash)
        # Shell script lint: Basic syntax check
        if bash -n "$FILE_PATH" 2>/dev/null; then
            echo "✓ Shell script syntax validated: $FILE_PATH" >&2
        else
            echo "✗ Shell script syntax error in: $FILE_PATH" >&2
            bash -n "$FILE_PATH" 2>&1 | head -5 >&2
            exit 1
        fi
        ;;

    json)
        # JSON lint: Validate JSON syntax
        if jq empty "$FILE_PATH" 2>/dev/null; then
            echo "✓ JSON syntax validated: $FILE_PATH" >&2
        else
            echo "✗ JSON syntax error in: $FILE_PATH" >&2
            jq empty "$FILE_PATH" 2>&1 | head -5 >&2
            exit 1
        fi
        ;;

    *)
        # For other file types, just report success
        echo "✓ File processed: $FILE_PATH" >&2
        ;;
esac

# Exit 0 for success (non-blocking for most issues)
exit 0
