## Auth Validation Report

**Spec:** `/Users/yangsim/Nanoleq/sideProjects/nikita/specs/111-consecutive-crises/spec.md`
**Status:** PASS
**Timestamp:** 2026-03-11T12:00:00Z

### Summary
- CRITICAL: 0
- HIGH: 0
- MEDIUM: 0
- LOW: 1

### Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| LOW | Protected Resources | `score_batch()` (FR-005) adds a `conflict_details` parameter. Future callers in the voice pipeline must pass the user's DB record, not a default. If a caller omits `conflict_details`, the counter silently starts at 0. This is not an auth gap but a data-integrity concern the spec already documents. | `spec.md:163` | Spec already notes this (FR-005 caller audit). No action needed now; track when voice pipeline unification spec is written. |

### Auth Flow Analysis

**Primary Method:** N/A -- no auth changes
**Session Type:** N/A -- no session changes
**Token Handling:** N/A -- no token changes

This spec modifies game engine internals only:
- `ConflictDetails` Pydantic model (adds 2 fields)
- `ScoringService._update_temperature_and_gottman()` (crisis increment/reset logic)
- `BreakupEngine.check_thresholds()` (reads counter instead of hardcoded 0)
- `ScoringService.score_batch()` (adds temperature update for voice path)

No new API endpoints, no new routes, no auth dependency changes, no new database tables or columns.

### Role & Permission Matrix

N/A -- No auth changes. Existing auth architecture is unaffected:
- Players access their own data via JWT (`get_current_user_id`)
- Admins access all users via `get_current_admin_user`
- Service role bypasses RLS for backend operations

### Protected Resources

N/A -- No new resources introduced. The `conflict_details` JSONB column already exists on the `users` table and is protected by existing RLS policies.

### Existing RLS Coverage (Verified)

The `users` table has RLS enabled (baseline_schema.sql:806) with these policies (lines 961-966):

| Policy | Operation | Rule |
|--------|-----------|------|
| `Users can read own data` | SELECT | `auth.uid() = id` |
| `Users can update own data` | UPDATE | `auth.uid() = id` |
| `users_own_data` | ALL | `id = auth.uid()` (both USING and WITH CHECK) |
| `Admin reads all users` | SELECT | `auth.uid() = id OR is_admin()` |
| `Admin updates users` | UPDATE | `is_admin()` |
| `Service role full access users` | ALL | `true` (service_role only) |

The `consecutive_crises` and `last_crisis_at` fields are embedded inside the existing `conflict_details` JSONB column (users table line 61). RLS operates at the row level, so all JSONB fields within a row inherit the same row-level protection. No additional policies are needed.

The `nikita_emotional_states` table also has `conflict_details` JSONB (line 382) with its own RLS policies (lines 870-873), all gated on `auth.uid() = user_id`.

### Security Checklist
- [N/A] Rate limiting on login - No auth endpoints affected
- [N/A] Account lockout policy - No auth endpoints affected
- [N/A] Session invalidation on logout - No session changes
- [N/A] CSRF protection - No new endpoints
- [N/A] Security headers (CSP, HSTS) - No new endpoints

### Recommendations

1. **LOW**: When the voice pipeline unification spec is written (future), ensure the auth validator checks that `conflict_details` is loaded from the authenticated user's DB record and not constructed from defaults. The `score_batch()` optional parameter (`conflict_details=None`) means a caller could silently skip crisis tracking without error. This is documented in FR-005 of the spec and is not an auth vulnerability, but a data-completeness concern for future work.
