<!-- Budget: <55 instructions always-loaded across root + .claude/CLAUDE.md. Audit quarterly. -->
# Claude Code Toolkit — Nikita Project

## Session Start

1. Review `event-stream.md` and `todos/master-todo.md` for current state
2. If task is complex or involves external APIs: research via MCP Ref/WebSearch/Firecrawl before coding
3. Determine next action → execute → log in `event-stream.md`
4. After completing work: mark tasks done in `todos/master-todo.md`, update `workbook.md` if critical context learned

## Skills & Commands

**Skills**: `/analyze`, `/bug`, `/e2e-test`, `/prompt`, `/verify`, `/feature`, `/plan`, `/audit`, `/implement`, `/tasks`
**Commands**: `/prime`, `/index`, `/commit`, `/team-agent`, `/gemini`, `/deep-audit`, `/security-audit`
**Agents**: `code-analyzer`, `implementation-planner`, `executor-implement-verify`, `workflow-orchestrator`, `tree-of-thought-agent`, `sdd-*-validator`

## Development Workflow

**SDD (Specification-Driven Development)**: `/feature` → auto-chains → `/plan` → `/tasks` → `/audit` → (if PASS) → `/implement`

**TDD per story**: Write failing tests → implement minimal code → tests pass → mark task done → next story

**E2E after implementation**: `/e2e-test full` — uses Telegram MCP, Gmail MCP, Supabase MCP, Chrome DevTools MCP

## Documentation Lifecycle

**Session artifacts**: Write to `docs-to-process/{YYYYMMDD}-{type}-{description}.md`
Types: research, analysis, decision, pattern, bug, integration

**Consolidation**: `/streamline-docs` → scan `docs-to-process/` → update `docs/{domain}/` → delete processed files

**Knowledge domains** (in `docs/`): architecture, patterns, decisions, guides, reference

**Living docs** (in `memory/`): architecture.md, backend.md, game-mechanics.md, user-journeys.md, integrations.md

## Orchestration Rules

- **Parallel agents for noisy tasks**: Delegate documentation reading, code exploration, screenshot analysis to subagents. Main context is precious.
- **Subagents vs teams**: Default to subagents (Task tool). Use teams (TeamCreate) only when agents must share findings and build on each other's work.
- **Repository hygiene**: No empty directories, no placeholder files, no floating docs in root. Archive quality content, delete duplicates.
- **File size enforcement**: Check `wc -l` on state files before session end. Prune if over limits (see root CLAUDE.md State Files table).
- **Documentation rules**: ONE authoritative file per topic in `docs/` (REPLACE, don't append). Max 500 lines per doc file.

## Gotchas

- Neo4j/Graphiti is legacy — all memory is SupabaseMemory (pgVector via Spec 042)
- Tests use async mocks — see `tests/conftest.py` for patterns
- ElevenLabs agent IDs are per-environment (dev vs prod)
- `--allow-unauthenticated` on Cloud Run is intentional (app-layer JWT auth)
- After plan/task changes: update `todos/master-todo.md`, check for orphaned session plans

## Maintenance

Quarterly: audit CLAUDE.md files for stale counts, dead file paths, and duplicated content. Run `/generate-claude-md` in audit mode.
