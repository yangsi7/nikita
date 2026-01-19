---
description: Test-driven implementation with AC verification - SDD Phase 8
allowed-tools: Bash(npm:*), Bash(pnpm:*), Bash(pytest:*), Bash(test:*), Bash(project-intel.mjs:*), Read, Write, Edit, Grep, Glob
argument-hint: <plan-file>
---

# Implementation - SDD Phase 8

Implement tasks using test-driven development (TDD) with mandatory AC verification.

## Unified Skill Routing

This command routes to **SDD Phase 8: Implementation** via the unified skill at @.claude/skills/sdd/SKILL.md.

**Phase 8 Workflow:** @.claude/skills/sdd/workflows/08-implementation.md

---

## Prerequisites

**REQUIRED:** Audit must PASS before implementation.

!`test -f specs/*/audit-report.md && grep -q "Result: PASS" specs/*/audit-report.md && echo "✓ Audit PASS - ready to implement" || echo "⚠️ Run /audit first - must PASS before /implement"`

---

## User Input

```text
$1
```

**Input:** Plan file path or auto-detect from spec directory.

---

## Phase 8 Process

Follow the **sdd skill Phase 8** workflow:

### 1. Load Plan & Tasks

- Read plan.md for architecture overview
- Read tasks.md for implementation order
- Select next task (lowest-numbered pending, dependencies met)

### 2. TDD Cycle: Write Tests FIRST

**CRITICAL:** Tests before implementation.

```
RED: Write test from AC → Test FAILS ✗
GREEN: Implement minimal code → Test PASSES ✓
REFACTOR: Clean up → Tests still PASS ✓
```

**Example:**
```python
# For AC: "users table has google_id column"
def test_ac_1_1_1_google_id_column():
    """AC-1.1.1: users table has google_id VARCHAR(255) column"""
    schema = get_table_schema('users')
    assert 'google_id' in schema.columns
    assert schema.columns['google_id'].type == 'VARCHAR(255)'
```

### 3. Implement Minimal Code

- Write only what's needed to pass tests
- Follow YAGNI (You Aren't Gonna Need It)
- No over-engineering

### 4. Verify Against ACs

For each task:
- [ ] All AC tests pass
- [ ] Lint passes
- [ ] Type check passes (if applicable)
- [ ] Build succeeds
- [ ] No regressions in existing tests

### 5. Update Task Status

**Immediately** after completing each task:
```markdown
### T1.1: Task Name
- **Status**: [x] Complete
- **ACs**:
  - [x] AC-1.1.1: First criterion
  - [x] AC-1.1.2: Second criterion
```

---

## Quality Gate

**Task Completion Requirements:**
- ✓ 100% AC coverage (every AC has test)
- ✓ All tests pass
- ✓ Code quality checks pass
- ✓ No regressions

**❌ NEVER mark task complete with failing tests**

---

## Handling Failures

If ANY test fails:
1. **Do NOT mark task complete**
2. Debug the issue (use debug-issues skill if needed)
3. Fix implementation
4. Re-run verification
5. Only mark complete when 100% pass

If unfixable:
1. Create handover document
2. Mark task as "blocked"
3. Document blocker details

---

## CoD^Σ Evidence Pattern

```
Step 1: → WriteTests (from ACs, should FAIL)
  ↳ File: tests/test_feature.py
  ↳ Result: 3 tests created, 3 failed ✗

Step 2: → Implement
  ↳ File: src/feature.py:45
  ↳ Code: Added required functionality

Step 3: → RunTests (should PASS)
  ↳ Command: pytest tests/test_feature.py
  ↳ Result: 3 passed ✓

Step 4: ∘ VerifyACs
  ↳ AC-1.1.1: ✓ Test passes
  ↳ AC-1.1.2: ✓ Test passes
  ↳ Coverage: 100%
  ↳ Status: TASK COMPLETE ✓
```

---

## Story-by-Story Execution

Tasks organized by user story priority:

```
P1 Stories (Must-have)
  └── T1.1, T1.2, T1.3 → Complete all before P2

P2 Stories (Should-have)
  └── T2.1, T2.2 → Complete after P1

P3 Stories (Nice-to-have)
  └── T3.1 → Complete after P2
```

---

## Output

**Per task:**
- Updated tasks.md with completion status
- Test files in appropriate test directory
- Implementation code

**End of feature:**
- All tasks marked complete
- All tests passing
- Verification report generated

---

## Start Now

Read the plan file and tasks file, then begin TDD implementation cycle.

**Remember:** Test FIRST, implement SECOND, verify ALWAYS.
