## Auth Validation Report

**Spec:** specs/081-onboarding-redesign-progressive-discovery/spec.md (v2)
**Status:** PASS
**Timestamp:** 2026-03-22T18:30:00Z
**Validator focus:** Magic link bridge security, token expiry, session establishment, middleware route protection, expired link fallback

### Summary
- CRITICAL: 0
- HIGH: 0
- MEDIUM: 4
- LOW: 4

### Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| MEDIUM | Magic Link Auth | Spec pseudocode uses sync `create_client()` (spec.md:1177-1181) but the codebase is fully async (`AsyncClient`). Calling sync `generate_link` inside an async handler blocks the event loop. The installed SDK (supabase 2.27.3, supabase_auth) confirms `AsyncGoTrueClient` has `self.admin = AsyncGoTrueAdminAPI(...)` with `generate_link`. | spec.md:1177-1181 | Use the existing `AsyncClient` (already injected into `TelegramAuth` via `self.supabase`). Call `await self.supabase.auth.admin.generate_link(...)` directly. Do NOT create a new sync client per call. This avoids event loop blocking and eliminates redundant client instantiation. |
| MEDIUM | Magic Link Auth | Spec creates a NEW Supabase client per `_generate_portal_magic_link` call (spec.md:1179-1181) without `ClientOptions(auto_refresh_token=False, persist_session=False)`. Service role clients should not maintain sessions. Creating per-call also wastes resources. | spec.md:1179-1181 | Reuse the existing `self.supabase` client already available in the OTP handler (it is constructed with the service role key). The `TelegramAuth` class at `nikita/platforms/telegram/auth.py:57` already stores `self.supabase`. Pass it through or access it from the handler context. |
| MEDIUM | Security Headers | `vercel.json` (portal/vercel.json:11-20) has `X-Content-Type-Options`, `X-Frame-Options`, and `Referrer-Policy` but is missing `Strict-Transport-Security` (HSTS). Magic link URLs transit via HTTPS, and the portal relies on HTTPS for session cookie security. Without HSTS, a first-visit downgrade attack is theoretically possible. This is a pre-existing gap but becomes more security-relevant with magic link auth. | portal/vercel.json:11-20 | Add `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload` to vercel.json headers. Vercel serves HTTPS by default but HSTS ensures browsers never attempt HTTP. |
| MEDIUM | Session Management | Spec states magic link expiry is "Supabase defaults (1 hour)" (spec.md:154) but the actual value depends on the project's `MAILER_OTP_EXP` setting in the Supabase dashboard. If an admin changed this setting, the 1-hour assumption could be wrong. The 5-minute fallback timer (FR-006) means most users click within minutes, but the spec should verify the actual configured value. | spec.md:154, NFR section | During implementation, verify the Supabase project's `MAILER_OTP_EXP` setting via dashboard. Document the confirmed value. If it is shorter than 1 hour (e.g., 5 minutes for OTP codes), the magic link may expire before slower users click. The magic link token type is distinct from OTP expiry, but verify both. |
| LOW | Magic Link Auth | `_generate_portal_magic_link` calls `supabase.auth.admin.get_user_by_id(user_id)` (spec.md:1185) to look up the email, but the email is already available in the OTP handler context from the pending registration record. This adds an unnecessary Admin API round-trip (~200ms). | spec.md:1183-1188 | Pass the email directly from the OTP handler context (it is already available from `pending_repo.get_email(telegram_id)` or from the `verify_otp_code` response). Remove the `get_user_by_id` call to save one API round-trip and reduce latency. |
| LOW | Protected Resources | The `/onboarding` route is correctly treated as a protected route by the existing middleware (middleware.ts:66-68 redirects unauthenticated users to `/login`). However, the middleware does not have any `/onboarding`-specific logic. The spec relies on the Server Component in `page.tsx` to check `onboarding_completed_at` and redirect returning users to `/dashboard` (spec.md:758-761). This is correct but means there are two redirect layers: middleware (auth check) then Server Component (onboarding status check). | portal/src/lib/supabase/middleware.ts:56-68, spec.md:1217-1237 | This two-layer approach is the correct Next.js pattern: middleware handles auth, Server Components handle business logic. No change needed. Document this dual-redirect pattern in the implementation plan for clarity. |
| LOW | Token Handling | The `/onboarding/page.tsx` Server Component (spec.md:1228) uses `supabase.auth.getSession()` to extract the access token for a server-side fetch to the backend API. Supabase docs recommend `getUser()` for server-side auth verification (which the spec already does at line 1219) and `getSession()` only for reading the token. The spec correctly calls `getUser()` first, then `getSession()` for the token. This is the correct pattern. | spec.md:1219, 1228 | No change needed. The spec correctly uses `getUser()` for auth verification and `getSession()` for token extraction. This matches the Supabase SSR best practices. |
| LOW | Monitoring | Spec does not specify logging/monitoring for magic link generation success/failure rates beyond the inline `logger.warning` in the except block (spec.md:1202). No persistent metrics or alerting. | spec.md:1201-1203 | Consider adding a structured log metric (e.g., `magic_link_generated` / `magic_link_failed` with user_id) for operational monitoring. This helps detect service role key expiry or Supabase auth API changes. Non-blocking for implementation. |

### Auth Flow Analysis

**Primary Method:** Supabase magic link generated server-side via `admin.generate_link()` (Admin API with service role key) -- one-tap portal auth from Telegram
**Session Type:** Cookie-based via Supabase SSR (`@supabase/ssr` `createServerClient`) with PKCE code exchange
**Token Handling:** Well-specified -- magic link contains a one-time PKCE code, exchanged via existing `/auth/callback/route.ts` which calls `supabase.auth.exchangeCodeForSession(code)`, then session cookies are set by the SSR middleware

**Magic Link Bridge Flow (verified against codebase):**
1. OTP handler in `otp_handler.py` completes user verification via `TelegramAuth.verify_otp_code()`
2. `_offer_onboarding_choice()` calls `_generate_portal_magic_link(user_id, "/onboarding")`
3. `_generate_portal_magic_link()` calls `await supabase.auth.admin.generate_link({"type": "magiclink", "email": email, "options": {"redirect_to": portal_url + "/onboarding"}})`
4. SDK returns `GenerateLinkResponse(properties=GenerateLinkProperties(action_link="https://<supabase>/auth/v1/verify?token=...&redirect_to=..."))`
5. `action_link` URL is embedded in Telegram inline keyboard URL button
6. Player taps button in Telegram --> opens mobile browser --> navigates to Supabase auth URL
7. Supabase verifies token (one-time use) --> redirects to `portal/auth/callback?code=...`
8. Existing callback handler (`portal/src/app/auth/callback/route.ts`) calls `exchangeCodeForSession(code)`
9. On success, `getUser()` determines role, redirects to `/onboarding` (via `next` param) or `/admin` (admin users)
10. Middleware (`portal/src/lib/supabase/middleware.ts`) validates session cookie, allows access to `/onboarding`
11. Server Component checks `onboarding_completed_at` -- if already set, redirects to `/dashboard`

**SDK Verification (confirmed locally):**
- Package: `supabase==2.27.3`, `supabase_auth` with `AsyncGoTrueAdminAPI`
- `AsyncGoTrueClient` initializes `self.admin = AsyncGoTrueAdminAPI(...)` in its constructor
- `admin.generate_link()` returns `GenerateLinkResponse` with `properties.action_link` (string) -- spec is **correct**
- Both sync and async versions exist; codebase should use async

**Fallback Flow (well-specified):**
- If `generate_link` fails: falls back to `{portal_url}/login?next=/onboarding` (regular login flow)
- If player does not click within 5 minutes: scheduled event triggers text onboarding fallback in Telegram
- If magic link expires (default 1 hour): Supabase returns error, callback redirects to `/login?error=auth_callback_failed`

### Role & Permission Matrix

| Resource | Unauthenticated | Player (new) | Player (onboarded) | Admin |
|----------|-----------------|--------------|---------------------|-------|
| `/onboarding` | Redirect `/login` | Full access (cinematic flow) | Redirect `/dashboard` | Redirect `/admin` |
| `/dashboard` | Redirect `/login` | Full access | Full access | Redirect `/admin` |
| `/login` | Full access | Redirect `/dashboard` | Redirect `/dashboard` | Redirect `/admin` |
| `/auth/callback` | Full access (PKCE exchange) | Redirect if logged in | Redirect if logged in | Redirect `/admin` |
| `POST /api/v1/onboarding/profile` | 401 | JWT required (own data) | JWT required (idempotent update) | JWT required |
| Magic link generation | N/A (server-side only) | N/A | N/A | N/A (service role key) |

### Protected Resources

| Resource | Auth Required | Allowed Roles | Mechanism | Notes |
|----------|---------------|---------------|-----------|-------|
| `/onboarding` | Yes | player | Middleware (cookie) + Server Component (status check) | Two-layer: middleware checks auth, SC checks onboarding_completed_at |
| `POST /api/v1/onboarding/profile` | Yes (JWT) | player, admin | `get_current_user_id` FastAPI dep | Existing JWT validation via `_decode_jwt` in `auth.py` |
| `admin.generate_link()` | Service role key | Server only | Backend service role client | Never exposed to portal/client |
| `/auth/callback` | No (public) | Any | Supabase PKCE validation | One-time token exchange, open redirect protection in place |

### Security Checklist
- [x] Rate limiting on login -- Supabase Auth handles magic link rate limiting natively (built-in per-email rate limit)
- [x] Account lockout policy -- Supabase Auth built-in brute-force protection on OTP/magic link
- [x] Session invalidation on logout -- Handled by existing Supabase SSR session management (unchanged by this spec)
- [x] CSRF protection -- Supabase PKCE flow provides CSRF protection via code verifier; session cookies use SameSite attribute
- [-] Security headers (CSP, HSTS) -- PARTIAL: X-Frame-Options=DENY, X-Content-Type-Options=nosniff, Referrer-Policy present; HSTS and CSP missing (pre-existing gap, MEDIUM finding)
- [x] Magic link one-time-use -- Supabase enforces server-side (token consumed on first exchange)
- [x] Service role key server-only -- Spec correctly scopes admin API to backend only (spec.md:253, 1172)
- [x] Open redirect prevention -- Existing callback handler validates `next` param (route.ts:9-10, rejects `//evil.com` and `https://evil.com`)
- [x] Fallback for generation failure -- Falls back to regular portal URL with `/login?next=/onboarding` (spec.md:1129)
- [x] Token expiry handling -- Expired magic links redirect to `/login?error=auth_callback_failed` (route.ts:23)
- [x] Middleware route protection for /onboarding -- Covered by existing protected route logic (middleware.ts:66-68); no special carve-out needed since /onboarding requires auth

### Comparison with v1 Auth Report

The v1 auth report (auth.md) validated the drip system (Phase 2) with `DripManager._generate_magic_link()`. This v2 report focuses on the **primary onboarding magic link bridge** (FR-001, FR-008). Key differences:

| Aspect | v1 Report | v2 Report (this) |
|--------|-----------|-------------------|
| Focus | DripManager drip delivery magic links | OTP handler --> portal onboarding magic link bridge |
| `generate_link` response shape | Flagged as MEDIUM (unverified) | **CONFIRMED correct** via local SDK inspection (`result.properties.action_link`) |
| Sync vs async client | Flagged as LOW | Elevated to **MEDIUM** -- the spec pseudocode uses sync `create_client()` in an async handler, which blocks the event loop |
| Session establishment | Not deeply checked | **Verified** -- callback route correctly exchanges code, sets cookies, redirects to `/onboarding` |
| Middleware handling | Not checked for `/onboarding` | **Verified** -- `/onboarding` inherits existing protected route logic, no middleware changes needed |
| Expired link fallback | Not checked | **Verified** -- callback redirects to `/login?error=auth_callback_failed` on expired/invalid tokens |

### Recommendations

1. **MEDIUM -- Use async client for generate_link**: Replace the sync `create_client()` pseudocode (spec.md:1177-1181) with the existing async `self.supabase` client. The OTP handler already has access to an async Supabase client via `TelegramAuth`. Call `await self.supabase.auth.admin.generate_link(...)`. This avoids event loop blocking in the async FastAPI/Telegram handler.

2. **MEDIUM -- Reuse existing Supabase client**: Do not create a new client per magic link generation. The `TelegramAuth` class already holds `self.supabase` (an `AsyncClient` initialized with the service role key). Pass the email from the OTP context rather than calling `admin.get_user_by_id()` for a redundant lookup.

3. **MEDIUM -- Add HSTS header to vercel.json**: Add `{"key": "Strict-Transport-Security", "value": "max-age=63072000; includeSubDomains; preload"}` to the headers array in `portal/vercel.json`. This is a pre-existing gap but directly relevant since magic link URLs depend on HTTPS integrity.

4. **MEDIUM -- Verify MAILER_OTP_EXP setting**: During implementation, check the Supabase dashboard for the magic link expiry value. Document it. If it is less than 1 hour, consider passing an explicit `expiry` in the `generate_link` options or adjusting the 5-minute fallback timer accordingly.

5. **LOW -- Pass email directly instead of admin lookup**: The `_generate_portal_magic_link` pseudocode calls `supabase.auth.admin.get_user_by_id(user_id)` to get the email (spec.md:1185). The email is already available from the pending registration context in the OTP handler. Pass it as a parameter to save ~200ms latency.

6. **LOW -- Document two-layer redirect pattern**: The `/onboarding` route uses middleware for auth and Server Component for business logic (onboarding status). Document this explicitly in the implementation plan to avoid confusion about where each check lives.

7. **LOW -- Consider structured logging for magic link metrics**: Add a structured log entry (e.g., `{"event": "magic_link_generated", "user_id": "...", "success": true/false}`) for operational monitoring beyond the inline `logger.warning`.

8. **LOW -- Server-side token extraction pattern**: The onboarding Server Component (spec.md:1228) correctly uses `getUser()` then `getSession()` for token extraction. This is the correct Supabase SSR pattern. No change needed, but implementation should follow this exact order.
