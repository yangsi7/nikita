# Tasks 058: Multi-Phase Boss + Warmth

**Spec**: 058-multi-phase-boss/spec.md
**Plan**: 058-multi-phase-boss/plan.md
**Total**: 24 tasks | **Est**: ~15.5 hours

---

## Phase A: Feature Flag + Models (Foundation)

### T-A1: Feature Flag — `multi_phase_boss_enabled`
- [ ] Add `multi_phase_boss_enabled: bool = Field(default=False, description="Enable 2-phase boss encounters with PARTIAL outcome. Rollback: MULTI_PHASE_BOSS_ENABLED=false")` to settings after `conflict_temperature_enabled` (~line 148)
- [ ] Add convenience function `is_multi_phase_boss_enabled() -> bool` in `nikita/engine/chapters/__init__.py`
- [ ] Write test: flag defaults OFF, respects env var `MULTI_PHASE_BOSS_ENABLED`
- **File**: `nikita/config/settings.py`, `nikita/engine/chapters/__init__.py`
- **Test**: `tests/engine/chapters/test_feature_flag_058.py`
- **AC**: AC-8.1, AC-8.2
- **Est**: 0.25h

### T-A2: `BossPhase` Enum + `BossPhaseState` Model
- [ ] Add `BossPhase(str, Enum)` with OPENING/RESOLUTION values to `boss.py`
- [ ] Add `BossPhaseState(BaseModel)` with fields: phase, chapter, started_at, turn_count (default 0), conversation_history (default [])
- [ ] Write tests: enum values, serialization round-trip, model defaults, datetime handling
- **File**: `nikita/engine/chapters/boss.py`
- **Test**: `tests/engine/chapters/test_boss_phase_models.py`
- **AC**: AC-2.1
- **Est**: 0.25h

### T-A3: Extend `BossResult` Enum with PARTIAL
- [ ] Add `PARTIAL = "PARTIAL"` to existing `BossResult` enum in `judgment.py`
- [ ] Update `JudgmentResult.outcome` type hint comment to include PARTIAL
- [ ] Verify backward compat: PASS/FAIL still work
- [ ] Write tests: PARTIAL member exists, all three outcomes roundtrip
- **File**: `nikita/engine/chapters/judgment.py`
- **Test**: `tests/engine/chapters/test_judgment_partial.py`
- **AC**: AC-3.1
- **Est**: 0.15h

### T-A4: Add `boss_phase` Field to `ConflictDetails`
- [ ] Add `boss_phase: dict[str, Any] | None = Field(default=None)` to `ConflictDetails` model (~line 394)
- [ ] When None, no boss is active (AC-2.5)
- [ ] Write tests: boss_phase None by default, stores BossPhaseState.model_dump() round-trip through JSONB
- **File**: `nikita/conflicts/models.py`
- **Test**: `tests/conflicts/test_models_boss_phase.py`
- **AC**: AC-2.2, AC-2.5
- **Est**: 0.25h
- **Depends on**: T-A2

### T-A5: DB Migration — `vulnerability_exchanges` Column
- [ ] Apply migration via Supabase MCP: `ALTER TABLE user_metrics ADD COLUMN vulnerability_exchanges INT DEFAULT 0;`
- [ ] Verify column exists with Supabase MCP `execute_sql`
- **Tool**: Supabase MCP `apply_migration`
- **AC**: AC-6.3
- **Est**: 0.15h

**Phase A tests**: ~8 unit tests (BossPhase enum, BossPhaseState ser/deser, BossResult.PARTIAL, ConflictDetails.boss_phase round-trip, feature flag default OFF)

---

## Phase B: Phase Manager (Core State Machine)

### T-B1: Create `BossPhaseManager` Class
- [ ] Create `nikita/engine/chapters/phase_manager.py` (NEW file)
- [ ] Method: `start_boss(chapter: int) -> BossPhaseState` — creates OPENING state with current timestamp
- [ ] Method: `advance_phase(state: BossPhaseState, user_message: str, nikita_response: str) -> BossPhaseState` — OPENING->RESOLUTION, appends to conversation_history, increments turn_count
- [ ] Method: `is_resolution_complete(state: BossPhaseState) -> bool` — True when phase=RESOLUTION and turn_count >= 2
- [ ] Method: `get_phase_prompt(state: BossPhaseState) -> dict[str, str]` — dispatches to phase-specific prompt from prompts.py
- [ ] Write tests: start_boss returns OPENING, advance transitions to RESOLUTION, history appended, resolution detection
- **File**: `nikita/engine/chapters/phase_manager.py` (CREATE)
- **Test**: `tests/engine/chapters/test_phase_manager.py`
- **AC**: AC-1.1, AC-1.2, AC-1.3, AC-2.3, AC-2.4
- **Est**: 1.5h
- **Depends on**: T-A2, T-A4

### T-B2: Persistence Helpers — Read/Write `boss_phase`
- [ ] Add static method: `persist_phase(conflict_details: dict | None, state: BossPhaseState) -> dict` — writes `state.model_dump(mode="json")` into `conflict_details["boss_phase"]`
- [ ] Add static method: `load_phase(conflict_details: dict | None) -> BossPhaseState | None` — parses `conflict_details.get("boss_phase")`, returns None if absent or parse error
- [ ] Use `ConflictDetails.from_jsonb()` pattern from Spec 057
- [ ] Write tests: persist round-trip, load returns None for empty/corrupt data, graceful degradation on parse error
- **File**: `nikita/engine/chapters/phase_manager.py`
- **Test**: `tests/engine/chapters/test_phase_manager.py` (extend)
- **AC**: AC-1.4, AC-2.2, AC-2.3
- **Est**: 0.5h
- **Depends on**: T-B1

### T-B3: Boss Timeout Logic (24h Auto-FAIL)
- [ ] Add method: `is_timed_out(state: BossPhaseState, now: datetime | None = None) -> bool` — checks `(now - state.started_at) > timedelta(hours=24)`
- [ ] Write tests: timeout at 24h+1s, no timeout at 23h59m, edge case at exactly 24h
- **File**: `nikita/engine/chapters/phase_manager.py`
- **Test**: `tests/engine/chapters/test_phase_manager.py` (extend)
- **AC**: AC-1.6
- **Est**: 0.25h
- **Depends on**: T-B1

**Phase B tests**: ~15 unit tests (start_boss, advance_phase transitions, history append, resolution complete, persist round-trip, load None for empty, timeout boundary, interrupted boss preserves state, clear_boss_phase)

---

## Phase C: Phase-Prompt Variants (10 Prompts)

### T-C1: Create Phase-Aware Prompt Structure
- [ ] Add `BOSS_PHASE_PROMPTS: dict[int, dict[str, BossPrompt]]` to `prompts.py`
- [ ] 2 phases x 5 chapters = 10 prompts total
- [ ] OPENING prompts: reuse/adapt existing `BOSS_PROMPTS[ch]` content
- [ ] RESOLUTION prompts: new content guiding toward judgment/resolution
- [ ] Each prompt includes: challenge_context, success_criteria, in_character_opening, phase_instruction
- [ ] Ch1 (Curiosity): light test | Ch5 (Established): deep vulnerability challenge
- [ ] Write tests: all 10 prompts exist, required keys present in each
- **File**: `nikita/engine/chapters/prompts.py`
- **Test**: `tests/engine/chapters/test_boss_phase_prompts.py`
- **AC**: AC-4.1, AC-4.2, AC-4.3, AC-4.4, AC-4.5, AC-4.6
- **Est**: 1.5h
- **Depends on**: T-A2

### T-C2: Add `get_boss_phase_prompt()` Function
- [ ] Implement `get_boss_phase_prompt(chapter: int, phase: str) -> BossPrompt`
- [ ] Validate chapter 1-5 and phase opening/resolution
- [ ] Raise `KeyError` for invalid chapter or phase
- [ ] Write tests: valid lookups for all 10 combos, invalid chapter raises, invalid phase raises, Ch1 opening matches existing BOSS_PROMPTS[1] content
- **File**: `nikita/engine/chapters/prompts.py`
- **Test**: `tests/engine/chapters/test_boss_phase_prompts.py` (extend)
- **AC**: AC-4.4, AC-4.6
- **Est**: 0.3h
- **Depends on**: T-C1

**Phase C tests**: ~12 tests (10 prompt existence/key checks, invalid chapter, invalid phase)

---

## Phase D: Multi-Turn Judgment

### T-D1: `judge_multi_phase_outcome()` Method
- [ ] Add `judge_multi_phase_outcome(phase_state: BossPhaseState, chapter: int, boss_prompt: dict) -> JudgmentResult` to `BossJudgment`
- [ ] Build judgment prompt with full conversation history from both phases
- [ ] Evaluate OPENING response quality + RESOLUTION response quality
- [ ] Include PARTIAL criteria: "acknowledged issue but didn't resolve"
- [ ] Three-way judgment: PASS (genuine resolution), PARTIAL (effort shown), FAIL (dismissive/avoidant)
- [ ] Write tests: multi-phase judgment returns PASS/PARTIAL/FAIL, full history passed, both phases evaluated, LLM failure -> FAIL
- **File**: `nikita/engine/chapters/judgment.py`
- **Test**: `tests/engine/chapters/test_judgment_multi_phase.py`
- **AC**: AC-5.1, AC-5.2, AC-5.3, AC-5.4
- **Est**: 1h
- **Depends on**: T-A2, T-A3

### T-D2: Confidence-Based PARTIAL Threshold
- [ ] Update judgment system prompt: instruct LLM to return confidence (0.0-1.0)
- [ ] Post-processing: if confidence < 0.7 AND outcome is PASS or FAIL, override to PARTIAL
- [ ] Write tests: high confidence PASS stays PASS, low confidence PASS -> PARTIAL, low confidence FAIL -> PARTIAL, high confidence FAIL stays FAIL
- **File**: `nikita/engine/chapters/judgment.py`
- **Test**: `tests/engine/chapters/test_judgment_multi_phase.py` (extend)
- **AC**: AC-5.5
- **Est**: 0.5h
- **Depends on**: T-D1

**Phase D tests**: ~10 tests (three-way judgment, confidence override, full history, error handling)

---

## Phase E: Boss State Machine + Message Handler Integration

### T-E1: Add `process_partial()` to `BossStateMachine`
- [ ] New method following `process_pass`/`process_fail` pattern
- [ ] PARTIAL: does NOT increment boss_attempts
- [ ] PARTIAL: does NOT advance chapter
- [ ] Sets status back to "active"
- [ ] Records cool-down timestamp for 24h delay
- [ ] Returns: `{"attempts": int, "game_status": "active", "cool_down_until": datetime}`
- [ ] Write tests: no attempts increment, no chapter advance, cool-down set, status "active"
- **File**: `nikita/engine/chapters/boss.py`
- **Test**: `tests/engine/chapters/test_boss_partial.py`
- **AC**: AC-3.2, AC-3.3, AC-3.4, AC-3.5
- **Est**: 0.5h
- **Depends on**: T-A3

### T-E2: Update `process_outcome()` for Three-Way Dispatch
- [ ] Modify `process_outcome` to accept `outcome: str` (PASS/FAIL/PARTIAL) instead of `passed: bool`
- [ ] When flag OFF, preserve `passed: bool` signature via overload or default
- [ ] Dispatch to `process_pass`, `process_fail`, or `process_partial`
- [ ] Write tests: three-way dispatch works, backward compat with bool param when flag OFF
- **File**: `nikita/engine/chapters/boss.py`
- **Test**: `tests/engine/chapters/test_boss_partial.py` (extend)
- **AC**: AC-3.1, AC-8.2, AC-8.3
- **Est**: 0.5h
- **Depends on**: T-E1

### T-E3: Rewrite `_handle_boss_response` for Multi-Phase Flow
- [ ] Branch at top: `is_multi_phase_boss_enabled()` -> `_handle_multi_phase_boss()` vs existing code
- [ ] Load `BossPhaseState` from `user.conflict_details` via `BossPhaseManager.load_phase()`
- [ ] If phase=OPENING: advance to RESOLUTION, persist state, send RESOLUTION prompt (no judgment)
- [ ] If phase=RESOLUTION: run `judge_multi_phase_outcome()`, process outcome (3-way), clear phase
- [ ] Handle timeout (24h auto-FAIL before advancing)
- [ ] When flag OFF: preserve existing single-turn flow exactly
- [ ] Write tests: full OPENING->RESOLUTION->PASS flow, timeout auto-FAIL, flag OFF preserves single-turn, interrupted boss preserves state
- **File**: `nikita/platforms/telegram/message_handler.py` (~line 794-886)
- **Test**: `tests/platforms/telegram/test_message_handler_boss.py`
- **AC**: AC-1.1 through AC-1.6, AC-8.2, AC-8.3
- **Est**: 2h
- **Depends on**: T-B1, T-B2, T-B3, T-D1, T-E2

### T-E4: Boss Initiation for Multi-Phase
- [ ] When boss triggers and flag ON: `initiate_boss()` creates `BossPhaseState(phase=OPENING)`
- [ ] Persist to conflict_details, send OPENING prompt
- [ ] Update `initiate_boss()` to accept optional `conflict_details` parameter and return updated details
- [ ] Write tests: initiation creates OPENING state, persisted in conflict_details, OPENING prompt sent
- **File**: `nikita/engine/chapters/boss.py`, `nikita/platforms/telegram/message_handler.py`
- **Test**: `tests/platforms/telegram/test_message_handler_boss.py` (extend)
- **AC**: AC-1.1, AC-2.2
- **Est**: 0.5h
- **Depends on**: T-B1, T-B2

### T-E5: PARTIAL Response Messaging
- [ ] Add `_send_boss_partial_message(chat_id, chapter)` following `_send_boss_pass_message`/`_send_boss_fail_message` pattern
- [ ] Empathetic truce tone, hint at cool-down period
- [ ] Write tests: PARTIAL message sent with correct tone indicators
- **File**: `nikita/platforms/telegram/message_handler.py`
- **Test**: `tests/platforms/telegram/test_message_handler_boss.py` (extend)
- **AC**: AC-3.5
- **Est**: 0.25h
- **Depends on**: T-E3

**Phase E tests**: ~18 tests (full multi-phase flows for each outcome, timeout, interrupted boss, flag OFF single-turn, process_partial, cool-down, boss initiation, PARTIAL messaging)

---

## Phase F: Vulnerability Exchange Detection + Warmth Bonus

### T-F1: Vulnerability Exchange Detection in Analyzer Prompt
- [ ] Append vulnerability exchange section to `ANALYSIS_SYSTEM_PROMPT` (~line 80)
- [ ] Detection criteria: Nikita shares something vulnerable + player responds with empathy/matching depth
- [ ] Add behavior tag `"vulnerability_exchange"` to `behaviors_identified`
- [ ] Only tag genuine mutual vulnerability — one-sided sharing is NOT an exchange
- [ ] Write tests: prompt contains vulnerability section, mock LLM returns tag, one-sided sharing not tagged
- **File**: `nikita/engine/scoring/analyzer.py`
- **Test**: `tests/engine/scoring/test_analyzer_vulnerability.py`
- **AC**: AC-6.1, AC-6.2, AC-6.4
- **Est**: 0.5h

### T-F2: Warmth Bonus in `ScoreCalculator`
- [ ] Add `apply_warmth_bonus(deltas: MetricDeltas, v_exchange_count: int) -> MetricDeltas`
- [ ] Bonus logic: count=0 -> +2 trust, count=1 -> +1 trust, count>=2 -> +0
- [ ] Trust capped at 10 (no overflow)
- [ ] Called in `calculate()` after engagement multiplier, only when `"vulnerability_exchange"` in behaviors
- [ ] Write tests: +2 first exchange, +1 second, +0 third, trust capped at 10, no bonus when no exchange
- **File**: `nikita/engine/scoring/calculator.py`
- **Test**: `tests/engine/scoring/test_calculator_warmth.py`
- **AC**: AC-7.1, AC-7.2, AC-7.3, AC-7.4
- **Est**: 0.5h
- **Depends on**: T-F1

### T-F3: Conversation-Scoped V-Exchange Counter
- [ ] Add `v_exchange_count: int = 0` parameter to `score_interaction()`
- [ ] When `"vulnerability_exchange"` detected in analysis, pass count to `calculator.apply_warmth_bonus()`
- [ ] Caller (orchestrator/message handler) tracks count per conversation, increments after each detection
- [ ] Write tests: counter increments per detection, resets per conversation, bonus applied after multiplier, flag OFF no bonus
- **File**: `nikita/engine/scoring/service.py`
- **Test**: `tests/engine/scoring/test_service_warmth.py`
- **AC**: AC-7.5
- **Est**: 0.5h
- **Depends on**: T-F2

**Phase F tests**: ~12 tests (vulnerability tag detection, warmth +2/+1/+0, trust cap, counter reset, no bonus without exchange, bonus after multiplier, flag OFF)

---

## Phase G: Integration + Backward Compatibility

### T-G1: Update `chapters/__init__.py` Exports
- [ ] Export: `BossPhase`, `BossPhaseState`, `BossPhaseManager`, `is_multi_phase_boss_enabled`, `get_boss_phase_prompt`
- [ ] Write test: all exports importable
- **File**: `nikita/engine/chapters/__init__.py`
- **Test**: `tests/engine/chapters/test_exports_058.py`
- **AC**: AC-8.1
- **Est**: 0.15h
- **Depends on**: T-B1, T-C2

### T-G2: Backward Compatibility Test Suite
- [ ] Run ALL existing boss tests with flag OFF — 0 failures
- [ ] Verify: single-turn PASS/FAIL flow unchanged
- [ ] Verify: BossResult still has PASS/FAIL
- [ ] Verify: `process_outcome` with `passed=True/False` still works
- [ ] Verify: no PARTIAL behavior when flag OFF
- [ ] Document any test modifications needed
- **File**: `tests/engine/chapters/test_boss_backward_compat.py` (CREATE)
- **AC**: AC-8.2, AC-8.4
- **Est**: 1h
- **Depends on**: T-E2

### T-G3: Multi-Phase Integration Test Suite
- [ ] Full 2-phase flow: OPENING -> RESOLUTION -> PASS
- [ ] Full 2-phase flow: OPENING -> RESOLUTION -> PARTIAL
- [ ] Full 2-phase flow: OPENING -> RESOLUTION -> FAIL
- [ ] Timeout at 24h auto-FAIL
- [ ] Interrupted boss (non-boss message between phases, state preserved)
- [ ] Persistence round-trip (server restart simulation)
- [ ] Vulnerability exchange + warmth bonus during boss encounter
- [ ] All tests with flag ON
- **File**: `tests/engine/chapters/test_boss_multi_phase.py` (CREATE)
- **AC**: AC-8.5
- **Est**: 1.5h
- **Depends on**: All T-E tasks, T-F3

### T-G4: Adversarial Test Suite
- [ ] Rapid phase transitions (back-to-back messages)
- [ ] Concurrent boss + conflict temperature interaction
- [ ] Boss during game_over/won status (should not start)
- [ ] Corrupt conflict_details JSONB (graceful degradation)
- [ ] Phase state with missing fields (partial data)
- [ ] boss_phase present but flag OFF (should ignore phase data, single-turn)
- [ ] Double boss initiation (should not create duplicate phases)
- **File**: `tests/engine/chapters/test_boss_adversarial.py` (CREATE)
- **AC**: AC-8.2, AC-8.3
- **Est**: 1h
- **Depends on**: T-G2, T-G3

---

## Summary

| Phase | Tasks | Est Hours | Key Output |
|-------|-------|-----------|------------|
| A: Foundation | T-A1..A5 (5 tasks) | 1h | Feature flag, models, PARTIAL enum, DB migration |
| B: Phase Manager | T-B1..B3 (3 tasks) | 2.25h | State machine, persistence, timeout |
| C: Prompts | T-C1..C2 (2 tasks) | 1.8h | 10 phase-prompt variants |
| D: Judgment | T-D1..D2 (2 tasks) | 1.5h | Multi-turn judgment, confidence threshold |
| E: Integration | T-E1..E5 (5 tasks) | 3.75h | PARTIAL processing, message handler, boss init |
| F: Warmth | T-F1..F3 (3 tasks) | 1.5h | Vulnerability detection, warmth bonus, counter |
| G: Compat + Tests | T-G1..G4 (4 tasks) | 3.65h | Exports, backward compat, integration, adversarial |
| **Total** | **24** | **~15.5h** | **~75 tests across phases** |

## Task Status Tracker

| ID | Status | Description |
|----|--------|-------------|
| T-A1 | [ ] | Feature flag `multi_phase_boss_enabled` |
| T-A2 | [ ] | BossPhase enum + BossPhaseState model |
| T-A3 | [ ] | BossResult PARTIAL enum extension |
| T-A4 | [ ] | ConflictDetails boss_phase field |
| T-A5 | [ ] | DB migration vulnerability_exchanges |
| T-B1 | [ ] | BossPhaseManager class |
| T-B2 | [ ] | Persistence helpers (read/write boss_phase) |
| T-B3 | [ ] | Boss timeout logic (24h auto-FAIL) |
| T-C1 | [ ] | Phase-aware prompt structure (10 prompts) |
| T-C2 | [ ] | `get_boss_phase_prompt()` function |
| T-D1 | [ ] | `judge_multi_phase_outcome()` method |
| T-D2 | [ ] | Confidence-based PARTIAL threshold |
| T-E1 | [ ] | `process_partial()` in BossStateMachine |
| T-E2 | [ ] | `process_outcome()` three-way dispatch |
| T-E3 | [ ] | `_handle_boss_response` multi-phase rewrite |
| T-E4 | [ ] | Boss initiation for multi-phase |
| T-E5 | [ ] | PARTIAL response messaging |
| T-F1 | [ ] | Vulnerability exchange detection in analyzer |
| T-F2 | [ ] | Warmth bonus in ScoreCalculator |
| T-F3 | [ ] | Conversation-scoped V-exchange counter |
| T-G1 | [ ] | Update chapters/__init__.py exports |
| T-G2 | [ ] | Backward compatibility test suite |
| T-G3 | [ ] | Multi-phase integration test suite |
| T-G4 | [ ] | Adversarial test suite |
