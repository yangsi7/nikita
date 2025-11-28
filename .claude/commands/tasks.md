---
description: Generate user-story-organized task list from implementation plan (project)
allowed-tools: Bash(fd:*), Bash(git:*), Read, Write
argument-hint: [plan-file]
---

# Task Generation Command

Execute the **generate-tasks skill** to create user-story-organized task breakdown from implementation plan.

**Usage**:
- `/tasks` - Auto-detect plan from git branch
- `/tasks specs/001-feature/plan.md` - Explicit plan file

---

## Process

### 1. Detect Plan File

If no argument provided, auto-detect from git branch:

```bash
FEATURE=$(git rev-parse --abbrev-ref HEAD 2>/dev/null | grep -oE '^[0-9]{3}-[a-z0-9-]+')
if [ -n "$FEATURE" ]; then
    PLAN_FILE="specs/$FEATURE/plan.md"
else
    echo "ERROR: No feature detected. Use: /tasks <plan-file> or create git branch with ###-name pattern"
    exit 1
fi
```

### 2. Validate Prerequisites

Check that spec.md and plan.md exist (Article IV: Specification-First Development):

```bash
SPEC_FILE="${PLAN_FILE%/plan.md}/spec.md"

if [ ! -f "$SPEC_FILE" ]; then
    echo "ERROR: Missing specification. Run /feature first to create spec.md"
    exit 1
fi

if [ ! -f "$PLAN_FILE" ]; then
    echo "ERROR: Missing implementation plan. Run /plan $SPEC_FILE first"
    exit 1
fi
```

### 3. Invoke generate-tasks Skill

**Instruct Claude** to use the generate-tasks skill:

"Use the **generate-tasks skill** to create tasks.md from:
- Specification: $SPEC_FILE
- Implementation plan: $PLAN_FILE

The skill will:
1. Load user stories from spec.md (with priorities P1, P2, P3)
2. Load technical details from plan.md
3. Organize tasks by user story (Article VII)
4. Ensure ≥2 ACs per story (Article III)
5. Mark parallelizable tasks with [P]
6. **Automatically invoke /audit for quality gate validation**

After task generation completes, the /audit command will run automatically to verify cross-artifact consistency before implementation can proceed."

---

## Quality Gate Enforcement

After tasks.md is generated, the generate-tasks skill will **automatically invoke**:

```
/audit $FEATURE_ID
```

This validates (Article IV, V, VII):
- Constitution compliance across all artifacts
- Requirements → Tasks mapping (100% coverage)
- User-story-centric organization
- No [NEEDS CLARIFICATION] markers remain
- All acceptance criteria are testable

**If audit FAILS with CRITICAL issues**:
- Implementation is BLOCKED
- Remediation guidance provided
- User must fix issues before /implement

**If audit PASSES**:
- Reports "Ready for implementation"
- User can proceed with `/implement plan.md`

---

## Constitutional Compliance

This command enforces:
- **Article III**: Test-First Imperative (≥2 ACs per story)
- **Article IV**: Specification-First Development (spec → plan → tasks order)
- **Article V**: Template-Driven Quality (automatic /audit validation)
- **Article VII**: User-Story-Centric Organization (tasks grouped by story)

---

## SDD Workflow Position

```
/feature → spec.md
  ↓
/plan spec.md → plan.md
  ↓
→ /tasks ← YOU ARE HERE
  ↓
/audit (automatic)
  ↓
/implement plan.md (if audit passes)
  ↓
/verify plan.md (automatic per story + final)
```

---

## Expected Output

**Generated File**: `specs/$FEATURE/tasks.md`

**Format** (from @.claude/templates/tasks.md):
- Phase 1: Setup (foundational)
- Phase 2: Foundational (blocking prerequisites)
- Phase 3+: User Story phases (P1, P2, P3...)
- Final Phase: Polish & cross-cutting

**Automatic Next Step**: `/audit $FEATURE_ID` runs immediately

---

## Related Commands

- **/feature** - Creates specification (run first)
- **/plan** - Creates implementation plan (run second)
- **→ /tasks** - Creates task breakdown (run third) ← YOU ARE HERE
- **/audit** - Validates consistency (runs automatically after /tasks)
- **/implement** - Executes tasks (run after audit passes)
- **/verify** - Validates ACs (runs automatically per story)

---

## Error Handling

**Missing spec.md**:
```
ERROR: Missing specification
Next: Run /feature to create spec.md
```

**Missing plan.md**:
```
ERROR: Missing implementation plan
Next: Run /plan specs/$FEATURE/spec.md
```

**Auto-detection failed**:
```
ERROR: No feature detected
Solution: Provide plan file explicitly: /tasks specs/###-feature/plan.md
```

---

**Note**: This command creates tasks.md and automatically invokes /audit quality gate. Do NOT run /audit manually after /tasks - it runs automatically.
