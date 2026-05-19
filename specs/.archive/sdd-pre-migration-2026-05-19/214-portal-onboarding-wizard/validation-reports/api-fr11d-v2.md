## API Validation Report — FR-11d Amendment Iter-1

**Spec:** `specs/214-portal-onboarding-wizard/spec.md` (FR-11d, Wire-Format Extension, AC-11d.1-10)
**Branch / Commit:** `spec/214-fr11d-slot-filling-amendment` @ `72e06d6` (re-validation post-iter-1)
**Status:** **PASS** (0 CRITICAL, 0 HIGH; 2 MEDIUM, 2 LOW)
**Timestamp:** 2026-04-23 (re-validation by sdd-api-validator on sonnet)

### Resolution of Prior FAIL Findings (v1 → iter-1)

**C1 — RESOLVED.** The "Wire-Format Extension" section in iter-1 explicitly adds `link_code: str | None = None` and `link_expires_at: datetime | None = None` to `ConverseResponse` as declared fields (not extra kwargs). The `extra="forbid"` invariant is preserved. The existing `conversation_complete: bool` field name is retained (no rename to `complete`). Confirmed against `nikita/agents/onboarding/converse_contracts.py:64,74`.

**H1 — RESOLVED.** AC-11d.3 now carries a second grep gate: `rg "_compute_progress\(extracted_fields" nikita/api/routes/portal_onboarding.py` MUST return empty. This explicitly mandates deletion of the per-turn snapshot helper.

**H2 — RESOLVED.** AC-11d.8 added with `link_code`, `link_expires_at`, and `link_code_expired: bool = False`. The expired-code re-mint flow is documented with named tests (`test_get_conversation_returns_link_after_completion`, `test_get_conversation_signals_link_expired_after_ttl`).

### New Findings Introduced by Iter-1 Fixes

| # | Severity | Issue | Recommendation |
|---|---|---|---|
| M1 | MEDIUM | GET response schema not named; `extra="forbid"` risk on GET path. Spec says GET /conversation is "similarly extended additively" but never names the GET response Pydantic model or confirms its `extra=` configuration. The model is `ConversationProfileResponse` at `portal_onboarding.py:681` and currently inherits Pydantic v2 default (`extra='ignore'`) — without explicit `extra='forbid'`, the project posture against spoofed fields is inconsistent across the two endpoints. | Name the model in spec language. Add a hard requirement that `ConversationProfileResponse` gains `model_config = ConfigDict(extra="forbid")` AND the three new fields are declared in the model schema. Add a grep gate. |
| M2 | MEDIUM | Re-mint INSERT conflict semantics not specified. The re-mint path (FE re-runs /converse after link code expiry) calls `TelegramLinkRepository.create_code` fresh. If `telegram_link_codes` has a `UNIQUE(user_id)` constraint, the second INSERT will fail with a unique-key violation. The spec dismisses this with "No spec change required to the existing `OnboardingProfileWriter` ON CONFLICT semantics" — but `OnboardingProfileWriter` is not involved in code minting. The `TelegramLinkRepository.create_code` re-mint conflict strategy is unspecified. | Specify whether `telegram_link_codes` has a UNIQUE constraint that blocks re-mint, and if so, describe the resolution (DELETE expired-then-INSERT, partial-index UPSERT, or `ON CONFLICT DO UPDATE`). If no UNIQUE constraint exists, say so explicitly so implementor doesn't add one. |
| L1 | LOW | AC-11d.7 test assertion missing format check. `link_code != None` passes even if the code is malformed. | Also assert `re.fullmatch(r"^[A-Z0-9]{6}$", link_code)` (per FR-11b AC-11b.3) to prevent silent downstream breakage in the Telegram bot regex gate. |
| L2 | LOW | "Idempotent" misnomer for re-mint path. The spec calls the re-mint path "idempotent" but it produces a fresh (different) code by design. | Replace "idempotent" with "deterministically re-completable" in the re-mint description. The wrong term could lead an implementor to use `ON CONFLICT DO NOTHING`, which would return a stale expired code. |

### Recommended Actions Before `/implement`

1. **M1 (blocking risk):** Name the GET response model, confirm `extra="forbid"`, add the three new fields to its declaration, and add a grep gate.
2. **M2 (blocking risk):** Specify `ON CONFLICT DO UPDATE` or DELETE-then-INSERT or "no UNIQUE constraint" semantics for `create_code` on the re-mint path.
3. **L1 (cheap):** Add regex assertion `^[A-Z0-9]{6}$` to AC-11d.7 test spec.
4. **L2 (doc clarity):** Replace "idempotent" with "deterministically re-completable" in re-mint description.

### Pass/Fail Determination

**PASS.** All three prior FAIL findings (C1/H1/H2) are resolved. Two new MEDIUM findings (M1/M2) are tightening recommendations addressed in iter-2 spec edits (commit pending). Two LOW findings (L1/L2) are doc clarity nits.
