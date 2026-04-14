# Auth Validation Report — Spec 213

**Spec**: `specs/213-onboarding-backend-foundation/spec.md`
**Status**: FAIL (iteration 1)
**Timestamp**: 2026-04-14T15:55:00Z
**Validator**: sdd-auth-validator

## Summary
| Severity | Count |
|---|---|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 3 |
| LOW | 4 |

## High Findings

| ID | Issue | Fix |
|---|---|---|
| AU-H1 | `_bootstrap_pipeline` doesn't write `pipeline_state` JSONB key — `/pipeline-ready` endpoint will always return `pending`. Same root cause as A-C3. | Add FR-5.1: `_bootstrap_pipeline` writes `pipeline_state` to `users.onboarding_profile` on entry (`pending`), success (`ready`), timeout/partial (`degraded`), exception (`failed`) |

## Medium Findings

| ID | Issue | Fix |
|---|---|---|
| AU-M1 | Pre-existing PII violations at `nikita/api/routes/onboarding.py:154` and `:239` — `logger.error(f"...: {e}")` may echo PII | Replace with `logger.exception("...", extra={"user_id": str(user_id)})`. Spec FR-7 covers these files explicitly. |
| AU-M2 | `onboarding_completed_at` column existence in `users` table not verified | Verify via Supabase MCP `information_schema.columns`. If missing, FR-9 must use `onboarding_status` field instead OR add migration |
| AU-M3 | Re-onboarding partial-update mechanism unclear — existing idempotency guard at `:752-769` returns early on `onboarding_status == "completed"` | FR-9 must specify: separate `PATCH /onboarding/profile` endpoint OR conditional bypass logic in `save_portal_profile` |

## Low Findings

| ID | Issue | Fix |
|---|---|---|
| AU-L1 | AC-2.4 `/pipeline-ready` 403 body shape unstated | Add to AC-2.4: body = `{"detail": "Not authorized"}` matching existing onboarding pattern at `:140` |
| AU-L2 | `user_profiles` UPDATE RLS policy missing `WITH CHECK (id = auth.uid())` | Add `WITH CHECK` clause via Supabase MCP — belt-and-suspenders |
| AU-L3 | FR-10 voice webhook auth: confirm Spec 212 HMAC pattern unchanged when payload enriched | Add explicit note in FR-10 |
| AU-L4 | FR-9 `onboarding_completed_at`: column vs JSONB key not specified | Clarify (likely top-level column on `users`, set by `update_onboarding_status`) |

## Verified
- Supabase RLS on `user_profiles`: 5 policies exist (SELECT own/admin, INSERT/UPDATE/DELETE own). New columns auto-covered.
- Cross-user 403 pattern matches existing impl at `onboarding.py:134-140`.
- JWT algorithm pinned `HS256`, audience `authenticated`. No algorithm-confusion risk.
- Current happy-path logs (FR-7 compliant); violation is exception-handler only.
- `_bootstrap_pipeline` confirmed missing `pipeline_state` write (verified by reading `handoff.py:551-625`).

## Verdict
**FAIL** — 1 HIGH (AU-H1) + spec needs 7 additional issues addressed for absolute-zero compliance per user directive.
