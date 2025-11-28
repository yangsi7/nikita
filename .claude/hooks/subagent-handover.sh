#!/bin/bash
# SubagentStop hook: Handover management
# Manages subagent completion and handover to next agent

set -euo pipefail

# Read JSON input from stdin
INPUT=$(cat)

# Extract session information
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty')
CWD=$(echo "$INPUT" | jq -r '.cwd // empty')

# Look for recent handover files (YYYYMMDD-HHMM-handover-*.md)
HANDOVER_DIR="${CWD}"

# Find handover files created in last 5 minutes
RECENT_HANDOVERS=$(find "$HANDOVER_DIR" -maxdepth 1 -name "*-handover-*.md" -mmin -5 2>/dev/null || true)

if [[ -n "$RECENT_HANDOVERS" ]]; then
    echo "✓ Subagent handover detected:" >&2

    # List recent handover files
    while IFS= read -r handover_file; do
        filename=$(basename "$handover_file")

        # Extract handover type from filename (e.g., analyzer-to-planner)
        if [[ $filename =~ ([0-9]{8}-[0-9]{4})-handover-(.+)\.md ]]; then
            timestamp="${BASH_REMATCH[1]}"
            handover_type="${BASH_REMATCH[2]}"

            echo "   📤 $handover_type ($timestamp)" >&2

            # Read first few lines to get context
            head -5 "$handover_file" | grep -v "^#" | grep -v "^$" | head -2 | \
                sed 's/^/      /' >&2 2>/dev/null || true
        fi
    done <<< "$RECENT_HANDOVERS"

    echo "" >&2
    echo "💡 Next agent guidance:" >&2
    echo "   Review handover document for context and continuation" >&2
    echo "   Use 'continue' to proceed with next phase" >&2
else
    # No handover file found - provide general completion feedback
    echo "✓ Subagent task completed" >&2
    echo "   No handover document generated" >&2
    echo "   Task may be complete or require review" >&2
fi

# Check if there are other subagents that should be invoked
# by looking for pending phases in planning.md
PLANNING_FILE="${CWD}/planning.md"
if [[ -f "$PLANNING_FILE" ]]; then
    # Check for pending orchestrator phases
    PENDING_ORCHESTRATION=$(grep -c "orchestrator\|delegation\|parallel" "$PLANNING_FILE" 2>/dev/null || echo "0")

    if [[ $PENDING_ORCHESTRATION -gt 0 ]]; then
        echo "" >&2
        echo "⚡ Multi-agent workflow detected:" >&2
        echo "   Planning document suggests additional agent coordination" >&2
        echo "   Consider orchestrator-led delegation if appropriate" >&2
    fi
fi

# Exit 0 for success (informational, not blocking)
exit 0
