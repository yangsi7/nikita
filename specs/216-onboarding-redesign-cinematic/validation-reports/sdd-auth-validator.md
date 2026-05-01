# Auth Validation Report — ITERATION 2

**Spec:** `/Users/yangsim/Nanoleq/sideProjects/nikita/specs/216-onboarding-redesign-cinematic/subspecs/216-A-telegram-canonical-routing/spec.md` (parent: `specs/216-onboarding-redesign-cinematic/spec.md`)
**Status:** PASS
**Timestamp:** 2026-04-29
**Iteration:** 2 (re-validation after iteration-1 fixes)

---

## Summary

- CRITICAL: 0
- HIGH: 0
- MEDIUM: 0
- LOW: 0

All iteration-1 findings (3 HIGH + 4 MEDIUM + 2 LOW) are now CLOSED in subspec 216-A and parent spec §HTTP API Contracts / §Cookie Contract.

---

## Iteration-1 Findings — Closure Audit

| Iter-1 ID | Severity | Issue | Closure mechanism | Verified at |
|-----------|----------|-------|-------------------|-------------|
| HIGH-1 | HIGH | A1.9 idempotency was non-deterministic disjunction ("400 OR redirect") | Replaced with deterministic cookie-presence predicate: cookie + session_valid → 302 `/dashboard`; else 400 + `ErrorEnvelope(magic_link_consumed)` with NO new session minting on path (b) | subspec AC A1.9 (line 39); parent spec §`/auth/confirm` lines 285-298 |
| HIGH-2 | HIGH | JWT cookie attributes unspecified | Explicit Cookie Contract: `HttpOnly=True`, `Secure=True`, `SameSite=Lax`, `Path=/`, `Max-Age >= 604800`; AC A1.10 asserts via `Set-Cookie` parse in integration test | subspec AC A1.10 (line 40); parent spec §Cookie Contract lines 300-307 |
| HIGH-3 | HIGH | Concurrent magic-link click race undefined (W3 #F.2) | AC A1.11: `asyncio.gather` integration test, exactly-one-200 + one-400 (`magic_link_consumed`), no partial DB state (no orphan `auth.users`, no missing `user_profiles`) | subspec AC A1.11 (line 41) |
| MED-1 | MED | Wrong-OTP destructive purge (#437) under-specified | AC A1.14: explicit guard — wrong OTP MUST NOT delete `pending_signup_session` row, MUST NOT clear `magic_link_token` if already issued, MUST NOT silently zero `code_attempts_remaining`; test `test_wrong_otp_does_not_destroy_session`; escalates to HIGH if violated | subspec AC A1.14 (line 44) |
| MED-2 | MED | Resume mid-wizard (NR-07) untested for cookie + empty-jsonb edge | AC A1.12: cookie-valid + `conversation_jsonb` populated → hydrate via `state_reconstruction.build_state_from_conversation`; cookie-valid + jsonb empty/null → fresh slot 1 (no redirect-loop) | subspec AC A1.12 (line 42) |
| MED-3 | MED | Plus-alias email regex tolerance unverified | Test Identity section: W4 walk uses `simon.yang.ch+spec216walk@gmail.com`; pre-walk assert `tests/platforms/telegram/test_signup_handler.py::test_plus_alias_email_accepted` | subspec lines 85-87 |
| MED-4 | MED | `disable_web_page_preview` only on magic-link reply, not enforced globally for SignupHandler | AC A1.13: ALL outbound `SignupHandler` messages with `nikita-mygirl.com` URL set `disable_web_page_preview=True`; test `test_disable_web_page_preview_on_all_signup_messages` | subspec AC A1.13 (line 43) |
| LOW-1 | LOW | `signup_state='completed'` transition undocumented | Out of Scope explicit (inherits Spec 215 documentation) | subspec lines 89-92 |
| LOW-2 | LOW | No `/start` rate limiting | Out of Scope explicit (Telegram Bot API ~1 msg/sec/chat implicit throttle) | subspec lines 89-92 |

---

## Auth Flow Analysis

**Primary Method:** Telegram-first conversational signup (FSM in `SignupHandler`) → email collection → 6-digit OTP via Supabase `generateLink` → PKCE magic-link `/auth/confirm?token_hash=...` → JWT cookie `nikita-session`
**Session Type:** JWT cookie `nikita-session` (HttpOnly, Secure, SameSite=Lax, Path=/, Max-Age ≥ 604800s / 7d)
**Token Handling:** PKCE `token_hash` (Spec 215 inheritance, preserved); single-use; replay yields deterministic 302 (live session) OR 400 (no/invalid cookie); never mints new session on replay path

## Role & Permission Matrix

| Resource | Unbound TG user | Bound TG user | Authed portal user |
|----------|-----------------|----------------|---------------------|
| `POST /telegram/webhook` `/start` (bare or `welcome`) | → `SignupHandler.handle_welcome` (FSM) | → `CommandHandler._handle_start` (existing) | n/a |
| `GET /auth/confirm?token_hash=...` (1st click) | 200 + Set-Cookie → `/onboarding` | n/a | n/a |
| `GET /auth/confirm?token_hash=...` (2nd click, cookie live) | 302 → `/dashboard` | 302 → `/dashboard` | 302 → `/dashboard` |
| `GET /auth/confirm?token_hash=...` (2nd click, no/invalid cookie) | 400 `magic_link_consumed` | 400 `magic_link_consumed` | n/a |
| `POST /api/v1/onboarding/answer` | 401 `auth_required` | 401 `auth_required` | 200 |
| `GET /api/v1/onboarding/state` | 401 | 401 | 200 (resume per NR-07 / AC A1.12) |

## Protected Resources

| Resource | Auth requirement | Notes |
|----------|------------------|-------|
| `/api/v1/onboarding/answer` | `Depends(require_auth_cookie)` (`nikita-session` JWT) | 401 on miss, 422 body, 429 rate (30/min) |
| `/api/v1/onboarding/state` | `Depends(require_auth_cookie)` | NR-07 resume per AC A1.12 |
| `/auth/confirm` | Public entry; sets `nikita-session` on 200 | Cookie Contract enforced (A1.10) |
| `/onboarding` (FE) | `nikita-session` cookie | Resume hydration via `build_state_from_conversation` |
| Telegram webhook `/start` | Telegram signature; predicate split bound vs unbound | A1.1, A1.2, A1.3 |

## Security Checklist

- [✓] Rate limiting on auth endpoints — `/api/v1/onboarding/answer` 30/min/user (parent spec line 238); `/start` Out of Scope (Telegram throttle, documented)
- [✓] Account lockout policy — `code_attempts_remaining` countdown preserved; A1.14 guards against silent decrement past 0
- [✓] Session invalidation on logout — JWT 7d Max-Age; cookie cleared via standard portal logout (Spec 215 inheritance)
- [✓] CSRF protection — `SameSite=Lax` on `nikita-session` cookie (A1.10)
- [✓] Security headers — `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/` enforced (Cookie Contract)
- [✓] No stack-trace leakage — `ErrorEnvelope.detail` scrubbed; only W3C `trace_id` exposed (parent spec line 283)
- [✓] No partial DB state on race — A1.11 asserts no orphan `auth.users`, no missing `user_profiles` (W3 #F.2 closed)
- [✓] No destructive purge on wrong OTP — A1.14 guard
- [✓] Telegram URL preview suppressed globally for SignupHandler messages with portal URLs — A1.13
- [✓] Resume mid-wizard hydration is cookie-gated — A1.12 (no orphan resume without auth)

## Findings

None.

## Recommendations

None blocking. Subspec 216-A is GATE-2 PASS for auth validation.

Optional follow-ups (non-blocking, accepted as Out of Scope):
1. (LOW) If Telegram per-chat throttle proves insufficient post-deploy, add explicit rate limit on bare `/start` in a follow-up spec.
2. (LOW) Document `signup_state='completed'` transition trigger + cleanup cron in Spec 215 archive notes.
