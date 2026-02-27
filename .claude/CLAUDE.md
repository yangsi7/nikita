<!-- Budget: <55 instructions always-loaded across root + .claude/CLAUDE.md. Audit quarterly. -->
# Claude Code Toolkit — Nikita Project

## Session Start

1. Review `event-stream.md` and `ROADMAP.md` for current state
2. If task is complex or involves external APIs: research via MCP Ref/WebSearch/Firecrawl before coding
3. Determine next action → execute → log in `event-stream.md`
4. After completing work: update `workbook.md` if critical context learned

## Skills & Commands

**Skills**: `/analyze`, `/bug`, `/e2e-test`, `/prompt`, `/verify`, `/feature`, `/plan`, `/audit`, `/implement`, `/tasks`
**Commands**: `/prime`, `/index`, `/commit`, `/team-agent`, `/gemini`, `/deep-audit`, `/security-audit`, `/roadmap`
**Agents**: `code-analyzer`, `implementation-planner`, `executor-implement-verify`, `workflow-orchestrator`, `tree-of-thought-agent`, `sdd-*-validator`

## Development Workflow

**SDD (Specification-Driven Development)**: `/feature` → auto-chains → `/plan` → `/tasks` → `/audit` → (if PASS) → `/implement`

**SDD Quick** (complexity 1-3): `/sdd quick` → abbreviated spec + TDD + ROADMAP sync (no plan/tasks/audit)

**TDD per story**: Write failing tests → implement minimal code → tests pass → mark task done → next story

**E2E after implementation**: `/e2e-test full` — uses Telegram MCP, Gmail MCP, Supabase MCP, Chrome DevTools MCP

## SDD Enforcement (Non-Negotiable)

1. **ROADMAP first**: Register every spec NNN in ROADMAP.md BEFORE creating spec.md (`/roadmap add NNN name`)
2. **Artifacts required**: spec.md → plan.md → tasks.md → audit-report.md (PASS) must ALL exist before writing implementation code in `nikita/` or `portal/src/`
3. **Validators mandatory**: GATE 2 requires 6 parallel Task(subagent_type="sdd-*-validator") calls. Reading the spec yourself is NOT a substitute for spawning validators.
4. **TDD enforced**: Write failing tests FIRST. Commit tests separately from implementation. Two commits minimum per user story.
5. **State persistence**: Update .sdd/sdd-state.md after every phase transition. Update ROADMAP.md after spec completion.
6. **Agent invocation**: Use Task tool to spawn sdd-coordinator, sdd-*-validator agents. Main context is for orchestration only — delegate validation and research to subagents.

**Spec Lifecycle Rules**:
- Specs are living documents — update when implementation diverges from original plan
- Superseded specs move to `specs/archive/` (don't delete)
- ROADMAP.md is the ONLY place for spec status tracking
- All new specs must be registered in ROADMAP.md first (`/roadmap add NNN name`)

## Review Finding Process

When code reviews or audits reveal misalignments with specs:

1. **Bugs (code doesn't match spec)**: Fix in current PR if small. Create GH issue if complex.
2. **Missing features (spec defines, code omits)**: Create GH issue with `enhancement` label.
3. **Design changes (behavior should differ from spec)**: Create GH issue + new spec via `/feature`.
4. **All findings**: Log in `event-stream.md` with `[REVIEW]` tag and GH issue number.

Format: `gh issue create --title "fix(scope): description" --label "bug" --body "..."`
Reference: Critical Rule #3 — "Fix, track (GitHub issue), or delete — never ignore."

## Documentation Lifecycle

**Session artifacts**: Write to `docs-to-process/{YYYYMMDD}-{type}-{description}.md`
Types: research, analysis, decision, pattern, bug, integration

**Consolidation**: `/streamline-docs` → scan `docs-to-process/` → update `docs/{domain}/` → delete processed files

**Knowledge domains** (in `docs/`): architecture, patterns, decisions, guides, reference

**Archive**: `specs/archive/` — superseded specs with full traceability

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
- After plan/task changes: check for orphaned session plans

## Maintenance

Quarterly: audit CLAUDE.md files for stale counts, dead file paths, and duplicated content. Run `/generate-claude-md` in audit mode.
