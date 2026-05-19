# Task List: Portal-First Cinematic Onboarding

**Spec**: spec.md | **Plan**: plan.md | **Generated**: 2026-03-22

## Summary
- Total tasks: 33
- P1 (Core): 22 tasks (~42hr)
- P2 (Fallback/Polish): 4 tasks (~7hr)
- P3 (Phase 2 Drips): 5 tasks (~13hr)
- Deployment: 5 tasks (~3hr)

## Task Status Key
- [ ] Not started
- [~] In progress
- [x] Complete
- [!] Blocked

## Parallelizable Work Streams
- **Stream A (Backend)**: T1.1-T1.3, T4.5-T4.6, T7.1
- **Stream B (Portal)**: T2.1-T2.5, T3.1-T3.3, T4.1-T4.4
- **Stream C (After A+B)**: T9.1-T9.3, T6.1-T6.3, T7.2

---

## P1 -- Core Portal-First Onboarding

### US-1: Portal Redirect After OTP

_As a new player who just verified OTP, I want to be taken to a visual introduction of Nikita's world._

- [ ] **T1.1**: Write tests for magic link generation and OTP handler message | Est: M (2hr) | Deps: none | File: `tests/platforms/telegram/test_otp_handler_onboarding.py` (new)
  - AC (spec AC-1.1, AC-1.2, AC-1.4): Test `_generate_portal_magic_link()` success path returns URL from `result.properties.action_link`
  - AC: Test `_generate_portal_magic_link()` returns `None` when user has no email
  - AC: Test `_generate_portal_magic_link()` returns `None` on Supabase error (exception swallowed, logged)
  - AC: Test `_generate_portal_magic_link()` returns `None` when `supabase_url` or `supabase_service_key` not configured
  - AC: Test `_offer_onboarding_choice()` sends Telegram message with single URL button containing magic link URL (verify `bot.send_message_with_keyboard` called with `keyboard=[[{"text": "Enter Nikita's World  ...", "url": magic_link_url}]]`)
  - AC: Test `_offer_onboarding_choice()` falls back to `{portal_url}/login?next=/onboarding` when magic link returns `None`
  - AC: Test `_offer_onboarding_choice()` calls `_schedule_onboarding_fallback()` after sending message

- [ ] **T1.2**: Implement `_generate_portal_magic_link()` on OTPVerificationHandler | Est: M (1.5hr) | Deps: T1.1 | File: `nikita/platforms/telegram/otp_handler.py` (~line 375)
  - AC (spec AC-1.2, AC-1.3): Method signature: `async def _generate_portal_magic_link(self, user_id: str, redirect_path: str) -> str | None`
  - AC: Returns `None` gracefully on any failure (missing config, no email, Supabase error) with `logger.warning`
  - AC (spec FR-008): Uses `self.telegram_auth.supabase.auth.admin.get_user_by_id(user_id)` to look up email, then `admin.generate_link()` with `type="magiclink"`, `email=email`, `redirect_to=f"{portal_url}/onboarding"`
  - AC: Returns `result.properties.action_link` on success
  - AC: All 4 tests from T1.1 (AC1-AC4) pass green

- [ ] **T1.3**: Replace `_offer_onboarding_choice()` method body | Est: M (1.5hr) | Deps: T1.2 | File: `nikita/platforms/telegram/otp_handler.py` (lines 326-377)
  - AC (spec AC-1.1): Voice call URL button and text callback button removed; replaced with single URL button "Enter Nikita's World"
  - AC (spec WF-6): Message text updated to spec copy ("You're in! ... Tap below -- it'll only take a minute.")
  - AC: `handle_callback()` method (lines 379-424) retained for backward compatibility
  - AC: All existing OTP handler tests in `tests/platforms/telegram/test_otp_handler.py` still pass (no regressions)
  - AC: Tests from T1.1 (AC5-AC7) pass green

---

### US-2: Score Section Cinematic

_As a new player on the onboarding page, I want to learn about the scoring system visually._

- [ ] **T2.1**: Create `/onboarding` route with Server Component auth gate [P] | Est: M (2hr) | Deps: none | Files: `portal/src/app/onboarding/page.tsx` (new), `portal/src/app/onboarding/loading.tsx` (new)
  - AC (spec AC-8.2): Server Component calls `supabase.auth.getUser()` -- redirects to `/login` if no user
  - AC (spec AC-8.1): Fetches `/api/v1/portal/stats` with Bearer token -- redirects to `/dashboard` if `onboarded_at` is set (server-side, no flash)
  - AC: Renders `<OnboardingCinematic userId={user.id} />` for authenticated users without `onboarded_at`
  - AC: `loading.tsx` shows centered spinner with "Loading..." text on void background

- [ ] **T2.2**: Create `OnboardingCinematic` client wrapper + scroll-snap layout | Est: M (2hr) | Deps: T2.1 | File: `portal/src/app/onboarding/onboarding-cinematic.tsx` (new)
  - AC (spec WF-12): `"use client"` component wrapping 5 section slots in a `snap-y snap-proximity h-screen overflow-y-auto scroll-smooth bg-void` container
  - AC (spec FR-003): Uses `react-hook-form` with `zodResolver(profileSchema)` for form state across sections 4-5
  - AC (spec AC-6.2): `handleSubmit`: POST to `/api/v1/onboarding/profile`, then `window.open("tg://resolve?domain=Nikita_my_bot", "_self")` with 2s fallback to `https://t.me/Nikita_my_bot`
  - AC (spec AC-6.3): Error state and submitting state passed to MissionSection

- [ ] **T2.3**: Create `ScoreSection` component (Section 1) [P] | Est: M (2hr) | Deps: T2.2 | File: `portal/src/app/onboarding/sections/score-section.tsx` (new)
  - AC (spec AC-2.3): Renders `SectionHeader` with title "The Score" and Nikita quote
  - AC (spec AC-2.1): Renders `ScoreRing` (reused from `@/components/charts/score-ring`) with `score={75}`, `size={200}` (md+) / `size={160}` (mobile)
  - AC (spec AC-2.2): Renders 4 metric mini-cards using `GlassCard` showing Intimacy 68.2, Passion 74.1, Trust 71.8, Secureness 76.0
  - AC: Section wrapped in `<section aria-label="The Score" className="snap-start h-screen ...">` with `max-w-[720px]` inner div
  - AC (spec AC-2.4): Scroll-triggered entrance animation via framer-motion `useInView({ once: true })` -- metric cards stagger fadeInUp
  - AC (spec AC-2.4): `prefers-reduced-motion: reduce` shows final state immediately (no animation)

- [ ] **T2.4**: Create `SectionHeader` and `NikitaQuote` shared components [P] | Est: S (45min) | Deps: T2.2 | Files: `portal/src/app/onboarding/components/section-header.tsx` (new), `portal/src/app/onboarding/components/nikita-quote.tsx` (new)
  - AC: `SectionHeader` renders `<h2>` with `text-xs md:text-sm font-medium uppercase tracking-[0.3em] text-muted-foreground` per spec typography table
  - AC: `NikitaQuote` renders `<blockquote>` with `<cite>` containing "-- Nikita", `text-sm md:text-base italic text-muted-foreground/80`
  - AC: Both accept `className` prop for composition

- [ ] **T2.5**: Create Zod profile schema [P] | Est: S (30min) | Deps: none | File: `portal/src/app/onboarding/schemas.ts` (new)
  - AC (spec FR-003): Schema validates `location_city` (string, min 2 chars), `social_scene` (enum of 5 values), `drug_tolerance` (number 1-5)
  - AC: Exports `ProfileFormValues` type via `z.infer`
  - AC: `social_scene` enum matches backend `VALID_SCENES = {"techno", "art", "food", "cocktails", "nature"}`

---

### US-3: Chapter Section Cinematic

_As a new player, I want to see the chapter progression system so I understand the journey ahead._

- [ ] **T3.1**: Create `ChapterStepper` component | Est: L (5hr) | Deps: T2.4 | File: `portal/src/app/onboarding/components/chapter-stepper.tsx` (new)
  - AC (spec AC-3.1): Props: `currentChapter: number`, `chapters: Array<{ number, name, tagline, locked }>`
  - AC (spec AC-3.2, WF-9): Desktop (md+): horizontal stepper. Active node: rose-500 bg, pulse animation, Check icon. Next node: dashed rose border. Locked nodes: muted bg, Lock icon.
  - AC (spec WF-2b): Mobile (<md): vertical stepper with chapter name/tagline to the right of each node
  - AC (spec WF-9): Connectors: solid rose-500 for completed, dashed rose-500/50 for to-next, muted-foreground/20 for locked
  - AC: `role="list"` container, `role="listitem"` per chapter, `aria-current="step"` on current chapter
  - AC: Scroll-triggered stagger animation: nodes fade-in 0.4s staggered 0.1s, connectors draw after nodes

- [ ] **T3.2**: Create `ChapterSection` (Section 2) | Est: M (1.5hr) | Deps: T3.1 | File: `portal/src/app/onboarding/sections/chapter-section.tsx` (new)
  - AC: Section structure matches snap-start h-screen pattern from T2.3
  - AC (spec AC-3.4): Chapter data: Ch1 "Curiosity" (active), Ch2 "Intrigue" (next), Ch3-5 locked with "???" descriptions
  - AC (spec AC-3.5): Includes SectionHeader ("The Chapters") and NikitaQuote ("We're just getting started...")
  - AC (spec AC-3.2): Active chapter description card (GlassCard) shows Nikita's voice text for current chapter

- [ ] **T3.3**: Create `RulesSection` (Section 3) [P] | Est: M (2hr) | Deps: T2.4 | File: `portal/src/app/onboarding/sections/rules-section.tsx` (new)
  - AC (spec AC-4.1, WF-3/WF-3b): 4 GlassCards in 2x2 grid (md+) / 1-col stack (mobile)
  - AC (spec AC-4.2, AC-4.3): Cards: "How You Score" (Heart), "Time Matters" (Clock), "Boss Encounters" (Shield), "Your Vices" (Flame) -- Nikita-voice copy from spec
  - AC: Each card is a semantic `<article>` with `<h3>` heading
  - AC: Cards fade-in staggered 0.3s via useInView animation
  - AC (spec AC-4.4): Hover/tap: subtle translateY(-2px) lift + glow intensification (CSS transition, not framer-motion)

---

### US-4: Profile Form on Portal

_As a new player, I want to tell Nikita about myself through an engaging visual form._

- [ ] **T4.1**: Create `SceneSelector` component [P] | Est: M (2.5hr) | Deps: T2.5 | File: `portal/src/app/onboarding/components/scene-selector.tsx` (new)
  - AC (spec AC-5.2): Props: `value: string | null`, `onChange: (scene: string) => void`
  - AC (spec WF-10): 5 scene cards (Techno, Art, Food, Cocktails, Nature) with emoji icon, title, and 1-line description
  - AC: Uses shadcn `<RadioGroup>` + `<RadioGroupItem>` (Radix) for accessibility (role="radiogroup", roving tabindex, arrow keys, aria-checked)
  - AC (spec AC-5.2): Selected card: rose-500 border, bg-rose-500/10, glow-rose shadow, Check icon top-right. Unselected: glass-border.
  - AC (spec WF-4/WF-4b): Desktop: 5-in-a-row flex. Mobile: 2-col grid with last card centered.
  - AC: Transition: border-color 150ms ease, background-color 150ms ease (CSS, no framer-motion)

- [ ] **T4.2**: Create `EdginessSlider` component [P] | Est: M (2hr) | Deps: T2.5 | File: `portal/src/app/onboarding/components/edginess-slider.tsx` (new)
  - AC (spec AC-5.3): Props: `value: number`, `onChange: (value: number) => void`
  - AC (spec WF-11): Uses existing shadcn `<Slider>` with `min={1} max={5} step={1}`
  - AC (spec AC-5.3): 5 emoji markers positioned above track at 0%, 25%, 50%, 75%, 100%
  - AC (spec WF-11): Large emoji (text-4xl) + label text for current value with crossfade animation (150ms opacity)
  - AC: `aria-valuetext` set to current label string, `aria-label="Edginess level"`
  - AC: Custom thumb styling via className for rose-500 color and glow

- [ ] **T4.3**: Create `ProfileSection` (Section 4) | Est: M (2hr) | Deps: T4.1, T4.2 | File: `portal/src/app/onboarding/sections/profile-section.tsx` (new)
  - AC (spec WF-12): Section uses `min-h-screen` (not `h-screen`) since form may overflow on mobile
  - AC (spec AC-5.4): Location input in GlassCard with label "Where are you?", placeholder "City, Country", `aria-required="true"`, validation error display with `role="alert"`
  - AC (spec AC-5.2): SceneSelector in GlassCard with label "What's your scene?"
  - AC (spec AC-5.3): EdginessSlider in GlassCard with label "How edgy should I be?"
  - AC (spec AC-5.5): All form fields wired to `react-hook-form` via `form.control` (passed from OnboardingCinematic)
  - AC: Entrance animation: opacity 0 to 1, translateY(20px) to 0, 0.5s ease-out via useInView

- [ ] **T4.4**: Create `MissionSection` (Section 5) [P] | Est: M (1.5hr) | Deps: T2.5 | File: `portal/src/app/onboarding/sections/mission-section.tsx` (new)
  - AC (spec AC-6.1, WF-5): "Don't Get Dumped" headline in `text-2xl md:text-4xl font-bold tracking-tight`
  - AC (spec WF-5): NikitaQuote farewell text ("Keep me interested. Keep me guessing. Make me feel something real. Or I walk.")
  - AC (spec AC-6.1): CTA button "Start Talking to Nikita" with `type="submit"` -- primary rose bg, hover glow, spring entrance animation
  - AC (spec AC-6.2): Shows loading spinner when `submitting` is true, disabled state
  - AC (spec AC-6.3): Shows inline error message (`role="alert"`) when `error` is not null
  - AC: Button entrance: scale 0.9 to 1, spring(1, 80, 10) via framer-motion useInView

- [ ] **T4.5**: Write tests for backend profile endpoint [P] | Est: M (2hr) | Deps: none | File: `tests/api/routes/test_onboarding_profile.py` (new)
  - AC (spec FR-004): Happy path: valid body `{"location_city": "Berlin", "social_scene": "techno", "drug_tolerance": 4}` returns 200 + `{"status": "ok", "user_id": "..."}`
  - AC: Invalid scene `"invalid"` returns 400
  - AC: Empty `location_city` (`""`) returns 422 (Pydantic `min_length=1`)
  - AC: `drug_tolerance` < 1 or > 5 returns 422
  - AC: No JWT returns 401
  - AC (spec FR-004 idempotency): Calling twice with different data updates (not duplicates) profile
  - AC (spec AC-6.5): `user_repo.update_onboarding_status(user_id, "completed")` is called (sets `onboarded_at`)
  - AC (spec NFR-005): Venue research exception is caught and logged, does not fail endpoint (non-blocking)

- [ ] **T4.6**: Implement `POST /api/v1/onboarding/profile` endpoint | Est: M (2hr) | Deps: T4.5 | File: `nikita/api/routes/onboarding.py` (add to EXISTING file)
  - AC (spec FR-004): Pydantic model `OnboardingProfileRequest` with `location_city` (str, min 1, max 100), `social_scene` (str), `drug_tolerance` (int, 1-5)
  - AC: Validates `social_scene` against `VALID_SCENES = {"techno", "art", "food", "cocktails", "nature"}`
  - AC (spec FR-004 idempotency): Creates or updates `user_profiles` row via `ProfileRepository` -- check `get_by_user_id()` first
  - AC (spec AC-6.5): Calls `user_repo.update_onboarding_status(user_id, "completed")` to set `onboarded_at`
  - AC (spec NFR-005): Fire-and-forget venue research via `asyncio.create_task()` -- exception caught, non-blocking
  - AC: Returns `{"status": "ok", "user_id": str(user_id)}`
  - AC: Auth via `Depends(get_current_user_id)` -- same JWT auth pattern as portal routes
  - AC: All 8 tests from T4.5 pass green

---

### US-5: Telegram Return + First Message

_As a new player who completed the portal tour, I want to return to Telegram to start talking to Nikita._

- [ ] **T5.1**: Implement Telegram deep link with fallback | Est: S (30min) | Deps: T4.4 | File: `portal/src/app/onboarding/onboarding-cinematic.tsx` (in `handleSubmit`)
  - AC (spec AC-6.2): After successful POST, `window.open("tg://resolve?domain=Nikita_my_bot", "_self")` fires
  - AC (spec AC-6.4): 2-second `setTimeout` fallback to `window.open("https://t.me/Nikita_my_bot", "_self")` for desktop browsers without Telegram
  - AC (spec AC-6.3): If POST fails, error displayed inline, no redirect fires

---

### US-7: Returning User Redirect (P1 portion)

_As a returning player, I want to go directly to my dashboard when visiting the portal._

- [ ] **T7.1**: Update `UserStatsResponse` schema and portal stats endpoint [P] | Est: M (1.5hr) | Deps: none | Files: `nikita/api/schemas/portal.py`, `nikita/api/routes/portal.py`
  - AC (spec AC-8.1): `onboarded_at: datetime | None = None` added to `UserStatsResponse`
  - AC: `welcome_completed: bool = False` added to `UserStatsResponse`
  - AC: `get_user_stats()` populates `onboarded_at` from `user.onboarded_at` and `welcome_completed` from `user.welcome_completed`
  - AC: Existing portal stats tests still pass

---

### Playwright E2E Test Suite (P1)

- [ ] **T9.1**: E2E tests for page structure (E2E-1 through E2E-4) | Est: M (2hr) | Deps: T2.3, T3.2, T3.3, T4.3, T4.4 | File: `portal/e2e/onboarding.spec.ts` (new)
  - AC: (E2E-1) All 5 sections render with correct `aria-label` attributes
  - AC: (E2E-2) Score ring displays with `data-testid="chart-score-ring"` and `aria-valuenow="75"`
  - AC: (E2E-3) Chapter stepper shows 5 items with Ch.1 having `aria-current="step"`
  - AC: (E2E-4) Rules section shows 4 article elements with heading text matching spec

- [ ] **T9.2**: E2E tests for form interactions (E2E-5 through E2E-7) | Est: M (2hr) | Deps: T9.1 | File: `portal/e2e/onboarding.spec.ts` (add to existing)
  - AC: (E2E-5) Clicking a scene card selects it -- verify `aria-checked="true"` and rose border class
  - AC: (E2E-6) Changing slider value updates displayed emoji and label text
  - AC: (E2E-7) CTA button shows validation error when location empty or scene not selected

- [ ] **T9.3**: E2E tests for submission + mobile (E2E-8 through E2E-10) [P] | Est: M (2hr) | Deps: T9.1 | File: `portal/e2e/onboarding.spec.ts` (add to existing)
  - AC: (E2E-8) CTA submits POST to `/api/v1/onboarding/profile` -- intercept with `page.route()`, verify request body matches form data
  - AC: (E2E-9) Returning user redirect (covered by T7.2)
  - AC: (E2E-10) Mobile viewport (375x812): scene cards in 2-col grid, chapter stepper vertical

---

## P2 -- Fallback & Polish

### US-6: Fallback Text Onboarding

_As a player who didn't click the portal link, I want an alternative onboarding path in Telegram._

- [ ] **T6.1**: Add `ONBOARDING_FALLBACK` to EventType enum [P] | Est: S (15min) | Deps: none | File: `nikita/db/models/scheduled_event.py` (line 48)
  - AC (spec AC-7.1): `ONBOARDING_FALLBACK = "onboarding_fallback"` added to `EventType` enum
  - AC: No migration needed -- enum is Python-side only (stored as string in JSONB)

- [ ] **T6.2**: Write tests for fallback scheduling and delivery | Est: M (2hr) | Deps: T6.1 | Files: `tests/platforms/telegram/test_otp_handler_fallback.py` (new), `tests/onboarding/test_fallback.py` (new)
  - AC (spec AC-7.1): Test `_schedule_onboarding_fallback()` creates event with `event_type=ONBOARDING_FALLBACK`, `scheduled_at` ~5 min in future, content contains `chat_id` and `telegram_id`
  - AC: Test `_schedule_onboarding_fallback()` failure does not raise (logs warning)
  - AC (spec AC-7.2): Test fallback delivery: when `onboarded_at` IS NULL, sends fallback message + calls `OnboardingHandler.start()`
  - AC (spec AC-7.3): Test fallback delivery: when `onboarded_at` IS NOT NULL, event discarded silently

- [ ] **T6.3**: Implement `_schedule_onboarding_fallback()` and event handler | Est: M (3hr) | Deps: T6.2 | Files: `nikita/platforms/telegram/otp_handler.py` (add method), event delivery handler
  - AC (spec AC-7.1): Creates scheduled event 5 minutes in future using `ScheduledEventRepository.create_event()` with `EventType.ONBOARDING_FALLBACK`
  - AC: Event content JSON: `{"chat_id": int, "telegram_id": int}`
  - AC (spec NFR-005): Failure in scheduling does not block the magic link message (try/except with logger.warning)
  - AC (spec AC-7.3, WF-7): Event handler checks `users.onboarded_at` -- if set, discards event. If null, sends fallback message per WF-7 copy and calls `OnboardingHandler.start()`
  - AC: All 4 tests from T6.2 pass green

### US-8: Returning User Redirect (P2 E2E portion)

- [ ] **T7.2**: E2E test for returning user redirect | Est: S (1hr) | Deps: T2.1, T7.1 | File: `portal/e2e/onboarding.spec.ts` (add to existing)
  - AC (spec AC-8.1): Mock `/api/v1/portal/stats` with `onboarded_at: "2026-03-22T10:00:00Z"` -- navigate to `/onboarding` -- assert redirect to `/dashboard`
  - AC (spec AC-8.3): Mock `/api/v1/portal/stats` with `onboarded_at: null` -- navigate to `/onboarding` -- assert onboarding page renders (server-side redirect, no flash)

---

## P3 -- Progressive Drips (Phase 2)

### US-9: Progressive Drips

_Phase 2 -- deferred until portal onboarding is validated._

- [ ] **T8.1**: DB migration -- add `drips_delivered` and `welcome_completed` columns | Est: M (1hr) | Deps: none | Files: Supabase MCP (apply DDL), `supabase/migrations/20260322100000_add_drips_and_welcome.sql` (2-line comment stub)
  - AC: `ALTER TABLE users ADD COLUMN drips_delivered JSONB NOT NULL DEFAULT '{}'::jsonb` applied
  - AC: `ALTER TABLE users ADD COLUMN welcome_completed BOOLEAN NOT NULL DEFAULT false` applied
  - AC: Comment stub created in migrations directory
  - AC: Existing RLS policy covers new columns (no additional policy needed)

- [ ] **T8.2**: Update SQLAlchemy User model | Est: S (30min) | Deps: T8.1 | File: `nikita/db/models/user.py`
  - AC: `drips_delivered: Mapped[dict]` with `JSONB, default=dict, server_default=text("'{}'::jsonb")`
  - AC: `welcome_completed: Mapped[bool]` with `Boolean, default=False, server_default=text("false")`
  - AC: All existing user model tests pass

- [ ] **T8.3**: Implement DripManager class | Est: L (5hr) | Deps: T8.2 | File: `nikita/onboarding/drip_manager.py` (new)
  - AC: 7 drip definitions per spec table (first_score, portal_intro, first_decay, chapter_advance, boss_warning, boss_debrief, nikitas_world)
  - AC: `evaluate_user(user)` returns list of eligible drips based on user state
  - AC: Rate limiting: max 1 drip per 2 hours per user (checked against `drips_delivered` timestamps)
  - AC: Each drip generates magic link portal button (reuses `_generate_portal_magic_link` pattern)

- [ ] **T8.4**: Write DripManager tests | Est: L (4hr) | Deps: T8.3 | File: `tests/onboarding/test_drip_manager.py` (new)
  - AC: 7 positive trigger tests (one per drip condition from spec drip table)
  - AC: 7 negative tests (condition not met, drip not returned)
  - AC: Rate limiting test: drip delivered <2hr ago is suppressed
  - AC: All 14+ tests pass

- [ ] **T8.5**: Implement pg_cron `check-drips` task endpoint | Est: M (2hr) | Deps: T8.3 | File: `nikita/api/routes/tasks.py` (add endpoint)
  - AC: `POST /api/v1/tasks/check-drips` endpoint with task auth
  - AC: Evaluates all active users with `DripManager.evaluate_user()`
  - AC: Sends Telegram messages with portal magic link buttons for eligible drips
  - AC: Records delivered drips in `users.drips_delivered` JSONB

---

## Deployment Tasks

- [ ] **T10.1**: Verify environment configuration [P] | Est: S (15min) | Deps: none
  - AC: `PORTAL_URL=https://portal-phi-orcin.vercel.app` in Cloud Run env vars
  - AC: `SUPABASE_SERVICE_KEY` is set (needed for `admin.generate_link()`)

- [ ] **T10.2**: Install shadcn `radio-group` if missing [P] | Est: S (15min) | Deps: none
  - AC: Run `cd portal && npx shadcn add radio-group` if `portal/src/components/ui/radio-group.tsx` doesn't exist
  - AC: Component imports work in SceneSelector

- [ ] **T10.3**: Deploy backend | Est: S (15min) | Deps: all backend tasks (T1.1-T1.3, T4.5-T4.6, T6.1-T6.3, T7.1)
  - AC: `gcloud run deploy nikita-api --source . --region us-central1 --project gcp-transcribe-test --allow-unauthenticated` succeeds
  - AC: `POST /api/v1/onboarding/profile` responds 401 without JWT (endpoint active)

- [ ] **T10.4**: Deploy portal | Est: S (15min) | Deps: all portal tasks (T2.1-T2.5, T3.1-T3.3, T4.1-T4.4, T5.1, T9.1-T9.3)
  - AC: `cd portal && npm run build && vercel --prod` succeeds
  - AC: `/onboarding` page loads (redirects to `/login` without auth)

- [ ] **T10.5**: End-to-end verification | Est: M (1hr) | Deps: T10.3, T10.4
  - AC: Send `/start` to `@Nikita_my_bot` -> OTP flow -> magic link button appears
  - AC: Click magic link -> portal `/onboarding` loads with all 5 sections
  - AC: Fill form + submit -> profile saved in DB, `onboarded_at` set
  - AC: Deep link returns to Telegram

---

## Dependency Graph

```
Phase 1 (P1) -- Core Flow:

  T2.5 (schema) -----------------------------------------------+
  T2.4 (SectionHeader/Quote) -----+----------------------------+ |
  T2.1 (page.tsx) --> T2.2 (Cinematic) --+--> T2.3 (S1)        | |
                                         |                      | |
  T3.1 (ChapterStepper) --> T3.2 (S2) <-+                      | |
  T3.3 (S3: Rules) <-------------------------------------------+ |
                                                                  |
  T4.1 (SceneSelector) --+--> T4.3 (S4: Profile) <---------------+
  T4.2 (EdginessSlider) -+
  T4.4 (S5: Mission) --> T5.1 (deep link)

  T1.1 (tests) --> T1.2 (magic link gen) --> T1.3 (replace choice)
  T4.5 (tests) --> T4.6 (profile endpoint)
  T7.1 (stats schema)

  E2E: T9.1 --> T9.2
               --> T9.3 [P]

Phase 2 (P2) -- Fallback:

  T6.1 (EventType) --> T6.2 (tests) --> T6.3 (fallback impl)
  T7.2 (E2E redirect)

Phase 3 (P3) -- Drips:

  T8.1 (migration) --> T8.2 (model) --> T8.3 (DripManager) --> T8.4 (tests)
                                                             --> T8.5 (cron)

Deployment:

  T10.1, T10.2 (parallel prep)
  All backend --> T10.3 (deploy backend)
  All portal  --> T10.4 (deploy portal)
  T10.3 + T10.4 --> T10.5 (E2E verify)
```

## Requirements Traceability

| Requirement | Tasks |
|---|---|
| FR-001: Replace voice/text choice with magic link | T1.1, T1.2, T1.3 |
| FR-002: Cinematic scroll experience at /onboarding | T2.1-T2.5, T3.1-T3.3, T4.1-T4.4 |
| FR-003: Profile collection via portal form | T4.1-T4.4 |
| FR-004: Backend profile endpoint | T4.5, T4.6 |
| FR-005: Telegram deep link return | T5.1 |
| FR-006: Fallback text onboarding (5 min) | T6.1, T6.2, T6.3 |
| FR-007: Returning user detection | T7.1, T7.2 |
| FR-008: Auth bridge via admin.generateLink() | T1.2 |
| NFR-001: Magic link latency <2s | T1.2 (verified in T10.5) |
| NFR-002: Page load <3s on 3G | T2.1-T2.2 (verified in T10.5) |
| NFR-003: Profile submission <1s | T4.6 (verified in T10.5) |
| NFR-004: Fallback delivery 5 min +/- 1 min | T6.3 (verified in T10.5) |
| NFR-005: Failure isolation | T1.2 (AC2), T4.6 (AC5), T6.3 (AC3) |
