---
phase: "01"
name: canonical-tg-first-signup
lifecycle: living
imported_from: docs-to-process/20260518-spec220-canonical-tg-first.md
created: 2026-05-19
---

# Phase 01 — SPEC: Canonical Telegram-First Signup

## Why

Walk #219 surfaced 5 critical regressions: `CODE_SENT` FSM expiry mismatch (5-min window vs 1-hour Supabase OTP), Path 3 portal-first late-bind completely non-functional (`telegram.py:577-618` coercion block drops the 6-char link code), HTTP 409 used as happy-path signal in `portal_auth.py:425-428`, 9 PII-leaking `[LLM-DEBUG]` log statements, and a missing FE toast key that fires a generic error on bind failure. Spec 219 patched symptoms in-place, but the root cause is Arch A's 3-path scatter: 6 FSM states, 5 provisioning sites, dual-confirmation (OTP in TG + magic-link click in browser), and a `dashboard_bridge` endpoint that exists solely to duct-tape portal-first signups onto a Telegram-native system.

A 3-expert panel (pragmatist + security + UX) evaluated 4 architectures on 6 axes (complexity, security, UX, maintainability, velocity, correctness). Arch B (canonical TG-first, 4 states, 1 provisioner, no portal-first path) scored 3.87/5 vs 3.03 for Arch A (status quo + #219 patches). The user has explicitly accepted the trade-off: no portal-first signup path, single Telegram entry point, zero retained users (safe to bulldoze migrations).

## Hard Constraints (user verbatim)

1. Telegram account linked instantly — atomic bind at OTP-verify, no late-bind window.
2. No stupid steps — eliminates dual-confirmation (OTP in TG + magic-link click).
3. End of onboarding you can chat — wizard completion flips `onboarding_status='completed'`; first pipeline turn fires immediately.

## Functional Requirements

**FR-1** — Landing page (`portal/src/app/(root)/page.tsx`) has a single signup CTA: "Start on Telegram" deep-link → `t.me/Nikita_my_bot?start=new`. No secondary email/password form. No `/login` button.

**FR-2** — `/login` route returns 410 GONE. Existing inbound links redirect to landing page. No email-form signup fallback.

**FR-3** — `/onboarding/auth` route handler deleted entirely (not just 410 response code; full route file removal).

**FR-4** — OTP signup flow (Flow A):

1. Bot collects email → calls `supabase.auth.sign_in_with_otp({ email, options: { data: { telegram_id: str(chat_id) }, should_create_user: True } })`. Supabase creates `auth.users` row with `email_confirmed_at=NULL` and stashes `telegram_id` in `raw_user_meta_data`.
2. User pastes 6-digit code into TG.
3. Bot calls `supabase.auth.verify_otp({ email, token: code, type: 'email' })`. Returns session. Supabase sets `email_confirmed_at=NOW()`, firing the UPDATE trigger (FR-4b).
4. Bot calls `supabase.auth.admin.update_user_by_id(user.id, { app_metadata: { telegram_id: str(chat_id), onboarded: false } })`. Locks telegram_id immutably.
5. Bot calls `supabase.auth.admin.generate_link({ type: 'magiclink', email })`. Posts `action_link` to TG.
6. User clicks portal link → `/auth/confirm?token_hash=...&type=email` → `supabase.auth.verify_otp({ token_hash, type: 'email' })` → session cookie set → redirect to `/onboarding`.

**FR-4b** — Atomic provisioning trigger fires on `auth.users UPDATE` when `OLD.email_confirmed_at IS NULL AND NEW.email_confirmed_at IS NOT NULL`. Body: `INSERT INTO public.users (id, telegram_id) VALUES (NEW.id, (NEW.raw_user_meta_data->>'telegram_id')::bigint) ON CONFLICT (id) DO UPDATE SET telegram_id = EXCLUDED.telegram_id`. Language: plpgsql, security definer, search_path=''. Idempotent via ON CONFLICT.

**FR-5** — Portal entry uses Supabase PKCE `action_link` from `admin.generate_link`. NOT a custom JWT. `/start` resend re-calls `admin.generate_link` to mint fresh `action_link`.

**FR-6** — `/auth/confirm` route handler **PRESERVED** as Supabase PKCE token_hash exchange endpoint. Autobind side-effect calls removed (lines 141, 156, 230, 254, 270, 279, 284, 289, 296, 310). Net: ≤80 LOC thin "exchange token_hash for session, redirect to /onboarding" handler.

**FR-7** — Wizard mount (`/onboarding`) validates `users.telegram_id IS NOT NULL` via `GET /api/v1/user/me`. Null state redirects to landing CTA. Defensive guard only (impossible in Arch B normal flow).

**FR-8** — Middleware (`portal/src/middleware.ts`): if session has `app_metadata.onboarded != true`, any `/dashboard/*` request redirects to `/onboarding`. JWT claim check is fast path.

**FR-9** — Bot `/start` handler is the single signup entry. No coercion block (`telegram.py:577-618` deleted). `/start new` triggers OTP flow. `/start` with no/unknown payload: if `authenticated_tg_bound` and not `onboarding_completed`, re-send portal action_link; if `onboarding_completed`, send "You're all set — chat below."

**FR-10** — DB migration drops `telegram_signup_sessions` and `telegram_link_codes` tables. FK constraints dropped first. Irreversible; safe (zero retained users).

**FR-11** — Wizard completion (`PATCH /api/v1/user/onboarding`) sets `public.users.onboarding_status='completed'` AND Supabase Admin API `app_metadata.onboarded=true`. SELECT FOR UPDATE serializes concurrent tabs.

**FR-12** — All existing portal sessions invalidated during migration deploy (Admin API bulk logout or `refresh_tokens` truncation).

**FR-13** — ROADMAP updated: Spec 220 ACTIVE. Specs 215 (all sub-specs), 216-G, 216-H, 219-C1, 219-C4 marked SUPERSEDED with pointer to Spec 220.

**FR-14** — No `[LLM-DEBUG]` log statements in any module. PII not in INFO-level logs. Debug-level PII logging permitted only with `DEBUG_PII=true` env flag (default off).

**FR-15** — 9 PII-leaking log lines at `telegram.py:604,620,639,653,669,675,682,694,695` deleted or replaced with non-PII equivalents.

## Acceptance Criteria

**AC-1** — Landing page (`/`) has exactly one signup path: "Start on Telegram" deep-link CTA. No email form, no `/login` link. Verified by: DOM assertion in Playwright test; `rg "signUp|signIn|email.*input" portal/src/app/\(root\)/page.tsx` returns 0 matches.

**AC-2** — `/login`, `/auth/confirm`, `/onboarding/auth`, `/api/v1/auth/autobind-telegram`, `/api/v1/auth/dashboard-bridge` all return 410 GONE (or 404 for deleted FE routes). Verified by: `curl -sI https://nikita-mygirl.com/login | grep HTTP` → 410.

**AC-3** — After OTP-verify in TG, `SELECT telegram_id FROM public.users WHERE id = $auth_uid` returns the user's Telegram ID. Verified by: unit test on `signup_handler.py` OTP-verify path + Supabase MCP `execute_sql` in live walk.

**AC-4** — After OTP-verify, bot delivers a message containing `https://nikita-mygirl.com/onboarding?token=` within 3 seconds. Verified by: unit test mocking Supabase Admin; live walk step 5 (Telegram MCP `get_history`).

**AC-5** — Wizard `/onboarding` page rejects requests with no valid session or expired token. Redirects to landing. Verified by: `curl -sI https://nikita-mygirl.com/onboarding` (no session) → redirect to `/`.

**AC-6** — Wizard completion (`PATCH /api/v1/user/onboarding`) sets `onboarding_status='completed'` in `public.users` AND `app_metadata.onboarded=true` in Supabase auth metadata. Verified by: unit test + Supabase MCP `execute_sql`.

**AC-7** — First Telegram message after onboarding completion passes through all 11 pipeline stages. Verified by: `gcloud logging read` after live walk first-chat turn; all stage names in structured log.

**AC-8** — TG bot rejects free-text from `telegram_id` with no bound `public.users` row. Responds: "Send /start to begin." Verified by: unit test with mock `telegram_id` not in `public.users`.

**AC-9** — Authenticated user with `onboarding_status='pending'` navigating to `/dashboard` is redirected to `/onboarding`. Verified by: Playwright test with mocked JWT lacking `app_metadata.onboarded`.

**AC-10** — `telegram_signup_sessions` and `telegram_link_codes` tables do not exist post-migration. `rg "telegram_signup_session\|telegram_link_code" nikita/ --type py` returns 0 matches.

**AC-11** — No Python file in `nikita/` references `autobind`, `dashboard_bridge`, `link_code`, or `TelegramLinkRepository`. Verified by: `rg "autobind|dashboard.bridge|link.code|TelegramLinkRepository" nikita/ --type py` returns 0.

**AC-12** — Live walk: TG-first signup → onboarding wizard → first chat turn completes in ≤12 manual user steps. Walk report at `docs-to-process/YYYYMMDD-walk-spec220-final.md`.

**AC-13** — `rg "\[LLM-DEBUG\]" nikita/platforms/telegram/telegram.py` returns 0 matches post-PR 220-D.

**AC-14** — No `email` or `telegram_id` literal values in INFO-level log output during live walk (verified by `gcloud logging read` grep).

**AC-15** — `on_auth_user_email_confirmed` UPDATE trigger fires on email confirmation, INSERT-OR-UPDATE `public.users(id, telegram_id)`. Verified by: pgTAP test in PR 220-D migration; Supabase MCP `execute_sql` SELECT after live walk step 8.

**AC-16** — `app_metadata.telegram_id` and `app_metadata.onboarded` set on `auth.users` post-verifyOtp and post-wizard-completion. Verified by: Supabase MCP `execute_sql` `SELECT raw_app_meta_data FROM auth.users WHERE id = $uid`.

**AC-17** — Concurrent wizard completion serialized: 2 simultaneous `PATCH /api/v1/user/onboarding` requests return (a) first → 200, (b) second → 200 idempotent or 409. No data corruption. Verified by: integration test with `asyncio.gather` of 2 PATCH calls.

**AC-18** — `onboarding_status` admit-list shrunk: `message_handler.py:1070` rejects `skipped` state. Verified by: unit test asserting `'skipped'` produces TG message "Finish setup first."
