# Implementation Examples (Few-Shot)

## Example 1: Successful Implementation

**Input:** Task T1 from plan.md
```markdown
### Task 1: Add email validation to login form
**Acceptance Criteria:**
- AC1: Email field rejects invalid formats
- AC2: Email field shows error message
- AC3: Form submission blocked until valid
```

**Execution (CoD^Σ):**
```
Step 1: → WriteTests (from ACs, should FAIL)
  ↳ File: src/components/LoginForm.test.tsx
  ↳ Tests:
    - testRejectsInvalidEmail (AC1)
    - testShowsErrorMessage (AC2)
    - testBlocksSubmission (AC3)

Step 2: → RunTests (expect FAIL)
  ↳ Command: npm test LoginForm.test.tsx
  ↳ Result: 3 failed ✗ (expected - not implemented yet)

Step 3: → Implement
  ↳ File: src/components/LoginForm.tsx:45
  ↳ Code: validateEmail regex + error display + disabled submit

Step 4: → RunTests (expect PASS)
  ↳ Command: npm test LoginForm.test.tsx
  ↳ Result: 3 passed ✓

Step 5: ∘ VerifyACs
  ↳ AC1: ✓ Test passes
  ↳ AC2: ✓ Test passes
  ↳ AC3: ✓ Test passes
  ↳ Coverage: 100%
  ↳ Status: TASK COMPLETE ✓
```

## Example 2: Failing AC → Debug → Fix

**Input:** Task T2 with AC failure
```markdown
### Task 2: Database migration for OAuth
**Acceptance Criteria:**
- AC1: Migration creates google_id column
- AC2: Migration runs without errors
```

**Execution:**
```
Step 1: → Implement
  ↳ File: migrations/002_add_google_id.sql
  ↳ Code: ALTER TABLE users ADD COLUMN google_id VARCHAR(255);

Step 2: → RunMigration
  ↳ Command: npm run migrate
  ↳ Result: ERROR - column google_id already exists ❌

Step 3: → VerifyACs
  ↳ AC1: ✗ FAIL (column exists but migration errored)
  ↳ AC2: ✗ FAIL (migration errored)
  ↳ Status: BLOCKED

Step 4: → Debug (use analyze-code skill)
  ↳ Query: project-intel.mjs --search "google_id"
  ↳ Data: Found in migrations/001_initial.sql (already added!)

Step 5: ∘ Fix
  ↳ Resolution: Migration 002 is duplicate
  ↳ Action: Mark task as "not needed (already done in 001)"
  ↳ Update plan status

Step 6: → ReVerifyACs
  ↳ AC1: ✓ Column exists (from migration 001)
  ↳ AC2: ✓ No errors (skip duplicate migration)
  ↳ Status: COMPLETE ✓
```

## Example 3: Rollback on Breaking Change

**Input:** Task T5 causing test failures
```markdown
### Task 5: Refactor API response format
**Acceptance Criteria:**
- AC1: New format includes { data, meta }
- AC2: All existing API tests pass
- AC3: No breaking changes to clients
```

**Execution:**
```
Step 1: → Implement
  ↳ File: src/api/format.ts
  ↳ Change: Return { data: result, meta: {...} }

Step 2: → RunTests
  ↳ Command: npm test
  ↳ Result: 15 tests FAILED ✗

Step 3: → VerifyACs
  ↳ AC1: ✓ New format works
  ↳ AC2: ✗ FAIL - 15 tests expect old format
  ↳ AC3: ✗ FAIL - breaking change detected
  ↳ Status: BLOCKED (ACs failed)

Step 4: → Rollback
  ↳ Command: git checkout src/api/format.ts
  ↳ Reason: Breaking change violates AC3

Step 5: → UpdatePlan
  ↳ Add task T5.1: Update all tests FIRST
  ↳ Add task T5.2: Then change API format
  ↳ Dependencies: T5.1 → T5.2

Step 6: ∘ Handover
  ↳ Create handover.md to planner
  ↳ Reason: Plan needs revision (missed dependency)
```

## Example 4: Story-Level Verification

**Input:** User Story P1 complete
```markdown
## Phase 3: User Story P1 - Basic Authentication

**Story Goal**: Users can login with email/password

**Tasks**:
- [ ] T10: Write tests for authentication
- [ ] T11: Implement auth service
- [ ] T12: Create login endpoint
```

**Execution:**
```
Step 1: → ImplementStory (all tasks)
  ↳ T10: Tests written (3 tests, all FAIL initially)
  ↳ T11: AuthService implemented (tests now PASS)
  ↳ T12: POST /auth/login endpoint (integration tests PASS)

Step 2: → VerifyStoryIndependently
  ↳ Command: /verify plan.md --story P1
  ↳ Tests: 8/8 passing (100%)
  ↳ ACs: 4/4 verified (100%)
  ↳ Independent Test: PASS (story works standalone)

Step 3: ∘ ReportCompletion
  ↳ Story P1: COMPLETE ✓
  ↳ Can Ship: YES (MVP ready)
  ↳ Next: Implement P2 or ship P1

Step 4: → DecideNext
  ↳ Option 1: Ship P1 as MVP now
  ↳ Option 2: Continue to P2 (add OAuth)
  ↳ Recommendation: Ship P1, get user feedback
```

## Example 5: Progressive Delivery Workflow

**Input:** Multi-story feature implementation

**Execution:**
```
Step 1: → ImplementP1 (Email/Password Auth)
  ↳ All P1 tasks complete
  ↳ /verify plan.md --story P1 → PASS
  ↳ Status: P1 SHIPPABLE ✓

Step 2: → DecisionPoint
  ↳ User chooses: Continue to P2 (add OAuth)

Step 3: → ImplementP2 (OAuth Integration)
  ↳ All P2 tasks complete
  ↳ /verify plan.md --story P2 → PASS
  ↳ Status: P2 SHIPPABLE ✓

Step 4: → DecisionPoint
  ↳ User chooses: Continue to P3 (add 2FA)

Step 5: → ImplementP3 (Two-Factor Auth)
  ↳ All P3 tasks complete
  ↳ /verify plan.md --story P3 → PASS
  ↳ Status: P3 SHIPPABLE ✓

Step 6: ∘ FinalVerification
  ↳ All stories verified independently
  ↳ Complete feature ready for production
  ↳ Each story was shippable at its completion point
```

## Key Patterns

### Pattern 1: Test-First Always
```
Write Test → Test FAILS → Implement → Test PASSES
```

### Pattern 2: Debug on Failure
```
AC Fails → Debug with analyze-code → Fix → Re-verify → PASS
```

### Pattern 3: Rollback on Breaking Changes
```
Change → Tests Fail → Rollback → Update Plan → Re-implement Correctly
```

### Pattern 4: Story-Level Progressive Delivery
```
P1 Complete → Verify → Ship or Continue → P2 Complete → Verify → Ship or Continue
```

### Pattern 5: Handover on Blockers
```
Blocked → Document Blocker → Create Handover → Transfer to Appropriate Agent
```
