## Data Layer Validation Report — FR-11d Amendment (Spec 214 v2)

**Spec:** `specs/214-portal-onboarding-wizard/spec.md` (FR-11d Conversation Persistence section, lines 654-753)
**Branch / Commit:** `spec/214-fr11d-slot-filling-amendment` @ `b4180e1`
**Status:** **PASS** (0 CRITICAL, 0 HIGH; 3 MEDIUM, 2 LOW — all advisory, none blocking)
**Timestamp:** 2026-04-22

### Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH     | 0 |
| MEDIUM   | 3 |
| LOW      | 2 |

FR-11d introduces NO new tables, NO new columns, NO migration. It re-uses the existing `users.onboarding_profile JSONB` field (defined `nikita/db/models/user.py:117`) and the existing `append_conversation_turn` write-path (`nikita/agents/onboarding/conversation_persistence.py`), both of which already enforce the union invariant the FR requires. RLS posture on `users` is unchanged. Read-path latency under the 100-turn cap is the only legitimate concern, and the spec already calls it out (option B as opt-in if reconstruction > 10 ms p95). Findings below are tightening advisories, not blockers.

### Findings

| # | Severity | Category | Issue | Location | Recommendation |
|---|----------|----------|-------|----------|----------------|
| 1 | MEDIUM | Performance / Read-path budget | Spec sets the option-B cutover threshold at "reconstruction cost > 10 ms p95" but does NOT specify how this is measured (synthetic 100-turn fixture vs. live p95 from prod logs vs. CI micro-bench). Without a falsifiable measurement contract, "10 ms" is a magic number per `.claude/rules/tuning-constants.md`. | spec.md L724 | Add an AC like AC-11d.7: "A pytest micro-bench `tests/agents/onboarding/test_reconstruction_perf.py::test_reconstruct_wizardslots_under_10ms` builds a synthetic 100-turn `onboarding_profile`, calls the reconstruction reducer, and asserts p95 < 10 ms over 100 iterations. If it fails, option (B) MUST ship in the same PR." Also: name `RECONSTRUCTION_BUDGET_MS = 10` as a `Final[int]` constant with a docstring rationale, not a bare literal. |
| 2 | MEDIUM | Elision invariant — last-write-wins direction | `append_conversation_turn` (lines 67-70) merges elided extracted fields with `if key not in elided_extracted: elided_extracted[key] = value` — i.e. **first-eviction-wins** within the elided cache. The code comment claims "Last-write-wins; the newer extraction already lives later in the conversation list", which is true for the cumulative reconstruction (later live turns override earlier elided values), but is the OPPOSITE of last-write-wins for the elided cache itself. If two evictions happen in sequence, the second eviction will NOT overwrite the first eviction's value for the same key — yet the spec's union invariant `extracted ∪ elided_extracted` requires the most-recent-elided value to be the one preserved. For 6 slots × 100-turn cap this is unlikely to bite (slots get refined, not re-extracted), but the code comment is misleading and could confuse a future maintainer into removing the guard. | `nikita/agents/onboarding/conversation_persistence.py:67-70` | Either (a) change the merge to `elided_extracted[key] = value` (true last-write-wins) so the comment matches behavior, OR (b) prove via test that within `WizardSlots` reconstruction order, live `conversation` always wins over `elided_extracted` (i.e. the cache is only consulted for keys absent from live turns) and update the comment to "first-eviction-wins; safe because live turns override on read". Add `tests/agents/onboarding/test_conversation_persistence.py::test_elision_preserves_last_extraction_for_repeated_slot` exercising a 102-turn fixture where slot X is set on turn 1 (will be elided), set again on turn 50 (also elided eventually), and read after the 102nd turn. |
| 3 | MEDIUM | Acceptance criteria gap — elision invariant not exercised | FR-11d states the elision invariant MUST hold ("dropped turns' `extracted` fields merge into `elided_extracted` so cumulative state stays monotonic across the elision boundary", L726), but no AC tests this. AC-11d.1 covers a 3-turn fixture; AC-11d.2 covers ≥3-turn monotonicity within the live cap. Neither crosses the 100-turn boundary. Walk V precedent: untested invariants regress silently. | spec.md L726, ACs L734-739 | Add **AC-11d.7 — Elision boundary monotonicity**: a fixture of `CONVERSATION_TURN_CAP + 5` turns (use a smaller `CONVERSATION_TURN_CAP=5` test override) where slots 1-3 are extracted in the FIRST 3 turns, then 8 no-op turns. Reconstruct `WizardSlots` and assert all 3 slots remain filled despite turns 1-3 being evicted. This is the test that proves the union invariant holds across elision. |
| 4 | LOW | Index strategy — JSONB GIN | No GIN index exists on `users.onboarding_profile` (verified by grepping `supabase/migrations/`). Reads use the `users` PK (`SELECT ... WHERE id = $user_id FOR UPDATE`), so JSONB-path queries are NOT in the hot path — the entire JSONB blob is loaded by PK lookup and reduced in Python. NO index is needed for the FR-11d read pattern. Flagging only so the reviewer can confirm there is no plan to add a path-query that would suddenly need GIN. | n/a | None — confirm no caller queries `onboarding_profile->>'something'` in a WHERE clause. If a future feature does, then add `CREATE INDEX idx_users_onboarding_profile_gin ON users USING GIN (onboarding_profile jsonb_path_ops);` in a fresh migration. |
| 5 | LOW | RLS / access control | `users` table RLS posture is unchanged by FR-11d (no new tables, no new columns, no policy changes). Existing user-isolation policies on `users` continue to apply. The /converse endpoint authenticates the caller and passes `user_id` server-side; no client-controlled JSONB writes. No action needed. | n/a | None. |

### Validation Against the 7 Specific Questions

1. **JSONB schema cumulative reconstruction lossy?** **No, with one caveat (Finding #2).** The reducer over `conversation[*].extracted ∪ elided_extracted` is lossless IFF live `conversation` is reduced AFTER `elided_extracted` (so live overrides). The spec implies this ordering but does not state it; recommend documenting in the FR body. Within the live cap (100 turns), `model_copy(update={...})` ordering preserves "last-write-wins" by list-iteration order. Across the elision boundary, see Finding #2.

2. **Schema migration for option (B) `profile["slots"]`?** **No migration needed.** Option (B) writes a top-level key into the existing `onboarding_profile` JSONB blob. The `MutableDict.as_mutable` pattern + `SELECT ... FOR UPDATE` already supports this. Spec correctly notes (A) is default. Validated.

3. **RLS / access control on `users` preserved?** **Yes.** No new tables. No policy changes. Existing posture intact.

4. **Read-path latency: 100-turn JSONB read?** Spec calls out the 10 ms p95 budget but lacks a measurement contract — see Finding #1. The pure-Python reduction over 100 dicts of ~6 keys each is well under 10 ms on Cloud Run (rough estimate: 100 × dict-merge × Pydantic validation ≈ 1-3 ms typical), so option (A) should be fine in practice. Add the bench AC to make this falsifiable.

5. **Concurrent /converse for same user, `SELECT ... FOR UPDATE` preserved?** **Yes.** `append_conversation_turn:50` retains `with_for_update()`. Per-user serialization is intact. No change required.

6. **Elision drops merge `extracted` into `elided_extracted`?** **Yes, the code already does this** (`conversation_persistence.py:62-70`, written for AC-T2.8.3). FR-11d does NOT introduce this as a NEW requirement; it RE-AFFIRMS the existing invariant. The function-level docstring (L11-16) already encodes "the cumulative extracted profile is monotonically non-decreasing." See Finding #2 for the merge-direction nit and Finding #3 for the missing AC.

7. **Index on `onboarding_profile` JSONB path?** **No, and none needed for FR-11d.** Reads are PK lookups. See Finding #4.

### Entity Inventory

| Entity | New / Existing | Attributes touched | PK | RLS | Notes |
|--------|----------------|--------------------|----|----|-------|
| `users` | Existing | `onboarding_profile JSONB` (existing column, default `{}`) | `id UUID` | Yes (existing user-isolation policies) | FR-11d adds new JSONB top-level keys: `conversation` (existing, list of turn dicts), `elided_extracted` (existing, dict), optionally `slots` (option B, new key, no migration). All keys live inside the existing JSONB column. |

### Relationship Map

No new relationships. `users.id` is the lock target via `SELECT ... FOR UPDATE`.

### RLS Policy Checklist

- [x] `users` RLS — UNCHANGED, existing policies cover access. No new policy needed for FR-11d.
- [x] No new tables → no new RLS work.
- [x] Storage buckets — N/A (FR-11d is JSONB-only, no file storage).

### Index Requirements

| Table | Column(s) | Type | Query Pattern | Status |
|-------|-----------|------|---------------|--------|
| `users` | `id` (PK) | btree (existing) | `SELECT ... WHERE id = $1 FOR UPDATE` | Existing, sufficient |
| `users` | `onboarding_profile` | GIN | None (FR-11d does NOT path-query JSONB) | Not needed |

### Migration Strategy

**No new migration required for FR-11d.** All persistence reuses existing `users.onboarding_profile JSONB`. If option (B) is later activated, it adds a new top-level key inside the same JSONB blob — no DDL, no migration file.

### Recommendations

1. **MEDIUM #1 (read-path budget falsifiability)**: Add AC-11d.7 micro-bench + `RECONSTRUCTION_BUDGET_MS` named constant.
2. **MEDIUM #2 (elision merge direction)**: Either flip merge to true last-write-wins OR fix the misleading comment + add a regression test on repeated-slot eviction. Prefer the comment-fix path because the live-conversation override on read makes the current behavior safe — the bug is documentation drift, not logic.
3. **MEDIUM #3 (elision boundary AC)**: Add AC-11d.8 — fixture > `CONVERSATION_TURN_CAP` proving cumulative state survives eviction. This is the canonical test for the union invariant.
4. **LOW #4 (GIN)**: No action; document non-need in tech-spec for future-reader clarity.
5. **LOW #5 (RLS)**: No action; confirm in tech-spec that FR-11d inherits existing `users` policies.

### Verification Commands (post-amendment)

```bash
# 1. Confirm no new migrations introduced for FR-11d
git -C $REPO diff master...HEAD -- supabase/migrations/ | head
# Expected: empty diff

# 2. Confirm append_conversation_turn unchanged
git -C $REPO diff master...HEAD -- nikita/agents/onboarding/conversation_persistence.py | head
# Expected: empty diff

# 3. Grep for forbidden completion-gate literals (AC-11d.3 grep contract)
rg "conversation_complete\s*=\s*(True|False)" nikita/api/routes/portal_onboarding.py
# Expected: empty post-implementation

# 4. Confirm onboarding_profile column intact in model
rg "onboarding_profile.*JSONB" nikita/db/models/user.py
# Expected: line 117 match
```

### Pass/Fail Determination

**PASS.** No CRITICAL, no HIGH. Three MEDIUM findings are tightening recommendations (one perf-budget AC, one elision-comment cleanup + regression test, one cross-cap-boundary AC) — none of them block planning. RLS, schema, write-path locking, and write-path elision are all intact and correctly described in the amendment. The amendment correctly avoids inventing a new migration where one is not needed.
