# CLAUDE.md

This file provides orchestration guidance to Claude Code when working in this repository.

---

## Core Constraints

1. **Event Logging**: Log all tool calls, agent invocations, skill activations, decisions, and observations in `event-stream.md` chronologically
2. **Planning**: Maintain `plans/master-plan.md` for high-level strategy; track tasks in `todos/master-todo.md`
3. **State Management**: Keep `todos/master-todo.md` (≤400 lines), `event-stream.md` (≤40 lines), `workbook.md` (≤300 lines) up-to-date; prune aggressively
4. **Context Engineering**: Use `workbook.md` for critical context, insights, anti-patterns, and short-term planning
5. **Documentation Lifecycle**: Write session artifacts to `docs-to-process/{timestamp}-{session-id}-{type}.md`, consolidate to `docs/{domain}/` via `/streamline-docs`, update CLAUDE.md for high-impact rules
6. **No Over-Engineering**: Implement ONLY what user requested; no invented features
7. **No Hallucination**: Research via MCP tools (Ref, Firecrawl) when uncertain; never guess
8. **Documentation-First Integration (STRICTLY ENFORCED)**:
   - **CRITICAL**: Training data is outdated - libraries change constantly
   - **BEFORE** implementing ANY external library/API integration: ALWAYS use MCP Ref tool to fetch latest official documentation
   - **NEVER** implement based on assumptions, training data, or what "seems to make sense"
   - **VERIFY** API signatures, parameters, patterns, and behavior against current docs
   - **RATIONALE**: Arrogant implementation without verification is the WORST failure mode - it creates technical debt, bugs, and wasted time
   - **Example**: Supabase Python client → `mcp__Ref__ref_search_documentation` query "Supabase Python sign_in_with_otp" → read official docs → THEN implement
   - **Zero tolerance** for hallucinations and unverified implementations
9. **rg, fd, jq**:
   - Use `rg` (ripgrep) instead of `grep`
   - Use `fd` instead of `find`
   - Use `jq` for JSON parsing
   - Limit output to prevent context overflow

---


## Start
Before performing any action first:
1. **Analyze Events:** Review @event-stream.md, @todos/master-todo.md to understand the user's request and the current state. Focus especially on the latest user instructions and any recent results or errors. If they are not up to date, update them.
2. **System Understanding:** If the task is complex or involves system design and/or system architecture, invoke the System Understanding Module to deeply analyze the problem. Identify key entities and their relationships, and construct a high-level outline or diagram of the solution approach. Use this understanding to inform subsequent planning.
3. **Research External Libraries (MANDATORY):** If implementing integration with external libraries/APIs (Telegram Bot API, Supabase, ElevenLabs, etc.), **STOP** and use MCP Ref tool to fetch official documentation BEFORE writing ANY code. **DO NOT TRUST TRAINING DATA** - it's outdated. Examples:
   - Telegram: `mcp__Ref__ref_search_documentation` → "Telegram Bot API sendMessage"
   - Supabase: `mcp__Ref__ref_search_documentation` → "Supabase Python sign_in_with_otp options"
   - Read returned docs fully, verify parameter names/types match current API
4. **Determine the next action to take.** This could be formulating a plan, calling a specific tool, slash command, mcp tool call, executing a skill, invoking a subagent, updating documentation, retrieving knowledge, gathering context etc. Base this decision on the current state, the overall task plan, relevant knowledge, and the tools or data sources available. Execute the chosen action. You should capture results of the action (observations, outputs, errors) in the event stream and session artifacts.
5. **Execute**
6. **Log & Maintain:**
   - Log the action in @event-stream.md
   - If a task is completed, mark it as done in @todos/master-todo.md
   - If you learned critical context, log it in @workbook.md
   - **CHECK FILE SIZES** after every significant update (see Session File Maintenance below)
   - Update Document Index when creating new research outputs
7. **Iterate**

## Repository Hygiene

1. **No Empty Directories**: Create directories ONLY when you have actual content
2. **No Useless Files**: No placeholder files, empty READMEs, or "coming soon" docs
3. **Quality Over Quantity**: Archive superior content, delete inferior duplicates
4. **No Random Floating Files**: No `temp.md`, `notes.md`, `scratch.md` littering the repo
5. **Clean Up After Yourself**: Delete temporary files/directories at session end if no permanent purpose
6. **Respect Existing Quality**: Check for better documentation before recreating

---

## State File Size Limits

**Purpose**: Prevent context pollution from bloated state files

**Limits**:

| File | Max Lines | Purpose | Maintenance |
|------|-----------|---------|-------------|
| `todos/master-todo.md` | 400 | Project task tracking | Reference spec tasks, prune completed |
| `plans/master-plan.md` | 1500 | Technical architecture | Link to spec plans, prune completed phases |
| `event-stream.md` | 40 | Last 35 events | Auto-trim at session start |
| `workbook.md` | 300 | Active context | Extract to docs/ or delete old context |

---

## Documentation Rules

### Directory Structure

**Root files** (allowed at project root):

| File | Max Lines | Required | Purpose |
|------|-----------|----------|---------|
| `CLAUDE.md` | 600 | Yes | Orchestration rules |
| `README.md` | 300 | Yes | Project overview |
| `workbook.md` | 300 | Optional | Session context |
| `event-stream.md` | 40 | Optional | Session log |
| `PROJECT_INDEX.json` | - | Optional | Codebase intelligence |

**Planning files** (in `plans/` and `todos/`):

| File | Max Lines | Purpose |
|------|-----------|---------|
| `plans/master-plan.md` | 1500 | Technical architecture, references spec plans |
| `todos/master-todo.md` | 400 | Project task tracking, references spec tasks |
| `specs/NNN-feature/plan.md` | 500 | Feature-specific implementation plan |
| `specs/NNN-feature/tasks.md` | 300 | Feature-specific tasks with ACs |

**docs-to-process/** (staging area):
- **Purpose**: Raw session artifacts before consolidation
- **Naming**: `{YYYYMMDD}-{type}-{4char-id}.md`
- **Types**: `research`, `analysis`, `decision`, `pattern`, `bug`, `integration`
- **Max size**: 300 lines per file
- **Lifecycle**: Created → processed by `/streamline-docs` → DELETED
- **Example**: `20251126-research-a3f2.md`, `20251126-decision-b8c1.md`

**docs/** (curated knowledge - 5 domains):
- **Structure**: `architecture/`, `patterns/`, `decisions/`, `guides/`, `reference/`
- **Principle**: ONE authoritative file per topic (REPLACE entirely, never append)
- **Max size**: 500 lines per file
- **Index**: `docs/README.md` provides navigation (≤200 lines)
- **Tracking**: `docs/CHANGELOG.md` logs all changes

**specs/** (future state):
- **Purpose**: Implementation specifications (NOT current state)
- **Lifecycle**: Created → implemented → archived or deleted

### Creating Session Artifacts

**When to create**:
- External research performed (MCP tools: Ref, Firecrawl)
- Internal analysis completed (code-analyzer agent)
- Architecture decisions made
- Patterns discovered during implementation

**Naming convention**: `{YYYYMMDD}-{type}-{4char-id}.md`
- Types: `research`, `analysis`, `decision`, `pattern`, `bug`, `integration`
- Example: `20251126-research-a3f2.md`, `20251126-decision-b8c1.md`

### Consolidation Process (via /streamline-docs)

1. **Scan** `docs-to-process/` for unprocessed artifacts
2. **Analyze** each artifact for valuable insights
3. **Update** `docs/{domain}/` files (REPLACE entirely, not append)
4. **Log** changes in `docs/CHANGELOG.md`
5. **Extract** high-impact rules → add to CLAUDE.md
6. **Delete** processed files from `docs-to-process/`
7. **Verify** no random docs in root (cleanup floating files)
8. **Enforce** size limits (prune aggressively if exceeded)

### Size Enforcement

**Before session end**, verify:
```bash
wc -l CLAUDE.md README.md workbook.md event-stream.md plans/master-plan.md todos/master-todo.md
```

**Limits**:
- CLAUDE.md ≤ 600, README.md ≤ 300, workbook.md ≤ 300, event-stream.md ≤ 40
- plans/master-plan.md ≤ 1500, todos/master-todo.md ≤ 400
- specs/NNN/plan.md ≤ 500, specs/NNN/tasks.md ≤ 300

### Prohibited Practices

- **No floating docs**: Only allowed root files: CLAUDE.md, README.md, workbook.md, event-stream.md
- **No duplication**: One source per topic (REPLACE, don't append)
- **No exceeding limits**: Prune or extract before committing
- **No stale artifacts**: Process docs-to-process/ regularly via `/streamline-docs`
- **No placeholders**: Empty "coming soon" files forbidden

---

## Start: Orchestration-Aware React Loop

**Main execution loop integrating agents, skills, and state management.**

### Flow

```
1. STATE ANALYSIS → Read event-stream.md, todos/master-todo.md, workbook.md
2. COMPLEXITY ASSESSMENT → Simple/Moderate/Complex
3. SYSTEM UNDERSTANDING → Use agents (code-analyzer, prompt-researcher)
4. PLANNING → Use skills (brainstorming, writing-plans)
5. EXECUTION → Tool calls + Agent invocations
6. STATE UPDATE → Log events, update tasks, prune if needed
7. ITERATE → Return to Step 1
```

## Session File Maintenance Protocol

Check and maintain file sizes after every major task completion.

### Automatic Maintenance Triggers

Run `wc -l event-stream.md workbook.md plans/master-plan.md todos/master-todo.md` when:
1. Creating new research documents
2. Completing any Phase/task
3. Before ending session
4. Every 5-10 tool calls

### Pruning Rules by File

**todos/master-todo.md** (400 line limit):
- Mark completed phases with ✅ and collapse to summaries
- Keep only current phase tasks in detail
- Reference spec tasks with links: `See specs/NNN-feature/tasks.md`
- Remove completed maintenance tasks

**plans/master-plan.md** (1500 line limit):
- Keep current architecture and active phases
- Reference spec plans: `See specs/NNN-feature/plan.md`
- Move completed phase details to `memory/` docs
- Prune superseded architecture decisions

**event-stream.md** (40 line limit):
- Keep header (3 lines) + last 35 events ONLY
- Delete oldest events when exceeding 38 events
- Priority: Keep errors, decisions, phase completions

**workbook.md** (300 line limit):
- Extract permanent insights to research documents
- Delete superseded context (old numbers, outdated priorities)
- Keep only current phase context
- Remove resolved anti-patterns

### When Files Exceed Limits

**IMMEDIATE ACTION REQUIRED**:
```bash
# 1. Check sizes
wc -l event-stream.md workbook.md plans/master-plan.md todos/master-todo.md

# 2. If todos/master-todo.md > 400: Collapse completed phases, reference specs
# 3. If plans/master-plan.md > 1500: Extract to memory/, reference specs
# 4. If event-stream.md > 40: Keep last 35 events only
# 5. If workbook.md > 300: Extract to docs/, delete outdated context
```

---

## CLAUDE.md Self-Improvement Protocol

**Continuous Refinement**: This file should evolve based on learnings.

### When to Update Project Description

Update **## Project Overview** section when:
1. **Strategic pivot identified** (e.g., ESG-first positioning discovery)
2. **New critical data discovered** (e.g., analyzed CSV reveals unexpected patterns)
3. **Key assumptions validated/invalidated** (e.g., competitor landscape different than expected)
4. **Major milestone reached** (e.g., Phase 1 complete, moving to implementation)
5. **User provides new context** that changes project understanding

### How to Self-Improve CLAUDE.md

**ADD** new sections when:
- Discovering repeating patterns requiring standard protocol
- Finding gaps in current instructions causing errors
- User feedback indicates confusion or misalignment

**UPDATE** existing sections when:
- Instructions proven incomplete through execution
- Better practices discovered during work
- Context has evolved (e.g., from research → implementation phase)

**REMOVE** sections when:
- No longer applicable (phase-specific instructions after phase ends)
- Superseded by better approach
- Redundant with other sections


---

## Project Overview

**Nikita: Don't Get Dumped** - AI girlfriend simulation game with dual-agent architecture (voice + text), temporal knowledge graphs, and sophisticated game mechanics.

**Status**: Phase 2 ✅ COMPLETE, Phase 3 ✅ MOSTLY COMPLETE (Game engine, 4 remaining: chapters, vice, voice, security)

**Streamlined Architecture** (Dec 2025):
- **Compute**: Google Cloud Run (serverless, scales to zero) - DEPLOYED
- **Voice**: ElevenLabs Conversational AI 2.0 (Server Tools pattern - REST only)
- **Text**: Pydantic AI + Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)
- **Memory**: Graphiti (3 temporal knowledge graphs) + **Neo4j Aura** (free tier, managed)
- **Database**: Supabase (PostgreSQL + pgVector + RLS)
- **Scheduling**: pg_cron + Cloud Run task endpoints (no Celery/Redis)
- **Platforms**: Telegram (@Nikita_my_bot) + Voice calls (future) + Portal (Next.js on Vercel)
- **Game Engine**: Scoring (4 metrics), chapters (1-5), boss encounters (55-75%), hourly decay

**Cost**: $35-65/mo (usage-based, can scale to near-free)

---

## GCP Deployment (CRITICAL)

**DO NOT USE `nikita-prod-446401`** - that project doesn't exist or has no permissions.

**Correct GCP Configuration:**
```bash
gcloud config set account simon.yang.ch@gmail.com
gcloud config set project gcp-transcribe-test
```

| Resource | Value |
|----------|-------|
| **GCP Project** | `gcp-transcribe-test` |
| **GCP Account** | `simon.yang.ch@gmail.com` |
| **Cloud Run Service** | `nikita-api` |
| **Region** | `us-central1` |
| **Backend URL** | `https://nikita-api-1040094048579.us-central1.run.app` |
| **Legacy URL** | `https://nikita-api-7xw52ajcea-uc.a.run.app` (auto-redirects) |

**Deploy Command:**
```bash
gcloud run deploy nikita-api --source . --region us-central1 --project gcp-transcribe-test --allow-unauthenticated
```

---

## Git Workflow

### Branch Strategy: GitHub Flow
- `main` is always deployable
- Feature branches for all changes
- PRs required for all merges to main

### Branch Naming
```
{type}/{spec-number}-{description}
```
Types: `feature/`, `fix/`, `refactor/`, `docs/`, `chore/`, `spike/`

### Commit Format: Conventional Commits
```
type(scope): description

[body - what and why, not how]
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`
**Scopes**: `api`, `portal`, `engine`, `db`, `auth`, `telegram`, `admin`, `sdd`

**Rules**:
- Subject ≤ 50 chars, imperative mood, no period
- One logical change per commit (atomic)
- Body wraps at 72 chars

### Pull Requests
- Size: <400 lines ideal, <1000 max
- Title: conventional commit format
- Self-review before requesting review
- Squash merge to main

### Merge Strategy
- **Default**: Squash merge (clean main history)
- **Exception**: Regular merge for multi-contributor PRs
- **Never**: Force push to main

### Examples
```bash
# Good commits
feat(portal): add score history chart
fix(api): handle null user in auth middleware
docs(specs): update 008-player-portal tasks
chore(deps): upgrade pydantic to v2.5

# Good branch names
feature/008-player-portal
fix/015-onboarding-telegram
refactor/cleanup-auth-flow
```

---

## Comprehensive Development Workflow

### The 5-Stage Process

```
STAGE 1: DISCOVERY     → discovery-driven-planning skill
STAGE 2: SPECIFICATION → /feature → /plan → /audit (auto-chain)
STAGE 3: IMPLEMENTATION → /implement (TDD per story)
STAGE 4: E2E VERIFICATION → /e2e-test (MANDATORY)
STAGE 5: DOCUMENTATION SYNC → Update memory/, event-stream, master files
```

### Stage 1: Discovery-Driven Planning

**Invoke**: `discovery-driven-planning` skill for non-trivial implementations.

Creates 5 artifacts:
- `requirements.md` - Structured requirements
- `RESEARCH.md` - Parallel research findings
- `SYSTEM-UNDERSTANDING.md` - Knowledge graph
- `GAP-ANALYSIS.md` - Known vs unknown matrix
- `IMPLEMENTATION-PLAN.md` - Actionable tasks

### Stage 2: SDD Specification

**Commands → Skills**:
- `/feature` → `specify-feature` skill → `specs/NNN/spec.md`
- `/plan` → `create-implementation-plan` skill → `specs/NNN/plan.md`
- `/tasks` → `generate-tasks` skill → `specs/NNN/tasks.md`
- `/audit` → audit command → `specs/NNN/audit-report.md`

**Auto-chains**: `/feature` → `/plan` → `/tasks` → `/audit` (if PASS → ready for /implement)

### Stage 3: Implementation

**Command**: `/implement plan.md` → `implement-and-verify` skill

Per-story TDD cycle:
1. Write failing tests from ACs
2. Implement minimal code
3. Tests pass → mark task complete in tasks.md
4. Commit with conventional format
5. Repeat for next story

### Stage 4: E2E Verification (MANDATORY)

**Command**: `/e2e-test [scope]` → `e2e-test-automation` skill

| Scope | Tests | MCP Tools |
|-------|-------|-----------|
| `full` | All systems | Telegram, Gmail, Supabase, Chrome, gcloud |
| `telegram` | Bot interactions | Telegram MCP, Supabase MCP |
| `portal` | Web portal | Chrome DevTools MCP |
| `otp` | Auth flow | Gmail MCP, Supabase MCP |

**CRITICAL**: Run `/e2e-test full` after every `/implement` completion.

### Stage 5: Documentation Sync

After implementation + E2E pass:
1. Update `todos/master-todo.md` - Mark tasks complete
2. Update `plans/master-plan.md` - If architecture changed
3. Update `memory/*.md` - If domain knowledge changed
4. Update `event-stream.md` - Log key events
5. Commit and push

---

**Specifications** (14 specs with complete SDD artifacts):
- **specs/001-014/**: Each has spec.md, plan.md, tasks.md, audit-report.md
- **Critical path**: 013 (Config) → 014 (Engagement) → 012 (Context) → Game Engine
- **Security issues**: Webhook validation (CRITICAL), rate limiting (HIGH)

**Key Files**:
- `nikita/config/settings.py`: All environment settings
- `nikita/engine/constants.py`: Game constants (chapters, thresholds 55-75%, decay 0.8-0.2/hr)
- `nikita/memory/graphiti_client.py`: NikitaMemory class (3 graphs)
- `nikita/db/models/user.py`: User, UserMetrics, UserVicePreference
- `nikita/agents/text/agent.py`: Pydantic AI text agent (156 tests)
- `nikita/platforms/telegram/`: 7 files, 74 tests (message handling, auth, rate limiting)

**Documentation**:
- **memory/**: Living docs (architecture, backend, game-mechanics, user-journeys, integrations)
- **plans/master-plan.md**: SDD orchestration plan
- **todos/master-todo.md**: Phase-organized tasks with verification gates
- **specs/**: 14 implementation specifications

**Next Steps**: Security hardening (parallel) + 013 Configuration System


## Planning & Todo Hierarchy

**Master files** are the authoritative source for project-wide planning and task tracking. They reference spec-specific files and Claude Code session plans.

### File Hierarchy

```
plans/
├── master-plan.md          # ← Authoritative project plan
├── {feature}-plan.md       # ← One-off plans (maintenance, hotfixes)
└── (temporary Claude plans go to ~/.claude/plans/)

todos/
└── master-todo.md          # ← Authoritative project task list

specs/
└── NNN-feature/
    ├── spec.md             # Feature specification
    ├── plan.md             # Feature implementation plan
    ├── tasks.md            # Feature tasks with ACs
    └── audit-report.md     # Audit results
```

### Master Files Purpose

| File | Purpose | References |
|------|---------|------------|
| `plans/master-plan.md` | Technical architecture, phase roadmap, deployment config | Spec plans, architecture decisions |
| `todos/master-todo.md` | Phase-organized task tracking, maintenance tasks | Spec tasks, current sprint |

### SDD Workflow Integration

When creating new features via `/feature`:
1. **Spec created** → `specs/NNN-feature/spec.md`
2. **Plan created** → `specs/NNN-feature/plan.md` (auto via /plan)
3. **Tasks created** → `specs/NNN-feature/tasks.md` (auto via /tasks)
4. **Master todo updated** → Add entry referencing the spec

**Master todo entry format:**
```markdown
### Spec 015: Onboarding Fix
- Status: In Progress
- Spec: [specs/015-onboarding-fix/spec.md](specs/015-onboarding-fix/spec.md)
- Plan: [specs/015-onboarding-fix/plan.md](specs/015-onboarding-fix/plan.md)
- Tasks: [specs/015-onboarding-fix/tasks.md](specs/015-onboarding-fix/tasks.md)
- Progress: 5/8 tasks complete
```

### Claude Code Session Plans

When Claude Code enters plan mode:
1. Temporary plan created at `~/.claude/plans/{random-name}.md`
2. **After approval:**
   - If SDD feature: integrate into `specs/NNN-feature/plan.md`
   - If architecture change: update `plans/master-plan.md`
   - If maintenance: add to `plans/{topic}-plan.md` or directly to master
3. Delete temporary plan from `~/.claude/plans/`

**Check for orphaned session plans:** `ls -la ~/.claude/plans/*.md | tail -5`

### Maintenance Tasks

Non-SDD tasks (bug fixes, refactoring, infrastructure) go directly in `todos/master-todo.md`:

```markdown
## Maintenance
- [x] Fix OTP validation to accept 6-8 digits
- [ ] Add rate limiting to webhook endpoint
- [ ] Upgrade pydantic to v2.5
```

### Sync Requirements

After ANY plan or task change:
1. Update `plans/master-plan.md` if architecture changed
2. Update `todos/master-todo.md` with progress
3. Mark completed tasks with `[x]` immediately
4. Update spec-specific files if feature-related

### Event Stream Protocol

Maintain `event-stream.md` (max 40 lines) with one line per event:

**Format**: `[TIMESTAMP] EVENT_TYPE: concise description`

**Event Types**: `DEPLOY`, `FIX`, `FEATURE`, `TEST_STATUS`, `SECURITY_FIX`, `CLEANUP`, `ERROR`, `DECISION`

**Example**:
```
[2025-12-21T22:00:00Z] FIX: OTP validation - changed len==6 to 6<=len<=8
[2025-12-21T22:10:00Z] DEPLOY: nikita-api-00088-kj4 with OTP fix
```

---

## Proactive Plan/Todo Maintenance

<plan_todo_sync>
Keep `plans/master-plan.md` and `todos/master-todo.md` in sync with actual implementation state. These are the authoritative project tracking files.

### Session Plans Integration

Claude Code generates session-specific plans at `~/.claude/plans/{random-name}.md` when entering plan mode.

After plan approval:
1. Copy relevant sections to `plans/master-plan.md`
2. Add links to session plans if they contain unique context worth preserving
3. Remove temporary plans from `~/.claude/plans/` after integration

To check recent session plans: `ls -la ~/.claude/plans/*.md | tail -5`

### When to Update

Update the master files when:

| Trigger | plans/master-plan.md | todos/master-todo.md |
|---------|---------------------|---------------------|
| Task completion | - | Mark `[x]`, update progress |
| Architecture decision | Update tech stack, diagrams | - |
| Phase transition | Update phases_complete | Update current_phase |
| New feature planned | Add to relevant phase | Add tasks |
| Spec created/modified | Reference spec | Add spec tasks |
| Session end | Sync from `~/.claude/plans/` | Final task status |

### What to Update

**plans/master-plan.md**:
- Tech stack table (Section 2)
- Deployment architecture diagram (Section 12)
- Architecture decisions (Section 15)
- Phase status in implementation phases (Section 13)
- YAML frontmatter (updated timestamp, session_id, phases_complete)

**todos/master-todo.md**:
- Phase task lists (mark completed tasks with [x])
- Current Sprint section (keep focused on active work)
- YAML frontmatter (updated timestamp, session_id, current_phase)

### Post-Session Sync Protocol

Before ending an implementation session:
1. Check for session plans: `ls -la ~/.claude/plans/*.md | tail -5`
2. Extract architecture decisions to `plans/master-plan.md`
3. Mark completed tasks in `todos/master-todo.md`
4. Update YAML frontmatter timestamps
5. Delete integrated session plans from `~/.claude/plans/`

### Patterns to Avoid

- Leaving session plans orphaned in `~/.claude/plans/`
- Letting plan/todo drift from actual code state
- Leaving tasks unchecked when they're actually complete
- Forgetting to update YAML frontmatter timestamps
- Allowing implementation to diverge from documented plan
</plan_todo_sync>

---

## Documentation Navigation

**For detailed architecture, mechanics, and patterns, see:**

| Topic | File |
|-------|------|
| System Architecture | [memory/architecture.md](memory/architecture.md) |
| Backend & API | [memory/backend.md](memory/backend.md) |
| Game Mechanics | [memory/game-mechanics.md](memory/game-mechanics.md) |
| User Journeys | [memory/user-journeys.md](memory/user-journeys.md) |
| Integrations | [memory/integrations.md](memory/integrations.md) |
| Master Plan | [plans/master-plan.md](plans/master-plan.md) |
| Master Todo | [todos/master-todo.md](todos/master-todo.md) |
| Audit Report | [docs-to-process/20251202-system-audit-final-report.md](docs-to-process/20251202-system-audit-final-report.md) |

**Specs by domain** (all have spec.md, plan.md, tasks.md, audit-report.md):
- **Infrastructure**: 009-database, 010-api, 011-background-tasks
- **Configuration**: 013-configuration-system
- **Game Engine**: 003-scoring, 004-chapters, 005-decay, 006-vice, 014-engagement
- **Context**: 012-context-engineering
- **Agent**: 001-text-agent
- **Platforms**: 002-telegram, 007-voice, 008-portal

**Module-specific context**:
- [nikita/CLAUDE.md](nikita/CLAUDE.md) - Package overview
- [nikita/api/CLAUDE.md](nikita/api/CLAUDE.md) - FastAPI patterns
- [nikita/db/CLAUDE.md](nikita/db/CLAUDE.md) - Database layer
- [nikita/engine/CLAUDE.md](nikita/engine/CLAUDE.md) - Game engine
- [nikita/memory/CLAUDE.md](nikita/memory/CLAUDE.md) - Knowledge graphs


## Self-Improvement

**After each session**, consider:
1. What development patterns emerged?
2. What debugging steps worked best?
3. Did architecture assumptions hold?
4. Update CLAUDE.md with new learnings

**This file should evolve as the codebase grows.**
