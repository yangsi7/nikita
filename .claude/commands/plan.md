---
description: Create detailed implementation plan from specification - SDD Phase 5
allowed-tools: Bash(project-intel.mjs:*), Bash(test:*), Bash(jq:*), Read, Grep, Write
argument-hint: <spec-file>
---

# Implementation Plan - SDD Phase 5

Create a detailed implementation plan from a feature specification.

## Unified Skill Routing

This command routes to **SDD Phase 5: Planning** via the unified skill at @.claude/skills/sdd/SKILL.md.

**Phase 5 Workflow:** @.claude/skills/sdd/workflows/05-planning.md

---

## User Input

```text
$1
```

**Input Spec:** If not provided, auto-detect from current spec directory.

---

## Phase 5 Process

Follow the **sdd skill Phase 5** workflow:

### 1. Load Specification

- Read spec file: `$1` or detect from `specs/NNN-feature/spec.md`
- Extract all requirements (REQ-001, REQ-002, etc.)
- Identify constraints and success criteria

### 2. Task Breakdown

Break each requirement into granular tasks (2-8 hours each):

```markdown
### T1.1: Add OAuth Database Schema
- **ID:** T1.1
- **Owner:** executor-agent
- **Estimated:** 2 hours
- **Dependencies:** None
- **Acceptance Criteria:**
  - [ ] AC-1.1.1: users table has google_id VARCHAR(255) column
  - [ ] AC-1.1.2: Migration runs without errors
```

**CRITICAL:** Every task MUST have minimum 2 testable ACs.

### 3. Identify Dependencies

```bash
# Find existing files that will be modified
project-intel.mjs --search "auth|session" --json

# Check downstream dependencies
project-intel.mjs --dependencies src/auth/session.ts --direction downstream --json
```

### 4. Create Artifacts

**Output files in spec directory:**
- `plan.md` - Implementation plan
- `research.md` - External research findings (if any)
- `data-model.md` - Data model changes (if any)

---

## Quality Gate

**Article III Compliance**: Plan must have:
- ✓ 100% requirement coverage (every REQ → tasks)
- ✓ All tasks have 2+ testable ACs
- ✓ No circular dependencies
- ✓ Tasks sized 2-8 hours
- ✓ Dependency graph included

---

## Auto-Chain

After Phase 5 completes:
1. Auto-invoke Phase 6 (generate-tasks)
2. Auto-invoke Phase 7 (/audit)

---

## CoD^Σ Reasoning Pattern

```
Step 1: → LoadSpec
  ↳ Source: spec.md
  ↳ Requirements: N extracted

Step 2: ∘ BreakdownTasks
  ↳ REQ-001 → T1.1 (DB), T1.2 (API)
  ↳ REQ-002 → T2.1 (UI), T2.2 (Integration)

Step 3: ⇄ IntelQuery("dependencies")
  ↳ Query: project-intel.mjs --search "keyword"
  ↳ Found: Existing patterns at file:line

Step 4: → DefineACs
  ↳ T1.1: 2 ACs (schema, migration)
  ↳ T1.2: 3 ACs (endpoint, validation, response)
```

---

## Enforcement Rules

### Rule 1: Minimum 2 ACs Per Task

**❌ Violation:**
```markdown
Task: Add login button
ACs:
- Button exists
```

**✓ Correct:**
```markdown
Task: Add login button
ACs:
- AC-1: Button renders with "Log in with Google" text
- AC-2: Button click triggers OAuth redirect
```

### Rule 2: All Requirements → Tasks

Every requirement must have at least one task covering it.

---

## Start Now

Read the spec file and proceed with planning workflow.
