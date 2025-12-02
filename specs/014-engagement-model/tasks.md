# 014 - Engagement Model Tasks

**Generated**: 2025-12-02
**Plan Version**: 1.0
**Total Tasks**: 24

---

## User Story Organization

| User Story | Priority | Tasks | Status |
|------------|----------|-------|--------|
| US-1: Engagement State Machine | P1 | T1.1-T1.4, T4.1-T4.3 | Pending |
| US-2: Calibration Score | P1 | T3.1-T3.3 | Pending |
| US-3: Clinginess Detection | P1 | T2.1, T2.3 | Pending |
| US-4: Neglect Detection | P1 | T2.2, T2.3 | Pending |
| US-5: Recovery Mechanics | P2 | T5.1-T5.2 | Pending |
| US-6: Chapter Transitions | P2 | T4.3 | Pending |

---

## Phase 1: Core Models (2 hours)

### T1.1: Create Engagement Module Structure
- **Status**: [ ] Pending
- **Estimate**: 15 min
- **Dependencies**: None

**Acceptance Criteria**:
- [ ] AC-1.1.1: `nikita/engine/engagement/` directory exists
- [ ] AC-1.1.2: `__init__.py` exports `EngagementEngine`, `EngagementState`
- [ ] AC-1.1.3: `models.py` file created with base imports
- [ ] AC-1.1.4: Module importable without errors

### T1.2: Implement EngagementState Enum
- **Status**: [ ] Pending
- **Estimate**: 20 min
- **Dependencies**: T1.1

**Acceptance Criteria**:
- [ ] AC-1.2.1: `EngagementState` enum with 6 values
- [ ] AC-1.2.2: CALIBRATING = "calibrating", multiplier 0.9
- [ ] AC-1.2.3: IN_ZONE = "in_zone", multiplier 1.0
- [ ] AC-1.2.4: DRIFTING = "drifting", multiplier 0.8
- [ ] AC-1.2.5: CLINGY = "clingy", multiplier 0.5
- [ ] AC-1.2.6: DISTANT = "distant", multiplier 0.6
- [ ] AC-1.2.7: OUT_OF_ZONE = "out_of_zone", multiplier 0.2
- [ ] AC-1.2.8: `get_multiplier()` method returns correct value

### T1.3: Create Database Models
- **Status**: [ ] Pending
- **Estimate**: 30 min
- **Dependencies**: T1.2

**Acceptance Criteria**:
- [ ] AC-1.3.1: `EngagementStateModel` SQLAlchemy model in `db/models/`
- [ ] AC-1.3.2: Fields: user_id, current_state, state_started_at, consecutive_days
- [ ] AC-1.3.3: Fields: calibration_score, clinginess_score, neglect_score, multiplier
- [ ] AC-1.3.4: `EngagementHistoryModel` for state transitions
- [ ] AC-1.3.5: `EngagementMetricsModel` for daily aggregates
- [ ] AC-1.3.6: Relationships to User model defined

### T1.4: Create Database Migration
- **Status**: [ ] Pending
- **Estimate**: 25 min
- **Dependencies**: T1.3

**Acceptance Criteria**:
- [ ] AC-1.4.1: Migration creates `engagement_state` table
- [ ] AC-1.4.2: Migration creates `engagement_history` table
- [ ] AC-1.4.3: Migration creates `engagement_metrics` table
- [ ] AC-1.4.4: `engagement_state_enum` PostgreSQL type created
- [ ] AC-1.4.5: Index on `engagement_state.user_id`
- [ ] AC-1.4.6: Index on `engagement_metrics(user_id, date)`

---

## Phase 2: Detection Algorithms (3 hours)

### T2.1: Implement ClinginessDetector
- **Status**: [ ] Pending
- **Estimate**: 45 min
- **Dependencies**: T1.3

**Acceptance Criteria**:
- [ ] AC-2.1.1: `ClinginessDetector` class in `detection.py`
- [ ] AC-2.1.2: `_frequency_signal()` compares to clinginess_threshold
- [ ] AC-2.1.3: `_double_text_signal()` detects multiple messages before response
- [ ] AC-2.1.4: `_response_time_signal()` flags < 30 second responses
- [ ] AC-2.1.5: `_length_ratio_signal()` compares to Nikita's average
- [ ] AC-2.1.6: `detect()` returns `ClinginessResult` with score and signals
- [ ] AC-2.1.7: Score weights: frequency=0.35, double_text=0.20, response=0.15, length=0.10, needy=0.20
- [ ] AC-2.1.8: `is_clingy` = True when score > 0.7

### T2.2: Implement NeglectDetector
- **Status**: [ ] Pending
- **Estimate**: 45 min
- **Dependencies**: T1.3

**Acceptance Criteria**:
- [ ] AC-2.2.1: `NeglectDetector` class in `detection.py`
- [ ] AC-2.2.2: `_frequency_signal()` compares to neglect_threshold
- [ ] AC-2.2.3: `_response_time_signal()` flags > 4 hour responses
- [ ] AC-2.2.4: `_short_message_signal()` flags < 20 char average
- [ ] AC-2.2.5: `_abrupt_ending_signal()` detects conversation endings
- [ ] AC-2.2.6: `detect()` returns `NeglectResult` with score and signals
- [ ] AC-2.2.7: Score weights: frequency=0.35, slow=0.20, short=0.15, endings=0.10, distracted=0.20
- [ ] AC-2.2.8: `is_neglecting` = True when score > 0.6

### T2.3: Implement LLM Analysis
- **Status**: [ ] Pending
- **Estimate**: 40 min
- **Dependencies**: T2.1, T2.2

**Acceptance Criteria**:
- [ ] AC-2.3.1: `analyze_neediness()` function defined
- [ ] AC-2.3.2: Uses Pydantic AI structured output
- [ ] AC-2.3.3: Returns score 0-1 for needy language patterns
- [ ] AC-2.3.4: `analyze_distraction()` function defined
- [ ] AC-2.3.5: Returns score 0-1 for distracted patterns
- [ ] AC-2.3.6: Results cached per session to reduce API calls

---

## Phase 3: Calibration Calculator (2 hours)

### T3.1: Implement OptimalFrequency Calculator
- **Status**: [ ] Pending
- **Estimate**: 30 min
- **Dependencies**: 013-configuration-system

**Acceptance Criteria**:
- [ ] AC-3.1.1: `OptimalFrequencyCalculator` class in `calculator.py`
- [ ] AC-3.1.2: Reads `base_optimal` from engagement.yaml: {1: 15, 2: 12, 3: 10, 4: 8, 5: 6}
- [ ] AC-3.1.3: Reads `day_modifier` from config (Mon=0.9, Sat=1.2, etc.)
- [ ] AC-3.1.4: `get_optimal(chapter, day_of_week)` returns messages/day
- [ ] AC-3.1.5: `get_tolerance_band(chapter)` returns ±10/15/20/25/30%
- [ ] AC-3.1.6: `get_bounds(chapter, day_of_week)` returns (lower, upper)

### T3.2: Implement CalibrationScore Calculator
- **Status**: [ ] Pending
- **Estimate**: 40 min
- **Dependencies**: T3.1, T2.1, T2.2

**Acceptance Criteria**:
- [ ] AC-3.2.1: `CalibrationCalculator` class in `calculator.py`
- [ ] AC-3.2.2: `_frequency_component()` = 1 - |actual - optimal| / optimal (40% weight)
- [ ] AC-3.2.3: `_timing_component()` from response time analysis (30% weight)
- [ ] AC-3.2.4: `_content_component()` from conversation quality (30% weight)
- [ ] AC-3.2.5: `compute(player_metrics)` returns score 0-1
- [ ] AC-3.2.6: Score clamped to [0, 1] range

### T3.3: Implement State Mapping
- **Status**: [ ] Pending
- **Estimate**: 25 min
- **Dependencies**: T3.2

**Acceptance Criteria**:
- [ ] AC-3.3.1: `map_score_to_state()` function defined
- [ ] AC-3.3.2: Score >= 0.8 → IN_ZONE candidate
- [ ] AC-3.3.3: Score 0.5-0.8 → DRIFTING candidate
- [ ] AC-3.3.4: Score 0.3-0.5 → CLINGY or DISTANT (based on detectors)
- [ ] AC-3.3.5: Score < 0.3 → OUT_OF_ZONE candidate
- [ ] AC-3.3.6: Consecutive exchange tracking for transitions

---

## Phase 4: State Machine (2 hours)

### T4.1: Implement EngagementStateMachine
- **Status**: [ ] Pending
- **Estimate**: 45 min
- **Dependencies**: T1.3, T3.3

**Acceptance Criteria**:
- [ ] AC-4.1.1: `EngagementStateMachine` class in `state_machine.py`
- [ ] AC-4.1.2: `__init__(user_id)` loads current state from DB
- [ ] AC-4.1.3: `current_state` property returns EngagementState
- [ ] AC-4.1.4: `current_multiplier` property returns Decimal
- [ ] AC-4.1.5: `update(calibration_result)` evaluates transitions
- [ ] AC-4.1.6: State changes persisted immediately

### T4.2: Implement Transition Rules
- **Status**: [ ] Pending
- **Estimate**: 50 min
- **Dependencies**: T4.1

**Acceptance Criteria**:
- [ ] AC-4.2.1: CALIBRATING → IN_ZONE: score >= 0.8 for 3+ consecutive
- [ ] AC-4.2.2: CALIBRATING → DRIFTING: score < 0.5 for 2+ consecutive
- [ ] AC-4.2.3: IN_ZONE → DRIFTING: score < 0.6 for 1+ exchange
- [ ] AC-4.2.4: DRIFTING → IN_ZONE: score >= 0.7 for 2+ exchanges
- [ ] AC-4.2.5: DRIFTING → CLINGY: clinginess > 0.7 for 2+ days
- [ ] AC-4.2.6: DRIFTING → DISTANT: neglect > 0.6 for 2+ days
- [ ] AC-4.2.7: CLINGY → DRIFTING: clinginess < 0.5 for 2+ days
- [ ] AC-4.2.8: CLINGY → OUT_OF_ZONE: clingy 3+ consecutive days
- [ ] AC-4.2.9: DISTANT → DRIFTING: neglect < 0.4 for 1+ day
- [ ] AC-4.2.10: DISTANT → OUT_OF_ZONE: distant 5+ consecutive days
- [ ] AC-4.2.11: OUT_OF_ZONE → CALIBRATING: recovery + grace period
- [ ] AC-4.2.12: Each transition logs to engagement_history

### T4.3: Implement Chapter Reset
- **Status**: [ ] Pending
- **Estimate**: 25 min
- **Dependencies**: T4.1

**Acceptance Criteria**:
- [ ] AC-4.3.1: `on_chapter_change(new_chapter)` method defined
- [ ] AC-4.3.2: State reset to CALIBRATING on chapter change
- [ ] AC-4.3.3: Consecutive counters reset to 0
- [ ] AC-4.3.4: Multiplier set to 0.9 (calibrating default)
- [ ] AC-4.3.5: Historical data preserved in engagement_history
- [ ] AC-4.3.6: New calibration window uses new chapter parameters

---

## Phase 5: Recovery System (1.5 hours)

### T5.1: Implement RecoveryManager
- **Status**: [ ] Pending
- **Estimate**: 35 min
- **Dependencies**: T4.2

**Acceptance Criteria**:
- [ ] AC-5.1.1: `RecoveryManager` class in `recovery.py`
- [ ] AC-5.1.2: `get_recovery_action(state)` returns required action
- [ ] AC-5.1.3: CLINGY recovery: "Give space for 24 hours"
- [ ] AC-5.1.4: DISTANT recovery: "Engage meaningfully within 12 hours"
- [ ] AC-5.1.5: `check_recovery_complete(user_id)` validates action taken
- [ ] AC-5.1.6: Grace period enforced before state reset

### T5.2: Implement Game Over Triggers
- **Status**: [ ] Pending
- **Estimate**: 30 min
- **Dependencies**: T5.1

**Acceptance Criteria**:
- [ ] AC-5.2.1: `check_point_of_no_return(user_id)` method
- [ ] AC-5.2.2: Clingy: 7 consecutive days → GAME_OVER
- [ ] AC-5.2.3: Distant: 10 consecutive days → GAME_OVER
- [ ] AC-5.2.4: Game over triggers `game_status = 'game_over'`
- [ ] AC-5.2.5: Game over reason stored: "nikita_dumped_clingy" or "nikita_dumped_distant"

---

## Phase 6: Testing (2 hours)

### T6.1: Unit Tests for Detectors
- **Status**: [ ] Pending
- **Estimate**: 30 min
- **Dependencies**: T2.1, T2.2

**Acceptance Criteria**:
- [ ] AC-6.1.1: Test clinginess signals individually
- [ ] AC-6.1.2: Test clinginess composite score
- [ ] AC-6.1.3: Test neglect signals individually
- [ ] AC-6.1.4: Test neglect composite score
- [ ] AC-6.1.5: Test edge cases (0 messages, max messages)

### T6.2: Unit Tests for Calculator
- **Status**: [ ] Pending
- **Estimate**: 30 min
- **Dependencies**: T3.1, T3.2

**Acceptance Criteria**:
- [ ] AC-6.2.1: Test optimal frequency per chapter/day
- [ ] AC-6.2.2: Test tolerance bands per chapter
- [ ] AC-6.2.3: Test calibration score components
- [ ] AC-6.2.4: Test state mapping from scores

### T6.3: Unit Tests for State Machine
- **Status**: [ ] Pending
- **Estimate**: 35 min
- **Dependencies**: T4.2

**Acceptance Criteria**:
- [ ] AC-6.3.1: Test each transition rule
- [ ] AC-6.3.2: Test consecutive tracking
- [ ] AC-6.3.3: Test chapter reset
- [ ] AC-6.3.4: Test state persistence
- [ ] AC-6.3.5: Test game over triggers

### T6.4: Integration Tests
- **Status**: [ ] Pending
- **Estimate**: 35 min
- **Dependencies**: T5.2

**Acceptance Criteria**:
- [ ] AC-6.4.1: Test full flow: message → metrics → state → multiplier
- [ ] AC-6.4.2: Test chapter transition flow
- [ ] AC-6.4.3: Test recovery flow
- [ ] AC-6.4.4: Test multi-day simulation

---

## Progress Summary

| Phase | Tasks | Completed | Status |
|-------|-------|-----------|--------|
| Phase 1: Core Models | T1.1-T1.4 | 0 | Pending |
| Phase 2: Detection | T2.1-T2.3 | 0 | Pending |
| Phase 3: Calculator | T3.1-T3.3 | 0 | Pending |
| Phase 4: State Machine | T4.1-T4.3 | 0 | Pending |
| Phase 5: Recovery | T5.1-T5.2 | 0 | Pending |
| Phase 6: Testing | T6.1-T6.4 | 0 | Pending |
| **TOTAL** | **19** | **0** | **0%** |

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-02 | Claude | Initial task breakdown |
