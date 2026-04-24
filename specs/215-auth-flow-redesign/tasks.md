# Tasks: Spec 215 — Auth Flow Redesign (Telegram-First Signup)

**Generated**: 2026-04-24
**Feature**: 215-auth-flow-redesign
**Input**: `specs/215-auth-flow-redesign/{spec.md, plan.md}`
**Branch**: `feat/215-telegram-first-signup` (PR-F1a kickoff); per-PR sub-branches per `plan.md` §4
**Feature flag**: `NEXT_PUBLIC_TELEGRAM_FIRST_SIGNUP=true`

**Organization**: Tasks are grouped by PR (per plan.md §4) since the spec has a single product story (Telegram-first signup) but ships in 5 sequential PRs for blast-radius control. Each PR is treated as an independently testable phase.

**Test-First (Article III)**: All implementation tasks have ≥2 testable ACs. Write tests FIRST, watch them FAIL, then implement. RED commit + GREEN commit minimum per task.

**Subagent dispatch**: All subagent dispatches MUST include `HARD CAP: <N> tool calls` + scope + exit criterion per `.claude/rules/parallel-agents.md`.

---

## Format: `[ID] [P?] [Phase] Description`

- **[ID]**: T001, T002, ...
- **[P]**: Parallelizable (different files, no dependency)
- **[Phase]**: PR-F1a / PR-F1b / PR-F2a / PR-F2b / PR-F3 / W1
- **Each task**: 2+ ACs, TDD pair, file paths, dependencies, FR/AC mapping

---

## Phase 1: Setup (Branch + Feature Flag)

- [ ] **T001** [PR-F1a] Create branch `feat/215-pr-f1a-data-layer` from master + record baseline test counts
  - **AC-1**: `git branch --show-current` returns `feat/215-pr-f1a-data-layer`
  - **AC-2**: `uv run pytest -q --co | tail -1` baseline recorded in PR body
  - **Files**: branch only
  - **Estimate**: S (15 min)

- [ ] **T002** [PR-F2b] Add `NEXT_PUBLIC_TELEGRAM_FIRST_SIGNUP` to Vercel env (preview + production, value `false` initially)
  - **AC-1**: `vercel env ls` shows the var on both envs with `false`
  - **AC-2**: env var read by middleware + landing components (verified in T024)
  - **Files**: Vercel env (no repo change)
  - **Estimate**: S (10 min); deferred to PR-F2b kickoff

---

## Phase 2: Foundational — PR-F1a Data Layer + Admin Endpoint Contract

**Per plan.md §4 PR-F1a. Estimate: ~300 LOC, 6-8 hours.**

**Intelligence queries** (run once at PR-F1a start):
```bash
bash .claude/skills/project-intel/scripts/graph-ops.sh briefing nikita/db/models/pending_registration.py
bash .claude/skills/project-intel/scripts/graph-ops.sh briefing nikita/api/routes/portal_auth.py
bash .claude/skills/project-intel/scripts/graph-ops.sh search "pending_registration"
```

### Tests for PR-F1a ⚠️ WRITE FIRST

- [ ] **T003** [P] [PR-F1a] RED: `tests/db/repositories/test_telegram_signup_session_repository.py` — atomic CAS transitions per spec §7.2.1
  - **AC-1**: AWAITING_EMAIL → CODE_SENT CAS update returns 0 rows when prior state mismatch (concurrent worker race)
  - **AC-2**: CODE_SENT → MAGIC_LINK_SENT CAS update returns 0 rows when expired (`now() > expires_at`)
  - **AC-3**: MAGIC_LINK_SENT → COMPLETED is idempotent (re-tap returns 0 rows; no error)
  - **Mapped FR/AC**: §7.2.1, AC-3.2, AC-5.5
  - **Verify FAIL**: `uv run pytest tests/db/repositories/test_telegram_signup_session_repository.py -v` shows RED
  - **Estimate**: M (2hr)

- [ ] **T004** [P] [PR-F1a] RED: `tests/api/routes/test_portal_auth_generate_magiclink.py` — admin endpoint contract per spec §7.6 + Testing H2
  - **AC-1**: end-user JWT returns 401 (service-role guard)
  - **AC-2**: valid service-role call returns Pydantic `GenerateMagiclinkResponse` with `verification_type` from Supabase response (no hardcoded literal)
  - **AC-3**: static-grep fixture asserts no `'magiclink'`/`'signup'` literal in handler source outside `Literal[...]` annotation
  - **Mapped FR/AC**: FR-5, AC-5.1, AC-5.2, Testing H2, §7.6
  - **Verify FAIL**: pytest RED
  - **Estimate**: M (2hr)

- [ ] **T005** [P] [PR-F1a] RED: `tests/monitoring/test_signup_funnel_events.py` — 9 Pydantic event models per Testing H5
  - **AC-1**: every emitter call uses named Pydantic model (not free-form dict) — assert-via-mock
  - **AC-2**: `model_dump_json()` round-trip emits no PII fields (no raw `email`, `telegram_id`, `phone`, `name`); only `*_hash` derivatives
  - **AC-3**: anti-pattern grep gate (`test_no_raw_pii_in_emitter_calls`) returns empty
  - **Mapped FR/AC**: FR-Telemetry-1, Testing H5
  - **Verify FAIL**: pytest RED
  - **Estimate**: M (2hr)

### Implementation for PR-F1a

- [ ] **T006** [PR-F1a] GREEN: Migration `<NNN>_rename_pending_registrations_to_telegram_signup_sessions.sql` per spec §9.1
  - **AC-1**: RENAME table + RENAME `otp_state` → `signup_state` + RENAME `otp_attempts` → `attempts` (data-layer H2)
  - **AC-2**: ADD COLUMNs (`magic_link_token`, `magic_link_sent_at`, `verification_type`, `last_attempt_at`)
  - **AC-3**: `chat_id` column verbatim retained (data-layer H1; FR-11c routing dependency)
  - **AC-4**: ENABLE RLS + service-role-only policy (per `.claude/rules/testing.md` DB Migration Checklist)
  - **AC-5**: Migration applied to local Supabase + verified via `mcp__supabase__list_tables`
  - **Files**: `supabase/migrations/<NNN>_*.sql`
  - **Dependencies**: T003
  - **Estimate**: M (2hr)

- [ ] **T007** [P] [PR-F1a] GREEN: Migration `<NNN>_add_preferred_call_window_to_user_profiles.sql` (FR-12)
  - **AC-1**: `ALTER TABLE user_profiles ADD COLUMN preferred_call_window text NULL`
  - **AC-2**: Migration is idempotent (`IF NOT EXISTS`); applied + verified
  - **Files**: `supabase/migrations/<NNN>_*.sql`
  - **Estimate**: S (30 min)

- [ ] **T008** [PR-F1a] GREEN: Rename + extend ORM model `nikita/db/models/telegram_signup_session.py` (was `pending_registration.py`)
  - **AC-1**: `signup_state` enum constrained to `{awaiting_email, code_sent, magic_link_sent, completed}`
  - **AC-2**: `verification_type` typed as `Literal["email","signup","magiclink","recovery"]`
  - **AC-3**: existing imports of `PendingRegistration` updated repo-wide; `git grep "PendingRegistration"` returns only the new alias or zero
  - **Files**: rename `pending_registration.py` → `telegram_signup_session.py`; update callers
  - **Dependencies**: T006
  - **Estimate**: M (2hr)

- [ ] **T009** [PR-F1a] GREEN: Repository `nikita/db/repositories/telegram_signup_session_repository.py` with CAS helpers
  - **AC-1**: `transition_to_code_sent(telegram_id, email)` returns `id` or raises `ConcurrentTransitionError`
  - **AC-2**: `transition_to_magic_link_sent(telegram_id, hashed_token, verification_type)` returns `id` or raises `ExpiredOrConcurrentError`
  - **AC-3**: `delete_on_completion(telegram_id)` is idempotent (returns count; no exception on 0)
  - **AC-4**: `increment_attempts(telegram_id)` returns new attempts count atomically
  - **Files**: `nikita/db/repositories/telegram_signup_session_repository.py`
  - **Dependencies**: T003, T008
  - **Estimate**: L (4hr)
  - **Verify GREEN**: T003 tests pass

- [ ] **T010** [P] [PR-F1a] GREEN: 9 telemetry event Pydantic models in `nikita/monitoring/events.py`
  - **AC-1**: All 9 models from spec §8.7 Testing H5 table exist as Pydantic v2 classes with required fields
  - **AC-2**: `email_hash` / `telegram_id_hash` helpers return `sha256(...)[:12]`
  - **AC-3**: emitter helpers (one per event) accept the Pydantic model and call structured logger
  - **Files**: `nikita/monitoring/events.py`
  - **Dependencies**: T005
  - **Estimate**: M (2hr)
  - **Verify GREEN**: T005 tests pass

- [ ] **T011** [PR-F1a] GREEN: Admin endpoint `nikita/api/routes/portal_auth.py::generate_magiclink_for_telegram_user` per spec §7.6
  - **AC-1**: Pydantic `GenerateMagiclinkRequest` + `GenerateMagiclinkResponse` declared
  - **AC-2**: service-role guard rejects end-user JWT with 401
  - **AC-3**: handler calls `client.auth.admin.generate_link({type:"magiclink", email, options:{redirect_to}})` and persists `hashed_token` + `verification_type` via T009 repo
  - **AC-4**: response `verification_type` is from Supabase response verbatim (no normalization)
  - **AC-5**: handler emits `signup_magic_link_minted` telemetry event (T010)
  - **Files**: `nikita/api/routes/portal_auth.py`
  - **Dependencies**: T004, T009, T010
  - **Estimate**: L (4hr)
  - **Verify GREEN**: T004 tests pass

### Verification for PR-F1a

- [ ] **T012** [PR-F1a] Run pre-PR grep gates per `.claude/rules/testing.md`: zero-assertion shells, PII format strings, raw cache_key
  - **AC-1**: All 3 grep commands return empty
  - **AC-2**: Output recorded in PR body under `## Pre-PR grep gates`

- [ ] **T013** [PR-F1a] Pre-push HARD GATE: `uv run pytest -q` full nikita suite passes
  - **AC-1**: Full suite green; no skipped tests in PR-F1a-touched modules
  - **AC-2**: PR body `## Local tests` section records pass count + duration

- [ ] **T014** [PR-F1a] Open PR-F1a + dispatch `/qa-review --pr N` (HARD CAP 5 tool calls; scope: 6 changed files; exit: report CLEAN or N findings)
  - **AC-1**: PR opened with body referencing spec.md + plan.md §4 PR-F1a + tasks T003-T013
  - **AC-2**: Fresh-context QA review returns 0 findings across ALL severities

**Checkpoint**: PR-F1a merged. Migration applied to prod via Supabase MCP. Telegram FSM data layer + admin endpoint shipped. Ready for PR-F1b.

---

## Phase 3: PR-F1b — Backend FSM `signup_handler.py` + Telegram webhook routing

**Per plan.md §4 PR-F1b. Estimate: ~400 LOC, 8-12 hours.**

**Trigger phrase check**: this PR touches `nikita/agents/**` indirectly via persona changes in PR-F3, but the FSM itself is `nikita/platforms/**`. Per `.claude/rules/agentic-design-patterns.md`: read it BEFORE planning the FSM (NOT a Pydantic AI agent — single-purpose state machine — so 4 hard rules don't directly apply, but cumulative-state discipline still informs).

### Tests for PR-F1b ⚠️ WRITE FIRST

- [ ] **T015** [P] [PR-F1b] RED: `tests/platforms/telegram/test_signup_handler.py` — FSM transitions per FR-2/3/4
  - **AC-1**: `/start welcome` for unbound telegram_id triggers welcome message + `signup_state=AWAITING_EMAIL` row
  - **AC-2**: invalid email keeps state `AWAITING_EMAIL` and emits Nikita-voiced rejection
  - **AC-3**: valid email transitions to `CODE_SENT` via T009 CAS helper + emits `signup_email_received` telemetry
  - **AC-4**: invalid OTP increments `attempts`; 3rd invalid in 1h triggers rate-limit + reset to AWAITING_EMAIL
  - **AC-5**: expired code (now > expires_at) emits Nikita-voiced "Code expired" + row purge
  - **AC-6**: valid OTP transitions to `MAGIC_LINK_SENT` via FR-5 admin endpoint + Telegram delivery
  - **Mapped FR/AC**: AC-2.1..AC-2.3, AC-3.1..AC-3.4, AC-4.1..AC-4.4, AC-5.4
  - **Verify FAIL**: pytest RED
  - **Estimate**: L (4hr)

- [ ] **T016** [P] [PR-F1b] RED: `tests/platforms/telegram/test_signup_handler_link_preview.py` per Testing H1
  - **AC-1**: FR-5 path → `bot.send_message` called with `disable_web_page_preview=True`
  - **AC-2**: NEGATIVE control: FR-2 welcome message does NOT force `disable_web_page_preview=True`
  - **AC-3**: simulated Telegram crawler `GET <action_link>` followed by user tap still consumes token (single-use semantics not pre-burned)
  - **Mapped FR/AC**: AC-5.3, Testing H1, NFR-Sec-1
  - **Verify FAIL**: pytest RED
  - **Estimate**: M (2hr)

### Implementation for PR-F1b

- [ ] **T017** [PR-F1b] GREEN: `nikita/platforms/telegram/signup_handler.py` consolidated FSM
  - **AC-1**: `handle_welcome(update, context)` greets Nikita-voiced + transitions UNKNOWN → AWAITING_EMAIL
  - **AC-2**: `handle_email(update, context)` regex-validates, calls `client.auth.sign_in_with_otp(email, options:{should_create_user:True})`, transitions via T009 CAS
  - **AC-3**: `handle_code(update, context)` regex-validates `^[0-9]{6}$`, calls `client.auth.verify_otp({email, token, type:"email"})`, on success calls FR-5 admin endpoint (T011)
  - **AC-4**: rate-limit per D10: 10 emails/hr, 15 codes/hr, 60s resend cooldown, 5min code TTL
  - **AC-5**: every transition emits corresponding telemetry event (T010)
  - **AC-6**: post-magic-link bind: `UPDATE public.users SET telegram_id = <tg_id> WHERE id = <auth_uid>` is idempotent
  - **Files**: `nikita/platforms/telegram/signup_handler.py`
  - **Dependencies**: T009, T011, T015
  - **Estimate**: XL → break: T017a (handle_welcome+handle_email, M 3hr), T017b (handle_code + admin call + bind, L 4hr)
  - **Verify GREEN**: T015 tests pass

- [ ] **T018** [PR-F1b] GREEN: Wire `signup_handler.py` into `nikita/api/routes/telegram.py` webhook
  - **AC-1**: webhook routes `/start welcome` to `signup_handler.handle_welcome` (replaces legacy registration_handler dispatch)
  - **AC-2**: webhook routes free-text from `signup_state IN ('awaiting_email','code_sent')` to corresponding handler
  - **AC-3**: legacy `registration_handler.py` + `otp_handler.py` wiring removed (deletion deferred to PR-F3 to keep PR-F1b additive; this task only swaps the dispatch)
  - **Files**: `nikita/api/routes/telegram.py`
  - **Dependencies**: T017
  - **Estimate**: M (2hr)

- [ ] **T019** [PR-F1b] GREEN: Telegram delivery enforces `disable_web_page_preview=True` for magic-link messages
  - **AC-1**: helper `send_magic_link_message(chat_id, action_link, button_label)` always passes `disable_web_page_preview=True`
  - **AC-2**: T016 tests pass
  - **Files**: helper inside `signup_handler.py` or shared `nikita/platforms/telegram/utils.py`
  - **Dependencies**: T016, T017

### Verification for PR-F1b

- [ ] **T020** [PR-F1b] Pre-push HARD GATE + grep gates + open PR-F1b + `/qa-review` loop to 0 findings
  - **AC-1**: Full pytest passes
  - **AC-2**: Fresh-context QA returns 0 findings ALL severities

**Checkpoint**: PR-F1b merged. Backend FSM live. Magic-link minting and Telegram delivery functional. Ready for PR-F2a.

---

## Phase 4: PR-F2a — Portal `/auth/confirm` route + IS-A interstitial + middleware

**Per plan.md §4 PR-F2a. Estimate: ~250 LOC, 6 hours.**

**Intelligence queries** (run once at PR-F2a start):
```bash
bash .claude/skills/project-intel/scripts/graph-ops.sh briefing portal/src/lib/supabase/middleware.ts
bash .claude/skills/project-intel/scripts/graph-ops.sh search "createServerClient"
```

### Tests for PR-F2a ⚠️ WRITE FIRST

- [ ] **T021** [P] [PR-F2a] RED: `portal/tests/app/auth/confirm/route.test.ts` per Testing H3 (T-E22/E23/E24/E27)
  - **AC-1** (T-E22): `verifyOtp` returning expired-token error → response is `Response.redirect("/login?error=link_expired", 302)`
  - **AC-2** (T-E23): same `token_hash` consumed twice → both succeed; second call returns IS-A interstitial without `?error=*`
  - **AC-3** (T-E24): fresh device (no cookie jar) → `Set-Cookie` headers present on response
  - **AC-4** (T-E27): same `token_hash` after `expires_at` → redirect to `/login?error=link_expired` (matches T-E22)
  - **AC-5**: missing `?token_hash` or `?type` → redirect to `/login?error=missing_params`
  - **Mapped FR/AC**: FR-6, AC-6.1..AC-6.6, Testing H3
  - **Verify FAIL**: vitest RED
  - **Estimate**: M (2hr)

- [ ] **T022** [P] [PR-F2a] RED: `portal/tests/app/auth/confirm/interstitial.test.tsx` per Testing H4 (UA-spoof)
  - **AC-1**: render with iOS Safari UA → primary "Continue to Nikita" button renders; "Open in Safari" Universal Link does NOT render (already in Safari)
  - **AC-2**: render with Telegram-IAB UA → primary button renders + "Open in Safari" Universal Link visible
  - **AC-3**: ARIA contract per FR-6a: `role="main"`, `aria-labelledby`, `aria-describedby` present
  - **Mapped FR/AC**: FR-6, FR-6a, Testing H4
  - **Verify FAIL**: vitest RED
  - **Estimate**: M (2hr)

### Implementation for PR-F2a

- [ ] **T023** [PR-F2a] GREEN: `portal/src/app/auth/confirm/route.ts` server route handler
  - **AC-1**: reads `?token_hash`, `?type`, `?next` from URL; missing params → 302 to `/login?error=missing_params`
  - **AC-2**: `createServerClient` (`@supabase/ssr` cookies adapter); calls `supabase.auth.verifyOtp({token_hash, type})` server-side
  - **AC-3**: error → 302 to `/login?error=<code>`; success → renders interstitial (NOT raw 302)
  - **AC-4**: `type` from query passed VERBATIM to `verifyOtp` (no hardcoding)
  - **Files**: `portal/src/app/auth/confirm/route.ts`
  - **Dependencies**: T021
  - **Estimate**: M (2hr)
  - **Verify GREEN**: T021 tests pass

- [ ] **T024** [PR-F2a] GREEN: `portal/src/app/auth/confirm/interstitial.tsx` IS-A always-interstitial Client Component
  - **AC-1**: ~150 LOC; renders Nikita-voiced "You're cleared. Enter the portal." copy
  - **AC-2**: primary button "Enter the portal" calls `router.push(next)` with `next` from query
  - **AC-3**: secondary "Open in Safari" Universal Link rendered conditionally on Telegram-IAB UA detection (regex centralized per GH #420 — helper `isTelegramIAB(ua)` in `portal/src/lib/auth/ua.ts`)
  - **AC-4**: ARIA per FR-6a (`role="main"`, etc.)
  - **AC-5**: gated behind `process.env.NEXT_PUBLIC_TELEGRAM_FIRST_SIGNUP === 'true'` (rollback safety)
  - **Files**: `portal/src/app/auth/confirm/interstitial.tsx`, `portal/src/lib/auth/ua.ts`
  - **Dependencies**: T022
  - **Estimate**: L (3hr)
  - **Verify GREEN**: T022 tests pass

- [ ] **T025** [PR-F2a] GREEN: Update `portal/src/lib/supabase/middleware.ts` exemptions
  - **AC-1**: ADD `/auth/confirm` to public-allowed routes
  - **AC-2**: `/onboarding/auth` exemption REMAINS (deletion happens in PR-F2b)
  - **Files**: `portal/src/lib/supabase/middleware.ts`
  - **Dependencies**: T023

### Verification for PR-F2a

- [ ] **T026** [PR-F2a] Portal pre-push HARD GATE: `(cd portal && npm run test -- --run && npm run lint && npm run build)`
  - **AC-1**: Full vitest passes; lint clean; build succeeds
  - **AC-2**: PR body records output

- [ ] **T027** [PR-F2a] Open PR-F2a + `/qa-review` loop to 0 findings
  - **AC-1**: PR open with FR-6/6a + Testing H3/H4 references
  - **AC-2**: Fresh QA 0 findings

**Checkpoint**: PR-F2a merged. Portal `/auth/confirm` route live. Magic-link → portal session round-trip working end-to-end (with PR-F1b backend mint). Ready for PR-F2b.

---

## Phase 5: PR-F2b — Portal UI: `/login` redesign + landing CTA flip + `/onboarding/auth` deletion

**Per plan.md §4 PR-F2b. Estimate: ~350 LOC, 6 hours.**

### Tests for PR-F2b ⚠️ WRITE FIRST

- [ ] **T028** [P] [PR-F2b] RED: `portal/tests/components/landing/cta-href.test.tsx` per FR-1
  - **AC-1**: anon visitor → all 3 CTAs (`hero-section.tsx`, `cta-section.tsx`, `landing-nav.tsx`) emit `<a href="https://t.me/Nikita_my_bot?start=welcome">`
  - **AC-2**: auth'd-not-onboarded → CTA routes to `/dashboard` (middleware redirects to `/onboarding`)
  - **AC-3**: auth'd-onboarded → primary CTA routes to `/dashboard`; nav shows "Continue with Nikita" → Telegram URL
  - **Mapped FR/AC**: FR-1, FR-11, AC-1.1..AC-1.3, AC-11.1..AC-11.3
  - **Verify FAIL**: vitest RED
  - **Estimate**: M (2hr)

- [ ] **T029** [P] [PR-F2b] RED: `portal/tests/app/login/page-client.test.tsx` per FR-10
  - **AC-1**: page renders Nikita-voiced copy (greppable string from `docs-to-process/20260423-auth-templates-v17-1.md` §1.2)
  - **AC-2**: `signInWithOtp({email, options:{emailRedirectTo:"<portal>/auth/confirm?next=/dashboard"}})` is called
  - **AC-3**: NO code-input field rendered (link-only template — D2; AC-10.6 negation guard)
  - **Mapped FR/AC**: FR-10, FR-10a, AC-10.1..AC-10.6
  - **Verify FAIL**: vitest RED
  - **Estimate**: M (2hr)

### Implementation for PR-F2b

- [ ] **T030** [P] [PR-F2b] GREEN: Flip 3 landing CTAs to Telegram URL
  - **AC-1**: `hero-section.tsx`, `cta-section.tsx`, `landing-nav.tsx` anon `href` → `https://t.me/Nikita_my_bot?start=welcome`
  - **AC-2**: feature-flagged: when `NEXT_PUBLIC_TELEGRAM_FIRST_SIGNUP !== 'true'`, fallback to `/onboarding/auth` (until flag flips post-W1)
  - **Files**: 3 landing components
  - **Dependencies**: T028
  - **Verify GREEN**: T028 tests pass

- [ ] **T031** [P] [PR-F2b] GREEN: `landing-nav.tsx` adds visible "Sign in" + "Continue with Nikita" entries (FR-11)
  - **AC-1**: "Sign in" link → `/login`
  - **AC-2**: "Continue with Nikita" link → Telegram URL (visible to auth'd-onboarded only)
  - **Files**: `portal/src/components/landing/landing-nav.tsx`
  - **Dependencies**: T028

- [ ] **T032** [PR-F2b] GREEN: Redesign `portal/src/app/login/page-client.tsx` Nikita-voiced
  - **AC-1**: copy from `docs-to-process/20260423-auth-templates-v17-1.md` §1.2 verbatim
  - **AC-2**: `emailRedirectTo` → `/auth/confirm?next=/dashboard`
  - **AC-3**: NO code-input field (link-only)
  - **AC-4**: existing `ResendButton` (60s cooldown) preserved
  - **Files**: `portal/src/app/login/page-client.tsx`
  - **Dependencies**: T029
  - **Verify GREEN**: T029 tests pass
  - **Estimate**: M (3hr)

- [ ] **T033** [PR-F2b] GREEN: `ClearanceGrantedCeremony.tsx` adds S3 portal-orientation copy (FR-14)
  - **AC-1**: ceremony copy includes "Bookmark this portal — your dashboard, history, and Nikita's daily highlights live here."
  - **AC-2**: copy is greppable for regression assertion
  - **Files**: `portal/src/components/onboarding/ClearanceGrantedCeremony.tsx`
  - **Estimate**: S (30 min)

- [ ] **T034** [PR-F2b] GREEN: DELETE `portal/src/app/onboarding/auth/` route (entire directory)
  - **AC-1**: `git status` shows directory deleted; no callers remain (`grep -r "onboarding/auth" portal/src/` returns empty except this task ref)
  - **AC-2**: middleware exemption for `/onboarding/auth` removed (T025 left it in place)
  - **AC-3**: T-E29 cache purge step recorded in PR body for post-merge execution
  - **Files**: deletion + `portal/src/lib/supabase/middleware.ts` adjust
  - **Dependencies**: T030 (landing CTA migrated first)
  - **Estimate**: S (30 min)

### Verification for PR-F2b

- [ ] **T035** [PR-F2b] Portal pre-push HARD GATE + grep gates
  - **AC-1**: vitest + lint + build pass
  - **AC-2**: `grep -r "onboarding/auth" portal/src/` returns empty

- [ ] **T036** [PR-F2b] Open PR-F2b + `/qa-review` loop to 0 findings
- [ ] **T037** [PR-F2b] Post-merge: Vercel cache purge for `/onboarding/auth` (T-E29) + verify route returns 404

**Checkpoint**: PR-F2b merged. Full Telegram-first signup flow live behind feature flag. Ready for Phase F W1 dogfood.

---

## Phase 6: W1 — Phase F Live Dogfood Walk

**Per spec §8.3 + plan.md §9. Strict adherence to `.claude/rules/live-testing-protocol.md` 12-step canonical protocol.**

- [ ] **T038** [W1] Live dogfood walk W1 with `youwontgetmyname777+walk1@gmail.com`
  - **AC-1**: 12 steps executed verbatim per `.claude/rules/live-testing-protocol.md`
  - **AC-2**: 0 CRITICAL findings, 0 unfiled HIGH
  - **AC-3**: All 9 FR-Telemetry-1 events fired correctly (verified via Cloud Run logs)
  - **AC-4**: AC-LiveWalk satisfied
  - **AC-5**: NO DB fabrication (any `INSERT INTO auth.users` / `signInWithPassword` / `E2E_AUTH_BYPASS` is PR-blocker per ADR-011)
  - **AC-6**: Walk report at `docs-to-process/20260424-dogfood-walk-W1.md`
  - **AC-7**: DB cleanup applied per FK-safe template
  - **Estimate**: 2-4 hours
  - **Dispatch**: as background subagent with `HARD CAP: 25 tool calls` + scope (Telegram MCP + Gmail MCP + agent-browser only) + exit (walk report + GH issues for findings)

- [ ] **T039** [W1] On W1 PASS: flip `NEXT_PUBLIC_TELEGRAM_FIRST_SIGNUP=true` in Vercel prod via REST API
  - **AC-1**: `vercel env ls` shows `true` on production
  - **AC-2**: Vercel redeploy triggered + verified live via curl probe of landing CTAs
  - **AC-3**: 1 deploy cycle (24h minimum) elapses before PR-F3 kickoff (rollback safety)

- [ ] **T040** [W1] On W1 FAIL: file CRITICAL/HIGH GH issues + iterate via fix PR + W2 (cap 3 walks per ADR-011)
  - **AC-1**: Each finding has GH issue with severity label
  - **AC-2**: Fix PR per finding follows pr-workflow.md TDD + qa-review loop
  - **AC-3**: W2 dispatched only after fixes merged

**Checkpoint**: W1 PASS + flag flipped + 24h rollback window elapsed. Ready for PR-F3 legacy deletion.

---

## Phase 7: PR-F3 — Legacy Code Removal + `auth_bridge_tokens` Drop + FR-12/13/14

**Per plan.md §4 PR-F3. Estimate: ~400 LOC deletions, 4 hours. Dependency: W1 PASS + flag flipped + 1 deploy cycle.**

**Trigger phrase check**: `nikita/agents/**` touched (FR-13 persona fragment + FR-12 wizard slot). Per `.claude/rules/agentic-design-patterns.md`: consult rule. The wizard slot addition MUST follow §8.4 mandatory tests (cumulative-state monotonicity, completion-gate triplet, mock-LLM recovery).

### Tests for PR-F3 ⚠️ WRITE FIRST

- [ ] **T041** [P] [PR-F3] RED: `tests/agents/onboarding/test_wizard_slots_preferred_call_window.py` per `.claude/rules/agentic-design-patterns.md` §8.4
  - **AC-1** (cumulative-state monotonicity): 3-turn fixture with `preferred_call_window` slot; `progress_pct[t+1] >= progress_pct[t]` for every t
  - **AC-2** (completion-gate triplet): empty WizardSlots → False/0%; partial (no preferred_call_window) → False/<100%; full → True/100%
  - **AC-3** (mock-LLM recovery): mocked agent returns wrong slot kind for "weekday evenings" → deterministic regex/fallback recovers `preferred_call_window`
  - **Mapped FR/AC**: FR-12, AC-12.1..AC-12.4, §8.4 mandatory tests
  - **Verify FAIL**: pytest RED
  - **Estimate**: L (4hr)

- [ ] **T042** [P] [PR-F3] RED: assertion test `tests/architecture/test_legacy_imports_removed.py`
  - **AC-1**: `grep -r "registration_handler\|otp_handler" nikita/` returns only test files in `tests/architecture/`
  - **AC-2**: `grep -r "auth_bridge\|AuthBridge" nikita/ portal/src/` returns only test files
  - **AC-3**: `grep -r "onboarding-wizard-legacy\|steps/legacy\|components/legacy" portal/src/` returns empty
  - **Verify FAIL**: pytest RED (until deletions land)

### Implementation for PR-F3

- [ ] **T043** [P] [PR-F3] GREEN: ADD `preferred_call_window` slot to `nikita/agents/onboarding/wizard_slots.py` (FR-12)
  - **AC-1**: New `Optional[str]` field on `WizardSlots` Pydantic model
  - **AC-2**: `FinalForm` requires `preferred_call_window` non-empty (cross-field validator allows reasonable values: weekday/weekend × morning/afternoon/evening)
  - **AC-3**: T041 monotonicity + completion-gate tests pass
  - **Files**: `nikita/agents/onboarding/wizard_slots.py`
  - **Dependencies**: T041
  - **Verify GREEN**: T041 pass

- [ ] **T044** [P] [PR-F3] GREEN: ADD S2 phone-call proposal fragment to `nikita/agents/text/persona.py` (FR-13)
  - **AC-1**: persona prompt includes guidance to proactively propose phone-call within first 3 turns post-handoff
  - **AC-2**: greppable string for regression
  - **Mapped FR/AC**: FR-13, AC-13.1..AC-13.2

- [ ] **T045** [PR-F3] GREEN: DELETE `nikita/platforms/telegram/registration_handler.py` + `otp_handler.py`
  - **AC-1**: Files removed; `git status` shows deletions
  - **AC-2**: T042 grep tests pass for these patterns

- [ ] **T046** [PR-F3] GREEN: DELETE `nikita/platforms/telegram/auth.py:61-141` (`register_user` + `verify_otp` deprecated methods)
  - **AC-1**: Methods removed; remaining file content syntactically valid
  - **AC-2**: All callers either deleted (T045) or migrated (T017)

- [ ] **T047** [PR-F3] GREEN: DELETE `nikita/db/models/auth_bridge.py` + `nikita/api/routes/auth_bridge.py` + `auth_bridge_repository.py`
  - **AC-1**: Files removed
  - **AC-2**: Migration `<NNN>_drop_auth_bridge_tokens.sql` exists and applies cleanly
  - **AC-3**: `mcp__supabase__execute_sql` confirms `auth_bridge_tokens` row count was 0 before drop (Plan §18.9 verified)

- [ ] **T048** [P] [PR-F3] GREEN: DELETE legacy portal wizard files
  - **AC-1**: `portal/src/components/onboarding/onboarding-wizard-legacy.tsx` removed
  - **AC-2**: `portal/src/components/onboarding/steps/legacy/` removed (entire dir)
  - **AC-3**: `portal/src/components/onboarding/components/legacy/` removed (entire dir)
  - **AC-4**: D4 verification: `vercel env ls | grep NEXT_PUBLIC_USE_LEGACY_FORM_WIZARD` returns empty (already verified Plan §22)

- [ ] **T049** [P] [PR-F3] GREEN: Collapse dual `generate_portal_bridge_url` (closes GH #233 finally)
  - **AC-1**: `nikita/onboarding/bridge_tokens.py` is the single source
  - **AC-2**: `nikita/utils.py` duplicate removed; all callers updated
  - **AC-3**: GH #233 closed referencing PR-F3

- [ ] **T050** [P] [PR-F3] GREEN: DELETE `_send_bare_portal_auth_link` + `/onboard` slash-command + help-text reference
  - **AC-1**: `nikita/platforms/telegram/commands.py:408-429` deleted (`_send_bare_portal_auth_link`)
  - **AC-2**: `commands.py:198` `/onboard` handler deleted
  - **AC-3**: `commands.py:643` help-text reference removed

### Verification for PR-F3

- [ ] **T051** [PR-F3] Pre-push HARD GATE: full `uv run pytest -q` + portal vitest + lint + build
  - **AC-1**: All pass; T042 grep tests now GREEN
  - **AC-2**: PR body records counts

- [ ] **T052** [PR-F3] Open PR-F3 + `/qa-review` loop to 0 findings + merge + post-merge smoke

**Checkpoint**: PR-F3 merged. All legacy auth code removed. Spec 215 implementation COMPLETE. ROADMAP sync.

---

## Phase 8: Polish & Cross-Cutting

- [ ] **T053** [P] Update `docs/deployment.md` with Supabase Email Templates section (signup vs login template configs per spec §7.4)
  - **AC-1**: Section added with both template HTML linked to `docs-to-process/20260423-auth-templates-v17-1.md`
  - **AC-2**: Dashboard config screenshots or step-by-step instructions

- [ ] **T054** [P] Copy 6 supporting diagrams from Plan §18.10 into `docs/diagrams/onboarding-journey-v17.md`
  - **AC-1**: All 6 diagrams present (landing decision tree, FSM, happy-path sequence, 3 failure-mode sequences, ERD, Gantt)
  - **AC-2**: Markdown ASCII or mermaid where structurally appropriate

- [ ] **T055** Run `/roadmap sync` after PR-F3 merge
  - **AC-1**: ROADMAP.md reflects Spec 215 COMPLETE status

- [ ] **T056** Close referenced GH issues with PR refs
  - **AC-1**: GH #393 closed referencing PR-F2a (PKCE eliminated)
  - **AC-2**: GH #233 closed referencing PR-F3 (bridge URL consolidated)

---

## Dependencies & Execution Order

```
Phase 1 Setup (T001-T002)
   ↓
Phase 2 PR-F1a (T003-T014)  ← tests T003-T005 [P], impl T006-T011 staggered
   ↓
Phase 3 PR-F1b (T015-T020)  ← tests T015-T016 [P], impl T017-T019 staggered
   ↓
Phase 4 PR-F2a (T021-T027)  ← tests T021-T022 [P], impl T023-T025 staggered
   ↓
Phase 5 PR-F2b (T028-T037)  ← tests T028-T029 [P], impl T030-T034 staggered
   ↓
Phase 6 W1 (T038-T040)
   ↓ (W1 PASS + flag flip + 24h)
Phase 7 PR-F3 (T041-T052)  ← tests T041-T042 [P], impl T043-T050 mostly [P]
   ↓
Phase 8 Polish (T053-T056) [P]
```

### Parallelization summary

- Within each PR's test phase: all RED tests can run in parallel ([P] markers)
- Within PR-F3: most deletions and additions are independent ([P]) since they touch different files
- Across PRs: STRICTLY SEQUENTIAL — no parallelization (per plan.md §4 staging)

## Implementation Strategy

**Incremental, feature-flagged**:
1. PR-F1a → ship → PR-F1b → ship → PR-F2a → ship → PR-F2b → ship (all behind flag)
2. Phase F W1 dogfood walk validates end-to-end
3. Flag flip + 24h rollback window
4. PR-F3 legacy deletion + FR-12/13/14 additions

This gives 4 ship checkpoints before any irreversible deletion lands.

## Test-First Checklist (Article III)

Every implementation task in this plan has:
- [x] ≥2 acceptance criteria defined
- [x] Tests specified BEFORE implementation tasks
- [x] RED → GREEN commit pair required (per `.claude/rules/pr-workflow.md`)
- [x] AC mapping back to spec.md FRs

## Subagent Dispatch Compliance

Every subagent dispatched in this plan (QA review, dogfood walk, fix subagents) MUST include per `.claude/rules/parallel-agents.md`:
- HARD CAP: <N> tool calls (5 for QA, 10 for research, 25 for dogfood walk)
- Explicit scope clause (changed files / specific URLs / specific MCP tools)
- Defined exit criterion (CLEAN / N findings / partial-results-on-cap)

## Live-Walk Anti-Fabrication Compliance

Phase F W1 (T038) MUST follow `.claude/rules/live-testing-protocol.md` 12-step protocol with NO exceptions. ADR-011 + Walk Y precedent (#410, #411 synthetic findings) governs.

---

**Generated by**: `/tasks` skill (SDD Phase 6)
**Validated by**: `/audit` skill (SDD Phase 7) — auto-chains next
**Implementor**: `/implement` skill (SDD Phase 8) — unblocked on `/audit` PASS
