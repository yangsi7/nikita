#!/usr/bin/env bash
# PreToolUse Workflow Validation Hook
# Purpose: Block invalid workflow operations (e.g., plan without spec)
# Replaces: check-prerequisites.sh validation logic

set -e

# Read JSON input from stdin
INPUT=$(cat)

# Extract tool name and file path
TOOL=$(echo "$INPUT" | jq -r '.tool_name')
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Only validate Write operations on spec/plan/tasks files
if [[ "$TOOL" != "Write" ]]; then
    exit 0
fi

# Skip if not a spec-related file
if [[ ! "$FILE_PATH" =~ specs/[0-9]{3}- ]]; then
    exit 0
fi

# Extract feature directory
FEATURE_DIR=$(dirname "$FILE_PATH")

# Extract spec number (e.g., "042" from "specs/042-unified-pipeline")
SPEC_NUM=$(echo "$FILE_PATH" | sed -n 's|.*specs/\([0-9]\{3\}\).*|\1|p')
if [ -z "$SPEC_NUM" ]; then
    exit 0  # Could not extract spec number — skip validation
fi

# Validation 0: Cannot create spec.md without ROADMAP.md entry
if [[ "$FILE_PATH" == *"/spec.md" ]]; then
    ROADMAP="$CLAUDE_PROJECT_DIR/ROADMAP.md"
    if [[ -f "$ROADMAP" ]] && ! grep -qE "^\| *${SPEC_NUM} *\|" "$ROADMAP"; then
        echo "BLOCKED: Spec ${SPEC_NUM} not registered in ROADMAP.md. Run /roadmap add ${SPEC_NUM} <name> first." >&2
        exit 2
    fi
fi

# Validation 1: Cannot create plan.md without spec.md
if [[ "$FILE_PATH" == *"/plan.md" ]]; then
    if [[ ! -f "$FEATURE_DIR/spec.md" ]]; then
        echo "BLOCKED: Cannot create plan.md without spec.md. Run /feature first. Order: spec.md -> plan.md -> tasks.md" >&2
        exit 2
    fi
fi

# Validation 2: Cannot create tasks.md without plan.md
if [[ "$FILE_PATH" == *"/tasks.md" ]]; then
    if [[ ! -f "$FEATURE_DIR/plan.md" ]]; then
        echo "BLOCKED: Cannot create tasks.md without plan.md. Run /plan first. Order: spec.md -> plan.md -> tasks.md" >&2
        exit 2
    fi
fi

# All validations passed - allow operation
cat << 'EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "permissionDecisionReason": "Workflow validation passed. File creation follows Article IV Specification-First order."
  },
  "suppressOutput": true
}
EOF

exit 0
