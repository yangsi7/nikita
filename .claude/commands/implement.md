---
description: Implement tasks from plan using test-driven development (TDD) with mandatory AC verification via implement-and-verify skill (project)
allowed-tools: Bash(npm:*), Bash(test:*), Bash(project-intel.mjs:*), Read, Write, Edit, Grep, Glob
argument-hint: <plan-file>
---

## Pre-Execution

<!-- Bash pre-validation removed - $1 not available in !`` context. Claude will validate file existence when reading. -->

# Implement Command - Test-Driven Implementation with AC Verification

You are now executing the `/implement <plan-file>` command. This command implements tasks from a plan using **test-driven development (TDD)** with mandatory AC verification using the **implement-and-verify skill**.

## Your Task

Implement tasks from the provided plan using the **implement-and-verify skill** (@.claude/skills/implement-and-verify/SKILL.md).

**Input Plan:** `$1` (validated to exist)

## Process Overview

Follow the implement-and-verify skill workflow:

1. **Load Plan** (Phase 1)
   - Read the plan file: `$1` (should use @.claude/templates/plan.md format)
   - Verify task dependencies are met
   - Select next task to implement (lowest-numbered pending task with deps met)
   - Extract ACs for selected task

2. **Write Tests FIRST** (Phase 2)
   - **CRITICAL:** Write tests BEFORE implementing
   - Create one test per AC (1:1 mapping)
   - Tests should FAIL initially (if they pass, test is invalid!)
   - Example:
     ```typescript
     // For AC: "users table has google_id VARCHAR(255) column"
     it('AC1: adds google_id VARCHAR(255) column to users table', async () => {
       await runMigration('002_add_google_id')
       const schema = await db.getTableSchema('users')
       const googleIdCol = schema.columns.find(c => c.name === 'google_id')
       expect(googleIdCol).toBeDefined()
       expect(googleIdCol.type).toBe('VARCHAR(255)')
     })
     ```
   - Run tests to verify they FAIL

3. **Implement** (Phase 3)
   - Write minimal code to make tests pass
   - Follow YAGNI (You Aren't Gonna Need It)
   - No over-engineering
   - Run tests frequently
   - Fix until all tests pass

4. **Verify Against ACs** (Phase 4)
   - Run ALL tests (not just new ones)
   - Run lint checks
   - Run type checks (if TypeScript)
   - Run build
   - Use @.claude/templates/verification-report.md to document results
   - **CRITICAL:** Task cannot be marked complete unless ALL ACs pass

5. **Update Plan & Handover** (Phase 5)
   - Update plan.md with task status = "completed"
   - Mark all ACs as checked
   - Add completion timestamp
   - Generate verification report
   - If blocked, create @.claude/templates/handover.md

## Templates Reference

**Input Templates:**
- @.claude/templates/plan.md - Implementation plans (input)

**Output Templates:**
- @.claude/templates/verification-report.md - AC verification results (required for each task)
- @.claude/templates/handover.md - For blocked tasks or transitions (if needed)

## Test-Driven Development (TDD) Rules

### Red-Green-Refactor Cycle

```
1. RED: Write test from AC → Test FAILS ✗
2. GREEN: Implement minimal code → Test PASSES ✓
3. REFACTOR: Clean up code → Tests still PASS ✓
```

### Why Test-First Matters

**❌ Code-first approach:**
```
1. Implement feature
2. Write tests
3. Tests pass (but are they testing the right thing?)
```

**✓ Test-first approach:**
```
1. Write tests from ACs (tests FAIL ✗)
2. Implement feature
3. Tests pass (proves implementation meets ACs ✓)
```

Test failure before implementation PROVES the test is valid!

## AC Verification Requirements

### 100% Coverage Required

**❌ Violation:**
```markdown
Total ACs: 3
Tested ACs: 2
Coverage: 67%  # NOT ACCEPTABLE!
Task Status: Complete  # WRONG!
```

**✓ Correct:**
```markdown
Total ACs: 3
Tested ACs: 3
Coverage: 100% ✓
Task Status: Complete ✓
```

### No Completion Without Passing ACs

**❌ Violation:**
```markdown
Task: Add login feature
Status: ✓ Complete
Test Results: 2 passed, 1 failed
```

**✓ Correct:**
```markdown
Task: Add login feature
Status: BLOCKED
Test Results: 2 passed, 1 failed
Action:
1. Debug failing test (use debug-issues skill)
2. Fix implementation
3. Re-run tests
4. Mark complete ONLY when all pass
```

## Handling Test Failures

If ANY test fails:

1. **Do NOT mark task complete**
2. Use **debug-issues skill** (@.claude/skills/debug-issues/SKILL.md) to diagnose
3. Fix the issue
4. Re-run verification
5. Only mark complete when 100% pass

If unfixable after debugging:

1. Create @.claude/templates/handover.md
2. Document the blocker
3. Mark task as "blocked"
4. Hand over to appropriate agent (code-analyzer for investigation)

## CoD^Σ Reasoning

Use @.claude/shared-imports/CoD_Σ.md for implementation reasoning:

```
Step 1: → WriteTests (from ACs, should FAIL)
  ↳ File: src/components/LoginForm.test.tsx
  ↳ Result: 3 tests created, 3 failed ✗

Step 2: → Implement
  ↳ File: src/components/LoginForm.tsx:45
  ↳ Code: validateEmail + error display + disabled submit

Step 3: → RunTests (should PASS)
  ↳ Command: npm test LoginForm.test.tsx
  ↳ Result: 3 passed ✓

Step 4: ∘ VerifyACs
  ↳ AC1: ✓ Test passes
  ↳ AC2: ✓ Test passes
  ↳ AC3: ✓ Test passes
  ↳ Coverage: 100%
  ↳ Status: TASK COMPLETE ✓
```

## Verification Checklist

Before marking ANY task complete, verify:

```markdown
## Verification Checklist

### AC Verification
- [ ] All ACs have corresponding tests (1:1 mapping)
- [ ] All AC tests pass
- [ ] AC coverage: 100%

### Code Quality
- [ ] Lint passes (`npm run lint` or equivalent)
- [ ] Type check passes (if TypeScript)
- [ ] Build succeeds (`npm run build` or equivalent)

### Integration
- [ ] All existing tests still pass (no regressions)
- [ ] Integration tests pass (if applicable)

### Documentation
- [ ] Verification report generated using template
- [ ] Plan.md updated with task status
- [ ] All ACs marked as checked
```

## Expected Outputs

For each completed task:

1. **Updated plan.md** - Task marked complete, ACs checked
2. **verification-report.md** - Saved as `YYYYMMDD-HHMM-verification-{task-id}.md`
3. *If blocked:* **handover.md** - Saved as `YYYYMMDD-HHMM-handover-{from}-to-{to}.md`

## Success Criteria

Before completing the command, verify:
- [ ] Selected task dependencies were met
- [ ] Tests written from ACs FIRST
- [ ] All tests pass (100%)
- [ ] Lint, type-check, build pass
- [ ] Verification report generated
- [ ] Plan updated with task status
- [ ] No task marked complete with failing tests

## Start Now

Read the plan file: `$1`

Identify the next task to implement (check dependencies).

Then proceed with the implement-and-verify skill workflow using TDD approach.

**Remember:** Test FIRST, implement SECOND, verify ALWAYS.
