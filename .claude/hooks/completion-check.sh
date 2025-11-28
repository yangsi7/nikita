#!/bin/bash
# Stop hook: Completion checking
# Verifies task completion status and provides continuation guidance

set -euo pipefail

# Read JSON input from stdin
INPUT=$(cat)

# Extract session information
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty')
CWD=$(echo "$INPUT" | jq -r '.cwd // empty')

# Check for todo.md and planning.md in project directory
TODO_FILE="${CWD}/todo.md"
PLANNING_FILE="${CWD}/planning.md"

# Initialize completion status
HAS_INCOMPLETE=false
INCOMPLETE_TASKS=""
PENDING_PHASES=""

# Check todo.md for incomplete tasks
if [[ -f "$TODO_FILE" ]]; then
    # Count in_progress tasks
    IN_PROGRESS=$(grep -c "\"status\":\"in_progress\"" "$TODO_FILE" 2>/dev/null || echo "0")

    # Count pending tasks
    PENDING=$(grep -c "\"status\":\"pending\"" "$TODO_FILE" 2>/dev/null || echo "0")

    if [[ $IN_PROGRESS -gt 0 || $PENDING -gt 0 ]]; then
        HAS_INCOMPLETE=true

        # Extract task descriptions for in_progress and pending
        if command -v jq >/dev/null 2>&1; then
            # Use TodoWrite format parsing
            INCOMPLETE_TASKS=$(grep -o '"content":"[^"]*","status":"in_progress\|pending"' "$TODO_FILE" 2>/dev/null | \
                sed 's/"content":"//g' | sed 's/","status":"in_progress//g' | sed 's/","status":"pending//g' | \
                head -5)
        fi

        echo "⚠️  Incomplete tasks detected:" >&2
        echo "   - In Progress: $IN_PROGRESS" >&2
        echo "   - Pending: $PENDING" >&2

        if [[ -n "$INCOMPLETE_TASKS" ]]; then
            echo "" >&2
            echo "   Next tasks:" >&2
            echo "$INCOMPLETE_TASKS" | head -3 | sed 's/^/     • /' >&2
        fi
    fi
fi

# Check planning.md for pending phases
if [[ -f "$PLANNING_FILE" ]]; then
    # Look for pending status markers
    PENDING_COUNT=$(grep -c "⏳\|pending\|TODO" "$PLANNING_FILE" 2>/dev/null || echo "0")

    if [[ $PENDING_COUNT -gt 0 ]]; then
        echo "" >&2
        echo "📋 Planning document has $PENDING_COUNT pending items" >&2
    fi
fi

# Provide continuation guidance
if [[ "$HAS_INCOMPLETE" == "true" ]]; then
    echo "" >&2
    echo "💡 Continuation guidance:" >&2
    echo "   Use 'continue' or 'proceed' to work on next task" >&2
    echo "   Review todo.md for complete task list" >&2
fi

# Exit 0 for success (this is informational, not blocking)
exit 0
