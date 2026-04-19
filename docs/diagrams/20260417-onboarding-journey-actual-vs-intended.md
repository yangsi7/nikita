# Onboarding Journey: Actual vs Intended (Spec 214)

**Date**: 2026-04-17 (PM revision)
**Scope**: Portal entry flows for anonymous and authenticated users, from landing
          page through wizard to Telegram handoff.
**Spec reference**: `specs/214-portal-onboarding-wizard/spec.md`
**Status vs earlier AM revision**: Gates 1 and 2 closed (PRs #312, #315, #317, #319
  merged). Wizard completes fields 1 through 11 end-to-end for a fresh user
  (verified by Agent H-4, `docs-to-process/20260417-adv-e2e/K-post-fix3-dogfood.md`,
  POST-FIX3-PASS). Remaining HIGH gap: Telegram binding for portal-first users
  (GH #321, Agent I probe
  `docs-to-process/20260417-adv-e2e/L-telegram-handoff-probe.md`).

**Evidence sources (post-Gate-1/2, master 19aed54)**:
- `portal/src/app/page.tsx`
- `portal/src/components/landing/{hero,cta,landing-nav}-section.tsx`
- `portal/src/app/onboarding/auth/{page.tsx,page-client.tsx}`
- `portal/src/app/onboarding/_components/onboarding-cinematic.tsx`
- `portal/src/app/onboarding/steps/{Location,Scene,Darkness,Identity,BackstoryReveal,Phone,PipelineGate,Handoff}Step.tsx`
- `portal/src/app/onboarding/steps/copy.ts` (TELEGRAM_URL, WIZARD_COPY)
- `portal/src/app/onboarding/hooks/use-onboarding-api.ts`
- `nikita/api/routes/portal.py:574-598` (POST /portal/link-telegram, issued 2026-03-10, never wired)
- `nikita/platforms/telegram/commands.py:32-38,84-162` (COMMANDS, _handle_start branches)
- `nikita/db/repositories/{telegram_link_repository,user_repository}.py`
- `nikita/db/models/telegram_link.py` (6-char uppercase alnum, 10-min TTL)
- `specs/214-portal-onboarding-wizard/spec.md` (lines 50-248)

---

## 1. Actual Journey Tree (master HEAD, 2026-04-17 PM)

```
Anonymous fresh visitor (unauthenticated)
  |
  v
[portal/src/app/page.tsx]                               LandingPage()
  isAuthenticated = false
  |
  +--[HeroSection]     hero-section.tsx
  |    ctaHref = "/onboarding/auth"                    POST-#312 FIXED
  |
  +--[CtaSection]      cta-section.tsx
  |    ctaHref = "/onboarding/auth"                    POST-#312 FIXED
  |
  +--[LandingNav]      landing-nav.tsx
       ctaHref = "/onboarding/auth"                    POST-#312 FIXED
         |
         v (CTA click)
  [/onboarding/auth]                                   POST-#312 NEW ROUTE
    page-client.tsx: Nikita-voiced magic-link form
    supabase.auth.signInWithOtp({ emailRedirectTo: "/auth/callback?next=/onboarding" })
    Copy: "Show her the file" / "I'll know when you open it."
         |
         v (user clicks magic link in email)
  [/auth/callback?next=/onboarding]                    auth/callback/route.ts
    exchangeCodeForSession(code)
    redirect to next ("/onboarding") when present
         |
         v
  [/onboarding]                                        onboarding/page.tsx
    server: redirect(/onboarding/auth) if no session
    server: redirect(/dashboard) if onboarded_at not null
    else: render <OnboardingCinematic />
         |
         v
  [OnboardingCinematic]      onboarding-cinematic.tsx  POST-Gate-1/2 11-STEP WIZARD
    Step 1-2 handled upstream (landing + /onboarding/auth)
    Step 3  DossierHeader       real UserMetrics 50/50/50/50, "Continue."
    Step 4  LocationStep        city text, PATCH {location_city, wizard_step:4}
    Step 5  SceneStep           social_scene grid, PATCH {social_scene, life_stage, wizard_step:5}
    Step 6  DarknessStep        EdginessSlider 1-5, PATCH {drug_tolerance, wizard_step:6}
    Step 7  IdentityStep        name/age/occupation, PATCH {..., wizard_step:7}
    Step 8  BackstoryReveal     POST /onboarding/preview-backstory on mount
                                PATCH {profile, wizard_step:8} BEFORE
                                PUT  /onboarding/profile/chosen-option  GH #313 FIX (#315)
    Step 9  PhoneStep           voice/text branch, PATCH {phone, wizard_step:9}
    Step 10 PipelineGate        POST /onboarding/profile -> poll /pipeline-ready
                                stamp PENDING -> CLEARED or PROVISIONAL timeout 20s
    Step 11 HandoffStep         TELEGRAM_URL = "https://t.me/Nikita_my_bot"    GH #321 GAP
                                bare URL, no ?start= payload, no link code
         |
         v (user taps "Open Telegram")
  [t.me/Nikita_my_bot]
    bot receives /start from a new telegram_id not in public.users
    _handle_start branch 3: "I don't think we've met before... I'll need your email"
    runs parallel email-OTP registration (pending_registrations -> auth.create_user)
    IF bot-OTP email == portal magic-link email
      -> Supabase auth.create_user returns same UUID -> rows collapse -> bind works by coincidence
    IF emails differ
      -> two orphan rows, wizard profile never reaches Telegram chat            GH #321 FAILURE


Authenticated returning visitor
  |
  v
[portal/src/app/page.tsx]
  isAuthenticated = true -> ctaHref = "/dashboard"
         |
         v
  [/dashboard]             middleware.ts
    onboarded_at gate: NOT ENFORCED in dashboard (sequencing-gap, low impact now)
```

**Middleware routing summary** (`portal/src/lib/supabase/middleware.ts`):
```
"/"                         always public, pass through
"/login"                    if authed: redirect /admin or /dashboard
"/auth/*"                   if authed: redirect /admin or /dashboard
"/onboarding/auth"          public (magic-link entry, new in #312)
"/onboarding"               protected, redirect /onboarding/auth if anonymous
all other paths             if unauthed: redirect /login
```

---

## 2. Intended Journey Tree (Spec 214 full target state)

```
Anonymous fresh visitor
  |
  v [landing CTA]
  /onboarding/auth
  |
  v [magic-link session]
  /auth/callback?next=/onboarding  ->  /onboarding
  |
  v [11-step wizard]
  Step 3 Dossier  ->  Step 4 Location  ->  Step 5 Scene  ->  Step 6 Darkness
    ->  Step 7 Identity  ->  Step 8 Backstory Reveal  ->  Step 9 Phone
    ->  Step 10 Pipeline Gate  ->  Step 11 Handoff
  |
  v [handoff, two branches by phone preference]
  IF phone provided
    -> voice call via ElevenLabs (Spec 208 voice agent)
  IF no phone
    -> Telegram deep-link with binding token         MISSING TODAY (GH #321)
       t.me/Nikita_my_bot?start=<opaque-token>
       bot _handle_start extracts token -> telegram_link_repository.verify
       -> UserRepository.update_telegram_id(user_id, msg.from.id)
       -> atomic bind; wizard profile reaches Telegram chat
```

localStorage persistence per FR-NR-1 (wizard state keyed by user_id) — **ALREADY
SHIPPED** as of Spec 214 PR 214-B/C.

---

## 3. Divergence Table (post-Gate-1/2, updated)

| Step | Intended (Spec 214) | Actual (master, 2026-04-17 PM) | Status | Ref |
|------|--------------------|-------------------------------|--------|-----|
| Landing CTA (anon) | `/onboarding/auth` | `/onboarding/auth` | FIXED | #312 |
| Landing nav CTA | `/onboarding/auth` | `/onboarding/auth` | FIXED | #312 |
| Step 2 Auth route | Nikita-voiced magic link at `/onboarding/auth` | Implemented | FIXED | #312 |
| Auth callback `next` | redirect to `/onboarding` for new users | Honors `next=/onboarding` param | FIXED | #312 |
| Step 3 Dossier header | real metrics, "Continue." | Implemented | OK | 214-B |
| Step 4-7 data collection | one field per step, PATCH each | Implemented | OK | 214-B,C |
| Step 8 Backstory reveal | preview + 3 cards + PATCH-then-PUT | Implemented, ordering fixed | FIXED | #315 |
| Step 8 jsonb_set path | TEXT[] for asyncpg compatibility | `postgresql.array([key])` | FIXED | #317 |
| Step 8 JSONB value bind | raw Python via `cast(value, JSONB)` | Fixed (no json.dumps) | FIXED | #319 |
| Step 9 Phone branch | binary voice/text, tel input expands | Implemented | OK | 214-B |
| Step 10 Pipeline gate | poll `/pipeline-ready` | Implemented | OK | 214-C |
| Step 11 Handoff URL | `t.me/Nikita_my_bot?start=<token>` | Armed via `linkTelegram()` mint-on-mount + `?start=<code>` href | FIXED | #322 |
| Bot `_handle_start` payload consumer | parse token, verify, set `users.telegram_id` | Regex `^[A-Z0-9]{6}$` + atomic verify + short-circuit on reject | FIXED | #322 |
| `UserRepository.update_telegram_id` | exists, used by bind flow | Predicate-filter UPDATE + RETURNING + `BindResult` enum + typed conflict exception | FIXED | #322 |
| `TelegramLinkRepository.verify_code` atomicity | single statement, no race window | Single `DELETE ... WHERE expires_at > now() RETURNING user_id` | FIXED | #322 |
| Dashboard onboarded_at gate | redirect to `/onboarding` if null | shows empty state, no redirect | open, low | D-3 |
| Voice call branch (Step 11 phone path) | ElevenLabs call dispatch | deferred to Spec 208 voice integration | open, scope | spec |
| Telegram `/start` no-payload routing | Portal bridge button for every branch (new/game_over/limbo/pending) | Legacy in-bot 8-step Q&A fires on `/start` for unonboarded + game_over/won + limbo users | **OPEN** | **FR-11c** |
| Bot message_handler pre-onboard text | Bridge nudge; no Q&A advance | Text consumed as Q&A answer | **OPEN** | **FR-11c** |
| Portal onboarding wizard form | Chat-first conversation with Nikita agent; extraction via Claude tool-use; confirmation loops | Static form with Nikita-voiced step copy; no reactive agent reading input | **OPEN** | **FR-11d** |
| Portal->Telegram handoff ceremony | Stamp "FILE CLOSED. CLEARANCE: GRANTED." + proactive Nikita greeting on bind (not first-message) | Silent handoff; greeting fires only on first user message | **OPEN** | **FR-11e** |

---

## 4. Divergence Flow Overlay (post-Gate-1/2)

```
                    ANONYMOUS VISITOR
                          |
                          v
                  /onboarding/auth
                          |
                          v
              /auth/callback?next=/onboarding
                          |
                          v
                  [/onboarding wizard steps 3-11]
                          |
                          v
                  [Step 11 Handoff]
                          |
              +-----------+---------------+
              |                           |
  INTENDED (Spec 214)           ACTUAL (master)
  ---------------------         ---------------
  t.me/Nikita_my_bot            t.me/Nikita_my_bot
   ?start=<token>               (bare URL)
              |                           |
              v                           v
  bot _handle_start             bot _handle_start branch 3
  parses payload                "I don't think we've met..."
  verifies via                  initiates email-OTP
  telegram_link_repo            (pending_registrations row)
              |                           |
              v                           v
  UserRepository                IF bot-OTP email == portal email
  .update_telegram_id             -> Supabase same UUID
  (user_id, msg.from.id)          -> rows collapse, bind by coincidence
              |                   IF emails differ
              v                     -> two orphan rows
  PROFILE BINDS TO CHAT             -> wizard data lost
  portal data reaches bot
```

---

## 5. GH #321 Fix Shape (recommended)

**Approach B selected** (deep-link `?start=<token>`) per pr-approach-evaluator panel
vote (Staff Engineer + Product Designer chose B; Security DBA chose A /link code).
Rationale: Telegram-native pattern, zero user friction, reuses existing
`telegram_link_codes` table.

Three-surface change:
1. **Portal** (`HandoffStep.tsx` + `copy.ts` + `use-onboarding-api.ts`): on mount,
   call `POST /portal/link-telegram` (already implemented at
   `nikita/api/routes/portal.py:574-598`). Render CTA as
   `https://t.me/Nikita_my_bot?start=<code>`. Loading, error, retry states.
2. **Bot** (`nikita/platforms/telegram/commands.py`): extend `_handle_start` to
   extract payload from `message["text"]` (format `/start <code>`), call
   `telegram_link_repository.verify_code(code)`, then
   `UserRepository.update_telegram_id(user_id, telegram_id)`. Preserve the 3
   existing branches for the no-payload case.
3. **Repo** (`nikita/db/repositories/user_repository.py`): add
   `async def update_telegram_id(self, user_id: UUID, telegram_id: int) -> None`.
   Currently does NOT exist; current code only sets `telegram_id` at user-create
   time (line 183).

Fallback path: if payload parsing or verify fails, fall through to the existing
branch-3 email-OTP flow (no regression for Telegram-first users).

---

## 6. Live Issues on master today

These are NOT blocked on Spec 214 state; they exist as of 2026-04-17 PM.

1. **Telegram binding gap for portal-first users** (GH #321, HIGH):
   `HandoffStep` renders bare URL; bot has no payload consumer; no bind path
   exists. Portal-first users depend on email-OTP coincidence for binding.

2. **Dashboard missing onboarding gate** (pre-existing, LOW):
   `/dashboard` shows `DashboardEmptyState` for new users with no
   `stats.last_interaction_at` and does not redirect to `/onboarding`. Impact
   reduced now that `/onboarding` is wired from landing (#312).

3. **Phone voice-call branch** (Spec 208 scope, deferred):
   HandoffStep's voice path is a UI rendering but does not dispatch an
   ElevenLabs call. Deferred to Spec 208 voice integration work.

---

## 7. Remediation plan

See `.claude/plans/quirky-floating-liskov.md` Gate 3 and the companion planning
brief produced 2026-04-17 PM. Testing path uses TDD per
`.claude/rules/testing.md`: failing unit test for `update_telegram_id` repo
method, failing unit test for `_handle_start` payload parsing, failing widget
test for `HandoffStep` `?start=` href composition, real-DB integration test for
end-to-end bind round-trip, and one Playwright E2E covering portal-first happy
path.

---

## 8. Historical context

An earlier version of this diagram (2026-04-17 AM) captured the landing-CTA
bypass gap (#310) and the wizard step-count gap (7 vs 11). Both were addressed
in the Gate 1 and Gate 2 cycle:
- PR #312 (#310): landing CTAs routed to `/onboarding/auth`
- PR #315 (#313): BackstoryReveal PATCH-before-PUT ordering fix
- PR #317 (#316): jsonb_set TEXT[] path for asyncpg
- PR #319 (#318): drop json.dumps; raw Python value via `cast(value, JSONB)`
- PR #322 (#321): Portal->Telegram deep-link binding. Shipped 4 components:
  atomic `verify_code`, predicate-filter `update_telegram_id` + `BindResult`
  enum, `_handle_start` payload consumer with regex gate + short-circuit,
  `HandoffStep` mint-on-mount with 3-state armed CTA. Merged as a663af2.
- real-DB integration tests added at
  `tests/db/integration/test_repositories_integration.py::test_update_onboarding_profile_key_stores_native_json_types`
  and `::test_update_telegram_id_three_cases`.

The wizard now completes fields 1 through 11 end-to-end AND the Telegram
binding closes the portal-first loop. Gates 1, 2, and 3 closed. Remaining
follow-up: end-to-end live dogfood walk (tooling-limited; Agent H-5 report at
`docs-to-process/20260417-adv-e2e/N-post-321-e2e.md` is PARTIAL per Gmail-MCP
plus-alias read limitation and admin-Telegram already-bound state; static
evidence confirms fix is live).
