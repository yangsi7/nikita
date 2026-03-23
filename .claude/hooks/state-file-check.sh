#!/usr/bin/env bash
# State file line limit enforcement hook
# Warns when state files approach or exceed their documented limits
set -e

WARNINGS=""
for spec in "event-stream.md:200" "workbook.md:300" "ROADMAP.md:400"; do
  f="${spec%%:*}"
  limit="${spec##*:}"
  filepath="$CLAUDE_PROJECT_DIR/$f"
  [ -f "$filepath" ] || continue
  lines=$(wc -l < "$filepath" | tr -d ' ')
  warn_threshold=$(( limit * 80 / 100 ))
  if [ "$lines" -gt "$limit" ]; then
    WARNINGS="${WARNINGS}  - OVER LIMIT: $f has $lines lines (max $limit)\n"
  elif [ "$lines" -gt "$warn_threshold" ]; then
    WARNINGS="${WARNINGS}  - APPROACHING: $f has $lines lines (limit $limit)\n"
  fi
done

[ -z "$WARNINGS" ] && exit 0

# Stop hooks use top-level fields only (no hookSpecificOutput)
# stderr is shown to user; stdout must be valid hook JSON
echo -e "STATE FILE WARNING:\n${WARNINGS}Prune before next session." >&2
jq -n --arg r "State files approaching limits" '{stopReason: $r}'
