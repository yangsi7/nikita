#!/usr/bin/env bash
# PreCompact Hook — Preserve SDD state across context compaction
# Injects active spec, recent events, and git state into compaction context

set -e

# Read JSON input from stdin (PreCompact provides conversation context)
INPUT=$(cat)

CONTEXT_PARTS=""

# 1. Current branch + working tree status
BRANCH=$(cd "$CLAUDE_PROJECT_DIR" && git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
DIRTY=$(cd "$CLAUDE_PROJECT_DIR" && git status --porcelain 2>/dev/null | head -5)
CONTEXT_PARTS="**Git**: branch=$BRANCH"
if [ -n "$DIRTY" ]; then
    CONTEXT_PARTS="$CONTEXT_PARTS (dirty: $(echo "$DIRTY" | wc -l | tr -d ' ') files)"
fi

# 2. Last 5 event-stream entries
if [ -f "$CLAUDE_PROJECT_DIR/event-stream.md" ]; then
    RECENT_EVENTS=$(grep '^\[' "$CLAUDE_PROJECT_DIR/event-stream.md" | head -5 | sed 's/"/\\"/g')
    CONTEXT_PARTS="$CONTEXT_PARTS\n**Recent Events**:\n$RECENT_EVENTS"
fi

# 3. Active spec detection (from branch name or recent events)
if [[ "$BRANCH" =~ ^[0-9]{3}- ]] || [[ "$BRANCH" =~ ^feature/[0-9]{3} ]]; then
    SPEC_ID=$(echo "$BRANCH" | sed -n 's|.*\([0-9]\{3\}\).*|\1|p' | head -1)
    SPEC_DIR="$CLAUDE_PROJECT_DIR/specs/${SPEC_ID}-*"
    SPEC_DIR_RESOLVED=$(ls -d $SPEC_DIR 2>/dev/null | head -1)
    if [ -n "$SPEC_DIR_RESOLVED" ]; then
        HAS_SPEC=$([[ -f "$SPEC_DIR_RESOLVED/spec.md" ]] && echo "Y" || echo "N")
        HAS_PLAN=$([[ -f "$SPEC_DIR_RESOLVED/plan.md" ]] && echo "Y" || echo "N")
        HAS_TASKS=$([[ -f "$SPEC_DIR_RESOLVED/tasks.md" ]] && echo "Y" || echo "N")
        CONTEXT_PARTS="$CONTEXT_PARTS\n**Active Spec**: ${SPEC_ID} at ${SPEC_DIR_RESOLVED}\n  spec.md=$HAS_SPEC plan.md=$HAS_PLAN tasks.md=$HAS_TASKS"
    fi
fi

# 4. ROADMAP quick status
if [ -f "$CLAUDE_PROJECT_DIR/ROADMAP.md" ]; then
    ACTIVE=$(grep -c "ACTIVE\|IN_PROGRESS" "$CLAUDE_PROJECT_DIR/ROADMAP.md" 2>/dev/null || echo "0")
    PLANNED=$(grep -c "PLANNED\|BACKLOG" "$CLAUDE_PROJECT_DIR/ROADMAP.md" 2>/dev/null || echo "0")
    CONTEXT_PARTS="$CONTEXT_PARTS\n**ROADMAP**: ${ACTIVE} active, ${PLANNED} planned"
fi

# Output context for compaction
jq -n \
  --arg ctx "## SDD State (Pre-Compaction Snapshot)\n${CONTEXT_PARTS}" \
  '{
    hookSpecificOutput: {
      hookEventName: "PreCompact",
      additionalContext: $ctx
    },
    suppressOutput: true
  }'

exit 0
