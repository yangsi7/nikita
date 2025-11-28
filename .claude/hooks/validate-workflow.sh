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

# Validation 1: Cannot create plan.md without spec.md
if [[ "$FILE_PATH" == *"/plan.md" ]]; then
    if [[ ! -f "$FEATURE_DIR/spec.md" ]]; then
        cat >&2 << 'EOF'
{
  "decision": "block",
  "reason": "Article IV Violation: Cannot create plan.md without spec.md. Specification-First Development requires spec.md → plan.md → tasks.md order.",
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Article IV (Specification-First Development) enforcement.\n\n**Missing**: spec.md must exist before creating plan.md\n\n**Next Action**: Create specification first using specify-feature skill or /feature command\n\n**Workflow Order**:\n1. /feature → spec.md (WHAT/WHY)\n2. /plan → plan.md (HOW with tech)\n3. /tasks → tasks.md (organized by user story)\n4. /implement → progressive delivery"
  }
}
EOF
        exit 2
    fi
fi

# Validation 2: Cannot create tasks.md without plan.md
if [[ "$FILE_PATH" == *"/tasks.md" ]]; then
    if [[ ! -f "$FEATURE_DIR/plan.md" ]]; then
        cat >&2 << 'EOF'
{
  "decision": "block",
  "reason": "Article IV Violation: Cannot create tasks.md without plan.md. Specification-First Development requires spec.md → plan.md → tasks.md order.",
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Article IV (Specification-First Development) enforcement.\n\n**Missing**: plan.md must exist before creating tasks.md\n\n**Next Action**: Create implementation plan first using create-implementation-plan skill or /plan command\n\n**Workflow Order**:\n1. /feature → spec.md (WHAT/WHY) ✓\n2. /plan → plan.md (HOW with tech) ← REQUIRED\n3. /tasks → tasks.md (organized by user story) ← BLOCKED\n4. /implement → progressive delivery"
  }
}
EOF
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
