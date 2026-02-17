# Tasks 057: Conflict System CORE

**Spec**: 057-conflict-system-core/spec.md
**Plan**: 057-conflict-system-core/plan.md
**Total**: 20 tasks | **Est**: 3-4 days

---

## Phase 1: Foundation

### T1: Feature Flag + Settings
- [ ] Add `conflict_temperature_enabled: bool = False` to `nikita/config/settings.py`
- [ ] Create utility: `is_conflict_temperature_enabled() -> bool` in `nikita/conflicts/__init__.py`
- [ ] Write test: flag defaults OFF, respects env var `CONFLICT_TEMPERATURE_ENABLED`
- **File**: `nikita/config/settings.py`, `nikita/conflicts/__init__.py`
- **Test**: `tests/conflicts/test_feature_flag.py`
- **AC**: US-2 AC-2.6
- **Est**: 0.5h

### T2: ConflictTemperature + Supporting Models
- [ ] Add `TemperatureZone` enum: CALM, WARM, HOT, CRITICAL
- [ ] Add `HorsemanType` enum: CRITICISM, CONTEMPT, DEFENSIVENESS, STONEWALLING
- [ ] Add `ConflictTemperature` model: value (0.0-100.0), zone, last_update
- [ ] Add `GottmanCounters` model: positive_count, negative_count, session_positive, session_negative, window_start
- [ ] Add `RepairRecord` model: at, quality, temp_delta
- [ ] Add `ConflictDetails` model: temperature, zone, gottman counters, horsemen_detected, repair_attempts, last_temp_update
- [ ] Write tests: model validation, zone calculation, serialization
- **File**: `nikita/conflicts/models.py`
- **Test**: `tests/conflicts/test_models_temperature.py`
- **AC**: US-1 AC-1.1, AC-1.5
- **Est**: 1.5h

### T3: DB Migration — conflict_details + last_conflict_at
- [ ] Apply migration: `ALTER TABLE nikita_emotional_states ADD conflict_details JSONB DEFAULT '{}'`
- [ ] Apply migration: `ALTER TABLE users ADD last_conflict_at TIMESTAMPTZ`
- [ ] Apply migration: `CREATE INDEX idx_emotional_states_conflict_details ON nikita_emotional_states USING GIN (conflict_details)`
- [ ] Verify migration with Supabase MCP `execute_sql`
- **Tool**: Supabase MCP `apply_migration`
- **AC**: US-1 AC-1.5, US-6 AC-6.4
- **Est**: 0.5h

### T4: Temperature Engine
- [ ] Create `nikita/conflicts/temperature.py` with `TemperatureEngine` class
- [ ] Method: `increase(current: float, delta: float) -> float` — clamp 0-100
- [ ] Method: `decrease(current: float, delta: float) -> float` — clamp 0-100
- [ ] Method: `apply_time_decay(current: float, hours_elapsed: float, rate: float = 0.5) -> float`
- [ ] Method: `get_zone(temperature: float) -> TemperatureZone`
- [ ] Method: `get_injection_probability(zone: TemperatureZone) -> tuple[float, float]` — returns (min_prob, max_prob)
- [ ] Method: `get_max_severity(zone: TemperatureZone) -> float`
- [ ] Method: `calculate_delta_from_score(score_delta: float) -> float` — maps score changes to temp deltas
- [ ] Method: `calculate_delta_from_horseman(horseman: HorsemanType) -> float`
- [ ] Constants: ZONE_BOUNDARIES, INJECTION_PROBABILITIES, HORSEMAN_DELTAS, TIME_DECAY_RATE
- [ ] Write tests: boundary values (0, 25, 50, 75, 100), zone transitions, clamping, decay over time
- **File**: `nikita/conflicts/temperature.py`
- **Test**: `tests/conflicts/test_temperature.py`
- **AC**: US-1 AC-1.1-1.4, US-2 AC-2.1-2.4
- **Est**: 2h

### T5: Gottman Tracker
- [ ] Create `nikita/conflicts/gottman.py` with `GottmanTracker` class
- [ ] Method: `record_interaction(is_positive: bool, timestamp: datetime) -> GottmanCounters`
- [ ] Method: `get_ratio(counters: GottmanCounters) -> float` — positive/negative, handle div-by-zero
- [ ] Method: `get_target(is_in_conflict: bool) -> float` — 5.0 conflict, 20.0 normal
- [ ] Method: `is_below_target(counters: GottmanCounters, is_in_conflict: bool) -> bool`
- [ ] Method: `calculate_temperature_delta(counters: GottmanCounters, is_in_conflict: bool) -> float` — +2-5 below target, -1-2 above
- [ ] Method: `prune_window(counters: GottmanCounters, window_days: int = 7) -> GottmanCounters`
- [ ] Method: `reset_session(counters: GottmanCounters) -> GottmanCounters`
- [ ] Method: `initialize_from_history(score_entries: list[dict]) -> GottmanCounters` — bootstrap from score_history
- [ ] Write tests: ratio calculation, window pruning, target comparison, initialization
- **File**: `nikita/conflicts/gottman.py`
- **Test**: `tests/conflicts/test_gottman.py`
- **AC**: US-3 AC-3.1-3.7
- **Est**: 2h

---

## Phase 2: Scoring Integration

### T6: Four Horsemen in Analyzer Prompt
- [ ] Add Four Horsemen definitions to `ANALYSIS_SYSTEM_PROMPT` in `analyzer.py`
- [ ] Add instruction: detect and tag each horseman in `behaviors_identified`
- [ ] Use prefix convention: `horseman:criticism`, `horseman:contempt`, `horseman:defensiveness`, `horseman:stonewalling`
- [ ] Write tests: prompt contains horsemen definitions, mock LLM returns horsemen tags
- **File**: `nikita/engine/scoring/analyzer.py`
- **Test**: `tests/engine/scoring/test_analyzer.py` (extend)
- **AC**: US-4 AC-4.1-4.5, AC-4.7
- **Est**: 1h

### T7: ResponseAnalysis Horsemen Extension
- [ ] Add `HORSEMEN_PREFIXES` constant to `models.py`
- [ ] Add helper: `get_horsemen_from_behaviors(behaviors: list[str]) -> list[HorsemanType]`
- [ ] Ensure existing behaviors_identified field accepts horsemen tags (no schema change needed, list[str])
- [ ] Write tests: horsemen extraction from mixed behaviors list
- **File**: `nikita/engine/scoring/models.py`
- **Test**: `tests/engine/scoring/test_models.py` (extend)
- **AC**: US-4 AC-4.5
- **Est**: 0.5h

### T8: Gottman Counter in Scoring Service
- [ ] After `score_interaction()`, determine is_positive from `result.delta`
- [ ] Call `GottmanTracker.record_interaction()` with result polarity
- [ ] Read current `conflict_details` from DB (or initialize empty)
- [ ] Write updated `conflict_details` with new Gottman counters
- [ ] Gate all new behavior behind feature flag
- [ ] Write tests: positive interaction increments positive counter, negative increments negative
- **File**: `nikita/engine/scoring/service.py`
- **Test**: `tests/engine/scoring/test_service.py` (extend)
- **AC**: US-3 AC-3.1, AC-3.4
- **Est**: 1.5h

### T9: Temperature Update in Scoring Service
- [ ] After scoring, calculate temperature delta from: score_delta, horsemen detected, Gottman ratio
- [ ] Apply temperature delta via `TemperatureEngine.increase()/decrease()`
- [ ] Write updated temperature to `conflict_details` JSONB
- [ ] Update `users.last_conflict_at` when temperature crosses into HOT/CRITICAL
- [ ] Gate behind feature flag
- [ ] Write tests: negative score -> temp increase, horseman -> temp increase, positive score -> temp decrease
- **File**: `nikita/engine/scoring/service.py`
- **Test**: `tests/engine/scoring/test_service_temperature.py`
- **AC**: US-1 AC-1.2-1.3, US-4 AC-4.6, US-3 AC-3.5-3.6
- **Est**: 2h

---

## Phase 3: Conflict System Rewire

### T10: Generator — Temperature Zone Injection
- [ ] Add `generate_with_temperature()` method to `ConflictGenerator`
- [ ] Read temperature zone -> determine injection probability
- [ ] Use `random.random() < probability` for stochastic injection
- [ ] Cap severity by zone max
- [ ] Update `generate()` to dispatch: flag ON -> `generate_with_temperature()`, flag OFF -> existing logic
- [ ] Write tests: CALM=no conflict, WARM=low prob, HOT=medium prob, CRITICAL=high prob
- **File**: `nikita/conflicts/generator.py`
- **Test**: `tests/conflicts/test_generation.py` (extend)
- **AC**: US-2 AC-2.1-2.6
- **Est**: 1.5h

### T11: Detector — Temperature on Trigger Detection
- [ ] After trigger detection, calculate temperature delta per trigger type
- [ ] DISMISSIVE: +3, NEGLECT: +5, JEALOUSY: +4, BOUNDARY: +8, TRUST: +6
- [ ] Update temperature in `conflict_details` JSONB
- [ ] Gate behind feature flag
- [ ] Write tests: each trigger type produces expected temperature increase
- **File**: `nikita/conflicts/detector.py`
- **Test**: `tests/conflicts/test_detection.py` (extend)
- **AC**: US-1 AC-1.2
- **Est**: 1h

### T12: Escalation — Temperature Integration
- [ ] Update `acknowledge()` to reduce temperature by 5-10 points
- [ ] Update `check_escalation()` to use temperature zones when flag ON
- [ ] HOT zone = DIRECT equivalent, CRITICAL zone = CRISIS equivalent
- [ ] Gate behind feature flag
- [ ] Write tests: acknowledgment reduces temperature, zone-based escalation
- **File**: `nikita/conflicts/escalation.py`
- **Test**: `tests/conflicts/test_escalation.py` (extend)
- **AC**: US-1 AC-1.2
- **Est**: 1h

### T13: Resolution — Temperature Reduction + Gottman
- [ ] After `resolve()`, calculate temperature reduction from quality
- [ ] EXCELLENT: -25, GOOD: -15, ADEQUATE: -5, POOR: +2, HARMFUL: +5
- [ ] Update Gottman positive counter on successful repair (EXCELLENT/GOOD/ADEQUATE)
- [ ] Record repair in `conflict_details.repair_attempts` array
- [ ] Gate behind feature flag
- [ ] Write tests: resolution quality maps to correct temperature delta, Gottman updated
- **File**: `nikita/conflicts/resolution.py`
- **Test**: `tests/conflicts/test_resolution.py` (extend)
- **AC**: US-5 AC-5.1-5.6
- **Est**: 1.5h

### T14: Breakup — Temperature Thresholds
- [ ] Add temperature-based checks to `check_threshold()`
- [ ] CRITICAL zone >24h: warning
- [ ] Temperature >90 for >48h: breakup trigger
- [ ] Read `last_conflict_at` for duration calculation
- [ ] Preserve existing score-based thresholds
- [ ] Gate behind feature flag
- [ ] Write tests: temperature-based warning, temperature-based breakup, score-based still works
- **File**: `nikita/conflicts/breakup.py`
- **Test**: `tests/conflicts/test_breakup.py` (extend)
- **AC**: US-6 AC-6.1-6.3
- **Est**: 1h

---

## Phase 4: Pipeline + Emotional State

### T15: ConflictStage — Temperature Consumption
- [ ] Read `conflict_details` from emotional state DB
- [ ] Extract temperature and zone
- [ ] Set `ctx.active_conflict = True` when zone is HOT or CRITICAL
- [ ] Set `ctx.conflict_type` to zone name (warm/hot/critical)
- [ ] Store temperature value in ctx for prompt builder access
- [ ] Default to temperature=0 when `conflict_details` is empty/missing
- [ ] Gate behind feature flag
- [ ] Write tests: each zone maps correctly to active_conflict boolean
- **File**: `nikita/pipeline/stages/conflict.py`
- **Test**: `tests/pipeline/test_conflict_stage.py` (extend or create)
- **AC**: US-7 AC-7.1-7.4
- **Est**: 1h

### T16: Emotional State — Deprecation Notice
- [ ] Add deprecation comment to `ConflictState` enum: "Deprecated by Spec 057. Use conflict_details.temperature when conflict_temperature flag is ON"
- [ ] Add static method `temperature_from_enum(state: ConflictState) -> float` to EmotionalStateModel
- [ ] Mapping: NONE=0, PA=40, COLD=50, VULNERABLE=30, EXPLOSIVE=85
- [ ] Write tests: enum-to-temperature mapping
- **File**: `nikita/emotional_state/models.py`
- **Test**: `tests/emotional_state/test_models.py` (extend)
- **AC**: US-1 AC-1.6
- **Est**: 0.5h

### T17: Temperature Time Decay
- [ ] Add `apply_passive_decay()` function to `temperature.py`
- [ ] Calculate hours since `last_temp_update`
- [ ] Apply decay: `new_temp = max(0, current - hours_elapsed * 0.5)`
- [ ] Update `last_temp_update` timestamp
- [ ] Integrate into ConflictStage (apply decay on each pipeline run)
- [ ] Write tests: decay over 1h, 24h, 48h; no negative temperature
- **File**: `nikita/conflicts/temperature.py`, `nikita/pipeline/stages/conflict.py`
- **Test**: `tests/conflicts/test_temperature.py` (extend)
- **AC**: US-1 AC-1.4
- **Est**: 1h

---

## Phase 5: Migration + Integration

### T18: Existing User Migration Utility
- [ ] Create `nikita/conflicts/migration.py` with `migrate_user_conflict_state()`
- [ ] Read current `conflict_state` enum from `nikita_emotional_states`
- [ ] Map to temperature via `temperature_from_enum()`
- [ ] Read `score_history` (last 7 days) to initialize Gottman counters
- [ ] Write `conflict_details` JSONB with initialized values
- [ ] Set `users.last_conflict_at` from last non-NONE conflict timestamp
- [ ] Write tests: each enum state migrates correctly, Gottman bootstraps from history
- **File**: `nikita/conflicts/migration.py`
- **Test**: `tests/conflicts/test_migration.py`
- **AC**: US-1 AC-1.6, US-3 AC-3.7
- **Est**: 1.5h

### T19: Integration Tests
- [ ] Test full flow: message scoring -> temperature increase -> conflict injection
- [ ] Test repair flow: resolution -> temperature decrease -> Gottman update
- [ ] Test breakup flow: sustained CRITICAL -> warning -> breakup
- [ ] Test feature flag OFF: zero behavior change in full flow
- [ ] Test feature flag ON: new temperature-based behavior active
- [ ] Mock DB interactions using existing test patterns
- **File**: `tests/conflicts/test_integration_temperature.py`
- **AC**: All user stories
- **Est**: 2h

### T20: Backward Compatibility Verification
- [ ] Run all `tests/conflicts/` with flag OFF — 0 failures
- [ ] Run all `tests/emotional_state/` with flag OFF — 0 failures
- [ ] Run all `tests/engine/scoring/` with flag OFF — 0 failures
- [ ] Run all `tests/pipeline/` with flag OFF — 0 failures
- [ ] Run full suite: `python -m pytest tests/ -x -q --timeout=60`
- [ ] Document any test modifications needed
- **File**: N/A (verification only)
- **AC**: All backward compatibility requirements
- **Est**: 1h

---

## Summary

| Phase | Tasks | Est Hours | Key Output |
|-------|-------|-----------|------------|
| 1: Foundation | T1-T5 | 6.5h | Models, engine, tracker |
| 2: Scoring | T6-T9 | 5h | Horsemen, Gottman, temp in scoring |
| 3: Rewire | T10-T14 | 6h | Generator, detector, resolution, breakup |
| 4: Pipeline | T15-T17 | 2.5h | Pipeline stage, deprecation, decay |
| 5: Integration | T18-T20 | 4.5h | Migration, integration tests, compat |
| **Total** | **20** | **24.5h** | |

## Task Status Tracker

| ID | Status | Description |
|----|--------|-------------|
| T1 | [ ] | Feature flag + settings |
| T2 | [ ] | ConflictTemperature models |
| T3 | [ ] | DB migration |
| T4 | [ ] | Temperature engine |
| T5 | [ ] | Gottman tracker |
| T6 | [ ] | Four Horsemen in analyzer |
| T7 | [ ] | ResponseAnalysis extension |
| T8 | [ ] | Gottman in scoring service |
| T9 | [ ] | Temperature in scoring service |
| T10 | [ ] | Generator temperature zones |
| T11 | [ ] | Detector temperature update |
| T12 | [ ] | Escalation temperature integration |
| T13 | [ ] | Resolution temperature reduction |
| T14 | [ ] | Breakup temperature thresholds |
| T15 | [ ] | ConflictStage temperature |
| T16 | [ ] | Emotional state deprecation |
| T17 | [ ] | Temperature time decay |
| T18 | [ ] | User migration utility |
| T19 | [ ] | Integration tests |
| T20 | [ ] | Backward compatibility |
