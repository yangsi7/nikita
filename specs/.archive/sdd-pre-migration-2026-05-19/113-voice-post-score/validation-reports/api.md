## API Validation Report

**Spec:** specs/113-voice-post-score/spec.md
**Status:** FAIL
**Timestamp:** 2026-03-14T12:00:00Z

### Summary
- CRITICAL: 1
- HIGH: 3
- MEDIUM: 2
- LOW: 1

### Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| CRITICAL | Schema | Spec references `call_score.total_delta` (FR-001 line 34, FR-002 lines 34/38) but `CallScore` dataclass has NO `total_delta` attribute. Fields are: `session_id`, `deltas` (MetricDeltas), `explanation`, `duration_seconds`, `behaviors_identified`, `confidence`. | spec.md:34,38 + scoring.py:32-43 | Replace `call_score.total_delta` with the inline sum already computed at voice.py:703-708: `call_score.deltas.intimacy + call_score.deltas.passion + call_score.deltas.trust + call_score.deltas.secureness`. Or define a `total_delta` property on `CallScore`. |
| HIGH | Session | `apply_score()` creates its own session internally (scoring.py:154-155 `get_session_maker()`) and commits within it (scoring.py:206). The webhook handler's `session` (voice.py:612) holds a STALE `user` object after `apply_score()` returns. The spec says "Reload user from DB to get updated `relationship_score`" (DD-2) via `session.refresh(user)` but this refresh will read from the webhook's session, which may return cached/stale data depending on isolation level. | spec.md:75 + voice.py:612,700 + scoring.py:154-206 | After `apply_score()`, use `await session.refresh(user)` which will re-query the DB within the webhook session. SQLAlchemy async sessions default to `AUTOFLUSH` and will see committed data from other sessions on refresh. Document this explicitly in the spec. Alternatively, re-fetch via `user_repo.get(user_id)` which is safer. |
| HIGH | Imports | Spec says "Reuse `BossStateMachine` (already imported in voice.py via engine)" (DD-4, line 77) but `BossStateMachine` is NOT imported in voice.py. No import from `nikita.engine.chapters` exists in the file. | spec.md:77 + voice.py:1-28 | Correct DD-4: `BossStateMachine` must be explicitly imported. Add `from nikita.engine.chapters.boss import BossStateMachine` inside the try block (lazy import to avoid circular deps). |
| HIGH | Architecture | FR-002 describes a simplified inline `consecutive_crises` increment approach (load ConflictDetails, increment, persist) that bypasses the established pattern. The text path uses `ScoringService._update_temperature_and_gottman()` which handles crises via `TemperatureEngine` + `GottmanTracker` + zone-based logic (service.py:315-321). The spec's approach directly increments without temperature/Gottman updates, creating behavioral divergence between text and voice paths. | spec.md:34-39 vs scoring_orchestrator.py:103-144 | Either: (A) reuse the existing `load_conflict_details`/`save_conflict_details` from `nikita.conflicts.persistence` (the spec does not reference this module), or (B) explicitly document WHY voice uses a simplified path (no temperature engine, just crisis counter). Option A is strongly recommended to avoid two divergent conflict tracking paths. |
| MEDIUM | Error Scope | DD-5 says "No user_repo in voice webhook: User is loaded via `session.get(User, user_id)` inline" but at voice.py:614, the webhook ALREADY uses `UserRepository(session)` and `user_repo.get(user_id)`. The spec contradicts existing code. Same for `set_boss_fight_status` -- spec says to call it directly but the method lives on `UserRepository` (user_repository.py:461), which requires the existing `user_repo` instance. | spec.md:78 + voice.py:614-615 | Remove DD-5 or correct it: a `UserRepository` is already instantiated at voice.py:614. The implementor should reuse `user_repo` for both `session.refresh(user)` and `user_repo.set_boss_fight_status(user_id)`. |
| MEDIUM | Threshold | FR-002 uses fixed threshold `Decimal("40")` for crisis zone (DD-3, line 76) while the text path determines crisis zone from `details.zone == "critical"` (scoring/service.py:316), which is computed by `TemperatureEngine` based on temperature value, not relationship score. These are different metrics -- relationship score vs conflict temperature. The spec conflates them. | spec.md:34,76 vs service.py:316 | Clarify: crisis detection should use `ConflictDetails.zone == "critical"` (temperature-based), not `relationship_score <= 40` (composite score). These measure different things. If the intent is truly score-based, document why this diverges from the text path. |
| LOW | Naming | Spec line 62 says "add post-score hooks after `apply_score()`" and references lines 699-718, but the insertion point should be INSIDE the `if transcript_pairs:` block (voice.py:676) and AFTER the scoring log statement (voice.py:717), still within the `try` block (voice.py:652-721). The line range is correct but the description should clarify this is inside the existing try/except. | spec.md:62 | Clarify that hooks go at voice.py:718 (after the logger.info), still inside the `try:` block starting at line 652. The outer `except Exception` at line 719 already provides the non-fatal guarantee. |

### API Inventory

No new API endpoints are introduced by this spec. All changes are internal to the existing webhook handler.

| Method | Endpoint | Purpose | Auth | Request | Response |
|--------|----------|---------|------|---------|----------|
| POST | /api/v1/voice/webhook | Process ElevenLabs call events (existing) | HMAC signature | ElevenLabs webhook payload | `{"status": "processed", ...}` |

### Server Actions

N/A -- this is a Python/FastAPI backend, not Next.js.

### Request/Response Schemas

No response schema changes are needed. The webhook already returns:
```python
{
    "status": "processed",
    "transcript_stored": True,
    "conversation_id": str,
    "db_conversation_id": str,
    "post_processing": {
        "scheduled": bool,
        "pipeline": str,
        "note": str,
    },
}
```

The boss trigger and crisis increment are internal side effects -- they do not alter the webhook response (correct: ElevenLabs ignores response body beyond HTTP status).

### Error Code Inventory

No new error codes. Both hooks are explicitly non-fatal (wrapped in try/except, webhook returns 200 regardless).

### Detailed Analysis

#### Q1: Does the spec correctly identify the webhook handler and insertion point?

**PARTIALLY.** The spec correctly identifies voice.py as the target and the general area (lines 699-718). However, the insertion point description is imprecise. The hooks must go at line 718 (after the scoring log), inside the existing `try:` block (line 652), and inside the `if transcript_pairs:` guard (line 676). The spec's line range is correct but does not call out these nesting constraints.

#### Q2: Does `call_score.total_delta` exist on VoiceCallScore?

**NO -- CRITICAL.** `CallScore` (scoring.py:32-43) is a `@dataclass` with fields: `session_id`, `deltas` (MetricDeltas), `explanation`, `duration_seconds`, `behaviors_identified`, `confidence`. There is no `total_delta` property or attribute. The existing code at voice.py:703-708 computes the sum inline as `score_delta`. The spec must reference this existing `score_delta` local variable or compute its own sum from `call_score.deltas.*`.

#### Q3: Is `session` available in the voice webhook handler at the point of hooks?

**YES, with caveats.** The webhook handler opens `async with session_maker() as session:` at voice.py:612. The session is alive throughout the entire `async with` block (which extends to line 778). However, `apply_score()` creates and commits in its OWN separate session (scoring.py:154-206), so the webhook's `session` holds stale data for the `user` object. A `session.refresh(user)` is needed to reload from DB, which the spec correctly identifies in DD-2, but the spec does not note the cross-session staleness as the root cause.

#### Q4: Is `user` already loaded at line 699?

**YES.** `user` is loaded at voice.py:615 via `user_repo.get(user_id)` and is confirmed non-None by the guard at line 617-623. However, after `apply_score()` (line 700), the user's `relationship_score` is stale because `apply_score()` committed metric changes in a different session. The `session.refresh(user)` in DD-2 correctly addresses this.

#### Q5: Is the non-blocking asyncio pattern correct for these hooks?

**NOT APPLICABLE.** The spec describes the hooks as synchronous-ish (awaited inline, not fire-and-forget). This is correct -- both FR-001 and FR-002 should be awaited within the try/except block, not spawned as background tasks. They are fast operations (DB reads + conditional DB write), unlike the pipeline which takes 30-60s. The existing `asyncio.create_task()` pattern (voice.py:756) is only for the pipeline. The hooks should be `await`-ed inline. The spec is correct on this point.

#### Q6: Any response schema changes needed?

**NO.** Both hooks are internal side effects (boss status change, crisis counter update). The webhook response is consumed by ElevenLabs which only cares about HTTP 200. No response body changes needed.

### Recommendations

1. **CRITICAL (call_score.total_delta):** Replace all references to `call_score.total_delta` in spec FR-001/FR-002 with the local variable `score_delta` already computed at voice.py:703-708. The `score_delta` variable is in scope at the insertion point and contains the correct sum. Example:
   ```python
   # Use existing score_delta (computed at line 703-708)
   if score_delta < 0 and user.relationship_score <= Decimal("40"):
   ```
   Alternatively, add a `@property` to `CallScore`:
   ```python
   @property
   def total_delta(self) -> Decimal:
       return self.deltas.intimacy + self.deltas.passion + self.deltas.trust + self.deltas.secureness
   ```

2. **HIGH (stale session):** Add explicit note in spec that after `apply_score()`, the webhook's `user` object has stale metrics because `apply_score()` uses its own session. The refresh via `await session.refresh(user)` is the correct fix but should be documented as a cross-session refresh, not a same-session refresh.

3. **HIGH (BossStateMachine import):** Remove false claim in DD-4 that BossStateMachine is "already imported". Specify lazy import:
   ```python
   from nikita.engine.chapters.boss import BossStateMachine
   boss_sm = BossStateMachine()
   if boss_sm.should_trigger_boss(user.relationship_score, user.chapter, user.game_status, user.cool_down_until):
       await user_repo.set_boss_fight_status(user_id)
   ```

4. **HIGH (conflict details pattern):** Reuse `nikita.conflicts.persistence.load_conflict_details` and `save_conflict_details` instead of inline JSONB manipulation. This matches the text path pattern (scoring_orchestrator.py:106-144) and avoids introducing a second persistence approach. Update FR-002 to reference these functions.

5. **MEDIUM (DD-5 contradiction):** Delete DD-5 ("No user_repo in voice webhook") -- `UserRepository` is already instantiated at voice.py:614. The implementor should reuse the existing `user_repo`.

6. **MEDIUM (crisis zone semantics):** Align crisis detection with text path: use `ConflictDetails.zone == "critical"` (temperature-based) rather than `relationship_score <= 40` (composite score). These are fundamentally different metrics.
