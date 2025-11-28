---
description: "Task list template for feature implementation following Intelligence-First and Test-First principles"
---

# Tasks: [FEATURE NAME]

**Generated**: [YYYY-MM-DD]
**Feature**: [Feature ID] - [Feature Name]
**Input**: Design documents from `/specs/[###-feature-name]/`
**Prerequisites**:
- **Required**: plan.md (technical approach), spec.md (user stories)
- **Optional**: research.md (patterns), data-model.md (schema), contracts/ (APIs)

**Organization**: Tasks are grouped by user story (P1, P2, P3...) to enable:
- Independent implementation per story
- Independent testing per story
- MVP-first delivery (P1 → ship → P2 → ship...)

**Intelligence-First**: All tasks requiring code understanding MUST query `project-intel.mjs` BEFORE reading files:
```bash
# 1. Get overview
project-intel.mjs --overview --json

# 2. Search for relevant files
project-intel.mjs --search "keyword" --type tsx --json

# 3. Get symbols
project-intel.mjs --symbols path/to/file.ts --json

# 4. Check dependencies
project-intel.mjs --dependencies path/to/file.ts --direction downstream --json
```

**Test-First (Article III)**: All implementation tasks MUST have ≥2 testable acceptance criteria. Write tests FIRST, watch them FAIL, then implement.

---

## Format: `[ID] [P?] [Story] Description`

- **[ID]**: Sequential task number (T001, T002, etc.)
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story mapping (US1, US2, US3 for P1, P2, P3 priorities)
- **Description**: Include exact file paths and CoD^Σ evidence when available

---

## Path Conventions

Adapt based on plan.md structure:

- **Single project**: `src/`, `tests/` at repository root
- **Web app**: `backend/src/`, `frontend/src/`
- **Full stack**: `apps/web/`, `apps/api/`, `packages/shared/`
- **Mobile**: `api/src/`, `ios/src/`, `android/src/`

Paths shown below assume single project structure - adjust based on your plan.md.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

**CoD^Σ Query**: `project-intel.mjs --overview --json` to understand existing structure

- [ ] T001 Create project structure per implementation plan
- [ ] T002 Initialize [language] project with [framework] dependencies
- [ ] T003 [P] Configure linting and formatting tools
- [ ] T004 [P] Setup test framework and utilities
- [ ] T005 [P] Configure build and development scripts

**Checkpoint**: Basic project structure ready for foundational work

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete BEFORE any user story implementation

**⚠️ CRITICAL**: No user story work can begin until this phase completes

**Intelligence Queries**: Use `project-intel.mjs --search` to find existing patterns for:
- Authentication frameworks
- Database setup patterns
- API routing structures
- Error handling utilities

Example foundational tasks (adjust based on your project):

- [ ] T006 Setup database schema and migrations framework
- [ ] T007 [P] Implement authentication/authorization framework
- [ ] T008 [P] Setup API routing and middleware structure
- [ ] T009 [P] Create base models/entities that all stories depend on
- [ ] T010 Configure error handling and logging infrastructure
- [ ] T011 [P] Setup environment configuration management
- [ ] T012 Create shared utilities and helper functions

**Constitution Gate**: Verify Article VI (Simplicity) - are we building minimum necessary foundation?

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - [Title] (Priority: P1) 🎯 MVP

**From spec.md**: [Copy user story description from spec.md]

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works standalone, without other stories]

**Acceptance Criteria** (from spec.md):
- AC-REQ#-001: [Criterion 1]
- AC-REQ#-002: [Criterion 2]
- [Add all ACs for requirements mapped to P1]

### Intelligence Queries for User Story 1

**Before starting implementation**, gather context:

```bash
# Find existing patterns
project-intel.mjs --search "[relevant keyword]" --type tsx --json

# Understand dependencies
project-intel.mjs --dependencies [related-file] --json

# Find similar implementations
project-intel.mjs --symbols [similar-file] --json
```

### Tests for User Story 1 ⚠️ WRITE TESTS FIRST

**Article III: Test-First Imperative** - Write tests, watch them FAIL, then implement

- [ ] T013 [P] [US1] Contract test for [endpoint] in `tests/contract/test_[name].test.ts`
  - **Tests**: AC-REQ#-001, AC-REQ#-002
  - **Verify**: Test FAILS before implementation
- [ ] T014 [P] [US1] Integration test for [user journey] in `tests/integration/test_[name].test.ts`
  - **Tests**: AC-REQ#-003, AC-REQ#-004
  - **Verify**: Test FAILS before implementation
- [ ] T015 [P] [US1] Unit tests for [component] in `tests/unit/[name].test.ts`
  - **Tests**: AC-REQ#-005
  - **Verify**: Test FAILS before implementation

### Implementation for User Story 1

**CoD^Σ Tracing**: Document evidence for each implementation decision

- [ ] T016 [P] [US1] Create [Entity1] model in `src/models/[entity1].ts`
  - **Evidence**: Based on data-model.md Entity1 schema
  - **Tests**: T013, T014
- [ ] T017 [P] [US1] Create [Entity2] model in `src/models/[entity2].ts`
  - **Evidence**: Based on data-model.md Entity2 schema
  - **Tests**: T013, T014
- [ ] T018 [US1] Implement [Service] in `src/services/[service].ts`
  - **Evidence**: Follows pattern found at [file:line] via intel query
  - **Dependencies**: T016, T017
  - **Tests**: T014, T015
- [ ] T019 [US1] Implement [endpoint/feature] in `src/[location]/[file].ts`
  - **Evidence**: Endpoint contract in contracts/[name].md
  - **Dependencies**: T018
  - **Tests**: T013, T014
- [ ] T020 [US1] Add validation and error handling
  - **Evidence**: Error handling pattern at [file:line]
  - **Tests**: T013, T014
- [ ] T021 [US1] Add logging for User Story 1 operations
  - **Evidence**: Logging utility at [file:line]
  - **Tests**: T015

### Verification for User Story 1

- [ ] T022 [US1] Run all User Story 1 tests - verify all pass
- [ ] T023 [US1] Independent story test: [specific scenario to validate]
- [ ] T024 [US1] Verify all P1 acceptance criteria satisfied

**Checkpoint**: User Story 1 fully functional and testable independently. Ready to ship MVP.

---

## Phase 4: User Story 2 - [Title] (Priority: P2)

**From spec.md**: [Copy user story description from spec.md]

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works standalone]

**Acceptance Criteria** (from spec.md):
- AC-REQ#-001: [Criterion 1]
- AC-REQ#-002: [Criterion 2]
- [Add all ACs for requirements mapped to P2]

### Intelligence Queries for User Story 2

```bash
# Check integration points with US1
project-intel.mjs --dependencies [us1-file] --direction downstream --json

# Find similar patterns
project-intel.mjs --search "[keyword]" --json
```

### Tests for User Story 2 ⚠️ WRITE TESTS FIRST

- [ ] T025 [P] [US2] Contract test for [endpoint] in `tests/contract/test_[name].test.ts`
  - **Tests**: AC-REQ#-001, AC-REQ#-002
  - **Verify**: Test FAILS before implementation
- [ ] T026 [P] [US2] Integration test for [user journey] in `tests/integration/test_[name].test.ts`
  - **Tests**: AC-REQ#-003
  - **Verify**: Test FAILS before implementation

### Implementation for User Story 2

- [ ] T027 [P] [US2] Create [Entity] model in `src/models/[entity].ts`
  - **Evidence**: Based on data-model.md
  - **Tests**: T025, T026
- [ ] T028 [US2] Implement [Service] in `src/services/[service].ts`
  - **Evidence**: Pattern from [file:line]
  - **Dependencies**: T027
  - **Tests**: T026
- [ ] T029 [US2] Implement [endpoint/feature] in `src/[location]/[file].ts`
  - **Evidence**: Contract in contracts/[name].md
  - **Dependencies**: T028
  - **Tests**: T025, T026
- [ ] T030 [US2] Integrate with User Story 1 components (if needed)
  - **Evidence**: Integration point at [file:line] via intel query
  - **Dependencies**: T029
  - **Tests**: T026

### Verification for User Story 2

- [ ] T031 [US2] Run all User Story 2 tests - verify all pass
- [ ] T032 [US2] Independent story test: [specific scenario]
- [ ] T033 [US2] Verify User Story 1 still works (regression check)
- [ ] T034 [US2] Verify all P2 acceptance criteria satisfied

**Checkpoint**: User Stories 1 AND 2 both work independently. Ready for next iteration.

---

## Phase 5: User Story 3 - [Title] (Priority: P3)

**From spec.md**: [Copy user story description from spec.md]

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works standalone]

**Acceptance Criteria** (from spec.md):
- AC-REQ#-001: [Criterion 1]
- AC-REQ#-002: [Criterion 2]
- [Add all ACs for requirements mapped to P3]

### Intelligence Queries for User Story 3

```bash
# Check full integration surface
project-intel.mjs --dependencies [us1-file] --json
project-intel.mjs --dependencies [us2-file] --json

# Verify architecture consistency
project-intel.mjs --symbols [related-files] --json
```

### Tests for User Story 3 ⚠️ WRITE TESTS FIRST

- [ ] T035 [P] [US3] Contract test for [endpoint] in `tests/contract/test_[name].test.ts`
  - **Tests**: AC-REQ#-001, AC-REQ#-002
  - **Verify**: Test FAILS before implementation
- [ ] T036 [P] [US3] Integration test for [user journey] in `tests/integration/test_[name].test.ts`
  - **Tests**: AC-REQ#-003
  - **Verify**: Test FAILS before implementation

### Implementation for User Story 3

- [ ] T037 [P] [US3] Create [Entity] model in `src/models/[entity].ts`
  - **Evidence**: Based on data-model.md
  - **Tests**: T035, T036
- [ ] T038 [US3] Implement [Service] in `src/services/[service].ts`
  - **Evidence**: Pattern from [file:line]
  - **Dependencies**: T037
  - **Tests**: T036
- [ ] T039 [US3] Implement [endpoint/feature] in `src/[location]/[file].ts`
  - **Evidence**: Contract in contracts/[name].md
  - **Dependencies**: T038
  - **Tests**: T035, T036

### Verification for User Story 3

- [ ] T040 [US3] Run all User Story 3 tests - verify all pass
- [ ] T041 [US3] Independent story test: [specific scenario]
- [ ] T042 [US3] Verify User Stories 1 & 2 still work (regression check)
- [ ] T043 [US3] Verify all P3 acceptance criteria satisfied

**Checkpoint**: All user stories independently functional. Ready for polish phase.

---

[Add more user story phases as needed, following the same pattern]

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements affecting multiple user stories

**Constitution Check**: Verify Article VI (Simplicity) - are we over-engineering?

- [ ] TXXX [P] Update documentation in `docs/`
- [ ] TXXX [P] Update README with quickstart instructions
- [ ] TXXX Code cleanup and refactoring
- [ ] TXXX Performance optimization across all stories
- [ ] TXXX [P] Additional unit tests (if gaps identified)
- [ ] TXXX Security hardening (input validation, error messages)
- [ ] TXXX Run quickstart.md validation end-to-end

**Final Verification**: Run all tests, verify all acceptance criteria pass

---

## Dependencies & Execution Order

### Phase Dependencies

| Phase | Depends On | Can Start After | Parallelizable |
|-------|-----------|-----------------|----------------|
| **Setup (Phase 1)** | None | Immediately | Tasks marked [P] |
| **Foundational (Phase 2)** | Phase 1 complete | Setup done | Tasks marked [P] within phase |
| **User Story 1 (Phase 3)** | Phase 2 complete | Foundation ready | Tests in parallel, then implementation |
| **User Story 2 (Phase 4)** | Phase 2 complete | Foundation ready | Can start in parallel with US1 |
| **User Story 3 (Phase 5)** | Phase 2 complete | Foundation ready | Can start in parallel with US1/US2 |
| **Polish (Phase N)** | All desired stories | After target stories | Tasks marked [P] |

### Within Each User Story

**Test-First Workflow** (Article III):
1. ✅ Write tests FIRST (marked [P] can run in parallel)
2. ✅ Verify tests FAIL (red state)
3. ✅ Implement minimum code to pass (green state)
4. ✅ Refactor if needed (green state maintained)
5. ✅ Verify all ACs satisfied

**Implementation Order**:
- Tests before implementation (TDD)
- Models before services
- Services before endpoints
- Core implementation before integration
- Story verification before next priority

### Parallel Opportunities

**Setup Phase**: All tasks marked [P] can run simultaneously

**Foundational Phase**: All tasks marked [P] within Phase 2 can run simultaneously

**User Stories**: Once Foundation completes, ALL user stories can start in parallel (if team capacity allows)

**Within Story**:
- All tests marked [P] can run in parallel
- All models marked [P] can run in parallel
- Different team members can work on different stories

---

## Implementation Strategy

### MVP First (User Story 1 Only)

**Fastest path to validated value:**

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready (minimum viable product!)

### Incremental Delivery (Recommended)

**Progressive value delivery:**

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP! 🎯)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

**Benefits**:
- Early user feedback
- Risk reduction (smaller increments)
- Motivation (visible progress)
- Flexibility (can stop at any checkpoint)

### Parallel Team Strategy

**With multiple developers:**

1. Team completes Setup + Foundational together (highest leverage)
2. Once Foundational complete:
   - Developer A: User Story 1 (P1)
   - Developer B: User Story 2 (P2)
   - Developer C: User Story 3 (P3)
3. Stories complete and integrate independently
4. Each developer verifies their story independently
5. Team verifies integration at regular checkpoints

**Requirements**:
- Clear story boundaries (from spec.md)
- Independent test scenarios per story
- Communication at checkpoints
- Regression testing after integration

---

## Intelligence-First Checklist

Before implementing ANY task involving code:

- [ ] Run `project-intel.mjs --overview` to understand project structure
- [ ] Run `project-intel.mjs --search` to find relevant existing code
- [ ] Run `project-intel.mjs --symbols` to understand file contents
- [ ] Run `project-intel.mjs --dependencies` to check integration points
- [ ] Query MCP tools for library documentation if using new dependencies
- [ ] Read ONLY targeted files after intelligence queries narrow scope

**Token Efficiency Goal**: 80%+ savings by querying lightweight index before reading full files

---

## Test-First Checklist (Article III)

For EVERY implementation task:

- [ ] ≥2 acceptance criteria defined
- [ ] Tests written FIRST covering all ACs
- [ ] Tests FAIL before implementation (verified red state)
- [ ] Implementation written to pass tests
- [ ] Tests PASS after implementation (verified green state)
- [ ] All ACs verified satisfied

**No exceptions** - if task has no testable ACs, break it down further

---

## CoD^Σ Evidence Requirements

For EVERY implementation task, document:

- **Pattern Evidence**: "Based on pattern at [file:line] found via intel query"
- **Contract Evidence**: "Implementing contract in contracts/[name].md"
- **Schema Evidence**: "Using schema from data-model.md section X"
- **Dependency Evidence**: "Depends on [task-id] which provides [functionality]"

**Traceability**: All decisions must trace to spec.md, plan.md, research.md, or intel queries

---

## Notes

- **[P] tasks**: Different files, no dependencies, can run simultaneously
- **[Story] label**: Maps task to specific user story for traceability
- **Independent stories**: Each user story completable and testable standalone
- **Test-First**: Verify tests fail before implementing (TDD discipline)
- **Intelligence-First**: Query indexes before reading files (80% token savings)
- **Checkpoints**: Stop after each story to validate independently
- **Avoid**: Vague tasks, same-file conflicts, cross-story dependencies breaking independence

---

## Complexity Tracking (Optional)

If implementation reveals unexpected complexity, track here:

| Task ID | Original Estimate | Actual Effort | Complexity Factor | Notes |
|---------|------------------|---------------|-------------------|-------|
| T025 | 2h | 6h | 3x | Integration point more complex than expected |
| T038 | 1h | 4h | 4x | Required new utility function not in plan |

**Use**: Inform future estimations, identify underspecified areas

---

**Generated by**: generate-tasks skill via /tasks command
**Validated by**: /audit command (cross-artifact consistency check)
**Next Step**: /implement plan.md (progressive story-by-story implementation)
