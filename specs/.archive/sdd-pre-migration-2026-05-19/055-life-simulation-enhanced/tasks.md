# Spec 055: Task List

**Total tasks**: 22
**TDD approach**: Write failing test -> implement -> verify -> mark done

---

## US-1: Routine-Aware Event Generation

### T001: Add WeeklyRoutine and DayRoutine models
**File**: `nikita/life_simulation/models.py`
**Description**: Add Pydantic models for weekly routine configuration.
**Acceptance Criteria**:
- AC-T001.1: `DayRoutine` model with fields: day_of_week, wake_time, activities, work_schedule, energy_pattern, social_availability
- AC-T001.2: `WeeklyRoutine` model with days dict and timezone field
- AC-T001.3: Validation for day_of_week values (monday-sunday)
- AC-T001.4: `WeeklyRoutine.default()` class method returns hardcoded default
- AC-T001.5: `WeeklyRoutine.from_yaml(path)` class method loads from YAML
**Estimated hours**: 1
**TDD**: Write tests for model validation, from_yaml, default()

### T002: Create routine.yaml default config
**File**: `nikita/config_data/life_simulation/routine.yaml`
**Description**: Default weekly routine for Nikita (Berlin timezone).
**Acceptance Criteria**:
- AC-T002.1: 7 days defined with distinct patterns (weekday vs weekend)
- AC-T002.2: Work days: office/remote schedule, gym, social plans
- AC-T002.3: Weekend: errands, hobbies, self-care, mom call (Sunday)
- AC-T002.4: File parseable by `WeeklyRoutine.from_yaml()`
**Estimated hours**: 0.5
**TDD**: Validate YAML loads correctly with model

### T003: Add routine loader to entity_manager or new module
**File**: `nikita/life_simulation/entity_manager.py` (or new `routine.py`)
**Description**: Load and cache weekly routine from YAML or user config.
**Acceptance Criteria**:
- AC-T003.1: `load_routine(user_id)` returns `WeeklyRoutine`
- AC-T003.2: Falls back to system default if user has no custom config
- AC-T003.3: Caches loaded routine (LRU or singleton pattern)
- AC-T003.4: `get_day_routine(routine, target_date)` returns `DayRoutine` for specific date
**Estimated hours**: 1
**TDD**: Test fallback, caching, date-to-day mapping

### T004: Add feature flag to settings.py
**File**: `nikita/config/settings.py`
**Description**: Add `life_sim_enhanced` bool flag.
**Acceptance Criteria**:
- AC-T004.1: `life_sim_enhanced: bool = Field(default=False, ...)`
- AC-T004.2: Env var `LIFE_SIM_ENHANCED` controls value
- AC-T004.3: Existing settings unchanged
**Estimated hours**: 0.25
**TDD**: Verify flag defaults to False

### T005: Add routine context to EventGenerator prompt
**File**: `nikita/life_simulation/event_generator.py`
**Description**: Inject day routine into LLM event generation prompt.
**Acceptance Criteria**:
- AC-T005.1: `generate_events_for_day()` accepts optional `routine: DayRoutine` param
- AC-T005.2: `_build_generation_prompt()` includes routine section when provided
- AC-T005.3: Routine section describes: work schedule, activities, energy level, social availability
- AC-T005.4: Without routine param, prompt is unchanged (backward compat)
**Estimated hours**: 1.5
**TDD**: Test prompt contains routine context; test prompt without routine unchanged

### T006: Wire routine loading in LifeSimulator
**File**: `nikita/life_simulation/simulator.py`
**Description**: Load routine for target date and pass to EventGenerator.
**Acceptance Criteria**:
- AC-T006.1: `generate_next_day_events()` loads routine when `life_sim_enhanced` flag is ON
- AC-T006.2: Passes `DayRoutine` for target_date's day of week to `EventGenerator`
- AC-T006.3: Flag OFF: no routine loaded, no param passed (existing behavior)
- AC-T006.4: Missing routine config falls back to system default
**Estimated hours**: 1
**TDD**: Test with flag ON/OFF; test routine passed correctly

---

## US-2: Bidirectional Mood-Event Flow

### T007: Add mood context to EventGenerator prompt
**File**: `nikita/life_simulation/event_generator.py`
**Description**: Inject mood state into LLM event generation prompt.
**Acceptance Criteria**:
- AC-T007.1: `generate_events_for_day()` accepts optional `mood_state: MoodState` param
- AC-T007.2: Prompt includes mood bias section when mood_state provided
- AC-T007.3: Low valence (< 0.4) biases toward stress-related events
- AC-T007.4: High valence (> 0.6) biases toward positive events
- AC-T007.5: Without mood_state, prompt is unchanged (backward compat)
**Estimated hours**: 1
**TDD**: Test prompt mood section; verify bias wording for low/high valence

### T008: Compute mood before event generation in simulator
**File**: `nikita/life_simulation/simulator.py`
**Description**: Pipeline change: compute mood first, feed into event generation.
**Acceptance Criteria**:
- AC-T008.1: `generate_next_day_events()` calls `get_current_mood()` before `EventGenerator`
- AC-T008.2: Passes resulting `MoodState` to `generate_events_for_day(mood_state=...)`
- AC-T008.3: Uses lookback_days=3 for mood computation (matches existing default)
- AC-T008.4: If mood computation fails, events generate without mood context (graceful degradation)
- AC-T008.5: Gated behind `life_sim_enhanced` flag
**Estimated hours**: 1
**TDD**: Test mood passed to generator; test fallback on mood failure

---

## US-3: NPC Consolidation

### T009: DB migration — users table additions
**File**: Supabase migration
**Description**: Add routine_config and meta_instructions columns.
**Acceptance Criteria**:
- AC-T009.1: `ALTER TABLE users ADD COLUMN routine_config JSONB DEFAULT '{}'`
- AC-T009.2: `ALTER TABLE users ADD COLUMN meta_instructions JSONB DEFAULT '{}'`
- AC-T009.3: Both nullable with empty object defaults
- AC-T009.4: Migration applied via Supabase MCP
**Estimated hours**: 0.25
**TDD**: Verify columns exist; verify default values

### T010: DB migration — user_social_circles additions
**File**: Supabase migration
**Description**: Add last_event and sentiment columns for NPC state tracking.
**Acceptance Criteria**:
- AC-T010.1: `ALTER TABLE user_social_circles ADD COLUMN last_event TIMESTAMPTZ`
- AC-T010.2: `ALTER TABLE user_social_circles ADD COLUMN sentiment TEXT DEFAULT 'neutral'`
- AC-T010.3: Existing rows get NULL last_event and 'neutral' sentiment
- AC-T010.4: Migration applied via Supabase MCP
**Estimated hours**: 0.25
**TDD**: Verify columns exist; verify defaults on existing rows

### T011: NPC name resolver
**File**: `nikita/life_simulation/entity_manager.py`
**Description**: Resolve character name to either social_circle or entity record.
**Acceptance Criteria**:
- AC-T011.1: `resolve_npc(user_id, name)` checks `user_social_circles` first
- AC-T011.2: Falls back to `nikita_entities` if not in social circle
- AC-T011.3: Returns `None` if name not found in either store
- AC-T011.4: Case-insensitive matching
**Estimated hours**: 1.5
**TDD**: Test resolution priority; test fallback; test unknown name

### T012: NPC state update on life events
**File**: `nikita/life_simulation/simulator.py` or new `npc_tracker.py`
**Description**: Update user_social_circles when life events reference NPCs.
**Acceptance Criteria**:
- AC-T012.1: After event generation, iterate event entities
- AC-T012.2: For each entity that resolves to a social circle NPC, update `last_event` timestamp
- AC-T012.3: Compute sentiment from event's emotional_impact (positive/negative/neutral/mixed)
- AC-T012.4: Sentiment logic: valence_delta > 0.1 = positive, < -0.1 = negative, else neutral
- AC-T012.5: Gated behind `life_sim_enhanced` flag
**Estimated hours**: 1.5
**TDD**: Test state update; test sentiment computation; test unknown entity skipped

### T013: Lazy NPC initialization
**File**: `nikita/life_simulation/entity_manager.py`
**Description**: Create user_social_circles row on first NPC reference if not exists.
**Acceptance Criteria**:
- AC-T013.1: When NPC name matches a CORE_CHARACTERS template but no row exists, create row
- AC-T013.2: Uses `SocialCircleGenerator.CORE_CHARACTERS` as template source
- AC-T013.3: Only creates for known core characters (Lena, Viktor, Yuki, etc.)
- AC-T013.4: Unknown names are ignored (not lazy-initialized)
- AC-T013.5: Thread-safe: check-then-create with conflict handling
**Estimated hours**: 1.5
**TDD**: Test first-reference creation; test idempotency; test unknown name

### T014: Update entities.yaml — Max K. rename, Ana deprecation
**File**: `nikita/config_data/life_simulation/entities.yaml`
**Description**: Resolve name collisions per mapping table.
**Acceptance Criteria**:
- AC-T014.1: Max colleague renamed to "Max K." with updated description noting disambiguation
- AC-T014.2: Ana entry replaced with comment noting merge into Lena
- AC-T014.3: All other entries unchanged
- AC-T014.4: Entity loading tests pass with updated YAML
**Estimated hours**: 0.5
**TDD**: Verify YAML loads; verify Max K. in entity list; verify Ana absent

### T015: Enhanced entity context with social circle merge
**File**: `nikita/life_simulation/entity_manager.py`
**Description**: Merge social circle NPC data into entity context for prompts.
**Acceptance Criteria**:
- AC-T015.1: `get_entity_context(user_id)` includes social circle friends with sentiment
- AC-T015.2: Format: "Lena (best friend, feeling positive lately)" when sentiment data exists
- AC-T015.3: Falls back to entity-only context when no social circle data
- AC-T015.4: Gated behind `life_sim_enhanced` flag
**Estimated hours**: 1
**TDD**: Test merged context output; test fallback; test with/without sentiment

### T016: Arc system NPC lookup via social circle
**File**: `nikita/life_simulation/arcs.py`
**Description**: NarrativeArcSystem checks social circle for NPC metadata.
**Acceptance Criteria**:
- AC-T016.1: `get_arc_context()` enriches character info from social circle when available
- AC-T016.2: Falls back to hardcoded template characters if no social circle data
- AC-T016.3: Does not break existing arc creation/progression logic
**Estimated hours**: 1
**TDD**: Test enriched context; test fallback to template; test arc lifecycle unaffected

---

## US-4: Meta-Instructions Schema + Integration

### T017: SQLAlchemy model update for users table
**File**: `nikita/db/models/user.py`
**Description**: Add routine_config and meta_instructions mapped columns.
**Acceptance Criteria**:
- AC-T017.1: `routine_config: Mapped[dict] = mapped_column(JSONB, default=dict)`
- AC-T017.2: `meta_instructions: Mapped[dict] = mapped_column(JSONB, default=dict)`
- AC-T017.3: Existing model fields unchanged
**Estimated hours**: 0.5
**TDD**: Test model instantiation with new fields

### T018: SQLAlchemy model update for user_social_circles
**File**: `nikita/db/models/social_circle.py`
**Description**: Add last_event and sentiment mapped columns.
**Acceptance Criteria**:
- AC-T018.1: `last_event: Mapped[datetime | None] = mapped_column(nullable=True)`
- AC-T018.2: `sentiment: Mapped[str | None] = mapped_column(String(20), default='neutral')`
- AC-T018.3: Existing model fields unchanged
- AC-T018.4: `to_dict()` includes new fields
**Estimated hours**: 0.5
**TDD**: Test model with new fields; test to_dict output

---

## Integration & Testing

### T019: Integration test — full day generation with enhancements
**File**: `tests/life_simulation/test_enhanced_generation.py`
**Description**: End-to-end test of enhanced event generation.
**Acceptance Criteria**:
- AC-T019.1: Test generates events with routine context (flag ON)
- AC-T019.2: Test generates events with mood bias (flag ON)
- AC-T019.3: Test updates NPC states after generation
- AC-T019.4: Test verifies flag OFF preserves original behavior
**Estimated hours**: 1.5
**TDD**: This IS the test task

### T020: Regression test — existing life_simulation tests pass
**File**: `tests/life_simulation/`
**Description**: Verify all existing tests pass without modification.
**Acceptance Criteria**:
- AC-T020.1: `pytest tests/life_simulation/ -v` passes with 0 failures
- AC-T020.2: No existing test requires modification
- AC-T020.3: Feature flag OFF by default ensures backward compat
**Estimated hours**: 0.5
**TDD**: Run existing tests as-is

### T021: Update __init__.py exports
**File**: `nikita/life_simulation/__init__.py`
**Description**: Export new models and functions.
**Acceptance Criteria**:
- AC-T021.1: `WeeklyRoutine` and `DayRoutine` in `__all__`
- AC-T021.2: Lazy import for new functions
- AC-T021.3: Existing exports unchanged
**Estimated hours**: 0.25
**TDD**: Test import works

### T022: LifeSimStage pipeline verification
**File**: `tests/pipeline/test_life_sim_stage.py`
**Description**: Verify pipeline stage works with enhanced simulator.
**Acceptance Criteria**:
- AC-T022.1: `LifeSimStage._run()` succeeds with enhanced simulator (flag ON)
- AC-T022.2: Pipeline stage handles enhanced simulator errors gracefully
- AC-T022.3: Flag OFF: stage behavior identical to current
**Estimated hours**: 0.5
**TDD**: Test stage with mocked enhanced simulator

---

## Summary

| Phase | Tasks | IDs | Hours |
|-------|-------|-----|-------|
| Foundation | 7 | T001-T004, T009-T010, T014 | 3.75 |
| Event Generation | 4 | T005-T008 | 4.5 |
| NPC Consolidation | 6 | T011-T013, T015-T016, T018 | 7 |
| Meta-Instructions | 1 | T017 | 0.5 |
| Integration | 4 | T019-T022 | 2.75 |
| **Total** | **22** | | **18.5** |

---

## Task Dependencies

```
T001 --> T002, T003 (models needed for config and loader)
T003 --> T005, T006 (loader needed for event gen and simulator)
T004 --> T006, T008, T012, T015 (flag needed for gating)
T005 --> T006 (event gen prompt needed before simulator wire)
T007 --> T008 (mood prompt needed before simulator wire)
T009 --> T017 (migration before model update)
T010 --> T018 (migration before model update)
T011 --> T012, T013, T015, T016 (resolver needed for NPC ops)
T014 --> T015 (yaml update before enhanced context)
T001-T018 --> T019 (all features before integration test)
T019 --> T020 (integration before regression)
T020 --> T021, T022 (regression before polish)
```
