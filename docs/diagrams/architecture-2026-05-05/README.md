# architecture-2026-05-05/

Code-verified architecture-diagram artifacts for W6.5 (master @ `28e21b8`).

## Files

| File | Purpose |
|---|---|
| `diagrams.json` | Structured manifest: 8 diagrams with full node lists, smell registries, embed targets, file:line refs |
| `SMELLS.md` | Aggregated smell registry (33 entries: 1 CRITICAL, 6 HIGH, 17 MEDIUM, 8 LOW, 1 INFO) — flat list with severity + file:line + mitigation |
| `images/` | PNG exports of each diagram. **Diagram A landed (W6.5c); B-G + Taxonomy pending** — see "PNG export" below |

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

**Status (2026-05-05)**: Figma plugin MCP (`plugin:figma:figma`) token TTL is single-call. After every `get_screenshot`, the next call returns `token expired` until the user runs `/mcp` to reauth. Cannot loop autonomously.

W6.5c landed Diagram A (`A-pipeline.png`, 411x1024 PNG). Remaining 7 are TODO.

### Recommended (PAT, batch)

One-time setup: https://www.figma.com/developers/api#access-tokens

```bash
export FIGMA_PAT=figd_...
bash scripts/export-diagrams.sh    # exports all 8 in one shot
```

### Fallback (MCP, interactive)

For each TODO diagram:
1. `/mcp` to reauth Figma
2. Call `mcp__plugin_figma_figma__get_screenshot` with the `file_key` from `diagrams.json`, `nodeId="0:1"`
3. `curl -o images/{ID}-{slug}.png <returned image_url>`

Run `bash scripts/export-diagrams.sh` (no PAT) to print the live TODO/DONE matrix.

## Provenance

- Wave: W6.5 (PR #511) + W6.5b (this PR)
- Verification: pre-render subagent (HARD CAP 8) confirmed file:line citations on master @ `36a5934`. PASS at 90% (1 minor shift, 0 missing).
- Smell collection: distilled from Mermaid node labels authored by code-verifying agent during W6.5; no docs were read.
