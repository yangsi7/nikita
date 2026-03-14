# Tasks — Spec 113: Voice Post-Score Evaluation

## Story 1: Boss trigger after voice scoring

- [ ] T1: Write failing tests for boss hook in `tests/api/routes/test_voice_post_score.py`
  - AC-001: triggers_boss when score >= threshold
  - AC-002: no_boss_below_threshold
  - AC-003: boss_exempt_non_active (game_status != "active")
  - AC-006a: boss_failure_non_fatal (boss hook raises → webhook still 200)
- [ ] T2: Implement boss hook in `voice.py` after `apply_score()`
  - `session.refresh(user)` → `BossStateMachine.should_trigger_boss()` → `set_boss_fight_status()`
  - Wrapped in `try/except`, non-fatal
- [ ] T3: Run Story 1 tests — all pass

## Story 2: Consecutive crises after voice scoring

- [ ] T4: Write failing tests for crises hook (append to `test_voice_post_score.py`)
  - AC-004: crises_increment on negative delta + score <= 40
  - AC-005: crises_reset on positive delta
  - AC-006b: crises_failure_non_fatal (save_conflict_details raises → webhook still 200)
- [ ] T5: Implement `_increment_voice_consecutive_crises` + `_reset_voice_consecutive_crises`
  - Load conflict_details for user, update consecutive_crises, persist
  - Wrapped in `try/except`, non-fatal
- [ ] T6: Run Story 2 tests — all pass

## Story 3: Pipeline context quality integration test

- [ ] T7: Create `tests/integration/test_pipeline_context_quality.py`
  - `pytest.mark.integration` + `skipif(not _SUPABASE_REACHABLE)` guards
  - Verify `_enrich_context` populates `ctx.memory_context`, `ctx.recent_facts`, `ctx.conversation_summary`
- [ ] T8: Run Story 3 tests — pass (or skip if Supabase unreachable)

## Commit Sequence

1. `test(voice): Spec 113 — post-score boss/crisis tests (RED)`
2. `feat(voice): Spec 113 — post-score boss trigger + consecutive crises (GREEN)`
3. `test(pipeline): Spec 113 DA-001 — pipeline context quality integration test`
