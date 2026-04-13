# Claude Code Toolkit — Nikita Project

## Session Start

1. Review `event-stream.md` and `ROADMAP.md` for current state
2. If task is complex or involves external APIs: research via MCP Ref/WebSearch/Firecrawl before coding
3. For multi-step workflows (audits, reviews, batch fixes): present the plan and wait for approval before executing. Do NOT jump to commands eagerly.
4. Determine next action → execute → log in `event-stream.md`
5. After completing work: update `workbook.md` if critical context learned

## Skills & Commands

**Skills**: `/analyze`, `/bug`, `/e2e`, `/prompt`, `/verify`, `/feature`, `/plan`, `/audit`, `/implement`, `/tasks`
**Commands**: `/prime`, `/index`, `/project-intel`, `/commit`, `/team-agent`, `/gemini`, `/deep-audit`, `/security-audit`, `/roadmap`
**Agents**: `code-analyzer`, `implementation-planner`, `executor-implement-verify`, `workflow-orchestrator`, `tree-of-thought-agent`, `sdd-*-validator`

## Development Workflow

**SDD (Specification-Driven Development)**: `/feature` → auto-chains → `/plan` → `/tasks` → `/audit` → (if PASS) → `/implement`

**SDD Quick** (complexity 1-3): `/sdd quick` → abbreviated spec + TDD + ROADMAP sync (no plan/tasks/audit)

**TDD per story**: Write failing tests → implement minimal code → tests pass → mark task done → next story

**E2E after implementation**: `/e2e full` — 13 epics, 363 scenarios via Telegram MCP, Gmail MCP, Supabase MCP, Chrome DevTools MCP

## Sprint Workflow (Multi-Issue Batches)

When working on multiple issues in parallel:
1. **Plan**: Create plan with issue-to-branch mapping (one branch per issue or logical group)
2. **Implement**: Launch worktree agents — each creates branch + commits
3. **PR per branch**: After agent completes, create PR via `gh pr create` from the branch
4. **QA gate per PR**: Run `/qa-review --pr N` on each PR — fix → fresh review loop until 0 findings across ALL severities
5. **Merge sequentially**: Squash merge PRs one at a time, running tests between each
6. **Close issues**: Reference PR in issue close comment

**Agent worktree rules**:
- Agents commit to their worktree branch (never to master)
- Main orchestrator creates PRs from agent branches
- PRs must pass `/qa-review` before merge
- If agent output is unsatisfactory, request fixes via SendMessage before creating PR
- See `.claude/rules/parallel-agents.md` for worktree verification + batch checkpointing

## Code Intelligence (`/project-intel`)

Queries PROJECT_INDEX.json (988 files indexed, 17ms jq). Refresh with `/index` when stale.
**Pattern: project-intel first → narrow scope → Read/Grep/Glob only identified files.**

| When | Command |
|------|---------|
| Session start / context recovery | `orient` |
| Before editing a file | `briefing <file>` |
| File imports + reverse-imports | `deps <file>` |
| Full blast radius of a change | `impact <file>` |
| Who calls function X | `callers <fn>` |
| Map module files, tests, wiring | `subsystem <name>` |
| Architecture / directory structure | `map` or `focus <dir>` |
| Find files, symbols, or docs | `search <term>` or `investigate <terms>` |
| Debug call chain (callers + callees) | `debug <fn\|file>` |
| Test coverage gaps | `test-map <module>` |
| Merge conflict / hotspot risk | `hotspots` |
| Unused exports | `dead` |

## SDD Enforcement (Non-Negotiable)

1. **ROADMAP first**: Register every spec NNN in ROADMAP.md BEFORE creating spec.md (`/roadmap add NNN name`)
2. **Artifacts required**: spec.md → plan.md → tasks.md → audit-report.md (PASS) must ALL exist before writing implementation code in `nikita/` or `portal/src/`
3. **Validators mandatory**: GATE 2 requires 6 parallel Task(subagent_type="sdd-*-validator") calls. Reading the spec yourself is NOT a substitute for spawning validators.
4. **TDD enforced**: Write failing tests FIRST. Commit tests separately from implementation. Two commits minimum per user story.
5. **State persistence**: Update .sdd/sdd-state.md after every phase transition. Update ROADMAP.md after spec completion.
6. **Agent invocation**: Use Task tool to spawn sdd-coordinator, sdd-*-validator agents. Main context is for orchestration only — delegate validation and research to subagents.
7. **GATE 2 Analyze-Fix Loop**: After 6 validators complete: (a) user reviews validation-reports/, (b) CRITICAL/HIGH → create GH issues + fix spec + re-validate (max 3 iterations), (c) MEDIUM → create GH issue or document as accepted, (d) LOW → log in validation-findings.md, (e) user approves proceeding to Phase 5, (f) gate fails 3x → escalate, NEVER auto-waive.
8. **Validation Findings Manifest**: Each spec gets `specs/NNN-*/validation-findings.md` with GH issue numbers for CRITICAL/HIGH, accept/defer decisions for MEDIUM, and user approval checkbox.
9. **PR mandatory**: Every implementation MUST go through a PR. After `/implement` completes, create PR via `gh pr create`, then run `/qa-review --pr N`. Merge only after a fresh review returns 0 findings across ALL severities (including nitpicks).
10. **`/implement` mandatory**: After `/audit` GATE 2 passes, invoke `/implement` skill formally to orchestrate TDD implementation. Do NOT bypass by dispatching implementor subagents directly — the skill provides guardrails that raw prompts miss.

**Spec Lifecycle Rules**:
- Specs are living documents — update when implementation diverges from original plan
- Superseded specs move to `specs/archive/` (don't delete)
- ROADMAP.md is the ONLY place for spec status tracking
- All new specs must be registered in ROADMAP.md first (`/roadmap add NNN name`)

## Review & Triage

See `.claude/rules/review-findings.md` and `.claude/rules/issue-triage.md` for review finding handling and issue severity classification.

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
- **Auto-dispatch mandatory steps**: Workflow steps the rules already mandate — `/qa-review`, post-merge smoke tests, deployment verification, `/e2e`/dogfood runs, live HTTP probes, log-sweep verifications — must auto-dispatch to a fresh subagent. Do NOT ask the user for permission to run them; they are already authorized by the workflow. Two reasons: (a) keeps the noisy review/test transcript out of main context, (b) eliminates confirmation bias by getting fresh-context analysis. Spawn via `Agent` tool with a self-contained prompt that includes target PR/branch, success criteria, and the report shape expected back.
- **Sub-agent anti-loop**: See `.claude/rules/parallel-agents.md` for execution constraints.
- **Repository hygiene**: No empty directories, no placeholder files, no floating docs in root. Archive quality content, delete duplicates.
- **File size enforcement**: Check `wc -l` on state files before session end. Prune if over limits (see root CLAUDE.md State Files table).
- **Documentation rules**: ONE authoritative file per topic in `docs/` (REPLACE, don't append). Max 500 lines per doc file.

## Gotchas

- Neo4j/Graphiti is legacy — all memory is SupabaseMemory (pgVector via Spec 042)
- Tests use async mocks — see `tests/conftest.py` for patterns; E2E tests have separate patterns in `tests/e2e/conftest.py` (ASGI transport, webhook simulator, no-op cleanup fixtures)
- ElevenLabs agent IDs are per-environment (dev vs prod); `config/elevenlabs.py` was DELETED in PR #231 (dead multi-agent code)
- `--allow-unauthenticated` on Cloud Run is intentional (app-layer JWT auth)
- pg_cron jobs use `net.http_post` with hardcoded Bearer token — if TASK_AUTH_SECRET changes, ALL 6 HTTP cron jobs must be updated via `cron.alter_job()`
- After plan/task changes: check for orphaned session plans
- Telegram MCP session expires — re-run `session_string_generator.py` in `../telegram-mcp/` if all Telegram MCP calls fail
- E2E testing: Use `/e2e` skill (NOT the archived `/e2e-test` or `/e2e-journey`). Covers 13 epics, 363 scenarios with realistic conversation simulation, portal monitoring, and time manipulation.
- Worktree agents cross-contaminate branches — see `.claude/rules/parallel-agents.md`

## Maintenance

Quarterly: audit CLAUDE.md files for stale counts, dead file paths, and duplicated content. Run `/generate-claude-md` in audit mode.
