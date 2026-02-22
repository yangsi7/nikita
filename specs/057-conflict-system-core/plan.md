# Plan 057: Conflict System CORE — Implementation Plan

**Spec**: 057-conflict-system-core/spec.md
**Approach**: TDD per task, feature-flagged, backward-compatible
**Total Tasks**: 20
**Estimated Effort**: 3-4 days

---

## Phase 1: Foundation (Tasks 1-5)

**Goal**: Data models, DB migration, feature flag, temperature zone engine.

### Task Sequence

1. **T1: Feature flag + settings** — Add `conflict_temperature_enabled` to Settings. Add feature flag check utility function.
2. **T2: ConflictTemperature model** — New Pydantic models: ConflictTemperature, TemperatureZone enum, HorsemanType enum, GottmanTracker, RepairRecord. All in `conflicts/models.py`.
3. **T3: DB migration** — Add `conflict_details JSONB` to `nikita_emotional_states`, `last_conflict_at TIMESTAMPTZ` to `users`, GIN index.
4. **T4: Temperature engine** — Core class `TemperatureEngine` with: `increase()`, `decrease()`, `apply_time_decay()`, `get_zone()`, `get_injection_probability()`. Pure functions, no DB.
5. **T5: Gottman tracker** — `GottmanTracker` class with: `record_positive()`, `record_negative()`, `get_ratio()`, `get_target()`, `is_below_target()`. Rolling 7-day + per-session.

**Dependencies**: T1 < T2 < T3, T4 depends on T2, T5 depends on T2.

### Risk Mitigation
- All constants are class-level attributes (tunable without code changes)
- Temperature engine is pure (no DB, no side effects) — easy to unit test

---

## Phase 2: Scoring Integration (Tasks 6-9)

**Goal**: Four Horsemen detection, Gottman counter updates in scoring pipeline.

### Task Sequence

6. **T6: Four Horsemen in analyzer prompt** — Add Horsemen definitions to `ANALYSIS_SYSTEM_PROMPT`. Add `horsemen_detected` field processing.
7. **T7: ResponseAnalysis model extension** — Add horsemen typing to `behaviors_identified`. Ensure backward-compatible (no breaking existing tests).
8. **T8: Gottman counter in scoring service** — After `score_interaction()`, increment positive/negative counters via `GottmanTracker`. Write to `conflict_details` JSONB.
9. **T9: Temperature update in scoring service** — After scoring, update temperature based on delta rules (score drops, horsemen detected). Read/write `conflict_details`.

**Dependencies**: T6 < T7, T8 depends on T5, T9 depends on T4+T8.

### Risk Mitigation
- Horsemen detection is additive to existing prompt (no removal of existing analysis)
- All new scoring behavior gated by feature flag
- Existing `score_interaction()` signature unchanged

---

## Phase 3: Conflict System Rewire (Tasks 10-14)

**Goal**: Replace cooldown with temperature zones, connect repairs, update breakup.

### Task Sequence

10. **T10: Generator temperature zones** — Replace `CONFLICT_COOLDOWN_HOURS` with zone-based injection probability in `ConflictGenerator.generate()`. Feature flag gates new path.
11. **T11: Detector temperature update** — Update `TriggerDetector.detect()` to update temperature on trigger detection. Each trigger type maps to a temperature delta.
12. **T12: Escalation temperature integration** — Update `EscalationManager.acknowledge()` to reduce temperature. Escalation checks use temperature zones instead of time thresholds.
13. **T13: Resolution temperature reduction** — Connect `ResolutionManager.resolve()` to temperature reduction. Map resolution quality to temperature delta. Update Gottman positive counter on repair.
14. **T14: Breakup temperature thresholds** — Add temperature-based breakup checks to `BreakupManager.check_threshold()`. CRITICAL zone >24h = warning, >90 for >48h = breakup.

**Dependencies**: T10 depends on T4, T11-T14 can run in parallel after T9.

### Risk Mitigation
- Each rewired function has `if not flag_enabled: return existing_behavior` guard
- Existing in-memory `ConflictStore` operations untouched
- All threshold constants are class-level (tunable)

---

## Phase 4: Pipeline + Emotional State Integration (Tasks 15-17)

**Goal**: Wire temperature into pipeline context, update emotional state model.

### Task Sequence

15. **T15: ConflictStage temperature consumption** — Update `ConflictStage._run()` to read temperature from `conflict_details`. Set `ctx.active_conflict` based on zone (HOT/CRITICAL = true).
16. **T16: Emotional state deprecation** — Add deprecation notice to `ConflictState` enum in `models.py`. Add helper method `temperature_from_enum()` for migration.
17. **T17: Temperature time decay** — Add temperature passive decay logic (0.5/hr). Integrate with existing decay processor or conflict stage.

**Dependencies**: T15 depends on T4, T16-T17 independent.

### Risk Mitigation
- ConflictStage already handles missing data gracefully (non-critical stage)
- Deprecation is documentation-only (no code removal)

---

## Phase 5: Migration + Integration Tests (Tasks 18-20)

**Goal**: Existing user migration, integration tests, end-to-end verification.

### Task Sequence

18. **T18: Existing user migration utility** — Migration function: read current `conflict_state` enum, map to temperature, initialize Gottman from `score_history`, write `conflict_details` JSONB.
19. **T19: Integration tests** — Test full flow: message -> scoring -> temperature update -> conflict injection -> resolution -> temperature decrease. Test feature flag ON/OFF paths.
20. **T20: Backward compatibility verification** — Run all existing conflict tests with flag OFF. Verify zero behavior change. Run with flag ON and verify new behavior.

**Dependencies**: T18 depends on T4+T5, T19 depends on all previous, T20 is final.

### Risk Mitigation
- Integration tests mock DB via existing test patterns
- Backward compatibility test is explicit pass/fail gate

---

## Testing Strategy

### Unit Tests (per task)
- Each task writes tests BEFORE implementation (TDD)
- Temperature engine: boundary values, zone transitions, clamping
- Gottman tracker: ratio calculation, rolling window, session tracking
- Four Horsemen: prompt output parsing, false positive rate
- Feature flag: ON/OFF behavior isolation

### Integration Tests (T19)
- Full scoring -> temperature -> conflict flow
- Resolution -> temperature reduction -> Gottman update
- Breakup threshold with temperature + score combination
- Pipeline stage with temperature data present/absent

### Backward Compatibility (T20)
- All existing `tests/conflicts/` pass with flag OFF
- All existing `tests/emotional_state/test_conflict.py` pass
- All existing `tests/engine/scoring/` pass
- No signature changes to public APIs

---

## Dependency Graph

```
T1 (flag) ──► T2 (models) ──► T3 (migration)
                 │
                 ├──► T4 (temp engine) ──► T9 (temp in scoring) ──► T10 (generator)
                 │                                                    T11 (detector)
                 │                                                    T12 (escalation)
                 │                                                    T13 (resolution)
                 │                                                    T14 (breakup)
                 │
                 └──► T5 (gottman) ──► T8 (gottman in scoring)
                                              │
T6 (horsemen prompt) ──► T7 (model ext)      │
                                              ▼
                              T15 (pipeline) ──► T17 (decay)
                              T16 (deprecation)
                              T18 (migration)
                              T19 (integration) ──► T20 (compat)
```

---

## File Change Summary

| File | Type | Lines Est |
|------|------|-----------|
| `nikita/config/settings.py` | MODIFY | +5 |
| `nikita/conflicts/models.py` | MODIFY | +120 |
| `nikita/conflicts/temperature.py` | CREATE | ~200 |
| `nikita/conflicts/gottman.py` | CREATE | ~150 |
| `nikita/conflicts/detector.py` | MODIFY | +30 |
| `nikita/conflicts/generator.py` | MODIFY | +40 |
| `nikita/conflicts/escalation.py` | MODIFY | +25 |
| `nikita/conflicts/resolution.py` | MODIFY | +30 |
| `nikita/conflicts/breakup.py` | MODIFY | +35 |
| `nikita/engine/scoring/analyzer.py` | MODIFY | +25 |
| `nikita/engine/scoring/service.py` | MODIFY | +40 |
| `nikita/engine/scoring/models.py` | MODIFY | +5 |
| `nikita/pipeline/stages/conflict.py` | MODIFY | +20 |
| `nikita/emotional_state/models.py` | MODIFY | +10 |
| `nikita/conflicts/migration.py` | CREATE | ~80 |
| Tests (multiple files) | CREATE/MODIFY | ~600 |
| **Total** | | ~1,415 |

---

## Constants Reference (Tunable)

| Constant | Value | Location |
|----------|-------|----------|
| CALM zone | 0-25 | temperature.py |
| WARM zone | 25-50 | temperature.py |
| HOT zone | 50-75 | temperature.py |
| CRITICAL zone | 75-100 | temperature.py |
| Time decay rate | 0.5/hr | temperature.py |
| Gottman conflict target | 5:1 | gottman.py |
| Gottman normal target | 20:1 | gottman.py |
| Rolling window | 7 days | gottman.py |
| Repair EXCELLENT delta | -25 | resolution.py |
| Repair GOOD delta | -15 | resolution.py |
| Horseman temp delta | +3 to +8 | temperature.py |
| Breakup temp threshold | 90 for 48h | breakup.py |
