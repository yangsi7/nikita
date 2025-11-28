# Phase 4: Parallelization Marking (Article VIII)

**Purpose**: Identify and mark tasks that can execute simultaneously to enable faster development.

---

## Criteria for [P] Marker

Task is parallelizable if:
1. **Different files**: No file conflicts with other parallel tasks
2. **No dependencies**: Doesn't depend on incomplete tasks
3. **Independent**: Can run without coordination

**Example**:
```
✓ [P] - [ ] T008 [P] [US1] Write test in tests/auth/register.test.ts
✓ [P] - [ ] T009 [P] [US1] Write test in tests/auth/login.test.ts
          (Different files, no dependencies)

✗ NO [P] - [ ] T010 [US1] Enhance User model
✗ NO [P] - [ ] T011 [US1] Create AuthService using User model
          (T011 depends on T010, must be sequential)
```

---

## Parallelization Assessment Process

### Step 1: Review Task List

For each task, identify:
- Which file(s) does it modify?
- Which previous tasks does it depend on?
- Can it execute independently?

### Step 2: Mark Parallel Tasks

Add `[P]` marker to task if all criteria met:

```markdown
✓ PARALLEL:
- [ ] T008 [P] [US1] Write test for AC-P1-001 in tests/auth/register.test.ts
- [ ] T009 [P] [US1] Write test for AC-P1-002 in tests/auth/register.test.ts
(Same story, different test files, no dependencies)

✓ PARALLEL:
- [ ] T002 [P] Install dependencies
- [ ] T003 [P] Configure environment variables
- [ ] T004 [P] Set up development database
(Setup tasks, independent operations)

✗ SEQUENTIAL:
- [ ] T010 [US1] Enhance User model with password_hash field
- [ ] T011 [US1] Create AuthService.register() using User model
(T011 requires T010, must run after)
```

### Step 3: Document Parallel Opportunities

In task summary, count parallelizable tasks per phase:

```markdown
Parallel Opportunities:
- Setup (Phase 1): 3 of 4 tasks can run in parallel
- Foundational (Phase 2): 0 of 3 (all sequential)
- User Story P1 (Phase 3): 2 test tasks can run in parallel
- User Story P2 (Phase 4): 3 test tasks can run in parallel
- Polish (Phase 6): 5 of 8 tasks can run in parallel
```

---

## Common Parallelization Patterns

### Pattern 1: Test Writing

**Multiple tests for same story** → Parallel
```
✓ [P] T008 [US1] Write test for AC-P1-001
✓ [P] T009 [US1] Write test for AC-P1-002
(Different test files, same story)
```

### Pattern 2: Setup Tasks

**Independent configuration steps** → Parallel
```
✓ [P] T002 Install dependencies
✓ [P] T003 Configure environment
✓ [P] T004 Set up database
(No interdependencies)
```

### Pattern 3: Documentation Tasks

**Updating different docs** → Parallel
```
✓ [P] T021 Update API documentation
✓ [P] T022 Update README
✓ [P] T023 Update changelog
(Different files, independent)
```

### Pattern 4: Sequential Implementation

**Dependent code changes** → NOT Parallel
```
✗ T010 Create User model
✗ T011 Create AuthService using User
✗ T012 Create API endpoint using AuthService
(Linear dependency chain)
```

---

## Key Principles

1. **When in doubt, don't mark parallel**: Sequential is safer than introducing race conditions
2. **Tests are often parallel**: Different test files can usually run simultaneously
3. **Model dependencies are sequential**: If B uses A, B must wait for A
4. **Documentation is often parallel**: Different doc files rarely conflict
5. **Setup tasks vary**: Some parallel (install deps), some sequential (database migrations)

---

## Verification Checklist

Before finalizing task list:

- [ ] All parallel tasks marked with [P]
- [ ] No [P] marker on tasks with dependencies
- [ ] Parallel count documented in summary
- [ ] Reviewed for accidental file conflicts
- [ ] Verified no shared state between parallel tasks
