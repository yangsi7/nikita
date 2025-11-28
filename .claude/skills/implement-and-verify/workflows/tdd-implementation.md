# Phases 3-7: TDD Implementation Workflow

## Phase 3: Load Tasks

Read **@.claude/templates/plan.md** file and:

1. **Verify dependencies met:**
   ```markdown
   Task T2 depends on T1
   - [ ] Check T1 status = "completed"
   - [ ] If not complete: BLOCK T2, notify user
   ```

2. **Select next task:**
   - Pick lowest-numbered pending task with dependencies met
   - Or user-specified task

3. **Extract ACs:**
   ```markdown
   ### Task 1: Add OAuth Database Schema
   **Acceptance Criteria:**
   - [ ] AC1: users table has google_id VARCHAR(255) column
   - [ ] AC2: Migration runs without errors
   - [ ] AC3: google_id is nullable
   ```

**Enforcement:**
- [ ] All task dependencies verified
- [ ] Task has minimum 2 ACs
- [ ] ACs are testable

## Phase 4: Write Tests FIRST

**CRITICAL:** Write tests from ACs BEFORE implementing. Tests should FAIL initially.

### Test-First Workflow

```
For each AC → Write test → Test FAILS → Implement → Test PASSES
```

**Example:**

**AC1:** "users table has google_id VARCHAR(255) column"

**Test (should FAIL initially):**
```typescript
// migrations/002_add_google_id.test.ts
describe('Add google_id column migration', () => {
  it('AC1: adds google_id VARCHAR(255) column to users table', async () => {
    await runMigration('002_add_google_id')

    const schema = await db.getTableSchema('users')
    const googleIdCol = schema.columns.find(c => c.name === 'google_id')

    expect(googleIdCol).toBeDefined()
    expect(googleIdCol.type).toBe('VARCHAR(255)')
  })
})
```

**Run test (should FAIL):**
```bash
npm test migrations/002_add_google_id.test.ts
# FAIL: Column 'google_id' not found
```

✓ **Test failure proves test is valid** - if it passed without implementation, test would be useless!

### Test Coverage Requirement

**1:1 mapping between ACs and tests:**
```markdown
AC1 → Test 1 (testAddGoogleIdColumn)
AC2 → Test 2 (testMigrationRunsWithoutErrors)
AC3 → Test 3 (testGoogleIdNullable)

Coverage: 3/3 ACs = 100% ✓
```

**Enforcement:**
- [ ] Every AC has corresponding test
- [ ] All tests initially FAIL
- [ ] Tests are specific (not generic)

## Phase 5: Implement

Now implement code to make tests pass.

### Implementation Guidelines

**Minimal implementation:**
- Write simplest code to pass tests
- Don't over-engineer
- Follow YAGNI (You Aren't Gonna Need It)

**Example:**

```sql
-- migrations/002_add_google_id.sql
ALTER TABLE users ADD COLUMN google_id VARCHAR(255) NULL;
```

```bash
# Run tests again (should PASS now)
npm test migrations/002_add_google_id.test.ts
# PASS: All 3 tests pass ✓
```

**If tests still fail:**
1. Debug using analyze-code skill
2. Fix implementation
3. Re-run tests
4. Repeat until all pass

**Enforcement:**
- [ ] Implementation is minimal (YAGNI)
- [ ] Follows project conventions
- [ ] All tests pass

## Phase 6: Verify Against ACs

Run complete verification using **@.claude/templates/verification-report.md**

### Verification Checklist

```markdown
## AC Verification

### Task 1: Add OAuth Database Schema

#### AC1: users table has google_id VARCHAR(255) column
- **Test:** testAddGoogleIdColumn
- **Status:** ✓ PASS
- **Evidence:** Test output shows column exists with correct type

#### AC2: Migration runs without errors
- **Test:** testMigrationRunsWithoutErrors
- **Status:** ✓ PASS
- **Evidence:** Migration completes with exit code 0

#### AC3: google_id is nullable
- **Test:** testGoogleIdNullable
- **Status:** ✓ PASS
- **Evidence:** Schema shows NULL constraint

**Coverage:** 3/3 ACs = 100% ✓
```

### Additional Checks

Beyond AC tests, also run:

```bash
# Lint checks
npm run lint

# Type checks (if TypeScript)
npm run type-check

# Build
npm run build

# Integration tests
npm run test:integration
```

### Handling Failures

**If ANY AC fails:**

```markdown
Status: BLOCKED ❌

Failing: AC2 (Migration runs without errors)
Error: "Column google_id already exists"

Action:
1. Use analyze-code skill to debug
2. Fix issue
3. Re-run verification
4. DO NOT mark task complete until 100% pass
```

**If unfixable after debugging:**
1. Create **@.claude/templates/handover.md**
2. Document blocker
3. Mark task as "blocked"
4. Handover to appropriate agent

**Enforcement:**
- [ ] ALL ACs verified (100% coverage)
- [ ] All ACs pass
- [ ] Lint passes
- [ ] Build succeeds
- [ ] No task marked complete with failures

## Phase 7: Update Plan & Handover

### Update plan.md

```markdown
### Task 1: Add OAuth Database Schema
- **ID:** T1
- **Status:** ✓ completed  # ← Update this
- **Completed:** 2025-10-19T15:30:00Z
- **Verified by:** executor-agent

**Acceptance Criteria:**
- [x] AC1: users table has google_id column ✓
- [x] AC2: Migration runs without errors ✓
- [x] AC3: google_id is nullable ✓
```

### Generate Verification Report

Use **@.claude/templates/verification-report.md**:

```markdown
---
plan_id: "plan-oauth-implementation"
status: "pass"
verified_by: "executor-agent"
timestamp: "2025-10-19T15:30:00Z"
---

# Verification Report: Task T1 Complete

## Test Summary
- Total ACs: 3
- Passed: 3 ✓
- Failed: 0
- Coverage: 100%

## AC Coverage
[Detailed results for each AC]

## Recommendations
None - all ACs passed, ready for next task
```

**File naming:** `YYYYMMDD-HHMM-verification-<task-id>.md`

### Generate Handover (if needed)

**When to create handover:**
- Task blocked on external dependency
- Need different agent (e.g., analyzer for debugging)
- Phase complete, moving to next phase

Use **@.claude/templates/handover.md**:

```markdown
---
from_agent: "executor-agent"
to_agent: "code-analyzer"
chain_id: "oauth-implementation"
timestamp: "2025-10-19T15:30:00Z"
---

# Handover: Task T1 Complete → T2 Ready

## Essential Context
- Completed: T1 (OAuth database schema)
- Next: T2 (OAuth flow implementation)
- Blocker: Need to analyze existing session.ts before implementing

## Pending
- T2: Implement OAuth flow
- T3-T7: Remaining tasks

## Blockers
None for T1. T2 needs analysis of existing auth system.

## Intel Links
- src/auth/session.ts (existing session management)
- migrations/002_add_google_id.sql (just created)
```

**Enforcement:**
- [ ] Plan updated with task status
- [ ] Verification report generated
- [ ] Handover created if transitioning
- [ ] Handover ≤ 600 tokens
