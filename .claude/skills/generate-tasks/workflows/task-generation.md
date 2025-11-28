# Phase 2-3: Task Generation Workflow

**Purpose**: Organize tasks by user story (Article VII) and generate implementation tasks using test-first approach (Article III).

---

## Phase 2: Organize Tasks by User Story (Article VII)

**CRITICAL**: Tasks MUST be grouped by user story, NOT by technical layer.

### Phase Structure

**Required Phases**:
1. **Phase 1: Setup** - Project initialization, dependencies
2. **Phase 2: Foundational** - Blocking prerequisites for ALL stories
3. **Phase 3+: User Story Phases** - One phase per story (P1, P2, P3...)
4. **Final Phase: Polish & Cross-Cutting** - Documentation, cleanup

**Within Each Story Phase**:
```
Phase N: User Story PX - [Title]

Goal: [What user can do after this phase]
Independent Test: [How to validate this story works standalone]

Tasks:
1. Tests (if TDD required)
2. Models needed for this story
3. Services needed for this story
4. Endpoints/UI needed for this story
5. Integration for this story
6. Verification of this story
```

---

## Phase 3: Generate Tasks

### Step 3.1: Phase 1 - Setup Tasks

**Purpose**: Initialize project structure, install dependencies

**Task Format**:
```
- [ ] T001 Create project structure per implementation plan
- [ ] T002 [P] Install dependencies: <list from plan.md>
- [ ] T003 [P] Configure environment variables
- [ ] T004 [P] Set up development database
```

**Parallel Marker** `[P]`: Tasks that can run simultaneously (different files, no dependencies)

### Step 3.2: Phase 2 - Foundational Tasks

**Purpose**: Blocking prerequisites that ALL user stories depend on

**Examples**:
```
- [ ] T005 Create base database schema (users table)
- [ ] T006 Set up authentication middleware
- [ ] T007 Configure error handling and logging
```

**NOT user-story-specific**: These enable multiple stories.

### Step 3.3: Phase 3+ - User Story Tasks

**Article VII Mandate**: One phase per user story, organized by priority.

#### Step 3.3.1: Identify Story Components

For each user story from spec.md:

**Map to Components** (from plan.md):
- Which models does this story need?
- Which services does this story need?
- Which endpoints/UI does this story need?
- Which tests validate this story?

**Example**: User Story P1 - Email/Password Registration

Components needed:
- Model: User (enhance existing)
- Service: AuthService (new)
- API: POST /register (new)
- UI: RegisterForm (new)
- Tests: Registration flow tests

#### Step 3.3.2: Generate Tasks with Article III Compliance

**Test-First Mandate** (Article III): Tests MUST come before implementation.

**Task Sequence**:
```
## Phase 3: User Story P1 - Email/Password Registration

**Story Goal**: Users can create accounts with email and password

**Independent Test**: Can register new user, receive session token, login with credentials

**Dependencies**: Phase 2 (foundational) complete

### Tests (Article III: Test-First)
- [ ] T008 [P] [US1] Write test for AC-P1-001 (valid registration) in tests/auth/register.test.ts
- [ ] T009 [P] [US1] Write test for AC-P1-002 (weak password rejection) in tests/auth/register.test.ts

### Implementation
- [ ] T010 [US1] Enhance User model with password_hash field in models/user.ts
- [ ] T011 [US1] Create AuthService.register() method in services/auth-service.ts
- [ ] T012 [US1] Implement POST /api/auth/register endpoint in api/auth/register.ts
- [ ] T013 [US1] Create RegisterForm component in components/auth/RegisterForm.tsx
- [ ] T014 [US1] Integrate RegisterForm with /register route in pages/register.tsx

### Verification
- [ ] T015 [US1] Run AC tests (must pass 100%)
- [ ] T016 [US1] Test registration flow end-to-end with quickstart scenario
- [ ] T017 [US1] Verify story works independently (no other stories required)
```

**Task ID Format**: T### (sequential numbering)
**Story Label Format**: [US#] where # is story number (US1, US2, US3...)
**Parallel Marker**: [P] for parallelizable tasks

#### Step 3.3.3: Repeat for All User Stories

Generate phases for:
- Phase 4: User Story P2
- Phase 5: User Story P3
- ...

Each phase:
- Independent test criteria
- Tests before implementation
- Story-specific tasks only
- Verification step

### Step 3.4: Final Phase - Polish

**Purpose**: Cross-cutting concerns, documentation, cleanup

**Examples**:
```
## Phase N: Polish & Cross-Cutting Concerns

- [ ] T### [P] Update API documentation
- [ ] T### [P] Run full test suite
- [ ] T### [P] Perform security audit
- [ ] T### Run linter and fix issues
- [ ] T### Build and verify production bundle
- [ ] T### Update changelog
```

---

## Key Patterns

**Pattern 1: User-Story-Centric Organization**
```
Phase per story (not layer) → Independent test → Demonstrable MVP
```

**Pattern 2: Test-First Structure**
```
Tests (Article III) → Implementation → Verification (AC pass check)
```

**Pattern 3: Story Independence**
```
Each story: Own tests + Own implementation + Own verification + Independent demo
```
