## Auth Validation Report

**Spec:** `specs/214-portal-onboarding-wizard/spec.md`
**Status:** PASS
**Timestamp:** 2026-04-15T15:30:00Z
**Iteration:** 3 (re-validation of iter-2 fixes, commit 1caaea8)

---

### Summary
- CRITICAL: 0
- HIGH: 0
- MEDIUM: 0
- LOW: 0

---

### Iter-2 Fix Verification

Both iter-2 LOW findings were checked against commit 1caaea8:

| Iter-2 ID | Severity | Status | Evidence |
|-----------|----------|--------|----------|
| A1 — FR-10.1 stale rate-limit header | LOW | RESOLVED | spec.md line 298 now reads `choice_rate_limit dependency (10/min per authenticated user via _ChoiceRateLimiter; CHOICE_RATE_LIMIT_PER_MIN in tuning.py); Retry-After: 60 header on 429.` — no `voice_rate_limit OR` phrasing present |
| A2 — cache_key absent from WizardPersistedState | LOW | RESOLVED | spec.md line 494 now shows `cache_key: string \| null  // from BackstoryPreviewResponse; required for PUT /profile/chosen-option` inside the `WizardPersistedState` type schema; Appendix B comment at line 953 cross-references the requirement; PR 214-A `WizardPersistence.ts` artifact note (line 894) documents writing `cache_key` alongside `chosen_option_id` on backstory card CTA click |

---

### Findings

No findings. All categories clear.

---

### Auth Flow Analysis

**Primary Method:** Magic link (Supabase-managed) for initial authentication; Supabase JWT (Bearer token) for all API calls
**Session Type:** Supabase SSR cookie-based sessions on the portal (via `@supabase/ssr`); JWT Bearer tokens for FastAPI backend calls
**Token Handling:** PKCE exchange at `/auth/callback` (existing, Spec 044 / Spec 081 pattern); `getUser()` for auth decisions, `getSession()` only for token extraction — explicitly mandated in PR 214-C `page.tsx` AC (spec.md line 934)

---

### Role & Permission Matrix

| Resource | Unauthenticated | Player (any auth) | Admin |
|----------|----------------|-------------------|-------|
| `/onboarding` (wizard page) | Redirect → `/login` (middleware) | ALLOWED | ALLOWED |
| `/onboarding/auth` (magic link entry) | ALLOWED (middleware fix in PR 214-C, line 935) | Redirect → `/dashboard` | Redirect → `/admin` |
| `POST /preview-backstory` | 401 (no JWT) | ALLOWED (5/min via `_PreviewRateLimiter`) | ALLOWED |
| `PUT /onboarding/profile/chosen-option` | 401 (no JWT) | ALLOWED (10/min `choice_rate_limit`; 403 on stale cache_key) | ALLOWED |
| `PATCH /onboarding/profile` | 401 (no JWT) | ALLOWED (own profile only, via JWT sub) | ALLOWED |
| `POST /onboarding/profile` | 401 (no JWT) | ALLOWED (own profile only) | ALLOWED |
| `GET /pipeline-ready/{user_id}` | 401 (no JWT) | ALLOWED (30/min `pipeline_ready_rate_limit`; 403 if user_id != caller) | ALLOWED |

---

### Protected Resources

| Resource | Auth Required | Allowed Roles | Notes |
|----------|--------------|---------------|-------|
| `/onboarding` (wizard) | Yes | player, admin | `page.tsx` calls `getUser()` + redirects on null; explicit AC in PR 214-C (line 934) |
| `/onboarding/auth` | No (pre-auth) | all | Middleware public-route fix mandated in PR 214-C artifact (line 935) |
| `PUT /profile/chosen-option` | Yes (JWT) | player | `Depends(get_current_user_id)` + `choice_rate_limit` (10/min); 403 cross-user guard via `compute_backstory_cache_key` recompute |
| `GET /pipeline-ready/{user_id}` | Yes (JWT) | player | 403 cross-user guard (Spec 213 AC-2.4, preserved by handler extension); 30/min rate limit (AC-5.6) |
| `localStorage` wizard state | Client-only | own user_id | Keyed by `nikita_wizard_{user_id}`; AC-NR1.4 guards against cross-user contamination |

---

### Security Checklist
- [✓] Rate limiting on auth/mutation endpoints — SPECIFIED: `POST /preview-backstory` (5/min), `PUT /profile/chosen-option` (10/min via `choice_rate_limit`), `GET /pipeline-ready` (30/min via `pipeline_ready_rate_limit`). `PATCH /onboarding/profile` deferral documented in Out of Scope §1. All 429 responses include `Retry-After: 60` per RFC 6585 (AC-10.9, line 879).
- [✓] Account lockout policy — N/A: Magic link auth only; Supabase handles OTP abuse at provider level. No password brute force surface.
- [✓] Session invalidation on logout — Out of scope (handled by existing Supabase SSR `updateSession()`). No new session management introduced.
- [✓] CSRF protection — COVERED: All backend-mutating calls use JWT Bearer tokens via `apiClient`. CSRF-immune by construction (browsers cannot auto-attach Authorization headers cross-origin).
- [✓] Security headers (CSP, HSTS) — Pre-existing gap (tracked in Specs 112, 081). QR canvas CSP check (`img-src data: blob:`) mandated in PR 214-C pre-deploy checklist (line 936). No new regression introduced.
- [✓] Cross-user IDOR on `PUT /profile/chosen-option` — SPECIFIED: ownership validated via `compute_backstory_cache_key(profile)` recompute-and-compare (FR-10.1, AC-10.3). 403 on mismatch. No `user_id` column on `backstory_cache` by design.
- [✓] Cross-user IDOR on `GET /pipeline-ready/{user_id}` — INHERITED from Spec 213 FR-5 (AC-2.4): `user_id != current_user_id` → 403 `{"detail": "Not authorized"}`. Handler extension in PR 214-D uses `...` body, preserving existing guard.
- [✓] PII in structured logs — SPECIFIED: `onboarding.backstory_chosen` event contains only `{user_id, chosen_option_id, tone, venue}` (AC-10.6). Negative-assertion tests mandatory in `test_portal_onboarding.py` (line 882).
- [✓] `WizardPersistedState` schema completeness — RESOLVED: `cache_key: string | null` field present at spec.md line 494 with comment referencing its required role in PUT resume path.
- [✓] `getUser()` vs `getSession()` pattern — SPECIFIED: PR 214-C `page.tsx` AC explicitly mandates `supabase.auth.getUser()` for auth decisions and `getSession()` only for token extraction (line 934).
- [✓] Magic link expiry handling — SPECIFIED: Edge case table (line 807): expired link redirects to `/onboarding/auth?error=link_expired` with Nikita-voiced banner and re-request CTA.
- [✓] Idempotency safety on `PUT /profile/chosen-option` — SPECIFIED: AC-10.4 requires identical state and response on repeated PUT with same body.

---

### Recommendations

No recommendations. All auth requirements are complete, consistent, and actionable.

---

### Iteration History

| Iter | Status | C | H | M | L | Commit |
|------|--------|---|---|---|---|--------|
| 1 | FAIL | 0 | 0 | 3 | 3 | pre-363e8ea |
| 2 | FAIL | 0 | 0 | 0 | 2 | 363e8ea |
| 3 | PASS | 0 | 0 | 0 | 0 | 1caaea8 |
