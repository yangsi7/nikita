# CLAUDE.md

This file provides orchestration guidance to Claude Code when working in this repository.

---

## Core Constraints

1. **Event Logging**: Log all tool calls, agent invocations, skill activations, decisions, and observations in `event-stream.md` chronologically
2. **Planning**: Maintain `planning.md` for high-level strategy; generate detailed tasks in `todo.md` organized by session-id
3. **State Management**: Keep `todo.md` (≤150 lines), `event-stream.md` (≤25 lines), `workbook.md` (≤300 lines) up-to-date; prune aggressively
4. **Context Engineering**: Use `workbook.md` for critical context, insights, anti-patterns, and short-term planning
5. **Documentation Lifecycle**: Write session artifacts to `docs-to-process/{timestamp}-{session-id}-{type}.md`, consolidate to `docs/{domain}/` via `/streamline-docs`, update CLAUDE.md for high-impact rules
6. **No Over-Engineering**: Implement ONLY what user requested; no invented features
7. **No Hallucination**: Research via MCP tools (Ref, Firecrawl) when uncertain; never guess
8. **rg, fd, jq**:
   - Use `rg` (ripgrep) instead of `grep`
   - Use `fd` instead of `find`
   - Use `jq` for JSON parsing
   - Limit output to prevent context overflow

---


## Start
Before performing any action first:
1. **Analyze Events:** Review @event-stream.md, @todo.md to understand the user's request and the current state. Focus especially on the latest user instructions and any recent results or errors. If they are not up to date, update them.
2. **System Understanding:** If the task is complex or involves system design and/or system architecture, invoke the System Understanding Module to deeply analyze the problem. Identify key entities and their relationships, and construct a high-level outline or diagram of the solution approach. Use this understanding to inform subsequent planning.
3. **Determine the next action to take.** This could be formulating a plan, calling a specific tool, slash command, mcp tool call, executing a skill, invoking a subagent, updating documentation, retrieving knowledge, gathering context etc. Base this decision on the current state, the overall task plan, relevant knowledge, and the tools or data sources available. Execute the chosen action. You should capture results of the action (observations, outputs, errors) in the event stream and session artifacts.
4. **Execute**
5. **Log & Maintain:**
   - Log the action in @event-stream.md
   - If a task is completed, mark it as done in @todo.md
   - If you learned critical context, log it in @workbook.md
   - **CHECK FILE SIZES** after every significant update (see Session File Maintenance below)
   - Update Document Index when creating new research outputs
6. **Iterate**

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
| `todo.md` | 150 | Current tasks only | Keep 5-10 active, archive completed |
| `event-stream.md` | 25 | Last 20 events | Auto-trim at session start |
| `workbook.md` | 300 | Active context | Extract to docs/ or delete old context |
| `planning.md` | 600 | Master plan | Link to detailed specs in docs/ |

---

## Documentation Rules

### Directory Structure

**Root files** (allowed at project root):

| File | Max Lines | Required | Purpose |
|------|-----------|----------|---------|
| `CLAUDE.md` | 600 | Yes | Orchestration rules |
| `README.md` | 300 | Yes | Project overview |
| `workbook.md` | 300 | Optional | Session context |
| `planning.md` | 600 | Optional | High-level strategy |
| `todo.md` | 150 | Optional | Current tasks |
| `event-stream.md` | 25 | Optional | Session log |
| `PROJECT_INDEX.json` | - | Optional | Codebase intelligence |

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
wc -l CLAUDE.md README.md workbook.md planning.md todo.md event-stream.md docs/README.md docs/**/*.md
```

**Limits**:
- CLAUDE.md ≤ 600, README.md ≤ 300, workbook.md ≤ 300
- planning.md ≤ 600, todo.md ≤ 150, event-stream.md ≤ 25
- docs/README.md ≤ 200, docs/{domain}/*.md ≤ 500

### Prohibited Practices

- **No floating docs**: Only allowed root files: CLAUDE.md, README.md, workbook.md, planning.md, todo.md, event-stream.md
- **No duplication**: One source per topic (REPLACE, don't append)
- **No exceeding limits**: Prune or extract before committing
- **No stale artifacts**: Process docs-to-process/ regularly via `/streamline-docs`
- **No placeholders**: Empty "coming soon" files forbidden

---

## Start: Orchestration-Aware React Loop

**Main execution loop integrating agents, skills, and state management.**

### Flow

```
1. STATE ANALYSIS → Read event-stream.md, todo.md, workbook.md
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

Run `wc -l todo.md event-stream.md workbook.md planning.md` when:
1. Creating new research documents
2. Completing any Phase/task
3. Before ending session
4. Every 5-10 tool calls

### Pruning Rules by File

**todo.md** (150 line limit):
- Remove all completed tasks older than current sprint
- Keep only 5-10 active/pending tasks
- Move detailed subtasks to @planning.md (reference by link)
- Archive completed sprints to planning.md if needed

**event-stream.md** (25 line limit):
- Keep header (3 lines) + last 20 events ONLY
- Delete oldest events when exceeding 23 events
- Priority: Keep errors, decisions, phase completions

**workbook.md** (300 line limit):
- Extract permanent insights to research documents
- Delete superseded context (old numbers, outdated priorities)
- Keep only current phase context
- Remove resolved anti-patterns

**planning.md** (600 line limit:
- Remove irrelevant, or superceded sections.
- update, prune with most up to date vision

### When Files Exceed Limits

**IMMEDIATE ACTION REQUIRED**:
```bash
# 1. Check sizes
wc -l todo.md event-stream.md workbook.md planning.md

# 2. If todo.md > 150: Prune completed tasks, keep only active sprint
# 3. If event-stream.md > 25: Keep last 20 events only
# 4. If workbook.md > 300: Extract to docs/, delete outdated context
# 5. If planning.md > 1000: Consider archive split (rare)
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

**Status**: Phase 1 Complete (39 Python files, database models, memory system)

**Architecture**:
- **Voice**: ElevenLabs Conversational AI 2.0
- **Text**: Pydantic AI + Claude Sonnet
- **Memory**: Graphiti (3 temporal knowledge graphs) + FalkorDB
- **Database**: Supabase (PostgreSQL + pgVector)
- **Platforms**: Telegram (text) + Voice calls
- **Game Engine**: Scoring (4 metrics), chapters (1-5), boss encounters, daily decay

**Documentation System**:
- **memory/**: Living docs with Current State vs Target Specs (architecture, backend, game-mechanics, user-journeys, integrations)
- **plan/master-plan.md**: Full technical plan (with YAML frontmatter)
- **todo/master-todo.md**: Phase-organized tasks (Phase 1 ✅, Phases 2-5 ❌)
- **nikita/*/CLAUDE.md**: Module-specific context for AI agents

**Key Files**:
- `nikita/config/settings.py`: All environment settings
- `nikita/engine/constants.py`: Game constants (chapters, thresholds, decay rates)
- `nikita/memory/graphiti_client.py`: NikitaMemory class (3 graphs)
- `nikita/db/models/user.py`: User, UserMetrics, UserVicePreference

**Next Steps**: Phase 2 (Text Agent + Telegram integration)


## Planning & Todo Files

The main planning file is `plan/master-plan.md`. All planning artifacts live in `plan/`.

| File | Purpose |
|------|---------|
| `plan/master-plan.md` | Technical architecture & implementation plan |
| `todo/master-todo.md` | Phase-organized task tracking |

### YAML Frontmatter

Planning and todo files have a YAML header for tracking:

```yaml
---
title: Document title
created: 2025-01-27T20:23:00Z
updated: 2025-01-28T02:00:00Z
session_id: nikita-phase2-text
status: active | complete | blocked
phases_complete: [1]        # for plans
phases_pending: [2, 3, 4, 5] # for plans
current_phase: 2            # for todos
blocked_by: null            # for todos
---
```

### Creating New Plans

When Claude Code enters plan mode:
1. A temporary plan is created at `~/.claude/plans/`
2. After approval, integrate relevant content into `plan/master-plan.md`
3. Delete the temporary plan file

Feature-specific plans can be created as `plan/{feature}-plan.md`, then consolidated into master-plan.md when the feature completes.

### Updating Plans

When modifying `plan/master-plan.md`:
1. Update the `updated` timestamp and `session_id` in YAML
2. Update `phases_complete` and `phases_pending` as phases finish
3. Archive completed phase details if the file grows too large

### Pruning Plans

Prune `plan/master-plan.md` when:
- A phase completes: move detailed implementation notes to `memory/` docs
- Content becomes outdated: remove superseded architecture decisions
- File exceeds ~1500 lines: extract completed work to documentation

Pruning approach:
- Keep current phase + future phases in full detail
- Reduce completed phases to summaries with links to memory/ docs
- Remove redundant explanations once code is implemented

### Updating Todos

When modifying `todo/master-todo.md`:
1. Update the `updated` timestamp and `session_id`
2. Mark tasks complete with `[x]` immediately after finishing
3. Update `current_phase` when moving to next phase

### Pruning Todos

Prune `todo/master-todo.md` when:
- A phase completes: collapse to summary (e.g., "Phase 1: Complete ✅")
- Tasks become irrelevant: remove rather than leave unchecked
- File exceeds ~400 lines: archive old phases

Keep:
- Current phase tasks in full detail
- Next phase tasks for context
- Summary line for each completed phase

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
| Master Plan | [plan/master-plan.md](plan/master-plan.md) |
| Master Todo | [todo/master-todo.md](todo/master-todo.md) |

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
