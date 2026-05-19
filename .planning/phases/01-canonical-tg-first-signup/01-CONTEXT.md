---
phase: "01"
name: canonical-tg-first-signup
lifecycle: living
imported_from: docs-to-process/20260518-spec220-canonical-tg-first.md
created: 2026-05-19
---

# Phase 01 — CONTEXT: Canonical Telegram-First Signup

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
| `/auth/confirm` autobind side-effects (NOT the route itself) | `portal/src/app/auth/confirm/route.ts` autobind blocks | Route PRESERVED as PKCE handler; autobind calls removed |
| `pending_registrations` table + repo + cron job | `nikita/db/repositories/pending_registration_repository.py` | Obsolete alongside `telegram_signup_sessions` |
| `TelegramSignupSessionRepository` file | `nikita/db/repositories/telegram_signup_session_repository.py` | Orphan after all callers removed |
| `generate_magiclink_for_telegram_user` endpoint | `nikita/api/routes/portal_auth.py:174-295` (~122 LOC) | Dead after signup_handler uses `admin.generate_link` inline |
| `/auth/bridge` route | `portal/src/app/auth/bridge/route.ts` (67 LOC) | Bridge token obsolete when `/auth/confirm` is canonical PKCE handler |
| `/auth/interstitial` page | `portal/src/app/auth/interstitial/` | Purpose-eliminated when dashboard_bridge is gone |
| 9 `[LLM-DEBUG]` log statements | `telegram.py:604,620,639,653,669,675,682,694,695` | PII (email+telegram_id plaintext) |
| `telegram_bind_failed` toast key | `portal/src/app/onboarding/page-client.tsx:41-66` | Route never sends this key; stale dead code |

### What's preserved

- `auth.users` + `auth.identities` — Supabase canonical auth; untouched
- `public.users` schema — untouched
- `create_with_metrics` — single provisioner; called atomically at OTP-verify
- `/onboarding` wizard — FE flow unchanged; wizard reads cumulative slots from BE
- Voice + Telegram downstream pipelines — gated on `onboarding_status='completed'`; no change
- Middleware onboarding-gate (`portal/src/middleware.ts`) — strengthened with JWT claim check

## State Machine

4 FSM states (in-code, not DB), each mapped to DB observables.

| Arch state | DB observable | Entry trigger | Exit trigger |
|---|---|---|---|
| `anon` | No `auth.users` row | First visit to landing | Clicks TG CTA |
| `tg_otp_pending` | `auth.users` with `email_confirmed_at IS NULL` | `signInWithOtp` called by bot | `verifyOtp` succeeds |
| `authenticated_tg_bound` | `auth.users.email_confirmed_at IS NOT NULL`; `public.users` row with `telegram_id`; `onboarding_status IN ('pending','in_progress')` | UPDATE trigger fires on email_confirmed_at transition | `onboarding_status='completed'` via wizard PATCH |
| `onboarding_completed` | `public.users.onboarding_status='completed'`; `app_metadata.onboarded=true` | Wizard PATCH with valid FinalForm | First chat turn fires pipeline |

`onboarding_status` enum collapsed from 4 → 3 values: `pending`, `in_progress`, `completed`. `skipped` retired alongside Spec 028 voice onboarding archive.

## Implementation Plan (5 PRs — Re-ordered 2026-05-19 for rolling-deploy safety)

**Order: A (FE) → D (BE refactor) → E (tests + ROADMAP + middleware) → B (BE endpoint deletions) → C (migration LAST)**

Rationale: BE refactor (D) ships before migration (C) so the deployed binary never references dropped tables. Endpoint deletions (B) follow once new BE-D code is 100% on traffic. Migration (C) is last after both BE and FE are clean.

| PR | Scope | Target diff |
|---|---|---|
| 220-A | Landing + auth-route tombstones + onboarding wizard PATCH idempotency (FE + thin BE shim) | ~600 lines (deletions dominate) |
| 220-D | Atomic provisioning trigger + signup_handler.py rewrite + bot /start simplify (BE refactor) | ~400 lines |
| 220-E | Tests + middleware + ROADMAP + supersede banners | <400 lines |
| 220-B | BE endpoint + repo deletions (AFTER 220-D 100% on traffic) | ~700 lines (pure deletions) |
| 220-C | DB migration — drop FSM + link-code + pending_registrations tables (LAST) | ~80 lines |

## Architectural Decision Log (locked 2026-05-19)

- **ADR-220-1**: OTP delivery channel = Flow A (`signInWithOtp` + 6-digit OTP paste in TG). Highest Supabase-best-practice alignment (5/5), zero Edge Functions for MVP, fully recoverable. User-locked.
- **ADR-220-2**: First chat surface = Telegram only. Portal stays observability-focused. User-locked.
- **ADR-220-3**: PR sequence = A → D → E → B → C. BE refactor before migration prevents rolling-deploy gap. User-locked.
- **ADR-220-4**: Provisioning via DB trigger on `auth.users UPDATE` (conditional on `email_confirmed_at NULL→NOT NULL`) with `ON CONFLICT DO UPDATE`. Application-layer `create_with_metrics` removed from signup path. Research-derived.
- **ADR-220-5**: `telegram_id` immutable source-of-truth = `auth.users.app_metadata` (admin-API writable only). RLS and middleware never read `user_metadata`. Research-derived security pattern.
- **ADR-220-6**: `/auth/confirm` PRESERVED as PKCE token_hash exchange handler. Only autobind side-effects stripped. Contradicts original brief FR-6 deletion. Research-derived.
- **ADR-220-7**: `onboarding_status` enum collapsed from 4 → 3 values. `skipped` retired. CHECK constraint in PR 220-C.

## Risks and Mitigations (high-priority only)

| Risk | Mitigation |
|---|---|
| Email-OTP `telegram_id` modifiable via `auth.updateUser({data:...})` | `telegram_id` read from `app_metadata` (admin-only writable) at all RLS/pipeline checkpoints. Compensating `admin.update_user_by_id(app_metadata=...)` write in FR-4 step 4 locks the binding. |
| Rolling Cloud Run deploy gap: 220-C migration runs while 220-D not yet 100% | RESOLVED by re-ordering: A → D → E → B → C. 220-D dead-code FSM writes remain as deprecated stubs until 220-B; migration is last after ≥30 min zero-invocation log confirmation. |
| `/auth/confirm` deletion breaks Supabase PKCE flow | RESOLVED: `/auth/confirm` PRESERVED (revised FR-6). Only autobind side-effects removed. |
| Concurrent wizard PATCH (two tabs) | RESOLVED: `SELECT FOR UPDATE` on `public.users` row + idempotent fast-path for already-`completed` state. |

## Research Sources

- Supabase-flow scoring research: 4 candidate flows, Flow A scored 24/30 on 6 axes (session 2026-05-19)
- Arch B brainstorm: 4-arch × 6-dim × 3-persona panel, Arch B scored 3.87/5 (session 2026-05-18)
- Codebase blast-radius audit: subagent `a9b846db29117f397` (2026-05-19)
- Supabase atomic-flow research: subagent `a775faa07bd2870fd` (2026-05-19)
- Devils-advocate review: subagent `af2ca68b60787369a` (2026-05-19)
