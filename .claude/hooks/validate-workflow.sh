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
    if [[ -f "$ROADMAP" ]] && ! grep -q "| ${SPEC_NUM}" "$ROADMAP"; then
        jq -n --arg spec "$SPEC_NUM" '{
          decision: "block",
          reason: ("ROADMAP Registration Required: Spec " + $spec + " is not registered in ROADMAP.md. Run /roadmap add " + $spec + " <name> first."),
          hookSpecificOutput: {
            hookEventName: "PreToolUse",
            permissionDecision: "deny",
            permissionDecisionReason: ("ROADMAP registration enforcement.\n\n**Missing**: Spec " + $spec + " not found in ROADMAP.md\n\n**Next Action**: Run `/roadmap add " + $spec + " <name>` to register this feature\n\n**Workflow Order**:\n0. /roadmap add NNN -> ROADMAP.md entry (GATE 0)\n1. /feature -> spec.md\n2. /plan -> plan.md\n3. /tasks -> tasks.md")
          }
        }' >&2
        exit 2
    fi
fi

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
