## Auth Validation Report

**Spec:** specs/081-onboarding-redesign-progressive-discovery/spec.md
**Status:** PASS
**Timestamp:** 2026-03-22T12:00:00Z

### Summary
- CRITICAL: 0
- HIGH: 0
- MEDIUM: 5
- LOW: 3

### Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| MEDIUM | Magic Link Auth | `generate_link` response shape: spec references `result.properties.action_link` but Supabase GoTrue HTTP API returns `action_link` at top level. Python SDK may wrap differently (e.g., `result.user` + `result.properties`). Incorrect attribute path would cause silent fallback to regular URL. | spec.md:877-878 | Verify exact Python SDK `GenerateLinkResponse` shape in implementation. Write a unit test that asserts the `action_link` attribute path. If the SDK returns `result.properties.action_link`, the spec is correct. If not, update to `result.action_link` or the correct accessor. |
| MEDIUM | Magic Link Auth | Service role client instantiation creates a NEW `create_client()` per magic link generation. No `ClientOptions(auto_refresh_token=False, persist_session=False)` specified, which Supabase docs recommend for service role clients to prevent session leakage. | spec.md:866-867 | Use `ClientOptions(auto_refresh_token=False, persist_session=False)` when creating the service role client. Consider caching the admin client as a singleton in `DripManager.__init__` rather than creating per-call. |
| MEDIUM | Session Management | Magic link expiry is documented as "Supabase defaults (typically 1 hour)" (NFR-003, line 1153) but the actual value depends on project-level `MAILER_OTP_EXP` setting in Supabase dashboard. If an admin has changed this, the assumption could be wrong. The spec correctly notes this but does not specify a verification step. | spec.md:1152-1154 | Add a task to verify the Supabase project's `MAILER_OTP_EXP` setting during implementation. Document the current value in deployment docs. |
| MEDIUM | Security Headers | `vercel.json` includes `X-Content-Type-Options`, `X-Frame-Options`, and `Referrer-Policy` but is missing `Strict-Transport-Security` (HSTS) and `Content-Security-Policy` (CSP). Magic link URLs transit through HTTPS, but without HSTS a downgrade attack is theoretically possible on first visit. | portal/vercel.json:11-20 | Add `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload` to vercel.json headers. Consider adding a basic CSP header. This is an existing gap, not introduced by Spec 081, but relevant since magic links increase reliance on HTTPS integrity. |
| MEDIUM | Rate Limiting | No rate limiting specified for the `/auth/callback` route handler itself. Magic links embedded in Telegram drips could be shared or replayed by third parties before expiry. While Supabase magic links are one-time-use (consumed on token exchange), a brute-force attempt on the `code` parameter before legitimate use is theoretically possible. | portal/src/app/auth/callback/route.ts | Supabase handles magic link token validation server-side (one-time-use, short-lived), which mitigates most brute-force risk. For defense in depth, consider Vercel's built-in rate limiting or a lightweight middleware check on `/auth/callback`. LOW urgency since Supabase's own rate limiting applies at the auth API level. |
| LOW | Magic Link Auth | Spec does not specify logging/monitoring for magic link generation success/failure rates. The `magic_link_failures` counter in the check-drips response (line 1108) is good for the API response but no persistent tracking (e.g., metrics, alerts) is defined. | spec.md:1108 | Consider logging magic link generation failures to a structured log or counter for operational monitoring. This helps detect if the service role key expires or the Supabase auth API changes. |
| LOW | Protected Resources | The welcome page (`/dashboard/welcome`) correctly inherits protection from the existing middleware pattern (all `/dashboard/*` routes require auth). The spec explicitly confirms this at line 991. No gap. However, the welcome page fetches stats server-side with a hardcoded `Bearer ${/* session token */}` pattern (line 957) that needs the actual session token extraction implemented. | spec.md:956-958 | Implementation should use `supabase.auth.getSession()` to extract the access token for the server-side fetch to the backend API. This is an implementation detail the plan should address. |
| LOW | Token Handling | The spec creates a Supabase client with `create_client(url, service_key)` (line 866-867) using the synchronous client. The rest of the codebase (`telegram/auth.py`) uses `AsyncClient`. Mixing sync and async Supabase clients could cause event loop issues in async FastAPI handlers. | spec.md:859-867 | Use `create_async_client()` with the service role key, or verify that `supabase.auth.admin.generate_link()` is available on the async client. If not, run the sync call in a thread executor via `asyncio.to_thread()`. |

### Auth Flow Analysis

**Primary Method:** Supabase magic link (server-generated via Admin API) -- seamless bridge from Telegram to portal
**Session Type:** Cookie-based (Supabase SSR via `@supabase/ssr` `createServerClient`) with PKCE code exchange
**Token Handling:** Specified -- magic link contains a one-time PKCE code, exchanged via existing `/auth/callback/route.ts` which calls `supabase.auth.exchangeCodeForSession(code)`. JWT stored in HTTP-only cookies by Supabase SSR middleware.

**Auth Bridge Flow (well-specified):**
1. Backend `DripManager._generate_magic_link()` calls `supabase.auth.admin.generate_link(type="magiclink")` using service role key
2. Returns `action_link` URL containing a hashed token
3. URL is embedded in Telegram inline keyboard button
4. Player taps button in Telegram, opens browser
5. Browser navigates to Supabase auth URL, which redirects to `portal/auth/callback?code=...`
6. Existing callback handler calls `exchangeCodeForSession(code)`, sets session cookies
7. Redirects to target portal page (from `redirectTo` parameter)

### Role & Permission Matrix

| Resource | Unauthenticated | Player | Admin |
|----------|-----------------|--------|-------|
| `/dashboard/welcome` | Redirect to `/login` | Full access | Redirect to `/admin` |
| `/dashboard` | Redirect to `/login` | Full access | Redirect to `/admin` |
| `GET /portal/stats` (welcome_completed) | 401 | Own data only (JWT) | Own data only (JWT) |
| `PUT /portal/settings` (welcome_completed) | 401 | Own data only (JWT) | Own data only (JWT) |
| `POST /tasks/check-drips` | 401 | 401 | 401 (TASK_AUTH_SECRET only) |
| Magic link generation | N/A (server-side) | N/A | N/A (service role key) |

### Protected Resources

| Resource | Auth Required | Allowed Roles | Notes |
|----------|---------------|---------------|-------|
| `/dashboard/welcome` | Yes (middleware) | player | New page, inherits existing `/dashboard/*` protection |
| `/dashboard` (first-visit redirect) | Yes (middleware) | player | Client-side redirect to `/dashboard/welcome` if `!welcome_completed` |
| `GET /portal/stats` | Yes (JWT) | player, admin | Additive change: adds `welcome_completed` field |
| `PUT /portal/settings` | Yes (JWT) | player, admin | Additive change: accepts `welcome_completed` |
| `POST /tasks/check-drips` | Yes (Bearer secret) | pg_cron only | New endpoint, follows existing `verify_task_secret` pattern |
| `supabase.auth.admin.generate_link()` | Service role key | Server only | Never exposed to clients |

### RLS Compatibility

| Table | Column | RLS Policy | Status |
|-------|--------|------------|--------|
| `users` | `drips_delivered` (new JSONB) | Existing `users_own_data` policy: `auth.uid() = id` | Covered -- no new policy needed |
| `users` | `welcome_completed` (new BOOLEAN) | Existing `users_own_data` policy: `auth.uid() = id` | Covered -- no new policy needed |

The spec correctly identifies (line 1069-1075) that both new columns are covered by the existing `users` table RLS policy. No new RLS policies are required.

### Security Checklist
- [x] Rate limiting on login -- Supabase Auth handles magic link rate limiting natively; drip delivery rate limited to 1 per 2h per user (FR-005)
- [x] Account lockout policy -- Supabase Auth handles (built-in brute-force protection on OTP/magic link)
- [x] Session invalidation on logout -- Handled by existing Supabase SSR session management (unchanged)
- [x] CSRF protection -- Supabase PKCE flow provides CSRF protection via code verifier; cookie-based sessions use SameSite attribute
- [-] Security headers (CSP, HSTS) -- Partial: X-Frame-Options=DENY, X-Content-Type-Options=nosniff, Referrer-Policy present; HSTS and CSP missing (pre-existing gap)
- [x] Magic link one-time-use -- Supabase enforces this server-side (token consumed on exchange)
- [x] Service role key server-only -- Spec correctly scopes admin API usage to backend DripManager only (line 1172)
- [x] Fallback for email-less users -- Spec handles gracefully: regular portal URL without magic link (line 107-108)
- [x] Check-drips endpoint auth -- Uses existing `verify_task_secret` pattern matching all other pg_cron endpoints
- [x] Open redirect prevention -- Existing callback handler validates `next` parameter (line 9-10 of route.ts)

### Recommendations

1. **MEDIUM -- Verify `generate_link` response shape**: Write a test that calls `supabase.auth.admin.generate_link()` and asserts the attribute path for `action_link`. The spec's `result.properties.action_link` may not match the Python SDK. Fix the accessor before shipping.

2. **MEDIUM -- Use proper ClientOptions for service role client**: When creating the Supabase client with the service role key, pass `ClientOptions(auto_refresh_token=False, persist_session=False)` per Supabase best practices. Consider caching this client as a singleton.

3. **MEDIUM -- Verify MAILER_OTP_EXP setting**: During implementation, check the Supabase dashboard for the magic link expiry setting. Document the value (expected: 3600 seconds) in deployment docs.

4. **MEDIUM -- Add HSTS header**: Add `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload` to `portal/vercel.json` headers. This is a pre-existing gap but becomes more relevant with magic link auth.

5. **MEDIUM -- Consider rate limiting on auth callback**: While Supabase handles token validation, adding a lightweight rate limit on `/auth/callback` provides defense in depth against token brute-force.

6. **LOW -- Add magic link failure monitoring**: Beyond the `magic_link_failures` counter in the API response, consider structured logging or a metric for operational alerting.

7. **LOW -- Use async Supabase client for generate_link**: The spec shows `create_client()` (sync) but the codebase uses async patterns. Use `create_async_client()` or wrap in `asyncio.to_thread()`.

8. **LOW -- Server-side token extraction for welcome page**: The welcome page's server-side fetch (spec line 956-958) needs the actual session token. Implementation should extract it from `supabase.auth.getSession()`.
