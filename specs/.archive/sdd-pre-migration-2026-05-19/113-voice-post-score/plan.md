# Plan — Spec 113: Voice Post-Score Evaluation

## Story 1: Boss trigger after voice scoring (DA-002)

**Files**: `nikita/api/routes/voice.py`, `tests/api/routes/test_voice_post_score.py`

### T1 — RED tests (boss hook)
Write failing tests in `tests/api/routes/test_voice_post_score.py`:
- `test_voice_post_score_triggers_boss` — after scoring with high score, `set_boss_fight_status` called
- `test_voice_post_score_no_boss_below_threshold` — low score, no boss triggered
- `test_voice_post_score_boss_exempt_non_active` — game_status="boss_fight", no re-trigger
- `test_voice_post_score_boss_failure_non_fatal` — `set_boss_fight_status` raises, webhook still 200

### T2 — GREEN implementation (boss hook)
In `voice.py` after `await scorer.apply_score(user_id, call_score)`:
```python
# Spec 113 FR-001: Boss threshold check after voice scoring (non-fatal).
# IMPORTANT: apply_score() commits in its own independent session (scoring.py:154-206).
# Must re-fetch user via repo.get() to get updated score — session.refresh() returns stale data.
# NOTE: user_repo is already instantiated at voice.py:614 — reuse it (DD-7).
try:
    from nikita.engine.chapters.boss import BossStateMachine
    fresh_user = await user_repo.get(user_id)
    if fresh_user:
        boss_sm = BossStateMachine()
        if boss_sm.should_trigger_boss(
            relationship_score=fresh_user.relationship_score,
            chapter=fresh_user.chapter,
            game_status=fresh_user.game_status,
            cool_down_until=fresh_user.cool_down_until,  # NOT boss_cooldown_until
        ):
            await user_repo.set_boss_fight_status(user_id)
            logger.info("[VOICE-BOSS] Boss triggered: user=%s chapter=%d", user_id, fresh_user.chapter)
except Exception as boss_err:
    logger.warning("[VOICE-BOSS] Boss check failed (non-fatal): %s", boss_err)
```

### T3 — Run Story 1 tests green

---

## Story 2: Consecutive crises after voice scoring (GE-005)

**Files**: `nikita/api/routes/voice.py`, `tests/api/routes/test_voice_post_score.py`

### T4 — RED tests (crises hook)
Append to `test_voice_post_score.py`:
- `test_voice_post_score_crises_increment` — negative delta + score ≤ 40 → `consecutive_crises` +1
- `test_voice_post_score_crises_reset` — positive delta + existing crises → reset to 0
- `test_voice_post_score_crises_failure_non_fatal` — crises update fails, webhook returns 200

### T5 — GREEN implementation (crises hook)
In `voice.py` after boss hook:
```python
# Spec 113 FR-002: Consecutive crises after voice scoring (non-fatal).
# Reuses conflicts/persistence.py directly (DRY — avoids duplicating scoring service logic).
# Crisis detection uses details.zone == "critical" (temperature-based), consistent with
# text path at scoring/service.py:316. NOT a raw relationship_score threshold.
try:
    from nikita.conflicts.persistence import load_conflict_details, save_conflict_details
    from nikita.conflicts.models import ConflictDetails

    raw_details = await load_conflict_details(user_id, session)
    details = ConflictDetails.from_jsonb(raw_details) if raw_details else ConflictDetails()

    if score_delta < 0 and details.zone == "critical":
        details.consecutive_crises += 1
        logger.info("[VOICE-CRISIS] crisis #%d user=%s", details.consecutive_crises, user_id)
    elif score_delta > 0 and details.consecutive_crises > 0:
        details.consecutive_crises = 0
        logger.info("[VOICE-CRISIS] crises reset user=%s", user_id)

    await save_conflict_details(user_id, details.to_jsonb(), session)
except Exception as crisis_err:
    logger.warning("[VOICE-CRISIS] Crisis update failed (non-fatal): %s", crisis_err)
```

### T6 — Run Story 2 tests green

---

## Story 3: Pipeline context quality test (DA-001)

**Files**: `tests/integration/test_pipeline_context_quality.py`

### T7 — Write integration test
New test verifying `_enrich_context` populates `ctx.memory_context`, `ctx.recent_facts`, `ctx.conversation_summary`.
Must have `pytest.mark.integration` + `skipif(not _SUPABASE_REACHABLE)` guards.

### T8 — Run Story 3 tests green

---

## Commit Sequence

1. `test(voice): Spec 113 — post-score boss/crisis tests (RED)`
2. `feat(voice): Spec 113 — post-score boss trigger + consecutive crises (GREEN)`
3. `test(pipeline): Spec 113 DA-001 — pipeline context quality integration test`
