# Tasks: 006-Vice-Personalization

**Generated**: 2025-11-29
**Feature**: 006 - Vice Personalization System
**Input**: Design documents from `/specs/006-vice-personalization/`
**Prerequisites**:
- **Required**: plan.md (technical approach), spec.md (user stories)
- **Existing**: VicePreferenceRepository, UserVicePreference model

**Organization**: Tasks grouped by user story (US1-US6) for independent implementation and testing.

---

## Phase 1: Setup

**Purpose**: Create vice module structure and constants

- [ ] T001 Add VICE_CATEGORIES constant to `nikita/engine/constants.py`
- [ ] T002 Add vice intensity weights/thresholds to `nikita/engine/constants.py`
- [ ] T003 Create `nikita/engine/vice/models.py` with Pydantic models
- [ ] T004 Create `tests/engine/vice/__init__.py` for test package

**Checkpoint**: Module structure ready for implementation

---

## Phase 2: Vice Detection Models

**Purpose**: Data models for vice analysis

### T005: Create ViceSignal Model
- **Status**: [ ] Pending
- **File**: `nikita/engine/vice/models.py`
- **Dependencies**: T001, T003
- **ACs**:
  - [ ] AC-T005.1: category field from VICE_CATEGORIES enum
  - [ ] AC-T005.2: confidence field (Decimal 0.0-1.0)
  - [ ] AC-T005.3: evidence field for detection reasoning
  - [ ] AC-T005.4: is_positive field (True=engagement, False=rejection)

### T006: Create ViceAnalysisResult Model
- **Status**: [ ] Pending
- **File**: `nikita/engine/vice/models.py`
- **Dependencies**: T005
- **ACs**:
  - [ ] AC-T006.1: signals list of ViceSignal
  - [ ] AC-T006.2: conversation_id for traceability
  - [ ] AC-T006.3: analyzed_at timestamp

### T007: Create ViceProfile Model
- **Status**: [ ] Pending
- **File**: `nikita/engine/vice/models.py`
- **Dependencies**: T001
- **ACs**:
  - [ ] AC-T007.1: user_id UUID field
  - [ ] AC-T007.2: intensities dict[str, Decimal] for all 8 categories
  - [ ] AC-T007.3: top_vices ordered list
  - [ ] AC-T007.4: updated_at timestamp

**Checkpoint**: Data models ready for services

---

## Phase 3: US-1 Vice Detection (P1 - Must-Have)

**From spec.md**: System MUST detect user engagement with 8 vice categories

**Goal**: Analyze conversations to detect vice signals using LLM

**Independent Test**: Send vice-signaling messages, verify detection and scoring

**Acceptance Criteria** (from spec.md):
- AC-FR001-001: Given user makes dark joke, When analyzed, Then dark_humor detected
- AC-FR002-001: Given user writes long enthusiastic reply about risk, Then risk_taking signal logged
- AC-FR003-001: Given multiple dark_humor signals, When intensity calculated, Then score increases

### Tests for US-1 ⚠️ WRITE TESTS FIRST

- [ ] T008 [P] [US1] Unit test for ViceAnalyzer.analyze_exchange() in `tests/engine/vice/test_analyzer.py`
  - **Tests**: AC-FR001-001, AC-FR002-001
  - **Verify**: Test FAILS before implementation

- [ ] T009 [P] [US1] Unit test for ViceScorer.process_signals() in `tests/engine/vice/test_scorer.py`
  - **Tests**: AC-FR003-001
  - **Verify**: Test FAILS before implementation

### Implementation for US-1

### T010: Create Vice Analysis Prompt Template
- **Status**: [ ] Pending
- **File**: `nikita/prompts/vice_analysis.py`
- **Dependencies**: T001
- **ACs**:
  - [ ] AC-T010.1: Prompt lists all 8 VICE_CATEGORIES with descriptions
  - [ ] AC-T010.2: Instructions for detecting signals in user message
  - [ ] AC-T010.3: Confidence scoring guidance (0.0-1.0)
  - [ ] AC-T010.4: Evidence extraction instructions

### T011: Implement ViceAnalyzer Class
- **Status**: [ ] Pending
- **File**: `nikita/engine/vice/analyzer.py`
- **Dependencies**: T006, T010
- **ACs**:
  - [ ] AC-T011.1: `analyze_exchange(user_message, nikita_response, context)` method
  - [ ] AC-T011.2: Uses Pydantic AI for structured output (ViceAnalysisResult)
  - [ ] AC-T011.3: Returns empty signals list if no vices detected
  - [ ] AC-T011.4: Detects rejection signals (short replies, topic changes)

### T012: Implement ViceScorer Class
- **Status**: [ ] Pending
- **File**: `nikita/engine/vice/scorer.py`
- **Dependencies**: T005, VicePreferenceRepository
- **ACs**:
  - [ ] AC-T012.1: `process_signals(user_id, signals)` updates intensities
  - [ ] AC-T012.2: Intensity = confidence × frequency × recency (per spec)
  - [ ] AC-T012.3: Uses VicePreferenceRepository.discover() for new vices
  - [ ] AC-T012.4: Uses VicePreferenceRepository.update_intensity() for updates

### Verification for US-1

- [ ] T013 [US1] Run all US-1 tests - verify all pass
- [ ] T014 [US1] Verify detection works for all 8 categories

**Checkpoint**: Vice detection functional. Signals detected from conversations.

---

## Phase 4: US-5 Profile Persistence (P1 - Must-Have)

**From spec.md**: System MUST persist vice profiles

**Goal**: Store and retrieve vice profiles across sessions

**Independent Test**: Create profile, restart system, verify preservation

**Acceptance Criteria** (from spec.md):
- AC-FR008-001: Given user with established profile, When returns after days, Then same profile loaded
- AC-FR008-002: Given profile update, When persisted, Then survives system restart
- AC-FR008-003: Given profile history, When queried, Then detection timeline available

### Tests for US-5 ⚠️ WRITE TESTS FIRST

- [ ] T015 [P] [US5] Unit test for ViceScorer.get_profile() in `tests/engine/vice/test_scorer.py`
  - **Tests**: AC-FR008-001, AC-FR008-002
  - **Verify**: Test FAILS before implementation

### Implementation for US-5

### T016: Implement ViceScorer.get_profile() Method
- **Status**: [ ] Pending
- **File**: `nikita/engine/vice/scorer.py`
- **Dependencies**: T012
- **ACs**:
  - [ ] AC-T016.1: Returns ViceProfile with all 8 category intensities
  - [ ] AC-T016.2: Categories without data return intensity 0.0
  - [ ] AC-T016.3: top_vices ordered by intensity (descending)

### T017: Implement ViceScorer.get_top_vices() Method
- **Status**: [ ] Pending
- **File**: `nikita/engine/vice/scorer.py`
- **Dependencies**: T012
- **ACs**:
  - [ ] AC-T017.1: Returns top N vices by intensity (default 3)
  - [ ] AC-T017.2: Returns (category, intensity) tuples
  - [ ] AC-T017.3: Filters vices below minimum threshold

### Verification for US-5

- [ ] T018 [US5] Run all US-5 tests - verify all pass
- [ ] T019 [US5] Integration test: Profile survives session restart

**Checkpoint**: Profile persistence functional. Vices stored across sessions.

---

## Phase 5: US-2 Vice-Influenced Responses (P1 - Must-Have)

**From spec.md**: System MUST inject vice preferences into Nikita's prompts

**Goal**: Nikita's responses reflect user's vice preferences

**Independent Test**: Set vice profile, get responses, verify alignment

**Acceptance Criteria** (from spec.md):
- AC-FR005-001: Given user with high dark_humor, When Nikita responds, Then dark humor elements present
- AC-FR006-001: Given Ch1 user with high sexuality, When responding, Then subtle flirtation (not explicit)
- AC-FR005-002: Given user with low risk_taking, When responding, Then risky content minimized

### Tests for US-2 ⚠️ WRITE TESTS FIRST

- [ ] T020 [P] [US2] Unit test for VicePromptInjector.inject() in `tests/engine/vice/test_injector.py`
  - **Tests**: AC-FR005-001, AC-FR006-001
  - **Verify**: Test FAILS before implementation

### Implementation for US-2

### T021: Create Vice Expression Templates
- **Status**: [ ] Pending
- **File**: `nikita/engine/vice/injector.py`
- **Dependencies**: T001
- **ACs**:
  - [ ] AC-T021.1: 5 chapter-specific templates (Ch1 subtle → Ch5 explicit)
  - [ ] AC-T021.2: Templates instruct natural, non-performative expression
  - [ ] AC-T021.3: Include intensity level indicators

### T022: Implement VicePromptInjector Class
- **Status**: [ ] Pending
- **File**: `nikita/engine/vice/injector.py`
- **Dependencies**: T007, T021
- **ACs**:
  - [ ] AC-T022.1: `inject(base_prompt, profile, chapter)` returns modified prompt
  - [ ] AC-T022.2: Uses chapter-appropriate template
  - [ ] AC-T022.3: Includes top 2-3 vices only (not all)
  - [ ] AC-T022.4: Returns unmodified prompt if no active vices

### T023: Create Vice Description Constants
- **Status**: [ ] Pending
- **File**: `nikita/engine/constants.py`
- **Dependencies**: T001
- **ACs**:
  - [ ] AC-T023.1: VICE_DESCRIPTIONS dict with human-readable descriptions
  - [ ] AC-T023.2: Descriptions suitable for prompt injection
  - [ ] AC-T023.3: Examples of expressions for each category

### Verification for US-2

- [ ] T024 [US2] Run all US-2 tests - verify all pass
- [ ] T025 [US2] Verify chapter-appropriate expression levels

**Checkpoint**: Prompt injection functional. Nikita reflects user vices.

---

## Phase 6: US-3 Multi-Vice Blending (P2 - Important)

**From spec.md**: System MUST support users having multiple active vices

**Goal**: Coherent personality when expressing multiple vices

**Independent Test**: Create multi-vice profile, verify coherent blended expression

**Acceptance Criteria** (from spec.md):
- AC-FR004-001: Given user high on intellectual_dominance AND dark_humor, Then both expressed
- AC-FR004-002: Given three active vices, When blending, Then coherent personality
- AC-FR006-002: Given vice blend, When expressed, Then feels like natural Nikita

### Tests for US-3 ⚠️ WRITE TESTS FIRST

- [ ] T026 [P] [US3] Unit test for multi-vice blending in `tests/engine/vice/test_injector.py`
  - **Tests**: AC-FR004-001, AC-FR004-002
  - **Verify**: Test FAILS before implementation

### Implementation for US-3

### T027: Implement Multi-Vice Blending Logic
- **Status**: [ ] Pending
- **File**: `nikita/engine/vice/injector.py`
- **Dependencies**: T022
- **ACs**:
  - [ ] AC-T027.1: Blends 2-3 vices into coherent prompt section
  - [ ] AC-T027.2: Higher intensity vices get more prominence
  - [ ] AC-T027.3: Complementary vices enhance each other
  - [ ] AC-T027.4: Conflicting vices handled gracefully

### Verification for US-3

- [ ] T028 [US3] Run all US-3 tests - verify all pass
- [ ] T029 [US3] Verify blended expressions feel natural

**Checkpoint**: Multi-vice blending complete. Coherent personality expressions.

---

## Phase 7: US-4 Discovery Over Time (P2 - Important)

**From spec.md**: System MUST enable iterative vice discovery

**Goal**: Nikita probes with varied expressions, profile builds naturally

**Independent Test**: Simulate 10-conversation arc, verify profile evolution

**Acceptance Criteria** (from spec.md):
- AC-FR007-001: Given new user with empty profile, When Nikita responds, Then varied vice hints included
- AC-FR007-002: Given user positively responds to probe, When analyzed, Then vice intensity increases
- AC-FR007-003: Given 10 conversations, When profile reviewed, Then dominant vices emerged

### Tests for US-4 ⚠️ WRITE TESTS FIRST

- [ ] T030 [P] [US4] Unit test for discovery probing in `tests/engine/vice/test_service.py`
  - **Tests**: AC-FR007-001, AC-FR007-002
  - **Verify**: Test FAILS before implementation

### Implementation for US-4

### T031: Create Discovery Probing Logic
- **Status**: [ ] Pending
- **File**: `nikita/engine/vice/service.py`
- **Dependencies**: T022
- **ACs**:
  - [ ] AC-T031.1: New users get varied vice hints in prompts
  - [ ] AC-T031.2: Unexplored categories get probed occasionally
  - [ ] AC-T031.3: Probe frequency decreases as profile stabilizes

### T032: Implement ViceScorer.apply_decay() Method
- **Status**: [ ] Pending
- **File**: `nikita/engine/vice/scorer.py`
- **Dependencies**: T012
- **ACs**:
  - [ ] AC-T032.1: Applies time-based decay to engagement scores
  - [ ] AC-T032.2: Old signals reduce weight (VICE_DECAY_RATE)
  - [ ] AC-T032.3: Allows profile to evolve with changing interests

### Verification for US-4

- [ ] T033 [US4] Run all US-4 tests - verify all pass
- [ ] T034 [US4] Integration test: 10-conversation profile evolution

**Checkpoint**: Discovery mechanism complete. Profiles evolve naturally.

---

## Phase 8: US-6 Ethical Boundaries (P1 - Must-Have)

**From spec.md**: System MUST respect ethical boundaries within vices

**Goal**: Vice expression stays within content policy

**Independent Test**: Max out vice intensities, verify responses stay within bounds

**Acceptance Criteria** (from spec.md):
- AC-FR010-001: Given high sexuality intensity, When expressing, Then flirtatious but not explicit
- AC-FR010-002: Given substances vice, When expressing, Then discusses but doesn't encourage
- AC-FR010-003: Given any vice pushed to extreme, When generating, Then content policy respected

### Tests for US-6 ⚠️ WRITE TESTS FIRST

- [ ] T035 [P] [US6] Unit test for boundary enforcement in `tests/engine/vice/test_boundaries.py`
  - **Tests**: AC-FR010-001, AC-FR010-002, AC-FR010-003
  - **Verify**: Test FAILS before implementation

### Implementation for US-6

### T036: Create ViceBoundaryEnforcer Class
- **Status**: [ ] Pending
- **File**: `nikita/engine/vice/boundaries.py`
- **Dependencies**: T001
- **ACs**:
  - [ ] AC-T036.1: CATEGORY_LIMITS defines allowed/forbidden for sensitive categories
  - [ ] AC-T036.2: `filter_expression(category, expression, chapter)` method
  - [ ] AC-T036.3: `max_intensity_for_chapter(category, chapter)` caps sensitive vices

### T037: Integrate Boundaries into Injector
- **Status**: [ ] Pending
- **File**: `nikita/engine/vice/injector.py`
- **Dependencies**: T022, T036
- **ACs**:
  - [ ] AC-T037.1: Injector uses boundary limits for sensitive categories
  - [ ] AC-T037.2: Early chapters get capped intensity for sexuality/substances
  - [ ] AC-T037.3: Expression guidance includes policy reminders

### Verification for US-6

- [ ] T038 [US6] Run all US-6 tests - verify all pass
- [ ] T039 [US6] Verify extreme intensities stay within bounds

**Checkpoint**: Ethical boundaries enforced. All vices stay within policy.

---

## Phase 9: Service Integration

**Purpose**: High-level service and text agent integration

### T040: Implement ViceService Class
- **Status**: [ ] Pending
- **File**: `nikita/engine/vice/service.py`
- **Dependencies**: T011, T012, T022, T036
- **ACs**:
  - [ ] AC-T040.1: `get_prompt_context(user_id, chapter)` returns ViceInjectionContext
  - [ ] AC-T040.2: `process_conversation(user_id, user_msg, nikita_msg)` analyzes exchange
  - [ ] AC-T040.3: Orchestrates analyzer, scorer, injector, enforcer

### T041: Integrate Vice into Text Agent
- **Status**: [ ] Pending
- **File**: `nikita/agents/text/agent.py`
- **Dependencies**: T040
- **ACs**:
  - [ ] AC-T041.1: Text agent calls ViceService.get_prompt_context() before generation
  - [ ] AC-T041.2: Vice injection added to system prompt
  - [ ] AC-T041.3: Post-exchange calls ViceService.process_conversation()

**Checkpoint**: Vice system integrated with text agent.

---

## Phase 10: Final Verification

**Purpose**: Full integration test and polish

- [x] T042 Run all tests: `pytest tests/engine/vice/ -v` ✅ 70 tests passing
- [x] T043 Verify 80%+ code coverage ✅ 83% coverage achieved
- [x] T044 Integration test: Full vice cycle → detection → scoring → injection → expression ✅ 11 integration tests
- [x] T045 Update `nikita/engine/vice/CLAUDE.md` with implementation notes ✅ Complete
- [x] T046 Update `nikita/engine/CLAUDE.md` status to reflect vice complete ✅ Complete

**Final Checkpoint**: Vice personalization system complete and verified.

---

## Dependencies & Execution Order

### Phase Dependencies

| Phase | Depends On | Can Start After |
|-------|-----------|-----------------|
| Phase 1: Setup | None | Immediately |
| Phase 2: Models | Phase 1 | Setup done |
| Phase 3: US-1 (Detection) | Phase 2 | Models ready |
| Phase 4: US-5 (Persistence) | Phase 3 | Detection done |
| Phase 5: US-2 (Responses) | Phase 4 | Persistence done |
| Phase 6: US-3 (Blending) | Phase 5 | Injection done |
| Phase 7: US-4 (Discovery) | Phase 5 | Injection done (parallel with 6) |
| Phase 8: US-6 (Boundaries) | Phase 5 | Injection done (parallel with 6-7) |
| Phase 9: Integration | Phases 6, 7, 8 | All stories done |
| Phase 10: Final | All prior | All phases done |

### Parallel Opportunities

- **T008, T009, T015** (tests) can run in parallel after models
- **Phase 6, 7, 8** can run in parallel after Phase 5
- **T042-T046** are sequential final verification

---

## Progress Summary

| Phase/User Story | Tasks | Completed | Status |
|------------------|-------|-----------|--------|
| Phase 1: Setup | 4 | 4 | ✅ Complete |
| Phase 2: Models | 3 | 3 | ✅ Complete (17 tests) |
| US-1: Vice Detection | 7 | 7 | ✅ Complete (15 tests) |
| US-5: Profile Persistence | 5 | 5 | ✅ Complete (11 tests) |
| US-2: Vice-Influenced Responses | 6 | 6 | ✅ Complete (14 tests) |
| US-3: Multi-Vice Blending | 4 | 4 | ✅ Complete (in injector) |
| US-4: Discovery Over Time | 5 | 5 | ✅ Complete (8 tests) |
| US-6: Ethical Boundaries | 5 | 5 | ✅ Complete (7 tests) |
| Phase 9: Integration | 2 | 2 | ✅ Complete |
| Phase 10: Final | 5 | 5 | ✅ Complete |
| **Total** | **46** | **46** | **100% Complete (81 tests)** |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-29 | Initial task generation from plan.md |
| 2.0 | 2025-12-11 | T001-T040, T042 complete. 70 tests passing. Remaining: T041, T043-T046 |
| 2.1 | 2025-12-11 | T041 complete - Vice integrated into post_processor.py (stage 7.5) |
| 3.0 | 2025-12-12 | **COMPLETE** - T043-T046 done. 81 tests (70 unit + 11 integration), 83% coverage |
