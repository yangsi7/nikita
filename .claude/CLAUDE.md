# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

---

## Project Overview

**Claude Code Intelligence Toolkit** - A meta-system for building intelligence-first AI agent workflows using skills, agents, slash commands, and SOPs.

**Core Innovation**: Intelligence-first architecture achieving 80%+ token savings by querying lightweight indexes (project-intel.mjs, MCP tools) before reading files.

---

## Intelligence-First Workflow

**Critical Pattern**: Query intelligence sources BEFORE reading files:

```bash
# 1. Get project overview (first step in new sessions)
project-intel.mjs --overview --json

# 2. Search for relevant files
project-intel.mjs --search "keyword" --type tsx --json

# 3. Get symbols from candidates
project-intel.mjs --symbols path/to/file.tsx --json

# 4. Trace dependencies if needed
project-intel.mjs --dependencies path/to/file.tsx --json

# 5. NOW read specific file sections
Read path/to/file.tsx
```

**Why**: 1-2% token usage vs reading full files → 80%+ savings

---

## Architecture

### Component Hierarchy

1. **Skills** (.claude/skills/) - Auto-invoked workflows: analyze-code, debug-issues, create-plan, implement-and-verify
2. **Agents** (.claude/agents/) - Specialized subagents: orchestrator, code-analyzer, planner, executor
3. **Slash Commands** (.claude/commands/) - User-triggered workflows: /analyze, /bug, /feature, /plan, /implement, /verify, /audit
4. **Templates** (.claude/templates/) - Structured output formats (22 templates, CoD^Σ traces)
5. **Shared Imports** (.claude/shared-imports/) - Core frameworks: CoD_Σ.md, project-intel-mjs-guide.md

**Detailed Architecture**: See docs/architecture/system-overview.md for dependency graphs, process flows, and token efficiency details.

---

## Component Decision Guide

- **Skill** - Complex workflow, auto-invoke based on context
- **Agent** - Isolated context for heavy analysis/specialized tasks
- **Command** - User-triggered shortcut for common workflows
- **Template** - Structured output format for consistency

---

## Development Workflows

### Creating Components

**Skills**: YAML frontmatter + progressive disclosure (metadata → instructions → resources)
**Agents**: YAML frontmatter + persona + @ imports for templates/skills
**Commands**: YAML frontmatter + description (SlashCommand tool) + allowed-tools + prompt expansion

**Guide**: See docs/guides/developing-agent-skills.md

### Bootstrapping Projects

```bash
cp .claude/templates/planning-template.md planning.md
cp .claude/templates/todo-template.md todo.md
cp .claude/templates/event-stream-template.md event-stream.md
cp .claude/templates/workbook-template.md workbook.md
```

**Reference**: See .claude/templates/BOOTSTRAP_GUIDE.md

---

## Chain of Density Σ (CoD^Σ)

All reasoning MUST include CoD^Σ traces with evidence.

### Operators
- `⊕` parallel | `∘` sequential | `→` delegation | `≫` transformation | `⇄` bidirectional | `∥` concurrent

### Evidence Requirements
Every claim needs: file:line references, MCP query results, project-intel.mjs output, or test logs.

**Bad**: "Component re-renders because of state"
**Good**: "Component re-renders: useEffect([state])@ComponentA.tsx:45 → mutation@ComponentA.tsx:52"

---

## File Organization

```
.claude/
├── agents/           # Subagent definitions
├── commands/         # Slash command definitions
├── skills/           # Auto-invoked workflows
├── templates/        # Structured outputs
└── shared-imports/   # Core frameworks
```

**Generated Files**: `{YYYYMMDD}-{type}-{4char-id}.md` (research, analysis, decision, pattern, bug, integration)

---

## MCP Tools

**Available**: Ref (docs), Supabase (DB), Shadcn (components), Chrome (E2E), Brave (search), 21st-dev (design)

**Usage**: Query MCP tools for authoritative external information before assumptions.

---

## Documentation Structure

**Root State Files**:
| File | Max Lines | Purpose |
|------|-----------|---------|
| planning.md | 600 | High-level strategy |
| todo.md | 150 | Current tasks |
| event-stream.md | 25 | Session log |
| workbook.md | 300 | Session context |

**docs/ Curated Knowledge (5 Domains)**:
```
docs/
├── README.md           # Navigation index (≤200 lines)
├── CHANGELOG.md        # Documentation changes
├── architecture/       # System design, data model
├── patterns/           # Reusable patterns (frontend, backend, testing)
├── decisions/          # ADRs (Architecture Decision Records)
├── guides/             # How-to docs, onboarding
└── reference/          # API docs, config, external resources
```

**docs-to-process/** - Staging for session artifacts (→ consolidate via `/streamline-docs` → DELETE)

---

## Specification-Driven Development (SDD)

### Canonical 8-Phase Workflow

```
Phase 1: /define-product    → memory/product.md       (define-product skill)
Phase 2: /generate-constitution → memory/constitution.md (generate-constitution skill)
Phase 3: /feature           → specs/$FEATURE/spec.md + todo/master-todo.md entry (specify-feature skill)
Phase 4: /clarify           → updated spec.md         (clarify-specification skill) [if needed]
Phase 5: /plan              → plan.md + research.md + data-model.md (create-implementation-plan skill)
Phase 6: /tasks             → tasks.md                (generate-tasks skill) [auto]
Phase 7: /audit             → audit-report.md         (/audit command) [auto]
Phase 8: /implement         → code + tests + verification (implement-and-verify skill)
```

**$FEATURE Convention**: `NNN-feature-name` (e.g., `001-therapy-app`, `002-oauth-auth`)

### Spec-First Principle (CRITICAL)

**All specification artifacts must be consistent and complete before implementation.**

When modifying requirements:
1. **Update ALL artifacts together** - spec.md, plan.md, tasks.md must stay synchronized
2. **Re-audit after changes** - Run `/audit` to verify consistency and coverage
3. **Never skip to implementation** - Audit must PASS before `/implement`

Why this matters:
- Prevents implementation drift from requirements
- Ensures acceptance criteria are testable
- Maintains traceability from requirements → tasks → code
- Catches gaps before they become bugs

**Anti-pattern**: Creating new requirements without updating plan.md tasks or tasks.md acceptance criteria

### User Actions (2-3 manual steps)

1. `/define-product` - Create memory/product.md (optional, for new projects)
2. `/feature "description"` - Create specification + register in todo/master-todo.md
3. `/implement plan.md` - Execute implementation + auto-sync memory/

### Automatic Workflow Progression

After `/feature`, the system automatically chains:
```
/feature → spec.md
    ↓ (auto-invokes /plan)
create-implementation-plan → plan.md + research.md + data-model.md
    ↓ (auto-invokes generate-tasks)
generate-tasks → tasks.md
    ↓ (auto-invokes /audit)
/audit → audit-report.md
    ↓ (if PASS)
Ready for /implement
```

After `/implement`, TDD verification per story:
```
/implement plan.md
    ↓
Story P1: Write tests → Implement → /verify (auto) → PASS
    ↓
Story P2: Write tests → Implement → /verify (auto) → PASS
    ↓
Story P3: Write tests → Implement → /verify (auto) → PASS
    ↓
Feature complete
```

### Quality Gates

- **Pre-Implementation** (`/audit`): Constitution compliance, requirement coverage, ambiguity detection
- **Per-Story** (`/verify --story <id>`): Test coverage, dependency validation, independent demos
- **Article III**: Minimum 2 acceptance criteria per user story, tests before implementation
- **Article VII**: User-story-centric organization (P1, P2, P3 priority order)

### Phase Prerequisites

| Phase | Requires | Produces |
|-------|----------|----------|
| 1. define-product | Repository with code/docs | memory/product.md |
| 2. generate-constitution | memory/product.md | memory/constitution.md |
| 3. feature | (optional) memory/product.md, memory/constitution.md | specs/$FEATURE/spec.md + todo/master-todo.md entry |
| 4. clarify | spec.md with [NEEDS CLARIFICATION] | Updated spec.md |
| 5. plan | spec.md (clarified) | plan.md, research.md, data-model.md |
| 6. tasks | plan.md | tasks.md + todo/master-todo.md subtasks |
| 7. audit | spec.md, plan.md, tasks.md | audit-report.md |
| 8. implement | tasks.md, audit PASS | Code, tests, verification reports + memory/ auto-sync |

### Workflow Coordination

**Automatic Orchestration (Recommended):**

The **sdd-orchestrator skill** auto-triggers on SDD-related requests and provides:
- Prerequisite validation before each phase
- Automatic routing to correct phase command
- Plan/todo sync after phase completion
- Supporting skill integration (TDD, code-analysis, shadcn, frontend-design)

The orchestrator invokes the **sdd-coordinator agent** via Task tool for workflow analysis.

**Trigger Patterns** (80%+ activation):
- "create feature", "new feature", "build"
- "implement", "start coding", "develop"
- "SDD status", "what's next", "workflow status"
- "/feature", "/implement", "/plan", "/audit"

**Manual Coordination:**

Use **sdd-coordinator agent** directly when:
- Checking workflow status
- Validating prerequisites between phases
- Diagnosing workflow failures
- Working with custom directory structures

---

## Best Practices

1. **Intel First** - project-intel.mjs queries before file reads
2. **Use Skills** - Let skills handle workflows, don't reinvent
3. **CoD^Σ Traces** - All claims need file:line evidence
4. **Templates** - Use @ syntax for consistency
5. **Progressive Disclosure** - Load details on-demand

---

## Task Tracking (CRITICAL)

**During implementation, ALWAYS track progress in tasks.md**

### Marking Tasks Complete

When implementing features via `/implement`:
1. **Mark tasks complete immediately** after finishing each task
2. Use checkbox format: `- **Status**: [x] Complete`
3. Mark ALL acceptance criteria checkboxes: `- [x] AC-X.X.X: ...`
4. Update the Progress Summary table
5. Add version history entry if significant milestone

### Task Status Format

```markdown
### T1.1: Task Name
- **Status**: [x] Complete  ← Mark when done
- **ACs**:
  - [x] AC-1.1.1: First criterion
  - [x] AC-1.1.2: Second criterion
```

### Progress Summary Table

Keep the table at the bottom of tasks.md updated:
```markdown
| Phase/User Story | Tasks | Completed | Status |
|------------------|-------|-----------|--------|
| US-1: Recording | 7 | 5 | In Progress |
```

### Why This Matters

- Prevents duplicate work in future sessions
- Shows clear progress to user
- Enables accurate audit reports
- Maintains traceability from requirements → code

---

## Troubleshooting

**Agent reads full files**: Verify skill invocation (analyze-code/debug-issues enforce intel-first)
**No evidence**: Check CoD^Σ trace, ensure skills used
**High token usage**: Use skills with intel queries first
**Skills not triggering**: Check SKILL.md description/YAML
**Templates not used**: Verify @ syntax in agents/commands
