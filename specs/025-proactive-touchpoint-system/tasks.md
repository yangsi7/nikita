# Tasks: 025 Proactive Touchpoint System

**Spec Version**: 1.0.0
**Created**: 2026-01-12

---

## Progress Summary

| Phase | Tasks | Completed | Status |
|-------|-------|-----------|--------|
| A: Infrastructure | 5 | 5 | ✅ Complete |
| B: Scheduling | 6 | 6 | ✅ Complete |
| C: Message Generation | 5 | 5 | ✅ Complete |
| D: Strategic Silence | 4 | 4 | ✅ Complete |
| E: Delivery | 5 | 5 | ✅ Complete |
| F: E2E | 3 | 3 | ✅ Complete |
| **Total** | **28** | **28** | **100%** |

---

## Phase A: Core Infrastructure

### T001: Create touchpoints module
- **Status**: [x] Complete
- **Estimate**: 30m
- **ACs**:
  - [x] AC-T001.1: Create `nikita/touchpoints/__init__.py`
  - [x] AC-T001.2: Module structure: engine.py, scheduler.py, generator.py, models.py, store.py

### T002: Implement ScheduledTouchpoint model
- **Status**: [x] Complete
- **Estimate**: 1h
- **Dependencies**: T001
- **ACs**:
  - [x] AC-T002.1: `ScheduledTouchpoint` Pydantic model with all fields
  - [x] AC-T002.2: `TouchpointConfig` Pydantic model
  - [x] AC-T002.3: Validation for trigger_type enum
  - [x] AC-T002.4: Unit tests for models (39 tests)

### T003: Add database migration
- **Status**: [x] Complete
- **Estimate**: 30m
- **Dependencies**: T002
- **ACs**:
  - [x] AC-T003.1: Migration creates `scheduled_touchpoints` table (SQLAlchemy model)
  - [x] AC-T003.2: Index on (delivered, delivery_at)
  - [x] AC-T003.3: Index on user_id
  - [x] AC-T003.4: Migration applied successfully (via Alembic/Supabase MCP)

### T004: Implement TouchpointStore
- **Status**: [x] Complete
- **Estimate**: 1.5h
- **Dependencies**: T003
- **ACs**:
  - [x] AC-T004.1: `TouchpointStore` class with CRUD operations
  - [x] AC-T004.2: `get_due_touchpoints()` method
  - [x] AC-T004.3: `mark_delivered()` method
  - [x] AC-T004.4: `get_user_touchpoints()` method (for dedup check)
  - [x] AC-T004.5: Unit tests for store

### T005: Phase A tests
- **Status**: [x] Complete
- **Estimate**: 1h
- **Dependencies**: T004
- **ACs**:
  - [x] AC-T005.1: Test file `tests/touchpoints/test_infrastructure.py` (39 tests)
  - [x] AC-T005.2: Coverage > 85% for Phase A modules

---

## Phase B: Scheduling

### T006: Implement TouchpointScheduler class
- **Status**: [x] Complete
- **Estimate**: 1.5h
- **Dependencies**: T005
- **ACs**:
  - [x] AC-T006.1: `TouchpointScheduler` class
  - [x] AC-T006.2: `schedule()` method creates touchpoint
  - [x] AC-T006.3: `evaluate_user()` checks if user eligible for touchpoint
  - [x] AC-T006.4: Unit tests for scheduler

### T007: Implement time-based triggers
- **Status**: [x] Complete
- **Estimate**: 1.5h
- **Dependencies**: T006
- **ACs**:
  - [x] AC-T007.1: Morning slot detection (8-10am user timezone)
  - [x] AC-T007.2: Evening slot detection (7-9pm user timezone)
  - [x] AC-T007.3: Probability check per slot (20-30% per chapter)
  - [x] AC-T007.4: Timezone handling from user profile
  - [x] AC-T007.5: Unit tests for time triggers

### T008: Implement event-based triggers
- **Status**: [x] Complete
- **Estimate**: 1.5h
- **Dependencies**: T006
- **ACs**:
  - [x] AC-T008.1: Subscribe to life events (022)
  - [x] AC-T008.2: High-importance events more likely to trigger
  - [x] AC-T008.3: Emotional events (upset, excited) trigger more often
  - [x] AC-T008.4: Unit tests with mock events

### T009: Implement gap-based triggers
- **Status**: [x] Complete
- **Estimate**: 1h
- **Dependencies**: T006
- **ACs**:
  - [x] AC-T009.1: Detect gaps > 24 hours without contact
  - [x] AC-T009.2: Trigger "reaching out" touchpoint
  - [x] AC-T009.3: Gap-based message style differs from time-based
  - [x] AC-T009.4: Unit tests for gap detection

### T010: Implement chapter-aware rates
- **Status**: [x] Complete
- **Estimate**: 1h
- **Dependencies**: T006
- **ACs**:
  - [x] AC-T010.1: Load rates from config (FR-002)
  - [x] AC-T010.2: Chapter 1: 15-20%, Chapter 2: 20-25%, Chapter 3+: 25-30%
  - [x] AC-T010.3: Rate lookup per user's current chapter
  - [x] AC-T010.4: Unit tests for rate calculation

### T011: Phase B tests
- **Status**: [x] Complete
- **Estimate**: 1.5h
- **Dependencies**: T010
- **ACs**:
  - [x] AC-T011.1: Test file `tests/touchpoints/test_scheduling.py` (36 tests)
  - [x] AC-T011.2: Coverage > 85% for Phase B modules

---

## Phase C: Message Generation

### T012: Implement MessageGenerator class
- **Status**: [x] Complete
- **Estimate**: 1.5h
- **Dependencies**: T011
- **ACs**:
  - [x] AC-T012.1: `MessageGenerator` class
  - [x] AC-T012.2: `generate()` method creates message content
  - [x] AC-T012.3: Uses MetaPromptService patterns (Claude Haiku)
  - [x] AC-T012.4: Unit tests for generator

### T013: Integrate with MetaPromptService
- **Status**: [x] Complete
- **Estimate**: 1h
- **Dependencies**: T012
- **ACs**:
  - [x] AC-T013.1: Pass trigger_type to MetaPromptService
  - [x] AC-T013.2: Pass trigger_context for personalization
  - [x] AC-T013.3: Use proactive message template
  - [x] AC-T013.4: Unit tests for integration

### T014: Add life event context
- **Status**: [x] Complete
- **Estimate**: 1h
- **Dependencies**: T013
- **ACs**:
  - [x] AC-T014.1: Load relevant life event from trigger_context
  - [x] AC-T014.2: Include event description in prompt
  - [x] AC-T014.3: Message references event naturally
  - [x] AC-T014.4: Unit tests for event context

### T015: Add emotional state context
- **Status**: [x] Complete
- **Estimate**: 1h
- **Dependencies**: T013
- **ACs**:
  - [x] AC-T015.1: Load current emotional state (023)
  - [x] AC-T015.2: Mood affects message tone
  - [x] AC-T015.3: Conflict state affects message style
  - [x] AC-T015.4: Unit tests for emotional context

### T016: Phase C tests
- **Status**: [x] Complete
- **Estimate**: 1.5h
- **Dependencies**: T015
- **ACs**:
  - [x] AC-T016.1: Test file `tests/touchpoints/test_generation.py` (30 tests)
  - [x] AC-T016.2: Coverage > 85% for Phase C modules

---

## Phase D: Strategic Silence

### T017: Implement strategic silence logic
- **Status**: [x] Complete
- **Estimate**: 1h
- **Dependencies**: T016
- **ACs**:
  - [x] AC-T017.1: `apply_strategic_silence()` method
  - [x] AC-T017.2: 10-20% of touchpoints skipped (per chapter)
  - [x] AC-T017.3: Skip recorded with reason
  - [x] AC-T017.4: Unit tests for silence logic

### T018: Add emotional state integration
- **Status**: [x] Complete
- **Estimate**: 1h
- **Dependencies**: T017
- **ACs**:
  - [x] AC-T018.1: More silence when upset (valence < 0.3)
  - [x] AC-T018.2: More silence in conflict states
  - [x] AC-T018.3: Silence rate modulated by emotional state
  - [x] AC-T018.4: Unit tests for emotional silence

### T019: Add random skip factor
- **Status**: [x] Complete
- **Estimate**: 30m
- **Dependencies**: T017
- **ACs**:
  - [x] AC-T019.1: Random factor adds unpredictability
  - [x] AC-T019.2: Not purely deterministic
  - [x] AC-T019.3: Unit tests for randomness

### T020: Phase D tests
- **Status**: [x] Complete
- **Estimate**: 1h
- **Dependencies**: T019
- **ACs**:
  - [x] AC-T020.1: Test file `tests/touchpoints/test_silence.py` (37 tests)
  - [x] AC-T020.2: Coverage > 85% for Phase D modules

---

## Phase E: Delivery

### T021: Implement TouchpointEngine.deliver()
- **Status**: [x] Complete
- **Estimate**: 1.5h
- **Dependencies**: T020
- **ACs**:
  - [x] AC-T021.1: `TouchpointEngine` orchestrates delivery
  - [x] AC-T021.2: `deliver_due_touchpoints()` processes queue
  - [x] AC-T021.3: Handles errors gracefully (retry logic)
  - [x] AC-T021.4: Unit tests for engine

### T022: Add pg_cron job configuration
- **Status**: [x] Complete
- **Estimate**: 30m
- **Dependencies**: T021
- **ACs**:
  - [x] AC-T022.1: pg_cron job: */5 * * * * (every 5 minutes)
  - [x] AC-T022.2: Job calls /api/v1/tasks/touchpoints
  - [x] AC-T022.3: SQL script in migrations/ (part of existing touchpoints job)

### T023: Add Telegram delivery integration
- **Status**: [x] Complete
- **Estimate**: 1h
- **Dependencies**: T021
- **ACs**:
  - [x] AC-T023.1: Use existing TelegramBot.send_message() via get_bot()
  - [x] AC-T023.2: Look up user's chat_id via _get_chat_id()
  - [x] AC-T023.3: Handle send failures (mark_failed + reschedule)
  - [x] AC-T023.4: Unit tests for delivery (27 tests)

### T024: Add deduplication logic
- **Status**: [x] Complete
- **Estimate**: 1h
- **Dependencies**: T021
- **ACs**:
  - [x] AC-T024.1: Check recent touchpoints before scheduling via _should_skip_for_dedup()
  - [x] AC-T024.2: Minimum gap between touchpoints (DEFAULT_MIN_GAP_MINUTES = 120)
  - [x] AC-T024.3: Prevent double messages via exclude_id parameter
  - [x] AC-T024.4: Unit tests for deduplication (4 tests)

### T025: Phase E tests
- **Status**: [x] Complete
- **Estimate**: 1.5h
- **Dependencies**: T024
- **ACs**:
  - [x] AC-T025.1: Test file `tests/touchpoints/test_delivery.py` (27 tests)
  - [x] AC-T025.2: Integration test with mock Telegram (TestTelegramDelivery)
  - [x] AC-T025.3: Coverage > 85% for Phase E modules

---

## Phase F: E2E

### T026: E2E tests
- **Status**: [x] Complete
- **Estimate**: 2h
- **Dependencies**: T025
- **ACs**:
  - [x] AC-T026.1: Full pipeline: trigger → schedule → generate → deliver (6 tests)
  - [x] AC-T026.2: Time-based touchpoint E2E (3 tests)
  - [x] AC-T026.3: Event-based touchpoint E2E (2 tests)
  - [x] AC-T026.4: Strategic silence E2E (2 tests in TestFullPipelineE2E)

### T027: Quality tests
- **Status**: [x] Complete
- **Estimate**: 1.5h
- **Dependencies**: T026
- **ACs**:
  - [x] AC-T027.1: Measure initiation rate over simulated period (TestQualityMetrics)
  - [x] AC-T027.2: Verify rate within target range (test_initiation_rate_within_target)
  - [x] AC-T027.3: Verify message diversity (TestMessageDiversity - 2 tests)

### T028: Fix flaky E2E tests (deterministic timing)
- **Status**: [x] Complete
- **Estimate**: 0.5h
- **Dependencies**: T026
- **ACs**:
  - [x] AC-T028.1: All `datetime.now()` in test_e2e.py replaced with fixed `_REF` constant
  - [x] AC-T028.2: Dedup test uses deterministic delta (1h < 4h min_gap)
  - [x] AC-T028.3: Full test suite passes at any UTC hour (0 flaky, 0 skipped in CI scope)

---

## Version History

### v1.0.1 - 2026-02-24
- Added T028: Deterministic test timing fix

### v1.0.0 - 2026-01-12
- Initial task breakdown
- 27 tasks with acceptance criteria
