# Spec 113 — Voice Post-Score Evaluation

## Status: In Progress

## Problem

`nikita/api/routes/voice.py` calls `VoiceCallScorer.score_call()` + `apply_score()` then stops.
Three post-score hooks present in the text path are entirely absent from the voice path:

1. **DA-002**: No boss threshold check → boss encounter never triggered by voice calls
2. **GE-005**: No `consecutive_crises` increment when voice score delta pushes score below crisis zone
3. **DA-001**: No integration test verifying pipeline context quality (the gap that let MP-002 go undetected)

The vice pipeline absence (GE-006) is addressed separately in Spec 114.

### Comparison: text path vs voice path

| Hook | Text path | Voice path |
|------|-----------|------------|
| Boss threshold | `_score_and_check_boss` → `set_boss_fight_status` | **MISSING** |
| `consecutive_crises` | `scoring_service.score_interaction` → `details.consecutive_crises += 1` | **MISSING** |
| Pipeline dispatch | via `pg_cron → /process-conversations` | `asyncio.create_task(run_pipeline())` ✅ |

## Functional Requirements

### FR-001 — Boss threshold check after voice scoring
After `scorer.apply_score(user_id, call_score)` completes:
- Reload user from DB to get updated `relationship_score`, `chapter`, `game_status`
- Call `BossStateMachine.should_trigger_boss(score, chapter, game_status, cool_down_until)`
- If True: call `user_repository.set_boss_fight_status(user_id)` and log `[VOICE-BOSS]`
- Non-fatal: failure must not abort webhook response

### FR-002 — Consecutive crises increment after voice scoring
- Use `score_delta` (sum of call_score.deltas.intimacy + .passion + .trust + .secureness) already computed at voice.py:702-708
- Load `conflict_details` for user via `load_conflict_details(user_id, session)` from `nikita.conflicts.persistence`
- If `score_delta < 0` AND `details.zone == "critical"`:
  - Increment `consecutive_crises` on `conflict_details`
  - Persist updated conflict_details via `save_conflict_details(user_id, details.to_jsonb(), session)`
- If `score_delta > 0` AND `consecutive_crises > 0`:
  - Reset `consecutive_crises = 0` (recovery path)
  - Persist updated conflict_details
- Non-fatal: failure must not abort webhook response

**Note**: `CallScore.deltas` is a `MetricDeltas` object. There is no `total_delta` field; use the already-computed `score_delta` variable from voice.py:702-708. Crisis detection uses `details.zone == "critical"` (temperature-based, consistent with text path at scoring/service.py:316) — not a raw relationship_score threshold.

### FR-003 — Pipeline context quality integration test (DA-001)
- New test: `tests/integration/test_pipeline_context_quality.py`
- Verifies that `_enrich_context` in `PipelineOrchestrator` properly populates `ctx.memory_context`, `ctx.recent_facts`, `ctx.conversation_summary` for a real conversation
- Guards against silent `None`-injection bugs like MP-002

## Acceptance Criteria

| ID | Criterion | Test |
|----|-----------|------|
| AC-001 | Voice call scoring triggers boss if threshold reached | `test_voice_post_score_triggers_boss` |
| AC-002 | Boss not triggered if score below threshold | `test_voice_post_score_no_boss_below_threshold` |
| AC-003 | Boss not triggered if game_status != "active" | `test_voice_post_score_boss_exempt_non_active` |
| AC-004 | Consecutive crises incremented on negative delta + zone == "critical" | `test_voice_post_score_crises_increment` |
| AC-005 | Consecutive crises reset on positive delta | `test_voice_post_score_crises_reset` |
| AC-006a | Boss hook failure is non-fatal (webhook returns 200) | `test_voice_post_score_boss_failure_non_fatal` |
| AC-006b | Crisis hook failure is non-fatal (webhook returns 200) | `test_voice_post_score_crises_failure_non_fatal` |
| AC-007 | Pipeline context quality test: enrich_context populates context fields | `test_pipeline_context_quality` |

## Implementation Scope

### Files to modify
- `nikita/api/routes/voice.py:699-718` — add post-score hooks after `apply_score()`

### Files to create
- `tests/api/routes/test_voice_post_score.py` — AC-001 through AC-006
- `tests/integration/test_pipeline_context_quality.py` — AC-007

### Out of scope
- Vice pipeline (Spec 114)
- Text path changes (already correct via `_score_and_check_boss`)

## Design Decisions

1. **Non-fatal**: Both hooks wrapped in `try/except Exception` — voice webhook must return 200
2. **User reload**: `apply_score()` commits in its own independent session (scoring.py:154-206). Must use `UserRepository(session).get(user_id)` — `session.refresh(user)` returns stale data
3. **Attribute name**: `User.cool_down_until` (not `boss_cooldown_until`) — use direct attribute access
4. **Crisis zone**: Use `details.zone == "critical"` (temperature-based, consistent with text path at scoring/service.py:316). `ConflictDetails` is loaded from `user.conflict_details` JSONB. No raw relationship_score threshold — these measure different things.
5. **Boss state machine import**: `BossStateMachine` is NOT pre-imported in voice.py. Use lazy import inside the try block: `from nikita.engine.chapters.boss import BossStateMachine`.
6. **Consecutive crises persistence**: Use `conflicts/persistence.py` directly (`load_conflict_details`/`save_conflict_details`) — avoids duplicating scoring service logic.
7. **user_repo reuse**: `UserRepository(session)` is already instantiated at voice.py:614 as `user_repo`. Reuse this instance for `user_repo.get(user_id)` and `user_repo.set_boss_fight_status(user_id)` — do not create a second instance.
