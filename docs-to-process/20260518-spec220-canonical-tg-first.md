---
title: Spec 220 - Canonical Telegram-First Signup
lifecycle: living
spec_number: 220
status: PLANNED
domain: 4-portal-auth
supersedes: 215-A, 215-PR-F1b, 216-G, 216-H, 219-C1, 219-C4
related: 218
---

# Spec 220 — Canonical Telegram-First Signup

## Why

Walk #219 surfaced 5 critical regressions: `CODE_SENT` FSM expiry mismatch (5-min window vs 1-hour Supabase OTP), Path 3 portal-first late-bind completely non-functional (`telegram.py:577-618` coercion block drops the 6-char link code), HTTP 409 used as happy-path signal in `portal_auth.py:425-428`, 9 PII-leaking `[LLM-DEBUG]` log statements, and a missing FE toast key that fires a generic error on bind failure. Spec 219 patched symptoms in-place, but the root cause is Arch A's 3-path scatter: 6 FSM states, 5 provisioning sites, dual-confirmation (OTP in TG + magic-link click in browser), and a `dashboard_bridge` endpoint that exists solely to duct-tape portal-first signups onto a Telegram-native system.

A 3-expert panel (pragmatist + security + UX) evaluated 4 architectures on 6 axes (complexity, security, UX, maintainability, velocity, correctness). Arch B (canonical TG-first, 4 states, 1 provisioner, no portal-first path) scored 3.87/5 vs 3.03 for Arch A (status quo + #219 patches). The user has explicitly accepted the trade-off: no portal-first signup path, single Telegram entry point, zero retained users (safe to bulldoze migrations).

Per user verbatim ask: "Telegram account linked instantly when creating account", "no stupid steps", "end of onboarding you can chat."

## Hard constraints (user verbatim)

1. Telegram account linked instantly — atomic bind at OTP-verify, no late-bind window.
2. No stupid steps — eliminates dual-confirmation (OTP in TG + magic-link click).
3. End of onboarding you can chat — wizard completion flips `onboarding_status='completed'`; first pipeline turn fires immediately.

## Architecture

### Canonical flow (4 states)

```
anon
  │  user hits landing → clicks "Start on Telegram" CTA
  ▼
tg_otp_pending
  │  bot sends OTP to TG; Supabase magic-link (OTP) valid 60 min
  ▼  user submits OTP to bot
authenticated_tg_bound
  │  atomic: create auth.users + public.users(telegram_id=<id>) in one tx
  │  bot sends portal JWT deep-link: https://nikita-mygirl.com/onboarding?token=<jwt>
  ▼  user clicks link (5-min TTL; re-sendable via /start)
onboarding_completed
     wizard completion: onboarding_status='completed' + app_metadata.onboarded=true
     first Telegram message fires full pipeline
```

No FSM table. No `CODE_SENT`/`MAGIC_LINK_SENT` rows. No portal-side signup form. No autobind. No dashboard_bridge.

### What's bulldozed

| Artifact | Location | Reason |
|---|---|---|
| Portal-first signup path | `/login` route, `/onboarding/auth` route | Only TG-first entry point |
| `/api/v1/auth/autobind-telegram` | `nikita/api/routes/portal_auth.py` | No late-bind in Arch B |
| `/api/v1/auth/dashboard-bridge` | `nikita/api/routes/portal_auth.py` | dashboard_bridge concept eliminated |
| `telegram_signup_sessions` FSM table | `supabase/migrations/` | 4-state machine lives in code, not DB |
| `telegram_link_codes` table | `supabase/migrations/` | No 6-char link-code path |
| `TelegramLinkRepository` | `nikita/db/repositories/` | Callers removed |
| `_handle_start_with_payload` 6-char-code path | `nikita/platforms/telegram/telegram.py:577-618` | Coercion block drops link code; eliminated |
| `/auth/confirm` autobind side-effect (NOT the route itself) | `portal/src/app/auth/confirm/route.ts` autobind block | Route PRESERVED as Supabase PKCE token_hash handler; autobind call sites removed. See FR-6 revision. |
| `pending_registrations` table + `PendingRegistrationRepository` + cron job | `nikita/db/repositories/pending_registration_repository.py`, `nikita/platforms/telegram/auth.py`, `tasks.py:681-697` | Pre-Spec-219 alternate FSM table; obsolete in Arch B alongside `telegram_signup_sessions`. Migration drops both. Cron endpoint deleted. |
| `TelegramSignupSessionRepository` file | `nikita/db/repositories/telegram_signup_session_repository.py` | Orphan after all callers removed; explicit deletion gate in AC-11. |
| `generate_magiclink_for_telegram_user` endpoint | `nikita/api/routes/portal_auth.py:174-295` (~122 LOC) | Dead after PR 220-D (signup_handler no longer mints magic-link via this admin route; uses inline `admin.generate_link` per FR-4 step 5). |
| `/auth/bridge` route | `portal/src/app/auth/bridge/route.ts` (67 LOC) | Bridge token / PKCE side-channel obsolete when `/auth/confirm` is canonical PKCE handler. |
| `/auth/interstitial` page + client | `portal/src/app/auth/interstitial/` | "Not yet bound" interstitial purpose-eliminated when `dashboard_bridge` is gone. |
| 9 `[LLM-DEBUG]` log statements | `telegram.py:604,620,639,653,669,675,682,694,695` | PII (email+telegram_id plaintext) |
| `telegram_bind_failed` toast key | `portal/src/app/onboarding/page-client.tsx:41-66` | Route never sends this key; stale dead code |

### What's preserved

- `auth.users` + `auth.identities` — Supabase canonical auth; untouched
- `public.users` schema — `id`, `telegram_id`, `onboarding_status`, `relationship_score`, etc.; untouched
- `create_with_metrics` (`nikita/db/repositories/user_repository.py`) — single provisioner called atomically at OTP-verify
- `/onboarding` wizard — FE flow unchanged; wizard reads cumulative slots from BE
- Voice + Telegram downstream pipelines — gated on `onboarding_status='completed'`; no change
- Middleware onboarding-gate (`portal/src/middleware.ts`) — strengthened with JWT claim check

## Functional Requirements

**FR-1** — Landing page (`portal/src/app/(root)/page.tsx`) has a single signup CTA: "Start on Telegram" deep-link → `t.me/Nikita_my_bot?start=new`. No secondary email/password form. No `/login` button.

**FR-2** — `/login` route returns 410 GONE. Existing inbound links redirect to landing page. No email-form signup fallback.

**FR-3** — `/onboarding/auth` route handler deleted (already returns 410 GONE post-PR #663 per Spec 219; this spec removes the route file entirely, not just the response code).

**FR-4** — **OTP signup flow (Flow A per 2026-05-19 Supabase research)**:

1. Bot collects email → calls `supabase.auth.sign_in_with_otp({ email, options: { data: { telegram_id: str(chat_id) }, should_create_user: True } })`. Supabase creates `auth.users` row with `email_confirmed_at=NULL` and stashes `telegram_id` in `raw_user_meta_data`. Supabase emails the 6-digit OTP per the Magic Link template (must contain `{{ .Token }}` to send OTP not magiclink).
2. User pastes 6-digit code into TG.
3. Bot calls `supabase.auth.verify_otp({ email, token: code, type: 'email' })`. Returns session. Supabase sets `email_confirmed_at=NOW()` on the auth.users row, firing the UPDATE trigger (FR-4b) which provisions `public.users(id, telegram_id)`.
4. Bot calls `supabase.auth.admin.update_user_by_id(user.id, { app_metadata: { telegram_id: str(chat_id), onboarded: false } })`. Locks telegram_id immutably (user-writable `user_metadata` is NOT a source of truth — RLS/middleware reads `app_metadata` only).
5. Bot calls `supabase.auth.admin.generate_link({ type: 'magiclink', email })`. Posts the response's `action_link` to TG.
6. User clicks portal link in TG → `/auth/confirm?token_hash=...&type=email` server route → calls `supabase.auth.verify_otp({ token_hash, type: 'email' })` → session cookie set → redirect to `/onboarding`.

**FR-4b — Atomic provisioning trigger (resolves C-1 / Risk row 5 NEEDS-CLARIFICATION)**: New DB trigger fires on `auth.users UPDATE` when `OLD.email_confirmed_at IS NULL AND NEW.email_confirmed_at IS NOT NULL`. Body: `INSERT INTO public.users (id, telegram_id) VALUES (NEW.id, (NEW.raw_user_meta_data->>'telegram_id')::bigint) ON CONFLICT (id) DO UPDATE SET telegram_id = EXCLUDED.telegram_id`. Trigger language plpgsql, security definer, search_path=''. Idempotent via ON CONFLICT — solves `create_with_metrics` INSERT-only limitation by moving provisioning into the trigger. Application-layer `create_with_metrics` is NO LONGER called by signup_handler; the trigger owns provisioning.

**FR-5** — Step 5 in FR-4 above replaces the original "5-min JWT deep-link" design. The portal entry uses Supabase's PKCE token_hash mechanism (`action_link` from `admin.generate_link`), NOT a custom JWT. Supabase's own token_hash TTL applies (default 1 hour, configurable; minimum allowed by Supabase). On `/start` resend before wizard completion (FR-9), bot re-calls `admin.generate_link` to mint a fresh `action_link`. No custom JWT minting in BE.

**FR-6** — `/auth/confirm` route handler **PRESERVED** as Supabase PKCE token_hash exchange endpoint. Existing implementation post-PR #663 already does `verify_otp({ token_hash, type: 'email' })`. Spec 220 KEEPS this route. **Removed**: all autobind side-effect calls inside `/auth/confirm` (lines 141, 156, 230, 254, 270, 279, 284, 289, 296, 310 per blast-radius scan). Net `/auth/confirm` becomes a thin "exchange token_hash for session, redirect to /onboarding" handler (≤80 LOC vs current 330 LOC). Corrects the earlier brief's "delete /auth/confirm" claim (was incompatible with Supabase canonical magiclink-PKCE flow).

**FR-7** — Wizard mount (`/onboarding` page) validates `users.telegram_id IS NOT NULL` via a lightweight `GET /api/v1/user/me` call. If NULL (impossible state in Arch B), redirect to landing CTA with message "Please start via Telegram." This is a defensive guard, not a normal flow path.

**FR-8** — Middleware (`portal/src/middleware.ts`) enforces: if session has `app_metadata.onboarded != true`, any `/dashboard/*` request redirects to `/onboarding`. JWT claim check is the fast path; `public.users.onboarding_status` is the authoritative source used by the BE for pipeline gates.

**FR-9** — Bot's `/start` handler is the single signup entry. No coercion block (`telegram.py:577-618` deleted), no 6-char payload parsing, no late-bind code paths. `/start new` triggers OTP flow. `/start` with no payload or unknown payload → idempotent: if user is `authenticated_tg_bound` and not `onboarding_completed`, re-send portal link; if `onboarding_completed`, send "You're all set — chat below."

**FR-10** — DB migration drops `telegram_signup_sessions` and `telegram_link_codes` tables. Any FK constraints referencing these are dropped first. Migration is irreversible; safe because zero retained users.

**FR-11** — Wizard completion (`PATCH /api/v1/user/onboarding`) sets `public.users.onboarding_status='completed'` AND issues a Supabase Admin API call to set `app_metadata.onboarded=true` on the user's JWT claims. The JWT claim enables O(1) middleware enforcement without a DB round-trip per request.

**FR-12** — During migration deploy: all existing portal sessions are invalidated (Supabase session revocation via Admin API bulk logout, or `supabase_auth.refresh_tokens` truncation). Solo dev, zero retained users; safe bulldoze.

**FR-13** — ROADMAP updated: Spec 220 added as ACTIVE. Specs 215 (all sub-specs), 216-G, 216-H, 219-C1, 219-C4 marked SUPERSEDED with pointer to Spec 220. Superseded banners added to their respective spec.md files.

**FR-14** — No `[LLM-DEBUG]` log statements in any module. PII (email, telegram_id) must not appear in log format strings at INFO level or above. Debug-level logging of PII is permitted only if filtered by a `DEBUG_PII=true` env flag (default off).

**FR-15** — The 9 PII-leaking log lines at `telegram.py:604,620,639,653,669,675,682,694,695` are deleted or replaced with non-PII equivalents (e.g., log hashed telegram_id or user_id UUID only).

## State machine

4 architectural FSM states (in-code, not DB), each maps to a concrete observable on `auth.users` + `public.users`. The DB-column mapping resolves H-1 (state-↔-column ambiguity).

| Arch state | DB observable | Entry trigger | Guard | Exit trigger | Failure mode | Recovery |
|---|---|---|---|---|---|---|
| `anon` | No `auth.users` row for email; no `public.users` row for telegram_id | First visit to landing | None | Clicks TG CTA → `/start` in bot | — | — |
| `tg_otp_pending` | `auth.users` row exists with `email_confirmed_at IS NULL`; no `public.users` row | `signInWithOtp` called by bot after email collected | No existing `public.users` row for this `telegram_id` (else cross-account conflict, edge case 5) | `verifyOtp` succeeds → `email_confirmed_at=NOW()` | OTP expires (60 min Supabase default) | Bot prompts `/start` again, re-issues OTP |
| `authenticated_tg_bound` | `auth.users.email_confirmed_at IS NOT NULL`; `public.users` row with `telegram_id`; `onboarding_status IN ('pending','in_progress')`; `app_metadata.onboarded != true` | UPDATE trigger fires on `email_confirmed_at` transition; provisions `public.users` row | Trigger ON CONFLICT DO UPDATE succeeds | `onboarding_status='completed'` set via wizard PATCH | Trigger ROLLBACK on uniqueness violation | Bot: "account conflict — contact support" + auto-rollback; user retries with different email |
| `onboarding_completed` | `public.users.onboarding_status='completed'`; `auth.users.app_metadata.onboarded=true` | Wizard `PATCH /api/v1/user/onboarding` with valid `FinalForm` | All wizard slots valid per `FinalForm.model_validate()`; **SELECT FOR UPDATE on user row** to serialize concurrent tabs (H-3) | First chat turn fires pipeline | Wizard abandonment leaves `pending` | Bot re-sends portal magic-link on next `/start` |

**`onboarding_status` DB enum**: legacy values `pending`, `in_progress`, `completed`, `skipped` collapsed in Spec 220 to **`pending`** (no slots filled), **`in_progress`** (wizard mid-flight, some slots), **`completed`** (terminal). The legacy `skipped` value is **eliminated** — `message_handler.py:1070` admit-list shrinks to `('completed',)` only. Voice onboarding archive (Spec 028, archived in PR #662) was the sole producer of `skipped`; safe to retire. Migration to add CHECK constraint enforcing 3-value enum lives in PR 220-C.

**Concurrent wizard completion (H-3)**: `PATCH /api/v1/user/onboarding` uses `SELECT ... FOR UPDATE` on `public.users` row inside the transaction wrapping the FinalForm validation + status flip + Supabase admin app_metadata write. Second concurrent request blocks; on unlock either (a) row is already `completed` → returns 200 idempotent; (b) slots differ → second writer's slot payload discarded with 409 + log. Test: `test_concurrent_wizard_completion_serialized` in PR 220-E.

## Edge cases addressed

1. **TG bot offline** — Supabase OTP already issued; bot re-delivers on reconnect within 60-min window. Out of scope for this spec; same risk as current arch.
2. **User dismisses portal link** — Sends `/start` in TG again; FR-9 re-sends fresh JWT deep-link (new 5-min TTL).
3. **Concurrent OTP-verify (race)** — `create_with_metrics` is idempotent by `UNIQUE(telegram_id)` constraint. Second concurrent call gets `IntegrityError`, handled gracefully (FR-4). No ghost users.
4. **Different device for portal link** — JWT deep-link is device-agnostic: click on phone or desktop both work. Session established on whatever device clicks the link.
5. **Existing telegram_id conflict (cross-account)** — `IntegrityError` on `UNIQUE(telegram_id)`. Bot responds: "This Telegram account is already linked. Contact support." GH issue filed for post-launch admin tooling.
6. **Wizard abandonment + restart** — `onboarding_status='pending'`; FR-9 re-sends portal link on `/start`. Wizard resumes with saved slot state (existing wizard slot-persistence logic unchanged).
7. **Expired Supabase OTP (>60 min)** — `POST /auth/v1/otp` fails with `invalid_otp`. Bot: "That code expired. Send /start to get a new one." New OTP issued fresh.
8. **Long onboarding session (>60 min, but OTP already verified)** — JWT-authenticated session is valid per Supabase session TTL (independent of OTP TTL). Wizard can take as long as needed post-authentication.
9. **Network failure during `create_with_metrics`** — Supabase transaction rolls back; `auth.users` row may exist without `public.users` row. On next `/start`, bot re-attempts provisioning via idempotent `create_or_update_with_metrics` variant. `[NEEDS CLARIFICATION: confirm idempotent upsert is safe vs insert-only semantics in current `create_with_metrics`]`
10. **`/dashboard` access without onboarding** — FR-8 middleware redirects to `/onboarding`. No 401/403 flash.
11. **Voice session before onboarding** — Voice pipeline gate checks `onboarding_status='completed'` (`nikita/engine/constants.py`). Returns TG message: "Finish setup first — click the link I sent you."
12. **User changes email mid-flow** — N/A in Arch B: no email-based signup path. Email is optionally collected during the wizard for notification preferences only, not for authentication.
13. **Portal JWT deep-link replayed after 5-min TTL** — JWT `exp` check in `/onboarding` page server component rejects expired tokens. Redirects to landing with message "Link expired. Send /start in Telegram to get a new one."
14. **`/auth/confirm` URL from old magic-link bookmarks** — Route deleted; Vercel returns 404 → user sees landing page. Old bookmarks gracefully degrade.

## Implementation plan (5 PRs) — RE-ORDERED 2026-05-19 to fix rolling-deploy gap (H-4)

**New order: A (FE) → D (BE refactor) → E (tests + ROADMAP + middleware) → B (BE endpoint deletions) → C (migration AFTER 100% traffic).** Rationale: BE refactor (D) ships before migration (C) so the deployed binary on Cloud Run during rolling update never references dropped tables. Endpoint deletions (B) follow once new BE-D code is 100% on traffic and FE-A no longer calls them. Migration (C) is LAST after both BE and FE are clean.

**PR 220-A: Landing + auth-route tombstones + onboarding wizard PATCH idempotency (FE + thin BE shim)**
- `portal/src/app/(root)/page.tsx` — replace signup section with single "Start on Telegram" CTA → `t.me/Nikita_my_bot?start=new`
- `portal/src/app/(auth)/login/page.tsx` — 410 GONE response
- `portal/src/app/onboarding/auth/` — delete route directory (already 410 GONE post-PR #663)
- `portal/src/app/auth/bridge/route.ts` — delete
- `portal/src/app/auth/interstitial/` — delete directory
- `portal/src/app/auth/confirm/route.ts` — strip autobind side-effect blocks (lines 141,156,230,254,270,279,284,289,296,310 per blast-radius scan); keep PKCE token_hash exchange (~250 LOC deleted, ~80 retained)
- Remove stale toast keys from wizard page-client (if any remain post-#663 — grep returned 0 hits, verify in PR)
- `dashboard-empty-state.tsx` — remove `dashboard-bridge` call; replace with static "Open Telegram chat" CTA
- Target: ~600 lines diff (deletions dominate)

**PR 220-D: Atomic provisioning trigger + signup_handler.py rewrite + bot /start simplify (BE refactor)**
- New migration `supabase/migrations/YYYYMMDD_atomic_provision_trigger.sql` — creates `on_auth_user_email_confirmed` UPDATE trigger per FR-4b (ON CONFLICT DO UPDATE for idempotency)
- `signup_handler.py` rewrite: implement Flow A per FR-4 (signInWithOtp → verifyOtp → admin.update_user_by_id(app_metadata) → admin.generate_link(magiclink) → post action_link to TG); remove all FSM table reads/writes
- `telegram.py:577-618` — delete `_handle_start_with_payload` 6-char-code coercion block
- `_handle_start` — implement FR-9 idempotent logic (anon → OTP; in_progress → re-send action_link; completed → "You're all set")
- Remove 9 PII `[LLM-DEBUG]` log lines (`telegram.py:604,620,639,653,669,675,682,694,695`)
- `PATCH /api/v1/user/onboarding` — add `SELECT FOR UPDATE` serialization (H-3) + Supabase admin `app_metadata.onboarded=true` write
- **FSM table writes left as no-ops or deprecated stubs** — keep `telegram_signup_sessions` table read/write code present but never invoked, so rolling deploy doesn't crash on old binary. Concrete: delete CALL SITES, keep IMPORTS until PR 220-B. The dead-code window is bounded by PR 220-B landing within 1 day after PR 220-D 100% traffic.
- Target: ~400 lines diff

**PR 220-E: Tests + middleware + ROADMAP + supersede banners**
- `portal/src/middleware.ts` — strengthen onboarding-gate to use `app_metadata.onboarded` JWT claim (FR-8)
- Rewrite `tests/platforms/telegram/test_signup_handler.py` for Flow A (signInWithOtp + verifyOtp + admin API mocks)
- New test: `test_atomic_provision_trigger.sql` — pgTAP or Python SQL test confirming UPDATE trigger fires + ON CONFLICT DO UPDATE works for re-signup
- New test: `test_concurrent_wizard_completion_serialized` for SELECT FOR UPDATE (H-3)
- New test: assert `onboarding_status` admit-list shrunk from `('completed','skipped')` to `('completed',)` in `message_handler.py:1070`
- Wizard-mount guard test (FR-7)
- ROADMAP.md — Spec 220 ACTIVE; 215/216-G/216-H/219-C1/219-C4 SUPERSEDED
- Supersede banners in `specs/215-*/spec.md`, `specs/216-*/spec.md`, `specs/219-*/spec.md`
- Target: <400 lines diff

**PR 220-B: BE endpoint + repo deletions (AFTER 220-D is 100% on traffic)**
- Delete `/api/v1/auth/autobind-telegram` route + handler (`portal_auth.py:329-513`)
- Delete `/api/v1/auth/dashboard-bridge` route + handler (`portal_auth.py:517-616`)
- Delete `/api/v1/auth/magiclink/<telegram_user_id>` orphan (`portal_auth.py:174-295` — dead after 220-D)
- Delete `TelegramLinkRepository` + `TelegramSignupSessionRepository` + `PendingRegistrationRepository` files (3 repos)
- Delete `tasks.py:681-697` `cleanup_pending_registrations` cron endpoint + corresponding pg_cron job
- Remove all imports of dropped repos from `portal_auth.py`, `signup_handler.py`, `commands.py`, `telegram.py`
- Target: ~700 lines diff (pure deletions)

**PR 220-C: DB migration — drop FSM + link-code + pending_registrations tables (LAST, after 220-B 100% on traffic)**
- `supabase/migrations/YYYYMMDD_drop_legacy_signup_tables.sql` — DROP TABLE in FK-safe order: `telegram_link_codes`, `telegram_signup_sessions`, `pending_registrations`
- DROP the related cron job entry via `cron.unschedule(...)`
- AC-10/AC-11 grep verification ensures zero remaining references before this PR can deploy
- `public.users` schema untouched
- Target: ~80 lines diff

Each PR uses TDD (failing tests first). Pre-push gate per `.claude/rules/pr-workflow.md`: `uv run pytest -q` + `(cd portal && npm run test -- --run && npm run lint && npm run build)`. **Between 220-D and 220-B**: wait for Cloud Run revision serving 100% traffic + verify zero invocations of deprecated endpoints in `gcloud logging read` for ≥30 min before merging 220-B. Same gate between 220-B and 220-C.

## Acceptance criteria

**AC-1** — Landing page (`/`) has exactly one signup path: "Start on Telegram" deep-link CTA. No email form, no `/login` link. Verified by: DOM assertion in Playwright test; `rg "signUp|signIn|email.*input" portal/src/app/\(root\)/page.tsx` returns 0 matches.

**AC-2** — `/login`, `/auth/confirm`, `/onboarding/auth`, `/api/v1/auth/autobind-telegram`, `/api/v1/auth/dashboard-bridge` all return 410 GONE (or 404 for deleted FE routes). Verified by: `curl -sI https://nikita-mygirl.com/login | grep HTTP` → 410.

**AC-3** — After OTP-verify in TG, `SELECT telegram_id FROM public.users WHERE id = $auth_uid` returns the user's Telegram ID. Verified by: unit test on `signup_handler.py` OTP-verify path + Supabase MCP `execute_sql` in live walk.

**AC-4** — After OTP-verify, bot delivers a message containing `https://nikita-mygirl.com/onboarding?token=` within 3 seconds. JWT is valid for 5 minutes. Verified by: unit test mocking Supabase Admin JWT sign; live walk step 5 (Telegram MCP `get_history`).

**AC-5** — Wizard `/onboarding` page server component rejects requests with no valid session or expired JWT deep-link token. Redirects to landing. Verified by: `curl -sI https://nikita-mygirl.com/onboarding` (no session) → redirect to `/`.

**AC-6** — Wizard completion (`PATCH /api/v1/user/onboarding`) sets `onboarding_status='completed'` in `public.users` AND `app_metadata.onboarded=true` in Supabase auth metadata. Verified by: unit test on completion endpoint + Supabase MCP `execute_sql` `SELECT raw_app_meta_data FROM auth.users WHERE id = $uid`.

**AC-7** — First Telegram message after onboarding completion passes through all 11 pipeline stages with no `STAGE_SKIP` or error. Verified by: `gcloud logging read` after live walk first-chat turn; all stage names present in structured log.

**AC-8** — TG bot rejects free-text from `telegram_id` with no bound `public.users` row. Bot responds: "Send /start to begin." Verified by: unit test with mock `telegram_id` not in `public.users`.

**AC-9** — Authenticated user with `onboarding_status='pending'` navigating to `/dashboard` is redirected to `/onboarding`. Verified by: Playwright test with mocked JWT lacking `app_metadata.onboarded`.

**AC-10** — `telegram_signup_sessions` and `telegram_link_codes` tables do not exist in the DB post-migration. Verified by: Supabase MCP `list_tables` returns neither name; `rg "telegram_signup_session\|telegram_link_code" nikita/ --type py` returns 0 matches.

**AC-11** — No Python file in `nikita/` references `autobind`, `dashboard_bridge`, `link_code`, or `TelegramLinkRepository`. Verified by: `rg "autobind|dashboard.bridge|link.code|TelegramLinkRepository" nikita/ --type py` returns 0 matches post-PR 220-B.

**AC-12** — Live walk: TG-first signup → onboarding wizard → first chat turn completes in ≤12 manual user steps end-to-end. Steps: (1) land on nikita-mygirl.com, (2) click TG CTA, (3) open Nikita bot, (4) send /start, (5) bot prompts for email, (6) user types email in TG, (7) user opens email client, copies 6-digit OTP, returns to TG, (8) user pastes OTP in TG, (9) bot delivers portal `action_link` in TG, (10) user clicks link → /auth/confirm exchanges token_hash → /onboarding opens with valid session, (11) complete wizard (counted as 1 step), (12) arrive at dashboard with "Open chat" CTA → send first message via TG → Nikita replies (full pipeline). Verified by: walk report in `docs-to-process/YYYYMMDD-walk-spec220-final.md`. NOTE: TG remains the chat surface (decision locked 2026-05-19); portal shows dashboard observability only.

**AC-15** — `on_auth_user_email_confirmed` UPDATE trigger fires on email confirmation, INSERT-OR-UPDATE `public.users(id, telegram_id)`. Verified by: pgTAP test in PR 220-D migration; Supabase MCP `execute_sql` SELECT after live walk step 8 confirms row appearance.

**AC-16** — `app_metadata.telegram_id` and `app_metadata.onboarded` set on `auth.users` post-verifyOtp and post-wizard-completion respectively. Verified by: Supabase MCP `execute_sql` `SELECT raw_app_meta_data FROM auth.users WHERE id = $uid` returns both keys.

**AC-17** — Concurrent wizard completion serialized: 2 simultaneous `PATCH /api/v1/user/onboarding` requests return (a) first → 200 with new state, (b) second → 200 idempotent or 409 with last-writer-loses semantics. No data corruption. Verified by: integration test with `asyncio.gather` of 2 PATCH calls.

**AC-18** — `onboarding_status` admit-list shrunk: `message_handler.py:1070` rejects `skipped` state. Verified by: unit test asserting `'skipped'` produces TG message "Finish setup first."

**AC-13** — `rg "\[LLM-DEBUG\]" nikita/platforms/telegram/telegram.py` returns 0 matches post-PR 220-D.

**AC-14** — No `email` or `telegram_id` literal values appear in INFO-level log output during a live walk (verified by `gcloud logging read` grep for `simon.yang` and any `7\d{8,}` telegram_id pattern).

## Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Portal SEO or ad-links that bypass Telegram | Low | Medium | User has accepted this trade-off ("no portal-first signup needed"). Out of scope. |
| Telegram down during signup | Low | High | Out of scope; same risk as current arch. Mitigation: future queued retry on OTP resend. |
| Migration breaks in-flight sessions | N/A | N/A | Zero retained users. Truncate `auth.users` + `public.users` pre-deploy. Safe bulldoze. |
| JWT deep-link TTL too short — user misses it | Medium | Medium | 5-min TTL + `/start` re-send (FR-9). Bot copy: "Link expires in 5 minutes. Tap it now or send /start for a new one." |
| `create_with_metrics` not truly idempotent on network retry | RESOLVED | RESOLVED | Provisioning moved into `on_auth_user_email_confirmed` UPDATE trigger with `ON CONFLICT (id) DO UPDATE` (FR-4b). Application-layer `create_with_metrics` no longer called in signup path. Idempotent by construction. |
| Email-OTP user-modifiable via `auth.updateUser({data:...})` | High | High | `telegram_id` is **read** from `app_metadata` (immutable, admin-only writable) at all RLS / pipeline gate checkpoints. `user_metadata` value is only used by the trigger at email-confirm time, after which `public.users.telegram_id` becomes authoritative. Compensating `admin.update_user_by_id(app_metadata=...)` write in step 4 of FR-4 locks the binding. |
| Cross-account telegram_id (user re-signs up with different email but same TG ID) | Medium | Medium | Trigger ON CONFLICT routes to UPDATE → `public.users.telegram_id = NEW.telegram_id`. Old account remains accessible via the old email if user still has it. Acceptable for solo-dev MVP; admin tool to merge accounts tracked as post-launch backlog. |
| Trigger function raises exception (e.g., FK violation) and rolls back auth.users INSERT | Low | High | ON CONFLICT DO UPDATE eliminates the most common failure (duplicate id). Wrap trigger body in `BEGIN ... EXCEPTION WHEN OTHERS THEN RAISE WARNING ...; END` for non-critical paths. AC: pgTAP test confirms trigger gracefully handles a representative failure (mocked FK violation). |
| Rolling Cloud Run deploy: 220-C migration runs while 220-D BE not yet 100% (H-4) | RESOLVED | RESOLVED | Re-ordered to A → D → E → B → C. 220-D dead-code FSM writes remain present as deprecated stubs until 220-B; migration is LAST, after both BE and FE are clean and ≥30 min of zero-invocation logs confirm safety. |
| `/auth/confirm` deletion breaks Supabase PKCE magic-link flow (M-2) | RESOLVED | RESOLVED | `/auth/confirm` PRESERVED in Spec 220 as canonical PKCE `token_hash` exchange handler (revised FR-6). Only autobind side-effects removed. |
| Concurrent wizard PATCH (two tabs) overwrites slot data (H-3) | RESOLVED | RESOLVED | `SELECT FOR UPDATE` on `public.users` row + idempotent fast-path for already-`completed` state. Test in PR 220-E. |
| Supabase Admin API call for `app_metadata` update fails silently | Low | Medium | Wrap in explicit error check; log ERROR + alert on failure. Middleware falls back to `public.users.onboarding_status` DB check if JWT claim missing. |
| Old `/auth/confirm` magic-link emails in user inboxes (pre-migration) | Low | Low | Zero users in prod. Post-launch: graceful 404 → landing page redirect. |

## Cross-references

- Source audits embedded above: flow audit (5 🔴 critical: `telegram.py:577-618`, `portal_auth.py:425-428`, `page-client.tsx:41-66`, `telegram.py:604,620,639,653,669,675,682,694,695`), external research (Supabase trigger pattern, autobind industry practice), Arch B brainstorm (3.87/5, 5-PR plan)
- Brainstorm: 4-arch × 6-dim × 3-persona panel (session 2026-05-18)
- Spec 219 plan: `docs-to-process/20260518-plan-spec219-telegram-late-bind.md` (symptoms patched by 219 that this spec eliminates at root)
- **2026-05-19 research swarm** (this revision): 3 parallel subagents (codebase blast-radius `a9b846db29117f397`, Supabase atomic-flow research `a775faa07bd2870fd`, devils-advocate `af2ca68b60787369a`) surfaced 2 CRITICAL + 4 HIGH gaps. Plus Supabase-flow scoring research `ab81f3e4e672abe1f` ranked 4 candidate flows; Flow A (signInWithOtp + 6-digit OTP paste in TG + admin.generate_link magiclink) won 24/30 on 6 axes. All findings folded into FR-4/FR-4b/FR-5/FR-6, state-machine DB mapping, PR ordering, AC-15..18, and risks table updates.

## Architectural Decision Log (locked 2026-05-19)

- **ADR-220-1**: OTP delivery channel = Flow A (Standard `signInWithOtp` + email-OTP paste in TG). Rationale: highest Supabase-best-practice alignment (5/5), zero Edge Functions for MVP, fully recoverable. Hook-based in-channel OTP (Flow B) deferred to Phase 2 if UX testing shows email context-switch friction. User-locked.
- **ADR-220-2**: First chat surface = Telegram only. Rationale: matches existing pipeline entry (`message_handler.py`), zero new code, single entry point. Portal stays observability-focused. User-locked.
- **ADR-220-3**: PR sequence = A → D → E → B → C. Rationale: BE refactor before migration prevents rolling-deploy gap; endpoint deletions wait for 100% traffic flip on new BE; migration last. User-locked.
- **ADR-220-4**: Provisioning via DB trigger on `auth.users UPDATE` (conditional on `email_confirmed_at NULL→NOT NULL`) with `ON CONFLICT DO UPDATE`. Application-layer `create_with_metrics` removed from signup path. Resolves C-1 idempotency. Research-derived.
- **ADR-220-5**: `telegram_id` immutable source-of-truth = `auth.users.app_metadata` (admin-API writable only). RLS and middleware never read `user_metadata`. Research-derived security pattern.
- **ADR-220-6**: `/auth/confirm` PRESERVED as PKCE token_hash exchange handler. Only autobind side-effects stripped. Contradicts original brief FR-6 deletion. Research-derived.
- **ADR-220-7**: `onboarding_status` enum collapsed from 4 → 3 values (`pending`, `in_progress`, `completed`). `skipped` retired alongside Spec 028 voice onboarding archive. CHECK constraint added in PR 220-C.
- Supersedes: Spec 215 (all sub-specs), Spec 216-G, Spec 216-H, Spec 219-C1, Spec 219-C4
- Related: Spec 218 (chat session isolation — downstream pipeline unchanged by this spec)
- Test precedents: `.claude/rules/testing.md` Agentic-Flow Test Requirements; `.claude/rules/pr-workflow.md` Pre-Push Test Gate
- Live walk protocol: `.claude/rules/live-testing-protocol.md` (12-step walk; use `simon.yang.ch+walk220@gmail.com` for test account)
