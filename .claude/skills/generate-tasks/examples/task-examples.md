# Complete Task Breakdown Example

**Feature**: User Authentication System
**User Stories**: 2 (P1: Registration, P2: Login)
**Phases**: 6 total (Setup → Foundational → 2 User Stories → Polish)

---

## Input

**From spec.md**:
- User Story P1: Users can create accounts with email and password
- User Story P2: Users can login with registered credentials

**From plan.md**:
- AC-P1-001: User can register with valid credentials
- AC-P1-002: System rejects weak passwords
- AC-P2-001: User can login with valid credentials
- AC-P2-002: System rejects invalid credentials

**From plan.md (components)**:
- Model: User (enhance with password_hash)
- Service: AuthService (register, login methods)
- API: POST /api/auth/register, POST /api/auth/login
- UI: RegisterForm, LoginForm

---

## Output: tasks.md

```markdown
---
feature: 001-user-authentication
created: 2025-10-23
plan: specs/001-user-authentication/plan.md
status: Ready for Implementation
total_tasks: 23
---

# Task Breakdown: User Authentication

## Summary

**Total Tasks**: 23
- Phase 1 (Setup): 3 tasks
- Phase 2 (Foundational): 2 tasks
- Phase 3 (US P1 - Registration): 9 tasks (2 tests, 5 impl, 2 verify)
- Phase 4 (US P2 - Login): 6 tasks (2 tests, 3 impl, 1 verify)
- Phase 5 (Polish): 3 tasks

**Parallel Opportunities**: 8 tasks marked [P]

**Acceptance Criteria Coverage**: 4 ACs → 4 test tasks (100%)

---

## Phase 1: Setup

**Purpose**: Initialize project structure and dependencies

- [ ] T001 Create project structure per plan.md
- [ ] T002 [P] Install dependencies: @supabase/auth-helpers, bcrypt, zod
- [ ] T003 [P] Configure environment variables (.env.local)

**Dependencies**: None

---

## Phase 2: Foundational

**Purpose**: Blocking prerequisites for ALL user stories

- [ ] T004 Create users table schema in database (id, email, password_hash, created_at)
- [ ] T005 Set up Supabase client configuration in lib/supabase.ts

**Dependencies**: Phase 1 complete

---

## Phase 3: User Story P1 - Email/Password Registration

**Story Goal**: Users can create accounts with email and password

**Independent Test**: Can register new user, receive session token, login with credentials

**Dependencies**: Phase 2 (foundational) complete

### Tests (Article III: Test-First)

- [ ] T006 [P] [US1] Write test for AC-P1-001 (valid registration) in tests/auth/register.test.ts
  - **AC**: User can register with valid email and strong password
  - **Test**: POST /api/auth/register with valid data returns 201 + session token

- [ ] T007 [P] [US1] Write test for AC-P1-002 (weak password rejection) in tests/auth/register.test.ts
  - **AC**: System rejects passwords that don't meet strength requirements
  - **Test**: POST /api/auth/register with weak password returns 400 with error message

### Implementation

- [ ] T008 [US1] Enhance User model with password_hash field in models/user.ts
  - Add password_hash: string field
  - Add validation for email format

- [ ] T009 [US1] Create AuthService.register() method in services/auth-service.ts
  - Hash password using bcrypt
  - Create user in database
  - Return user + session token

- [ ] T010 [US1] Implement POST /api/auth/register endpoint in api/auth/register.ts
  - Validate request body with Zod
  - Call AuthService.register()
  - Return 201 with user + session

- [ ] T011 [US1] Create RegisterForm component in components/auth/RegisterForm.tsx
  - Email input (validated)
  - Password input (with strength indicator)
  - Submit button
  - Error message display

- [ ] T012 [US1] Integrate RegisterForm with /register route in pages/register.tsx
  - Render RegisterForm
  - Handle form submission
  - Redirect to dashboard on success

### Verification

- [ ] T013 [US1] Run AC tests (must pass 100%)
  - Execute: npm test tests/auth/register.test.ts
  - Verify both AC-P1-001 and AC-P1-002 pass

- [ ] T014 [US1] Test registration flow end-to-end with quickstart scenario
  - Navigate to /register
  - Enter valid credentials
  - Verify successful registration and session creation
  - Verify redirect to dashboard

---

## Phase 4: User Story P2 - Login

**Story Goal**: Users can login with registered credentials

**Independent Test**: Can login with username/password and receive session token

**Dependencies**: Phase 2 (foundational) complete
**Note**: P2 can start after Phase 2, does NOT require P1 complete (independence)

### Tests (Article III: Test-First)

- [ ] T015 [P] [US2] Write test for AC-P2-001 (valid login) in tests/auth/login.test.ts
  - **AC**: User can login with registered email and password
  - **Test**: POST /api/auth/login with valid credentials returns 200 + session token

- [ ] T016 [P] [US2] Write test for AC-P2-002 (invalid credentials) in tests/auth/login.test.ts
  - **AC**: System rejects login with incorrect password
  - **Test**: POST /api/auth/login with wrong password returns 401 with error

### Implementation

- [ ] T017 [US2] Create AuthService.login() method in services/auth-service.ts
  - Find user by email
  - Verify password with bcrypt
  - Return session token

- [ ] T018 [US2] Implement POST /api/auth/login endpoint in api/auth/login.ts
  - Validate request body
  - Call AuthService.login()
  - Return 200 with session

- [ ] T019 [US2] Create LoginForm component and integrate with /login route
  - Email input
  - Password input
  - Submit button
  - Error handling

### Verification

- [ ] T020 [US2] Run all US2 tests and verify story works independently
  - Execute: npm test tests/auth/login.test.ts
  - Test login flow end-to-end
  - Verify works WITHOUT P1 implementation (story independence)

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, cleanup, final validation

**Dependencies**: All user story phases complete

- [ ] T021 [P] Update API documentation for /api/auth/register and /api/auth/login endpoints
- [ ] T022 [P] Run full test suite and verify 100% AC pass rate
- [ ] T023 Build production bundle and verify no errors

---

## Task Completion Checklist

**For Each Task**:
1. Read task description and AC reference
2. Implement or write test per task requirement
3. Verify implementation works (run relevant tests)
4. Mark task as complete: `- [x]`

**For Each Phase**:
1. Complete all tasks in sequential order (unless marked [P])
2. Run verification tasks for that phase
3. Verify phase goals met before moving to next phase

**For User Story Phases**:
1. Tests MUST pass before marking story complete
2. Story MUST work independently (can demo without other stories)
3. All ACs for story MUST be verified

---

## Quality Gate

**Status**: Audit ran automatically on task generation
**Report**: 20251023-1430-audit-001-user-authentication.md
**Result**: PASS ✓
**Date**: 2025-10-23

**Next Step**: Run `/implement plan.md` to begin implementation
```

---

## Key Observations

### Article VII Compliance (User-Story-Centric)

- ✓ Phase per story: P1 (Registration) and P2 (Login) are separate phases
- ✓ Each phase has independent test criteria
- ✓ Stories can be implemented in any order after foundational phase
- ✓ NO "all models" or "all services" phases (layer-based organization)

### Article III Compliance (Test-First)

- ✓ Tests come before implementation in each story phase
- ✓ Each AC has ≥1 test task
- ✓ Test tasks explicitly reference AC IDs
- ✓ Verification tasks ensure ACs pass

### Article VIII Compliance (Parallelization)

- ✓ Setup tasks marked [P] (install dependencies, configure env)
- ✓ Test writing tasks marked [P] (different test files)
- ✓ Polish tasks marked [P] (update docs, run tests)
- ✓ Implementation tasks NOT marked [P] (sequential dependencies)

### Progressive Delivery Pattern

```
Phase 1-2 → Phase 3 (US P1) → Verify P1 → Ship MVP
                           → Phase 4 (US P2) → Verify P2 → Ship Enhancement
```

**P2 can start after foundational** (does not depend on P1 complete) = True independence

---

## Template Reuse

This example demonstrates the standard pattern:
1. Setup (project structure, dependencies)
2. Foundational (shared prerequisites)
3. User Story Phases (tests → implementation → verification)
4. Polish (documentation, final checks)

**Adapt this pattern** for any feature with multiple user stories.
