#!/usr/bin/env bash
# Session Start Hook
# Purpose: Auto-detect feature, validate artifacts, report workflow state
#          + inject project index digest for codebase intelligence
# Replaces: common.sh + check-prerequisites.sh + setup-plan.sh

set -e

CONTEXT_MESSAGE=""

# --- Project Index Auto-Digest ---
if [ -f "$CLAUDE_PROJECT_DIR/PROJECT_INDEX.json" ]; then
    CHANGED=$(cd "$CLAUDE_PROJECT_DIR" && git diff --name-only HEAD~5 2>/dev/null | head -10)
    DIGEST=$(cd "$CLAUDE_PROJECT_DIR" && jq -c '{
        stats: {files: .stats.total_files, py: .stats.fully_parsed.python, ts: .stats.fully_parsed.typescript},
        top_modules: [.deps | to_entries | map(.value[]) | map(select(startswith("nikita."))) | group_by(.) | map({m: .[0], n: length}) | sort_by(-.n)[:8] | .[] | "\(.m):\(.n)"],
        high_coupling: [.deps | to_entries | map({f: .key, n: (.value | length)}) | sort_by(-.n)[:5] | .[] | "\(.f | split("/")[-1]):\(.n)"]
    }' PROJECT_INDEX.json 2>/dev/null || echo "{}")

    CONTEXT_MESSAGE="## Project Index\n$DIGEST\n**Changed files**: $(echo "$CHANGED" | tr '\n' ', ')\n\n"
fi

# --- SDD Workflow Detection ---
# Detect current feature (git branch or SPECIFY_FEATURE env var)
FEATURE=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "${SPECIFY_FEATURE:-}")

# Only add SDD context if on a feature branch (starts with ###- pattern)
if [[ "$FEATURE" =~ ^[0-9]{3}- ]]; then
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

    CONTEXT_MESSAGE="${CONTEXT_MESSAGE}## SDD Workflow Status

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
fi

# Only output if we have context to inject
if [ -n "$CONTEXT_MESSAGE" ]; then
    cat << EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "$CONTEXT_MESSAGE"
  },
  "suppressOutput": false
}
EOF
fi

exit 0
