# Phases 1-2: Story-by-Story Execution & Progressive Delivery

## Phase 1: Story-by-Story Execution

**Article VII Mandate**: Implement user stories in priority order, verify each independently.

### Step 1.1: Load Tasks by Story

From tasks.md:
- Phase 3: User Story P1 tasks
- Phase 4: User Story P2 tasks
- Phase 5: User Story P3 tasks

**Example**:
```markdown
## Phase 3: User Story P1 - Email/Password Registration

**Story Goal**: Users can create accounts with email and password

**Independent Test**: Can register new user, receive session token, login with credentials

**Dependencies**: Phase 2 (foundational) complete

### Tests
- [ ] T008 [P] [US1] Write test for AC-P1-001
- [ ] T009 [P] [US1] Write test for AC-P1-002

### Implementation
- [ ] T010 [US1] Enhance User model with password_hash
- [ ] T011 [US1] Create AuthService.register()
- [ ] T012 [US1] Implement POST /api/auth/register

### Verification
- [ ] T015 [US1] Run AC tests (must pass 100%)
- [ ] T016 [US1] Test registration flow end-to-end
- [ ] T017 [US1] Verify story works independently
```

### Step 1.2: Implement P1 Story

Execute all tasks for User Story P1:
1. Tests (Article III: tests first)
2. Implementation (minimal code to pass tests)
3. Verification (all P1 ACs pass)

### Step 1.3: Validate P1 Independently

**Independent Test**: Can P1 be demoed without P2/P3?

Verify:
- All P1 tests pass
- P1 can be used standalone
- No dependencies on incomplete stories

### Step 1.4: Report P1 Completion and Verify Story

**After completing P1 implementation**, report status and automatically verify the story:

```
✓ User Story P1 Complete

Tasks: 10 of 10 (100%)
Tests: 2 of 2 passing (100%)
ACs: 2 of 2 verified (100%)

Independent Test: PASS
- Can register new user
- Can login with credentials
- Feature works standalone
```

**Automatic Story Verification**:

Instruct Claude to run: `/verify $PLAN_FILE --story P1`

This validates (Article VII - Progressive Delivery):
- All P1 tests pass independently (100%)
- P1 can be demoed standalone (no dependencies on P2/P3)
- No blocking dependencies on incomplete stories
- Independent test criteria met

**Expected Verification Output**:
```
✓ Story P1 Verification PASSED

Tests: 8/8 passing (100%)
ACs: 4/4 verified (100%)
Independent Test: PASS (story works standalone)
Can Ship: YES

Next: Implement P2 story or ship P1 as MVP
```

**If Verification Fails**:
```
✗ Story P1 Verification FAILED

Tests: 6/8 passing (75%)
ACs: 3/4 verified (75%)
Failures:
- AC-P1-003: Weak password validation failing

Action:
1. Fix failing tests using debug-issues skill
2. Re-run /verify plan.md --story P1
3. Only proceed to P2 after P1 passes
```

**Only proceed to next story after P1 verification passes** (Article VII mandate)

### Step 1.5: Repeat for P2, P3, etc.

**Same process for each story**:
1. Implement all story tasks
2. Verify story independently (run `/verify $PLAN_FILE --story P2`, `/verify $PLAN_FILE --story P3`, etc.)
3. Report completion
4. Only proceed to next story after current story verification passes

**Example for P2**:
```
✓ User Story P2 Complete

Automatic verification: /verify plan.md --story P2

✓ Story P2 Verification PASSED
Tests: 12/12 passing (100%)
ACs: 5/5 verified (100%)
Independent Test: PASS

Next: Implement P3 story
```

**Progressive Delivery Pattern** (Article VII):
- P1 verified → ship MVP or continue to P2
- P2 verified → ship enhancement or continue to P3
- P3 verified → ship final feature or iterate

Each story must pass verification before proceeding to the next

**Enforcement**:
- [ ] Stories implemented in priority order
- [ ] Each story verified independently
- [ ] No story marked complete without 100% ACs passing

---

## Phase 2: Progressive Delivery

**Article VII Principle**: Each story is shippable when complete.

### Step 2.1: MVP Definition

**MVP = User Story P1 complete and verified**

At P1 completion:
- Feature has minimum viable value
- Can be shipped to users
- Independent of P2/P3 stories

### Step 2.2: Incremental Value

Each story adds incremental value:
- P1: Core functionality (MVP)
- P2: Enhancement to P1 (better, not necessary)
- P3: Nice-to-have (future iteration)

### Step 2.3: Ship-When-Ready

After each story verification:
- Option to ship (if P1)
- Option to demo (any story)
- Option to continue (next story)

**Example**:
```
✓ User Story P1 verified independently

Options:
1. Ship MVP now (P1 is complete and working)
2. Continue to P2 (add enhancements)
3. Demo P1 to stakeholders first

Recommendation: Ship P1 as MVP, iterate with P2/P3 based on feedback
```

**Enforcement**:
- [ ] MVP defined (P1 complete = shippable)
- [ ] Each story independently demostrable
- [ ] Shipping options presented after each story
