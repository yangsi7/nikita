# CLAUDE.md

This file provides orchestration guidance to Claude Code when working in this repository.

---

## Core Constraints

1. **Event Logging**: Log all tool calls, agent invocations, skill activations, decisions, and observations in `event-stream.md` chronologically
2. **Planning**: Maintain `plans/master-plan.md` for high-level strategy; track tasks in `todos/master-todo.md`
3. **State Management**: Keep `todos/master-todo.md` (≤400 lines), `event-stream.md` (≤100 lines), `workbook.md` (≤300 lines) up-to-date; prune aggressively
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
10. **DRY Principle & Clean Code (STRICTLY ENFORCED)**:
    - **Single Source of Truth**: ONE implementation for each API client, utility, or pattern
    - **No Duplicate Code**: If functionality exists, USE IT. Never rewrite httpx calls, API clients, or utilities
    - **Less Code = Better Code**: Fewer lines means fewer bugs, easier maintenance, less cognitive load
    - **Professional Standards**: Code should be clean, readable, and follow established patterns in the codebase
    - **Before Writing**: Search codebase for existing implementations (`rg "class.*Client" --type py`)
    - **Refactor Aggressively**: If you find duplicates, consolidate them. Don't add more.
    - **Example**: `ElevenLabsConversationsClient` is THE source for ElevenLabs API calls. Don't add httpx calls elsewhere.
    - **Rationale**: Duplicate code creates maintenance nightmares, inconsistent behavior, and technical debt
11. **Firecrawl MCP Usage (CRITICAL - Prevents Token Overflow)**:
    - **NEVER use `scrapeOptions` with `firecrawl_search`** - this scrapes ALL results and causes 200K+ character responses
    - **Two-Step Workflow (MANDATORY)**:
      1. **Search**: `firecrawl_search(query="...", limit=3-5)` → Get URLs only
      2. **Scrape**: `firecrawl_scrape(url="specific_url", formats=["markdown"], onlyMainContent=true)` → Get content from ONE page
    - **Required Parameters for Scrape**:
      - `formats: ["markdown"]` - Request markdown only (not HTML, rawHtml, etc.)
      - `onlyMainContent: true` - Strip navigation, sidebars, footers
    - **Search Limits**: Always use `limit` parameter (3-5 for most searches, max 10)
    - **Error Pattern to Avoid**:
      ```
      # WRONG - causes token overflow
      firecrawl_search(query="...", scrapeOptions={formats: ["markdown"]})

      # CORRECT - two-step approach
      firecrawl_search(query="...", limit=5)  # Step 1: Get URLs
      firecrawl_scrape(url="https://...", formats=["markdown"], onlyMainContent=true)  # Step 2: Get content
      ```
    - **Rationale**: `scrapeOptions` in search concatenates ALL result pages (5+ pages × 30K chars = 150K+ chars overflow)
12. **Zero Tolerance for Failing Tests (STRICTLY ENFORCED)**:
    - **Rule**: ZERO failing tests tolerated. Every failing test must be resolved before ending a task.
    - **Decision Tree**:
      1. Is it caused by my changes? → YES: Fix immediately (blocking)
      2. Is the test still valid? → NO: Delete test + commit + document why
      3. Can I fix it quickly (<15 min)? → YES: Fix now
      4. Complex fix needed? → Create GitHub issue + assign @claude
    - **NEVER acceptable**: "Note as pre-existing and move on"
    - **Action Options** (must choose one):
      - **Fix Now**: Quick fix (<15 min) → fix, verify, commit
      - **Subagent Fix**: Moderate fix → launch code-analyzer or implementor agent
      - **GitHub Issue**: Complex fix → create issue, comment `@claude fix this`
      - **Delete Test**: Obsolete/invalid → delete, commit, document
    - **After ANY test run with failures**:
      1. STOP - Do not proceed with other work
      2. ANALYZE - Determine root cause (2-5 min max)
      3. DECIDE - Choose action from decision tree
      4. EXECUTE - Take action immediately
      5. VERIFY - Confirm resolution
      6. LOG - Update event-stream with action taken
    - **Self-Check Questions** (before ending any task):
      1. Did I run the relevant tests?
      2. Are ALL tests passing?
      3. If tests failed, did I take action (not just note them)?
      4. Did I create tracking for any deferred fixes?
    - **Rationale**: A failing test is a bug. Bugs must be fixed, tracked, or explicitly deleted - never ignored.
13. **Parallel Agent Context Preservation (STRICTLY ENFORCED)**:
    - **Rule**: Outsource noisy tasks to parallel agents to preserve main context
    - **Always Delegate To Agents**:
      - Documentation reading and research (Ref MCP, Firecrawl)
      - Code exploration and pattern discovery
      - Screenshot and UI analysis
      - Planning and architecture design
      - External API investigation
      - Test suite analysis
    - **How To Delegate**:
      - Use `Task` tool with appropriate `subagent_type` (Explore, Plan, prompt-researcher, etc.)
      - Launch multiple agents in parallel when tasks are independent
      - Provide clear, focused prompts for each agent
    - **Rationale**: Main agent context is precious; noisy exploration consumes tokens without advancing goals
    - **Anti-Pattern**: Reading 10 files directly when an Explore agent could summarize findings in 1 response
14. **External Service Configuration Sync (CRITICAL)**:
    - **Problem**: Configuration drift between code and external dashboards (ElevenLabs, Supabase, etc.)
    - **Rule**: When integrating external services, document BOTH:
      1. **Code-side config**: API calls, environment variables, settings
      2. **Dashboard-side config**: Manual settings, knowledge bases, agent configurations
    - **Verification Checklist** (before marking integration complete):
      - [ ] What can ONLY be set via dashboard?
      - [ ] What can ONLY be set via API?
      - [ ] What can be set BOTH ways (and which is authoritative)?
      - [ ] Is there a sync mechanism or must changes be manual?
    - **Documentation Location**: `docs/reference/{service}-configuration.md`
    - **Rationale**: Dashboard vs API config mismatch causes silent failures and wasted debugging time
15. **Subagents vs Agent Teams**:
    - **Subagents** (Task tool): One-way result, single invocation, lower cost. Use for research, analysis, validation (SDD validators, `/deep-audit`, Explore)
    - **Agent Teams** (TeamCreate): Bidirectional messaging, persistent teammates, shared task list. 3-5x more expensive
    - **Default to subagents**. Use teams ONLY when agents must share findings and build on each other's work (debate, review cycles, coordinated multi-module workflows)
    - **Command**: `/team-agent "task" [--preset audit|implement|review|research]`

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
| `plans/master-plan.md` | 1000 | Technical architecture | Link to spec plans, prune completed phases |
| `event-stream.md` | 100 | Last 95 events | Auto-trim at session start |
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
| `event-stream.md` | 100 | Optional | Session log |
| `PROJECT_INDEX.json` | - | Optional | Codebase intelligence |

**Planning files** (in `plans/` and `todos/`):

| File | Max Lines | Purpose |
|------|-----------|---------|
| `plans/master-plan.md` | 1000 | Technical architecture, references spec plans |
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
- CLAUDE.md ≤ 600, README.md ≤ 300, workbook.md ≤ 300, event-stream.md ≤ 100
- plans/master-plan.md ≤ 1000, todos/master-todo.md ≤ 400
- specs/NNN/plan.md ≤ 500, specs/NNN/tasks.md ≤ 300

### Prohibited Practices

- **No floating docs**: Only allowed root files: CLAUDE.md, README.md, workbook.md, event-stream.md
- **No duplication**: One source per topic (REPLACE, don't append)
- **No exceeding limits**: Prune or extract before committing
- **No stale artifacts**: Process docs-to-process/ regularly via `/streamline-docs`
- **No placeholders**: Empty "coming soon" files forbidden

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

**Status**: Phase 2 ✅ COMPLETE, Phase 3 ✅ COMPLETE, Phase 4 ✅ COMPLETE (Voice deployed Jan 2026), Phase 5 ⚠️ IN PROGRESS (Portal 85%)

**Streamlined Architecture** (Dec 2025):
- **Compute**: Google Cloud Run (serverless, scales to zero) - DEPLOYED
- **Voice**: ElevenLabs Conversational AI 2.0 (Server Tools pattern - REST only)
- **Text**: Pydantic AI + Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)
- **Memory**: Graphiti (3 temporal knowledge graphs) + **Neo4j Aura** (free tier, managed)
- **Database**: Supabase (PostgreSQL + pgVector + RLS)
- **Scheduling**: pg_cron + Cloud Run task endpoints (no Celery/Redis)
- **Platforms**: Telegram (@Nikita_my_bot) + Voice (ElevenLabs, deployed Jan 2026) + Portal (Next.js on Vercel)
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
**Scopes**: `api`, `portal`, `engine`, `db`, `auth`, `telegram`, `admin`, `sdd`, `voice`, `memory`, `context`, `config`

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

**Specifications** (28 specs with complete SDD artifacts):
- **specs/001-028/**: Each has spec.md, plan.md, tasks.md, audit-report.md
- **Core (001-020)**: Infrastructure, game engine, agents, platforms, admin
- **Humanization (021-028)**: Hierarchical prompts, life simulation, emotional state, behavioral meta-instructions, proactive touchpoints, text patterns, conflict generation, voice onboarding
- **Critical path**: All 28 complete → Portal polish remaining

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
- **specs/**: 28 implementation specifications

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

Maintain `event-stream.md` (max 100 lines) with one line per event:

**Format**: `[TIMESTAMP] EVENT_TYPE: concise description`

**Event Types**: `DEPLOY`, `FIX`, `FEATURE`, `TEST_STATUS`, `SECURITY_FIX`, `CLEANUP`, `ERROR`, `DECISION`

**Example**:
```
[2025-12-21T22:00:00Z] FIX: OTP validation - changed len==6 to 6<=len<=8
[2025-12-21T22:10:00Z] DEPLOY: nikita-api-00088-kj4 with OTP fix
```

---

## Proactive Plan/Todo Maintenance

Keep master files synced with implementation. After ANY change:
1. Mark tasks complete in `todos/master-todo.md` immediately
2. Update `plans/master-plan.md` if architecture changed
3. Check session plans: `ls -la ~/.claude/plans/*.md | tail -5`
4. Delete integrated session plans from `~/.claude/plans/`

**Avoid**: Plan/todo drift, orphaned session plans, unchecked completed tasks.

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
- **Onboarding**: 015-onboarding-fix, 017-enhanced-onboarding
- **Admin**: 016-admin-debug-portal, 018-admin-prompt-viewing, 019-admin-voice-monitoring, 020-admin-text-monitoring

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
