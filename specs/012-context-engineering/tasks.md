# 012 - Context Engineering System Tasks

**Generated**: 2025-12-02
**Plan Version**: 1.0
**Total Tasks**: 25

---

## User Story Organization

| User Story | Priority | Tasks | Status |
|------------|----------|-------|--------|
| US-1: State Collection | P1 | T1.2, T2.1 | Pending |
| US-2: Temporal Context | P1 | T1.3, T2.2 | Pending |
| US-3: Memory Summarization | P1 | T1.4, T2.3 | Pending |
| US-4: Mood Computation | P1 | T1.5, T2.4 | Pending |
| US-5: Prompt Assembly | P1 | T2.5, T3.2 | Pending |
| US-6: Validation | P2 | T2.6 | Pending |
| US-7: Integration | P1 | T4.1, T4.2 | Pending |

---

## Phase 1: Data Models (2 hours)

### T1.1: Create Context Module Structure
- **Status**: [ ] Pending
- **Estimate**: 15 min
- **Dependencies**: None

**Acceptance Criteria**:
- [ ] AC-1.1.1: `nikita/context/` directory exists
- [ ] AC-1.1.2: `stages/` subpackage with 6 stage files
- [ ] AC-1.1.3: `models/` subpackage with 5 model files
- [ ] AC-1.1.4: `utils/` subpackage created
- [ ] AC-1.1.5: `__init__.py` exports `ContextGenerator`, models

### T1.2: Implement PlayerProfile Model
- **Status**: [ ] Pending
- **Estimate**: 25 min
- **Dependencies**: T1.1

**Acceptance Criteria**:
- [ ] AC-1.2.1: `PlayerProfile` dataclass in `models/player_profile.py`
- [ ] AC-1.2.2: Fields: user_id, telegram_id, chapter, relationship_score
- [ ] AC-1.2.3: Fields: boss_attempts, game_status, intimacy/passion/trust/secureness
- [ ] AC-1.2.4: Fields: engagement_state, calibration_score, vices
- [ ] AC-1.2.5: Fields: created_at, last_interaction, current_streak
- [ ] AC-1.2.6: `from_entities()` factory method from User, Metrics, Vices

### T1.3: Implement TemporalContext Model
- **Status**: [ ] Pending
- **Estimate**: 25 min
- **Dependencies**: T1.1

**Acceptance Criteria**:
- [ ] AC-1.3.1: `TemporalContext` dataclass in `models/temporal_context.py`
- [ ] AC-1.3.2: `TimeOfDay` enum: morning/afternoon/evening/night/late_night
- [ ] AC-1.3.3: `DayOfWeek` enum: weekday/weekend
- [ ] AC-1.3.4: `Availability` enum: free/busy/at_work/sleeping/event
- [ ] AC-1.3.5: `SilenceCategory` enum: normal/extended/concerning/critical
- [ ] AC-1.3.6: Fields: current_time, time_of_day, day_of_week, nikita_availability
- [ ] AC-1.3.7: Fields: hours_since_last_message, silence_category, is_within_grace_period

### T1.4: Implement MemoryContext Model
- **Status**: [ ] Pending
- **Estimate**: 20 min
- **Dependencies**: T1.1

**Acceptance Criteria**:
- [ ] AC-1.4.1: `MemoryContext` dataclass in `models/memory_context.py`
- [ ] AC-1.4.2: Fields: recent_facts (list[str]), relationship_milestones
- [ ] AC-1.4.3: Fields: user_preferences, last_conversation_summary
- [ ] AC-1.4.4: Fields: conversation_mood_trend, unresolved_topics
- [ ] AC-1.4.5: Fields: yesterday_summary, weekly_context
- [ ] AC-1.4.6: Field: total_memory_tokens (int)
- [ ] AC-1.4.7: `truncate_to_budget(max_tokens)` method

### T1.5: Implement NikitaState Model
- **Status**: [ ] Pending
- **Estimate**: 25 min
- **Dependencies**: T1.1

**Acceptance Criteria**:
- [ ] AC-1.5.1: `NikitaState` dataclass in `models/nikita_state.py`
- [ ] AC-1.5.2: `Mood` enum: flirty/playful/warm/distant/upset/needy
- [ ] AC-1.5.3: `EnergyLevel` enum: high/medium/low
- [ ] AC-1.5.4: `ResponseStyle` enum: enthusiastic/normal/reserved/cold
- [ ] AC-1.5.5: `NSFWLevel` enum: soft/full
- [ ] AC-1.5.6: Fields: mood, mood_intensity, energy_level, response_style
- [ ] AC-1.5.7: Fields: flirtiness, vulnerability, playfulness (0-1 floats)
- [ ] AC-1.5.8: Fields: should_initiate_more, should_pull_back, calibration_hint

### T1.6: Implement SystemPrompt Model
- **Status**: [ ] Pending
- **Estimate**: 15 min
- **Dependencies**: T1.1

**Acceptance Criteria**:
- [ ] AC-1.6.1: `SystemPrompt` dataclass in `models/system_prompt.py`
- [ ] AC-1.6.2: Fields: content (str), token_count (int)
- [ ] AC-1.6.3: Fields: sections (list[str]), is_valid (bool)
- [ ] AC-1.6.4: Fields: validation_warnings (list[str])
- [ ] AC-1.6.5: Fields: generation_time_ms, context_sources

---

## Phase 2: Stage Implementations (5 hours)

### T2.1: Implement StateCollector (Stage 1)
- **Status**: [ ] Pending
- **Estimate**: 45 min
- **Dependencies**: T1.2, 014-engagement-model

**Acceptance Criteria**:
- [ ] AC-2.1.1: `StateCollector` class in `stages/state_collector.py`
- [ ] AC-2.1.2: `collect(user_id)` method returns `PlayerProfile`
- [ ] AC-2.1.3: Parallel queries to User, Metrics, VicePreference repos
- [ ] AC-2.1.4: Integration with EngagementStateMachine from 014
- [ ] AC-2.1.5: Missing data handled with sensible defaults
- [ ] AC-2.1.6: Total execution time < 50ms

### T2.2: Implement TemporalBuilder (Stage 2)
- **Status**: [ ] Pending
- **Estimate**: 40 min
- **Dependencies**: T1.3, 013-configuration-system

**Acceptance Criteria**:
- [ ] AC-2.2.1: `TemporalBuilder` class in `stages/temporal.py`
- [ ] AC-2.2.2: `build(profile)` method returns `TemporalContext`
- [ ] AC-2.2.3: Time of day computed from current time (user timezone)
- [ ] AC-2.2.4: Nikita availability loaded from schedule.yaml
- [ ] AC-2.2.5: Silence analysis using last_interaction and chapter grace periods
- [ ] AC-2.2.6: Message frequency computed from conversation history

### T2.3: Implement MemorySummarizer (Stage 3)
- **Status**: [ ] Pending
- **Estimate**: 50 min
- **Dependencies**: T1.4

**Acceptance Criteria**:
- [ ] AC-2.3.1: `MemorySummarizer` class in `stages/memory_summarizer.py`
- [ ] AC-2.3.2: `summarize(user_id, message)` returns `MemoryContext`
- [ ] AC-2.3.3: Graphiti search for relevant facts (limit 10)
- [ ] AC-2.3.4: Relationship milestones from milestone graph
- [ ] AC-2.3.5: Conversation mood trend from recent summaries
- [ ] AC-2.3.6: Token budget enforced (< 1000 tokens)
- [ ] AC-2.3.7: Graceful fallback if Graphiti unavailable

### T2.4: Implement MoodComputer (Stage 4)
- **Status**: [ ] Pending
- **Estimate**: 45 min
- **Dependencies**: T1.5, 014-engagement-model

**Acceptance Criteria**:
- [ ] AC-2.4.1: `MoodComputer` class in `stages/mood_computer.py`
- [ ] AC-2.4.2: `compute(profile, temporal, memory)` returns `NikitaState`
- [ ] AC-2.4.3: Mood selected based on engagement state and metrics
- [ ] AC-2.4.4: Mood intensity computed (0-1)
- [ ] AC-2.4.5: Energy level from temporal context (late_night = low)
- [ ] AC-2.4.6: Calibration hints from engagement state
- [ ] AC-2.4.7: Chapter behavior modifier applied

### T2.5: Implement PromptAssembler (Stage 5)
- **Status**: [ ] Pending
- **Estimate**: 50 min
- **Dependencies**: T1.6, 013-configuration-system

**Acceptance Criteria**:
- [ ] AC-2.5.1: `PromptAssembler` class in `stages/assembler.py`
- [ ] AC-2.5.2: `assemble(profile, temporal, memory, state)` returns `SystemPrompt`
- [ ] AC-2.5.3: Prompt files loaded via PromptLoader from 013
- [ ] AC-2.5.4: Variable substitution: {{chapter}}, {{mood}}, {{name}}
- [ ] AC-2.5.5: Sections assembled in priority order
- [ ] AC-2.5.6: Token budget enforced (< 4000 tokens)
- [ ] AC-2.5.7: Truncation applied to low-priority sections if needed

### T2.6: Implement Validator (Stage 6)
- **Status**: [ ] Pending
- **Estimate**: 30 min
- **Dependencies**: T2.5

**Acceptance Criteria**:
- [ ] AC-2.6.1: `Validator` class in `stages/validator.py`
- [ ] AC-2.6.2: `validate(prompt)` returns `ValidationResult`
- [ ] AC-2.6.3: Token count checked against budget
- [ ] AC-2.6.4: Required sections verified present
- [ ] AC-2.6.5: Contradiction detection (e.g., mood=distant + calibration=should_initiate)
- [ ] AC-2.6.6: Warnings logged but don't block generation

---

## Phase 3: Context Generator (2 hours)

### T3.1: Implement ContextGenerator Class
- **Status**: [ ] Pending
- **Estimate**: 40 min
- **Dependencies**: T2.1-T2.6

**Acceptance Criteria**:
- [ ] AC-3.1.1: `ContextGenerator` class in `generator.py`
- [ ] AC-3.1.2: `generate(user_id, message)` orchestrates all stages
- [ ] AC-3.1.3: Stages executed in order with error handling
- [ ] AC-3.1.4: Performance tracked per stage
- [ ] AC-3.1.5: Total generation time < 200ms
- [ ] AC-3.1.6: Singleton pattern or factory for reuse

### T3.2: Implement Token Counter
- **Status**: [ ] Pending
- **Estimate**: 25 min
- **Dependencies**: T1.1

**Acceptance Criteria**:
- [ ] AC-3.2.1: `TokenCounter` class in `utils/token_counter.py`
- [ ] AC-3.2.2: Uses tiktoken with cl100k_base encoding
- [ ] AC-3.2.3: `count(text)` returns token count
- [ ] AC-3.2.4: Caching for repeated counts
- [ ] AC-3.2.5: `count_sections(sections)` returns per-section counts

### T3.3: Add Performance Metrics
- **Status**: [ ] Pending
- **Estimate**: 20 min
- **Dependencies**: T3.1

**Acceptance Criteria**:
- [ ] AC-3.3.1: `PerformanceMetrics` dataclass
- [ ] AC-3.3.2: Per-stage timing tracked
- [ ] AC-3.3.3: Total generation time logged
- [ ] AC-3.3.4: Token usage per section logged
- [ ] AC-3.3.5: Metrics accessible via `generator.last_metrics`

---

## Phase 4: Integration (2 hours)

### T4.1: Replace build_system_prompt()
- **Status**: [ ] Pending
- **Estimate**: 45 min
- **Dependencies**: T3.1

**Acceptance Criteria**:
- [ ] AC-4.1.1: `build_system_prompt()` in agent.py deprecated
- [ ] AC-4.1.2: `ContextGenerator.generate()` called instead
- [ ] AC-4.1.3: Dependencies injected via NikitaDeps
- [ ] AC-4.1.4: Async context handled correctly
- [ ] AC-4.1.5: Fallback to simple prompt if generator fails

### T4.2: Update Existing Tests
- **Status**: [ ] Pending
- **Estimate**: 40 min
- **Dependencies**: T4.1

**Acceptance Criteria**:
- [ ] AC-4.2.1: Agent tests mock ContextGenerator
- [ ] AC-4.2.2: All 156 existing agent tests pass
- [ ] AC-4.2.3: Performance regression < 100ms
- [ ] AC-4.2.4: Memory usage stable

---

## Phase 5: Testing (3 hours)

### T5.1: Unit Tests for Models
- **Status**: [ ] Pending
- **Estimate**: 30 min
- **Dependencies**: T1.2-T1.6

**Acceptance Criteria**:
- [ ] AC-5.1.1: Test each dataclass instantiation
- [ ] AC-5.1.2: Test validation for numeric ranges
- [ ] AC-5.1.3: Test factory methods
- [ ] AC-5.1.4: Test truncation methods

### T5.2: Unit Tests for Stages
- **Status**: [ ] Pending
- **Estimate**: 50 min
- **Dependencies**: T2.1-T2.6

**Acceptance Criteria**:
- [ ] AC-5.2.1: Test StateCollector with mocked repos
- [ ] AC-5.2.2: Test TemporalBuilder with various times
- [ ] AC-5.2.3: Test MemorySummarizer with mocked Graphiti
- [ ] AC-5.2.4: Test MoodComputer with various inputs
- [ ] AC-5.2.5: Test PromptAssembler with mocked PromptLoader
- [ ] AC-5.2.6: Test Validator with valid/invalid prompts

### T5.3: Integration Tests
- **Status**: [ ] Pending
- **Estimate**: 40 min
- **Dependencies**: T3.1

**Acceptance Criteria**:
- [ ] AC-5.3.1: Test full pipeline with test data
- [ ] AC-5.3.2: Test with various player states
- [ ] AC-5.3.3: Test performance bounds (< 200ms)
- [ ] AC-5.3.4: Test error recovery

### T5.4: Token Budget Tests
- **Status**: [ ] Pending
- **Estimate**: 30 min
- **Dependencies**: T2.5

**Acceptance Criteria**:
- [ ] AC-5.4.1: Verify budget < 4000 tokens for all test cases
- [ ] AC-5.4.2: Test truncation behavior
- [ ] AC-5.4.3: Test empty memory case
- [ ] AC-5.4.4: Test maximum memory case

---

## Progress Summary

| Phase | Tasks | Completed | Status |
|-------|-------|-----------|--------|
| Phase 1: Models | T1.1-T1.6 | 0 | Pending |
| Phase 2: Stages | T2.1-T2.6 | 0 | Pending |
| Phase 3: Generator | T3.1-T3.3 | 0 | Pending |
| Phase 4: Integration | T4.1-T4.2 | 0 | Pending |
| Phase 5: Testing | T5.1-T5.4 | 0 | Pending |
| **TOTAL** | **21** | **0** | **0%** |

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-02 | Claude | Initial task breakdown |
