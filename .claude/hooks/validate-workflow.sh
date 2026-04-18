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

# Derive the repo-root that owns this spec by stripping at /specs/.
# This is worktree-safe: $CLAUDE_PROJECT_DIR can point to the original repo
# (a different checkout/branch than the worktree we are writing into), so we
# MUST locate ROADMAP.md from the FILE_PATH itself, not from the env var.
# Bug history: 2026-04-17 in worktree `delightful-orbiting-ladybug`, Spec 215
# was registered in worktree ROADMAP.md but the hook read the original-repo
# ROADMAP.md (different branch, no 215) and falsely blocked.
SPEC_REPO_ROOT="${FILE_PATH%/specs/*}"

# Validation 0: Cannot create spec.md without ROADMAP.md entry
if [[ "$FILE_PATH" == *"/spec.md" ]]; then
    ROADMAP="$SPEC_REPO_ROOT/ROADMAP.md"
    # Fallback to CLAUDE_PROJECT_DIR if the derived path has no ROADMAP (e.g.
    # tests, sandboxes). Matches original behaviour for non-worktree cases.
    if [[ ! -f "$ROADMAP" && -n "${CLAUDE_PROJECT_DIR:-}" ]]; then
        ROADMAP="$CLAUDE_PROJECT_DIR/ROADMAP.md"
    fi
    if [[ -f "$ROADMAP" ]] && ! grep -qE "^\| *${SPEC_NUM} *\|" "$ROADMAP"; then
        echo "BLOCKED: Spec ${SPEC_NUM} not registered in ${ROADMAP}. Run /roadmap add ${SPEC_NUM} <name> first." >&2
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
