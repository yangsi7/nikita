#!/usr/bin/env bash
# Session Start Hook
# Purpose: Auto-detect feature, validate artifacts, report workflow state
# Replaces: common.sh + check-prerequisites.sh + setup-plan.sh

set -e

# Detect current feature (git branch or SPECIFY_FEATURE env var)
FEATURE=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "${SPECIFY_FEATURE:-}")

# Only process if on a feature branch (starts with ###- pattern)
if [[ ! "$FEATURE" =~ ^[0-9]{3}- ]]; then
    # Not on a feature branch, exit silently
    exit 0
fi

# Define feature directory
FEATURE_DIR="$CLAUDE_PROJECT_DIR/specs/$FEATURE"

# Check artifact existence
SPEC_EXISTS=$([ -f "$FEATURE_DIR/spec.md" ] && echo "true" || echo "false")
PLAN_EXISTS=$([ -f "$FEATURE_DIR/plan.md" ] && echo "true" || echo "false")
TASKS_EXISTS=$([ -f "$FEATURE_DIR/tasks.md" ] && echo "true" || echo "false")

# Determine workflow state
if [ "$SPEC_EXISTS" = "false" ]; then
    STATE="needs_spec"
elif [ "$PLAN_EXISTS" = "false" ]; then
    STATE="needs_plan"
elif [ "$TASKS_EXISTS" = "false" ]; then
    STATE="needs_tasks"
else
    STATE="ready"
fi

# Determine next action
case "$STATE" in
  needs_spec) NEXT_ACTION="Create specification with specify-feature skill" ;;
  needs_plan) NEXT_ACTION="Create implementation plan with create-implementation-plan skill" ;;
  needs_tasks) NEXT_ACTION="Generate tasks with generate-tasks skill" ;;
  ready) NEXT_ACTION="Begin implementation with implement-and-verify skill" ;;
esac

# Build context message for Claude
CONTEXT_MESSAGE="## SDD Workflow Status

**Feature**: $FEATURE
**Directory**: $FEATURE_DIR

**Artifacts**:
- spec.md: $([ "$SPEC_EXISTS" = "true" ] && echo "✓ EXISTS" || echo "❌ MISSING") ($FEATURE_DIR/spec.md)
- plan.md: $([ "$PLAN_EXISTS" = "true" ] && echo "✓ EXISTS" || echo "❌ MISSING") ($FEATURE_DIR/plan.md)
- tasks.md: $([ "$TASKS_EXISTS" = "true" ] && echo "✓ EXISTS" || echo "❌ MISSING") ($FEATURE_DIR/tasks.md)

**Workflow State**: $STATE
**Next Action**: $NEXT_ACTION

**Automated SDD Workflow**:
1. /feature → specify-feature skill → spec.md
2. /plan (auto-invoked) → create-implementation-plan skill → plan.md
3. /tasks (auto-invoked) → generate-tasks skill → tasks.md
4. /audit (auto-invoked) → validation
5. /implement → implement-and-verify skill → progressive delivery"

# Output proper Claude Code hook JSON structure
cat << EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "$CONTEXT_MESSAGE"
  },
  "suppressOutput": false
}
EOF

exit 0
