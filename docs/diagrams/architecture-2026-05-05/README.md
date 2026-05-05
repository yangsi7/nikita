# architecture-2026-05-05/

Code-verified architecture-diagram artifacts for W6.5 (master @ `28e21b8`).

## Files

| File | Purpose |
|---|---|
| `diagrams.json` | Structured manifest: 8 diagrams with full node lists, smell registries, embed targets, file:line refs |
| `SMELLS.md` | Aggregated smell registry (34 entries: 1 CRITICAL, 6 HIGH, 18 MEDIUM, 8 LOW, 1 INFO) — flat list with severity + file:line + mitigation |
| `images/` | PNG exports of each diagram. **Currently empty** — see "PNG export" below |

## Diagrams

| ID | Topic | Figma URL |
|---|---|---|
| A | 11-Stage Pipeline | https://www.figma.com/board/CgTUZGxzzNJNySxgf9IfGZ |
| B | Pydantic AI Agent Map | https://www.figma.com/board/Q0r37xW7CNT9WOY5ksyRAz |
| C | Memory Subsystem | https://www.figma.com/board/M9ul54PIv4W5h3EBmNbDHe |
| D | Game Engine | https://www.figma.com/board/D0Nc1NELEt6slO2ECQzIIk |
| E | Life Simulator | https://www.figma.com/board/vmYn6BXyL9KXh4bCjyZkum |
| F | Cron + Tasks | https://www.figma.com/board/xCjCjVhtERCFGYEK0eAufk |
| G | UX + Auth Handoff | https://www.figma.com/board/P9s9PS0yX0K5o3f8617zmm |
| Taxonomy | Doc Estate | https://www.figma.com/board/yYL1NJfD1y1wNBdnj0qNcn |

## PNG export

The Figma plugin MCP (`plugin:figma:figma`) returned `token expired` for `get_screenshot` calls in this session despite `whoami` succeeding moments earlier. PAT-based REST API is not configured on this dev box.

To regenerate PNGs once Figma MCP is reauthed:

```bash
# Each call writes images/{ID}.png
bash scripts/export-diagrams.sh
```

The script reads `diagrams.json`, calls `mcp__plugin_figma_figma__get_screenshot` for each `file_key` with `nodeId="0:1"`, and `curl`s the returned short-lived URL into `images/`.

Alternatively (PAT path), set `FIGMA_PAT` and run:

```bash
for KEY in $(jq -r '.diagrams[].file_key' diagrams.json); do
  curl -s -H "X-Figma-Token: $FIGMA_PAT" \
    "https://api.figma.com/v1/images/$KEY?ids=0:1&format=png&scale=2" \
    | jq -r '.images["0:1"]' \
    | xargs curl -o "images/$KEY.png"
done
```

## Provenance

- Wave: W6.5 (PR #511) + W6.5b (this PR)
- Verification: pre-render subagent (HARD CAP 8) confirmed file:line citations on master @ `36a5934`. PASS at 90% (1 minor shift, 0 missing).
- Smell collection: distilled from Mermaid node labels authored by code-verifying agent during W6.5; no docs were read.
