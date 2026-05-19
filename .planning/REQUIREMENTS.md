---
title: Project Requirements
lifecycle: living
last_updated: 2026-05-19
---

# REQUIREMENTS.md — Nikita Project Requirements

## Source of truth

This file is a summary index. The canonical requirements for Phase 01 (Spec 220 canonical TG-first signup) live in `.planning/phases/01-canonical-tg-first-signup/01-SPEC.md` (FR-1..FR-15, AC-1..AC-18). When REQ entries here drift from 01-SPEC.md, **01-SPEC.md wins**. Future REQ-NNN entries for new phases should reference the corresponding phase SPEC.md file.

## Phase 01: Canonical Telegram-First Signup (Spec 220)

Source: `docs-to-process/20260518-spec220-canonical-tg-first.md` (locked 2026-05-19)

### Functional Requirements

| REQ | Description | Phase 01 AC | GH Issue |
|---|---|---|---|
| REQ-001 | Landing page has single signup CTA: "Start on Telegram" deep-link to `t.me/Nikita_my_bot?start=new`. No email form, no /login button. | AC-1 | — |
| REQ-002 | `/login` route returns 410 GONE. Existing inbound links redirect to landing page. | AC-2 | — |
| REQ-003 | `/onboarding/auth` route file deleted entirely (not just 410, full deletion). | AC-2 | — |
| REQ-004 | OTP signup flow (Flow A): bot collects email → `signInWithOtp` → user pastes OTP in TG → `verifyOtp` → atomic provisioning trigger → `admin.update_user_by_id(app_metadata)` → `admin.generate_link(magiclink)` → action_link posted to TG. | AC-3, AC-4, AC-15 | — |
| REQ-004b | DB UPDATE trigger `on_auth_user_email_confirmed` provisions `public.users(id, telegram_id)` atomically on `email_confirmed_at NULL→NOT NULL`. Idempotent via `ON CONFLICT DO UPDATE`. | AC-15 | — |
| REQ-005 | Portal entry via Supabase PKCE `action_link` from `admin.generate_link`, NOT custom JWT. `/auth/confirm` preserved as PKCE token_hash exchange handler. | AC-4 | — |
| REQ-006 | `/auth/confirm` route preserved; autobind side-effect blocks removed (lines 141,156,230,254,270,279,284,289,296,310). Net: ≤80 LOC thin PKCE handler. | AC-2 | — |
| REQ-007 | Wizard mount (`/onboarding`) validates `users.telegram_id IS NOT NULL` via `GET /api/v1/user/me`. Null state redirects to landing CTA. Defensive guard only. | AC-5 | — |
| REQ-008 | Middleware (`portal/src/middleware.ts`) enforces `app_metadata.onboarded != true` → redirect to `/onboarding` for all `/dashboard/*` routes. | AC-9 | — |
| REQ-009 | Bot `/start` handler is single signup entry. No coercion block, no 6-char payload parsing, no late-bind. `/start new` → OTP flow; `/start` with no/unknown payload → idempotent re-send if in_progress; completed → "You're all set." | AC-8 | — |
| REQ-010 | DB migration drops `telegram_signup_sessions` and `telegram_link_codes` tables (FK-safe order). Zero retained users; safe bulldoze. | AC-10 | — |
| REQ-011 | Wizard completion `PATCH /api/v1/user/onboarding` sets `onboarding_status='completed'` AND `app_metadata.onboarded=true`. SELECT FOR UPDATE serializes concurrent requests. | AC-6, AC-17 | — |
| REQ-012 | All existing portal sessions invalidated during migration deploy (`refresh_tokens` truncation or Admin API bulk logout). | — | — |
| REQ-013 | ROADMAP updated: Spec 220 ACTIVE; Specs 215, 216-G, 216-H, 219-C1, 219-C4 SUPERSEDED with pointer. | — | — |
| REQ-014 | No `[LLM-DEBUG]` log statements in any module. PII not in INFO-level logs. | AC-13, AC-14 | — |
| REQ-015 | 9 PII-leaking log lines at `telegram.py:604,620,639,653,669,675,682,694,695` deleted or replaced with non-PII equivalents. | AC-13 | — |
| REQ-020 | `onboarding_status` enum collapsed to 3 values: `pending`, `in_progress`, `completed`. `skipped` retired. CHECK constraint in migration. | AC-18 | — |
| REQ-021 | `message_handler.py:1070` admit-list shrunk from `('completed','skipped')` to `('completed',)` only. | AC-18 | — |

### Known Defects (pre-migration carry-forward, not Phase 01 scope)

| REQ | Description | Severity | GH Issue |
|---|---|---|---|
| REQ-D01 | Wizard LLM bounce prefix leak — model response prefix appears in UI | Medium | GH #664 |
| REQ-D02 | Dashboard "Couldn't set up connection" banner post-onboarding | Medium | GH #665 |
| REQ-D03 | kill-skip code-debt: delete `nikita/agents/text/skip.py` + `skip_rates_enabled` flag (Spec 210A kill-half) | Low | GH #470 |

### Phase 01 Acceptance Criteria Traceability

| AC | REQ(s) | Description |
|---|---|---|
| AC-1 | REQ-001 | Landing page single CTA, no email form, no /login link |
| AC-2 | REQ-002, REQ-003, REQ-006 | /login, /auth/confirm, /onboarding/auth, autobind, dashboard-bridge → 410/404 |
| AC-3 | REQ-004, REQ-004b | Post-OTP-verify: `public.users.telegram_id` populated |
| AC-4 | REQ-004, REQ-005 | Bot delivers portal action_link within 3s of OTP-verify |
| AC-5 | REQ-007 | Wizard rejects unauthenticated or expired token; redirects to landing |
| AC-6 | REQ-011 | Wizard completion sets onboarding_status + app_metadata.onboarded |
| AC-7 | REQ-011 | First TG message post-onboarding passes all 11 pipeline stages |
| AC-8 | REQ-009 | Bot rejects free-text from unbound telegram_id |
| AC-9 | REQ-008 | Middleware redirects pending user from /dashboard to /onboarding |
| AC-10 | REQ-010 | FSM + link-code tables dropped; no Python references remain |
| AC-11 | REQ-010 | No autobind/dashboard_bridge/link_code/TelegramLinkRepository refs in `nikita/` |
| AC-12 | REQ-001..REQ-021 | Live walk: TG-first signup → wizard → first chat ≤12 manual steps |
| AC-13 | REQ-014, REQ-015 | Zero `[LLM-DEBUG]` in telegram.py |
| AC-14 | REQ-014 | No PII in INFO-level logs during live walk |
| AC-15 | REQ-004b | Provisioning trigger fires on email_confirmed_at transition |
| AC-16 | REQ-004 | `app_metadata.telegram_id` + `app_metadata.onboarded` set post-verify + post-wizard |
| AC-17 | REQ-011 | Concurrent wizard PATCH serialized (SELECT FOR UPDATE) |
| AC-18 | REQ-020, REQ-021 | `onboarding_status` 3-value enum; `skipped` rejected |
