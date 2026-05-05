#!/usr/bin/env bash
# Export W6.5 architecture diagrams as PNGs.
#
# Two paths:
#   1. Figma PAT (preferred, batch, no reauth):
#        FIGMA_PAT=figd_xxx bash scripts/export-diagrams.sh
#   2. Figma MCP plugin (interactive, single call per /mcp reauth):
#        See "MCP path" section below.
#
# Output: docs/diagrams/architecture-2026-05-05/images/{ID}-{slug}.png

set -euo pipefail

OUTDIR="docs/diagrams/architecture-2026-05-05/images"
mkdir -p "$OUTDIR"

# Diagram registry: id|file_key|slug
DIAGRAMS=(
  "A|CgTUZGxzzNJNySxgf9IfGZ|pipeline"
  "B|Q0r37xW7CNT9WOY5ksyRAz|agents"
  "C|M9ul54PIv4W5h3EBmNbDHe|memory"
  "D|D0Nc1NELEt6slO2ECQzIIk|game-engine"
  "E|vmYn6BXyL9KXh4bCjyZkum|life-simulator"
  "F|xCjCjVhtERCFGYEK0eAufk|cron-tasks"
  "G|P9s9PS0yX0K5o3f8617zmm|ux-auth"
  "Taxonomy|yYL1NJfD1y1wNBdnj0qNcn|doc-taxonomy"
)

if [[ -n "${FIGMA_PAT:-}" ]]; then
  echo "PAT path: batch via Figma REST API"
  for entry in "${DIAGRAMS[@]}"; do
    IFS='|' read -r id key slug <<< "$entry"
    out="$OUTDIR/${id}-${slug}.png"
    echo "Exporting $id ($slug) -> $out"
    img_url=$(curl -s -H "X-Figma-Token: $FIGMA_PAT" \
      "https://api.figma.com/v1/images/$key?ids=0:1&format=png&scale=2" \
      | jq -r '.images["0:1"]')
    if [[ -z "$img_url" || "$img_url" == "null" ]]; then
      echo "  FAILED: no image URL returned for $key" >&2
      continue
    fi
    curl -sL -o "$out" "$img_url"
    file "$out"
  done
  echo "Done. PAT path complete."
else
  echo "No FIGMA_PAT in env."
  echo
  echo "MCP path (interactive): the figma plugin MCP token expires after 1 screenshot."
  echo "Run /mcp in Claude Code between each diagram."
  echo
  echo "For each (id, file_key) pair below, in Claude Code:"
  echo "  1. /mcp                                            # reauth Figma"
  echo "  2. mcp__plugin_figma_figma__get_screenshot         # call with fileKey + nodeId=0:1"
  echo "  3. curl -o <out> <returned image_url>              # save PNG"
  echo
  for entry in "${DIAGRAMS[@]}"; do
    IFS='|' read -r id key slug <<< "$entry"
    out="$OUTDIR/${id}-${slug}.png"
    if [[ -f "$out" ]]; then
      echo "  [DONE] $id $key -> $out"
    else
      echo "  [TODO] $id $key -> $out"
    fi
  done
  echo
  echo "PAT setup (one-time): https://www.figma.com/developers/api#access-tokens"
  echo "  export FIGMA_PAT=figd_..."
  echo "  bash scripts/export-diagrams.sh"
  exit 1
fi
