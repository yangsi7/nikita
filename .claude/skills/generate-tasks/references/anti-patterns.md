# Anti-Patterns and Best Practices

**Purpose**: Avoid common mistakes in task organization and ensure constitutional compliance.

---

## Anti-Patterns to Avoid

### ❌ Layer-Based Organization

**BAD Example**:
```markdown
## Phase 3: Models
- [ ] T006 Create User model
- [ ] T007 Create Session model
- [ ] T008 Create Order model

## Phase 4: Services
- [ ] T009 Create UserService
- [ ] T010 Create SessionService
- [ ] T011 Create OrderService

## Phase 5: API Endpoints
- [ ] T012 Create POST /users
- [ ] T013 Create POST /sessions
- [ ] T014 Create POST /orders
```

**Why This Fails**:
- Violates Article VII (user-story-centric organization)
- No independent test criteria per component
- Big-bang integration (nothing works until all layers done)
- Cannot demo individual stories
- Difficult to prioritize work

### ✓ Story-Based Organization

**GOOD Example**:
```markdown
## Phase 3: User Story P1 - User Registration
Independent Test: Can register and login

### Tests
- [ ] T006 [P] [US1] Test user registration

### Implementation
- [ ] T007 [US1] Create User model
- [ ] T008 [US1] Create UserService.register()
- [ ] T009 [US1] Create POST /api/users

### Verification
- [ ] T010 [US1] Verify story P1 works independently

## Phase 4: User Story P2 - Session Management
Independent Test: Can create and validate sessions

### Tests
- [ ] T011 [P] [US2] Test session creation

### Implementation
- [ ] T012 [US2] Create Session model
- [ ] T013 [US2] Create SessionService
- [ ] T014 [US2] Create POST /api/sessions

### Verification
- [ ] T015 [US2] Verify story P2 works independently
```

**Why This Works**:
- Article VII compliant (story-centric)
- Independent test criteria per story
- Can demo P1 without P2 (progressive delivery)
- Clear priorities (P1 is MVP, P2 is enhancement)
- Test-first approach (Article III)

---

### ❌ Tasks Without Story Labels

**BAD Example**:
```markdown
- [ ] T010 Create User model
- [ ] T011 Create AuthService
- [ ] T012 Create login endpoint
```

**Problem**: Cannot trace which story each task belongs to

### ✓ Tasks With Story Labels

**GOOD Example**:
```markdown
- [ ] T010 [US1] Create User model for registration
- [ ] T011 [US1] Create AuthService.register() method
- [ ] T012 [US2] Create login endpoint for authentication
```

**Benefit**: Clear traceability (T010-T011 for US1, T012 for US2)

---

### ❌ Skipping Test Tasks

**BAD Example**:
```markdown
## Phase 3: User Story P1 - Registration

### Implementation
- [ ] T006 Create User model
- [ ] T007 Create AuthService
- [ ] T008 Create registration endpoint
```

**Problem**: Violates Article III (Test-First Imperative)

### ✓ Tests Before Implementation

**GOOD Example**:
```markdown
## Phase 3: User Story P1 - Registration

### Tests (Article III: Test-First)
- [ ] T006 [P] [US1] Write test for AC-P1-001

### Implementation
- [ ] T007 [US1] Create User model
- [ ] T008 [US1] Create AuthService
- [ ] T009 [US1] Create registration endpoint

### Verification
- [ ] T010 [US1] Run AC tests (must pass 100%)
```

**Benefit**: Tests written first, implementation follows TDD

---

### ❌ Mixing Multiple Stories in One Phase

**BAD Example**:
```markdown
## Phase 3: Core Features

- [ ] T006 [US1] Registration model
- [ ] T007 [US2] Login endpoint
- [ ] T008 [US1] Registration endpoint
- [ ] T009 [US2] Login validation
```

**Problem**: Violates story independence, hard to demo incrementally

### ✓ One Phase Per Story

**GOOD Example**:
```markdown
## Phase 3: User Story P1 - Registration
- [ ] T006 [US1] Registration model
- [ ] T008 [US1] Registration endpoint

## Phase 4: User Story P2 - Login
- [ ] T007 [US2] Login endpoint
- [ ] T009 [US2] Login validation
```

**Benefit**: Clear story boundaries, can complete and demo P1 before starting P2

---

### ❌ Creating Tasks That Span Stories

**BAD Example**:
```markdown
- [ ] T010 Create authentication system (covers registration + login + password reset)
```

**Problem**: Too broad, spans multiple stories, violates independence

### ✓ Story-Specific Tasks

**GOOD Example**:
```markdown
- [ ] T010 [US1] Implement registration authentication
- [ ] T015 [US2] Implement login authentication
- [ ] T020 [US3] Implement password reset authentication
```

**Benefit**: Each task maps to one story, independent implementation

---

### ❌ Forgetting Parallelization Markers

**BAD Example**:
```markdown
- [ ] T006 Write test for AC-P1-001
- [ ] T007 Write test for AC-P1-002
- [ ] T008 Write test for AC-P2-001
```

**Problem**: Misses opportunity for faster development

### ✓ Marking Parallel Tasks

**GOOD Example**:
```markdown
- [ ] T006 [P] [US1] Write test for AC-P1-001
- [ ] T007 [P] [US1] Write test for AC-P1-002
- [ ] T008 [P] [US2] Write test for AC-P2-001
```

**Benefit**: Clear which tasks can run simultaneously (Article VIII)

---

### ❌ Creating <2 Tests Per Story

**BAD Example**:
```markdown
## Phase 3: User Story P1 - Registration

### Tests
- [ ] T006 [US1] Test registration endpoint
```

**Problem**: Violates Article III (minimum 2 ACs per story)

### ✓ Minimum 2 Tests Per Story

**GOOD Example**:
```markdown
## Phase 3: User Story P1 - Registration

### Tests
- [ ] T006 [P] [US1] Test AC-P1-001 (valid registration)
- [ ] T007 [P] [US1] Test AC-P1-002 (weak password rejection)
```

**Benefit**: Article III compliant (≥2 ACs per story)

---

## Best Practices Checklist

### Task Organization (Article VII)

- ✓ **DO**: Organize tasks by user story (one phase per story)
- ✓ **DO**: Label every task with [US#] for traceability
- ✓ **DO**: Include independent test criteria per story
- ✓ **DO**: Keep story phases independent (can demo without other stories)
- ✗ **DON'T**: Organize by technical layer ("All models", "All services")
- ✗ **DON'T**: Mix multiple stories in one phase
- ✗ **DON'T**: Create tasks that span multiple stories

### Test-First Approach (Article III)

- ✓ **DO**: Write test tasks BEFORE implementation tasks
- ✓ **DO**: Create minimum 2 tests per user story
- ✓ **DO**: Map every AC to at least one test task
- ✓ **DO**: Include verification tasks to confirm ACs pass
- ✗ **DON'T**: Skip test tasks
- ✗ **DON'T**: Create stories with <2 ACs
- ✗ **DON'T**: Put tests after implementation

### Parallelization (Article VIII)

- ✓ **DO**: Mark tasks with [P] if they can run simultaneously
- ✓ **DO**: Check for file conflicts before marking parallel
- ✓ **DO**: Document parallel opportunities in summary
- ✗ **DON'T**: Mark dependent tasks as parallel
- ✗ **DON'T**: Assume all tasks are sequential
- ✗ **DON'T**: Skip parallelization analysis

### Task Validation

- ✓ **DO**: Verify 100% AC coverage (every AC has test task)
- ✓ **DO**: Check all tasks have [US#] labels
- ✓ **DO**: Confirm story independence (can demo alone)
- ✓ **DO**: Validate dependency graph is correct
- ✗ **DON'T**: Leave ACs without test tasks
- ✗ **DON'T**: Create circular dependencies
- ✗ **DON'T**: Skip verification tasks

### Quality Gates

- ✓ **DO**: Automatically invoke /audit after task generation
- ✓ **DO**: Fix CRITICAL issues before implementation
- ✓ **DO**: Document audit results in tasks.md
- ✗ **DON'T**: Ask user to run /audit manually
- ✗ **DON'T**: Proceed to implementation if audit fails
- ✗ **DON'T**: Ignore warnings from audit

---

## Common Mistakes and Fixes

### Mistake 1: "All Models" Phase

**Symptom**: Phase named "Create All Models" with User, Session, Order models

**Fix**: Split into user story phases:
- Phase 3: US P1 (needs User model)
- Phase 4: US P2 (needs Session model)
- Phase 5: US P3 (needs Order model)

### Mistake 2: Tests After Implementation

**Symptom**: Implementation tasks listed before test tasks

**Fix**: Reorder tasks - tests first, then implementation, then verification

### Mistake 3: No [US#] Labels

**Symptom**: Tasks like "T010 Create User model" without story reference

**Fix**: Add story labels: "T010 [US1] Create User model for registration"

### Mistake 4: Single Test for Story

**Symptom**: User story with only 1 AC test

**Fix**: Return to plan.md, add second AC, create test task for it

### Mistake 5: Missing Parallel Markers

**Symptom**: Test tasks without [P] even though different files

**Fix**: Review tasks, add [P] to tasks that can run simultaneously

---

## Validation Workflow

Before finalizing tasks.md:

1. **Check Organization** → Each user story has own phase? ✓
2. **Check Labels** → All tasks have [US#]? ✓
3. **Check Test-First** → Tests before implementation? ✓
4. **Check AC Coverage** → Every AC has ≥1 test? ✓
5. **Check Parallelization** → [P] markers added where applicable? ✓
6. **Check Independence** → Each story has independent test criteria? ✓
7. **Run /audit** → Quality gate passes? ✓

If any check fails, fix before proceeding to implementation.
