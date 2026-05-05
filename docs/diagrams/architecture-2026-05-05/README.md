# architecture-2026-05-05/

Code-verified architecture-diagram artifacts for W6.5 (master @ `28e21b8`).

## Files

| File | Purpose |
|---|---|
| `diagrams.json` | Structured manifest: 8 diagrams with full node lists, smell registries, embed targets, file:line refs |
| `SMELLS.md` | Aggregated smell registry (33 entries: 1 CRITICAL, 6 HIGH, 17 MEDIUM, 8 LOW, 1 INFO) — flat list with severity + file:line + mitigation |
| `images/` | PNG exports of all 8 diagrams (W6.5d, complete) |

## Diagrams

| ID | Topic | PNG | Figma source |
|---|---|---|---|
| A | 11-Stage Pipeline | [`images/A-pipeline.png`](images/A-pipeline.png) | https://www.figma.com/board/CgTUZGxzzNJNySxgf9IfGZ |
| B | Pydantic AI Agent Map | [`images/B-agents.png`](images/B-agents.png) | https://www.figma.com/board/Q0r37xW7CNT9WOY5ksyRAz |
| C | Memory Subsystem | [`images/C-memory.png`](images/C-memory.png) | https://www.figma.com/board/M9ul54PIv4W5h3EBmNbDHe |
| D | Game Engine | [`images/D-game-engine.png`](images/D-game-engine.png) | https://www.figma.com/board/D0Nc1NELEt6slO2ECQzIIk |
| E | Life Simulator | [`images/E-life-simulator.png`](images/E-life-simulator.png) | https://www.figma.com/board/vmYn6BXyL9KXh4bCjyZkum |
| F | Cron + Tasks | [`images/F-cron-tasks.png`](images/F-cron-tasks.png) | https://www.figma.com/board/xCjCjVhtERCFGYEK0eAufk |
| G | UX + Auth Handoff | [`images/G-ux-auth.png`](images/G-ux-auth.png) | https://www.figma.com/board/P9s9PS0yX0K5o3f8617zmm |
| Taxonomy | Doc Estate | [`images/Taxonomy-doc-taxonomy.png`](images/Taxonomy-doc-taxonomy.png) | https://www.figma.com/board/yYL1NJfD1y1wNBdnj0qNcn |

## PNG regeneration

Use `scripts/export-diagrams.sh` (lives at repo root):

### PAT (batch, no interaction)

```bash
export FIGMA_PAT=figd_...   # https://www.figma.com/developers/api#access-tokens
bash scripts/export-diagrams.sh
```

### MCP (interactive)

The Figma plugin MCP issues short-lived tokens. Initial W6.5c attempt observed apparent single-call expiry; W6.5d confirmed bursts succeed once the session is healthy. If a `get_screenshot` returns `token expired`, run `/mcp` to reauth and retry. The script prints a DONE/TODO matrix when run without `FIGMA_PAT`.

## Provenance

- Wave: W6.5 (PR #511) + W6.5b (this PR)
- Verification: pre-render subagent (HARD CAP 8) confirmed file:line citations on master @ `36a5934`. PASS at 90% (1 minor shift, 0 missing).
- Smell collection: distilled from Mermaid node labels authored by code-verifying agent during W6.5; no docs were read.
