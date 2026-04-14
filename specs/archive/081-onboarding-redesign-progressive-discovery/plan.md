# Implementation Plan: Portal-First Cinematic Onboarding

**Spec**: `specs/081-onboarding-redesign-progressive-discovery/spec.md`
**Status**: Ready
**Complexity**: 5
**Priority**: P1 (core), P2 (fallback/returning), P3 (drips)
**Date**: 2026-03-22

---

## Overview

Replace the voice/text onboarding choice after OTP verification with a single "Enter Nikita's World" magic link that opens a cinematic scroll experience on the portal. The portal teaches scoring, chapters, and rules through 5 immersive sections, collects a 3-field profile (location, scene, edginess), then deep-links the player back to Telegram. A 5-minute fallback ensures players who skip the portal link still get the existing text onboarding.

**Key changes**:
- Backend: Magic link generation in OTP handler, new `POST /api/v1/onboarding/profile` endpoint, `EventType.ONBOARDING_FALLBACK` in scheduled events, `drips_delivered`/`welcome_completed` columns
- Portal: `/onboarding` route with 5 scroll-snap sections, 3 new components (ChapterStepper, SceneSelector, EdginessSlider), Zod form validation
- Telegram: Replace `_offer_onboarding_choice()` from voice/text to magic link + schedule fallback

---

## Architecture Diagram

```
TELEGRAM (OTP handler)                 PORTAL (/onboarding)                   BACKEND (FastAPI)
========================               ======================                ==================

[OTP verified]
     |
     v
_offer_onboarding_choice()
     |
     +---> generate_portal_magic_link()
     |     (admin.generate_link via
     |      supabase service role key)
     |
     +---> Send "Enter Nikita's World"
     |     URL button (magic link)
     |
     +---> _schedule_onboarding_fallback()
           (scheduled_events, 5 min)

     [Player clicks]  ---------->  /auth/callback?code=...&next=/onboarding
                                        |
                                   exchangeCodeForSession()
                                        |
                                   /onboarding (page.tsx)
                                   Server Component:
                                     - getUser() -> redirect /login if none
                                     - fetch /portal/stats
                                     - if onboarded_at -> redirect /dashboard
                                        |
                                   OnboardingCinematic (client)
                                     S1: ScoreSection (ScoreRing reuse)
                                     S2: ChapterSection (ChapterStepper)
                                     S3: RulesSection (GlassCard reuse)
                                     S4: ProfileSection (form)
                                     S5: MissionSection (CTA)
                                        |
                                   [CTA: Submit + Redirect]
                                        |
                                   POST /api/v1/onboarding/profile -------> save_onboarding_profile()
                                        |                                      - ProfileRepository.create_profile()
                                   tg://resolve?domain=Nikita_my_bot           - update_onboarding_status("completed")
                                        |                                      - asyncio.create_task(venue_research)
                                        v
                              [Player returns to Telegram]
```

---

## Dependencies

| Dependency | Type | Status | Notes |
|---|---|---|---|
| Supabase `admin.generate_link()` | External API | Available | Requires service role key (already in `TelegramAuth`) |
| `ProfileRepository.create_profile()` | Internal | Exists | `nikita/db/repositories/profile_repository.py:61` |
| `UserRepository.update_onboarding_status()` | Internal | Exists | Sets `onboarded_at` + `onboarding_status` |
| `ScheduledEventRepository.create_event()` | Internal | Exists | `nikita/db/repositories/scheduled_event_repository.py:53` |
| `users.onboarded_at` column | DB | Exists | Already set by existing flows |
| `ScoreRing` component | Portal | Exists | `portal/src/components/charts/score-ring.tsx` |
| `GlassCard` component | Portal | Exists | `portal/src/components/glass/glass-card.tsx` |
| shadcn `Slider` component | Portal | Exists | `portal/src/components/ui/slider.tsx` |
| shadcn `RadioGroup` component | Portal | Check | May need `npx shadcn add radio-group` |
| framer-motion | Portal | Exists | Already bundled (used by ScoreRing, MoodOrb) |
| `portal/src/app/auth/callback/route.ts` | Portal | Exists | Handles `?next=/onboarding` via `searchParams.get("next")` |
| Supabase middleware auth | Portal | Exists | `portal/src/lib/supabase/middleware.ts` - `/onboarding` auto-protected |
| `VenueResearchService` | Internal | Exists | `nikita/services/venue_research.py` |
| `EventType` enum | Internal | Needs update | Add `ONBOARDING_FALLBACK` variant |
| `UserStatsResponse` schema | Internal | Needs update | Add `onboarded_at`, `welcome_completed` fields |

---

## Requirements Coverage

| Requirement | Tasks |
|---|---|
| FR-001: Replace voice/text choice with magic link | T1.1, T1.2, T1.3 |
| FR-002: Cinematic scroll experience at /onboarding | T2.1-T2.5, T3.1-T3.3, T4.1-T4.4 |
| FR-003: Profile collection via portal form | T4.1-T4.4 |
| FR-004: Backend profile endpoint | T4.5, T4.6 |
| FR-005: Telegram deep link return | T5.1 |
| FR-006: Fallback text onboarding (5 min) | T6.1, T6.2, T6.3 |
| FR-007: Returning user detection | T7.1 |
| FR-008: Auth bridge via admin.generateLink() | T1.2 |

---

## Tasks by User Story

---

### US-1: Portal Redirect After OTP (P1)

_As a new player who just verified OTP, I want to be taken to a visual introduction of Nikita's world._

| ID | Task | Est | Deps | [P] |
|---|---|---|---|---|
| T1.1 | Tests: OTP handler magic link + message | M | - | |
| T1.2 | Impl: `_generate_portal_magic_link()` method | M | T1.1 | |
| T1.3 | Impl: Replace `_offer_onboarding_choice()` body | M | T1.2 | |

**T1.1: Write tests for magic link generation and OTP handler message**
- **File**: `tests/platforms/telegram/test_otp_handler_onboarding.py` (new)
- **Est**: M (2hr)
- **ACs**:
  - AC1: Test `_generate_portal_magic_link()` success path returns URL from `result.properties.action_link` (mock `supabase.auth.admin.get_user_by_id()` returning user with email, mock `supabase.auth.admin.generate_link()` returning `MagicMock(properties=MagicMock(action_link="https://test.supabase.co/auth/v1/verify?token=abc"))`)
  - AC2: Test `_generate_portal_magic_link()` returns `None` when user has no email
  - AC3: Test `_generate_portal_magic_link()` returns `None` on Supabase error (exception swallowed, logged)
  - AC4: Test `_generate_portal_magic_link()` returns `None` when `supabase_url` or `supabase_service_key` not configured
  - AC5: Test `_offer_onboarding_choice()` sends Telegram message with single URL button containing magic link URL (verify `bot.send_message_with_keyboard` called with `keyboard=[[{"text": "Enter Nikita's World  ...", "url": magic_link_url}]]`)
  - AC6: Test `_offer_onboarding_choice()` falls back to `{portal_url}/login?next=/onboarding` when magic link returns `None`
  - AC7: Test `_offer_onboarding_choice()` calls `_schedule_onboarding_fallback()` after sending message
- **Notes**: Follow existing mock patterns in `tests/platforms/telegram/test_otp_handler.py`. The OTPVerificationHandler needs access to the Supabase client for `admin.generate_link()` -- currently it accesses it via `self.telegram_auth.supabase`.

**T1.2: Implement `_generate_portal_magic_link()` on OTPVerificationHandler**
- **File**: `nikita/platforms/telegram/otp_handler.py` (add method at ~line 375)
- **Est**: M (1.5hr)
- **Deps**: T1.1
- **ACs**:
  - AC1: Method signature: `async def _generate_portal_magic_link(self, user_id: str, redirect_path: str) -> str | None`
  - AC2: Returns `None` gracefully on any failure (missing config, no email, Supabase error) with `logger.warning`
  - AC3: Uses `self.telegram_auth.supabase.auth.admin.get_user_by_id(user_id)` to look up email, then `self.telegram_auth.supabase.auth.admin.generate_link(...)` with `type="magiclink"`, `email=email`, `redirect_to=f"{portal_url}/onboarding"`
  - AC4: Returns `result.properties.action_link` on success
  - AC5: All 4 tests from T1.1 (AC1-AC4) pass green

**T1.3: Replace `_offer_onboarding_choice()` method body**
- **File**: `nikita/platforms/telegram/otp_handler.py` (modify lines 326-377)
- **Est**: M (1.5hr)
- **Deps**: T1.2
- **ACs**:
  - AC1: Voice call URL button and text callback button are removed; replaced with single URL button "Enter Nikita's World"
  - AC2: Message text updated to spec WF-6 copy ("You're in! ... Tap below -- it'll only take a minute.")
  - AC3: `handle_callback()` method (lines 379-424) -- retain for backward compatibility but the `onboarding_text` callback is no longer triggered by new users
  - AC4: All existing OTP handler tests in `tests/platforms/telegram/test_otp_handler.py` still pass (no regressions)
  - AC5: Tests from T1.1 (AC5-AC7) pass green

---

### US-2: Score Section Cinematic (P1)

_As a new player on the onboarding page, I want to learn about the scoring system visually._

| ID | Task | Est | Deps | [P] |
|---|---|---|---|---|
| T2.1 | Portal: `/onboarding` route shell (Server Component) | M | - | [P] |
| T2.2 | Portal: `OnboardingCinematic` client wrapper + scroll-snap layout | M | T2.1 | |
| T2.3 | Portal: `ScoreSection` component | M | T2.2 | [P] |
| T2.4 | Portal: `SectionHeader` + `NikitaQuote` shared components | S | T2.2 | [P] |
| T2.5 | Portal: `onboarding/schemas.ts` Zod schema | S | - | [P] |

**T2.1: Create `/onboarding` route with Server Component auth gate**
- **Files**: `portal/src/app/onboarding/page.tsx` (new), `portal/src/app/onboarding/loading.tsx` (new)
- **Est**: M (2hr)
- **ACs**:
  - AC1: Server Component calls `supabase.auth.getUser()` -- redirects to `/login` if no user
  - AC2: Fetches `/api/v1/portal/stats` with Bearer token -- redirects to `/dashboard` if `onboarded_at` is set (server-side, no flash)
  - AC3: Renders `<OnboardingCinematic userId={user.id} />` for authenticated users without `onboarded_at`
  - AC4: `loading.tsx` shows centered spinner with "Loading..." text on void background
- **Notes**: Follow pattern from `portal/src/app/dashboard/page.tsx`. The `fetch()` call uses `cache: "no-store"` for fresh data. Auth callback already handles `?next=/onboarding` via existing `searchParams.get("next")` logic in `portal/src/app/auth/callback/route.ts:9`.

**T2.2: Create `OnboardingCinematic` client component with scroll-snap**
- **File**: `portal/src/app/onboarding/onboarding-cinematic.tsx` (new)
- **Est**: M (2hr)
- **Deps**: T2.1
- **ACs**:
  - AC1: `"use client"` component wrapping 5 section slots in a `snap-y snap-proximity h-screen overflow-y-auto scroll-smooth bg-void` container
  - AC2: Uses `react-hook-form` with `zodResolver(profileSchema)` for form state across sections 4-5
  - AC3: `handleSubmit` function: POST to `/api/v1/onboarding/profile`, then `window.open("tg://resolve?domain=Nikita_my_bot", "_self")` with 2s fallback to `https://t.me/Nikita_my_bot`
  - AC4: Error state (`useState<string | null>`) and submitting state (`useState(false)`) passed to MissionSection

**T2.3: Create `ScoreSection` component (Section 1)**
- **File**: `portal/src/app/onboarding/sections/score-section.tsx` (new)
- **Est**: M (2hr)
- **Deps**: T2.2
- **ACs**:
  - AC1: Renders `SectionHeader` with title "The Score" and Nikita quote
  - AC2: Renders `ScoreRing` (reused from `@/components/charts/score-ring`) with `score={75}` (starting score), `size={200}` (md+) / `size={160}` (mobile)
  - AC3: Renders 4 metric mini-cards using `GlassCard` (reused from `@/components/glass/glass-card`) showing Intimacy 68.2, Passion 74.1, Trust 71.8, Secureness 76.0 (hardcoded starting values)
  - AC4: Section wrapped in `<section aria-label="The Score" className="snap-start h-screen flex flex-col items-center justify-center px-4 md:px-8 py-12 md:py-16">` with `max-w-[720px]` inner div
  - AC5: Scroll-triggered entrance animation via framer-motion `useInView({ once: true })` -- metric cards stagger fadeInUp
  - AC6: `prefers-reduced-motion: reduce` shows final state immediately (no animation)

**T2.4: Create `SectionHeader` and `NikitaQuote` shared components**
- **Files**: `portal/src/app/onboarding/components/section-header.tsx` (new), `portal/src/app/onboarding/components/nikita-quote.tsx` (new)
- **Est**: S (45min)
- **Deps**: T2.2
- **ACs**:
  - AC1: `SectionHeader` renders `<h2>` with uppercase tracking-[0.3em] styling per spec typography table
  - AC2: `NikitaQuote` renders `<blockquote>` with `<cite>` containing "-- Nikita", italic muted text
  - AC3: Both accept `className` prop for composition

**T2.5: Create Zod profile schema**
- **File**: `portal/src/app/onboarding/schemas.ts` (new)
- **Est**: S (30min)
- **ACs**:
  - AC1: Schema validates `location_city` (string, min 2 chars), `social_scene` (enum of 5 values), `drug_tolerance` (number 1-5)
  - AC2: Exports `ProfileFormValues` type via `z.infer`
  - AC3: `social_scene` enum matches backend `VALID_SCENES = {"techno", "art", "food", "cocktails", "nature"}`

---

### US-3: Chapter Section Cinematic (P1)

_As a new player, I want to see the chapter progression system so I understand the journey ahead._

| ID | Task | Est | Deps | [P] |
|---|---|---|---|---|
| T3.1 | Portal: `ChapterStepper` component | L | T2.4 | |
| T3.2 | Portal: `ChapterSection` component (Section 2) | M | T3.1 | |
| T3.3 | Portal: `RulesSection` component (Section 3) | M | T2.4 | [P] |

**T3.1: Create `ChapterStepper` component**
- **File**: `portal/src/app/onboarding/components/chapter-stepper.tsx` (new)
- **Est**: L (5hr)
- **ACs**:
  - AC1: Props: `currentChapter: number`, `chapters: Array<{ number, name, tagline, locked }>` with default 5-chapter data
  - AC2: Desktop (md+): horizontal stepper with node + connector line pattern per WF-9. Active node: rose-500 bg, pulse animation, Check icon. Next node: dashed rose border. Locked nodes: muted bg, Lock icon.
  - AC3: Mobile (<md): vertical stepper with chapter name/tagline to the right of each node per WF-2b
  - AC4: Connectors: solid rose-500 for completed, dashed rose-500/50 for to-next, muted-foreground/20 for locked
  - AC5: `role="list"` container, `role="listitem"` per chapter, `aria-current="step"` on current chapter
  - AC6: Scroll-triggered stagger animation: nodes fade-in 0.4s staggered 0.1s, connectors draw after nodes
- **Notes**: Lucide icons: `Check` (active), `Lock` (locked). Responsive via `md:flex-row flex-col`.

**T3.2: Create `ChapterSection` (Section 2)**
- **File**: `portal/src/app/onboarding/sections/chapter-section.tsx` (new)
- **Est**: M (1.5hr)
- **Deps**: T3.1
- **ACs**:
  - AC1: Section structure matches snap-start h-screen pattern from T2.3
  - AC2: Chapter data: Ch1 "Curiosity" (active), Ch2 "Intrigue" (next), Ch3-5 locked with "???" descriptions
  - AC3: Includes SectionHeader ("The Chapters") and NikitaQuote ("We're just getting started...")
  - AC4: Active chapter description card (GlassCard) shows Nikita's voice text for current chapter

**T3.3: Create `RulesSection` (Section 3)**
- **File**: `portal/src/app/onboarding/sections/rules-section.tsx` (new)
- **Est**: M (2hr)
- **Deps**: T2.4
- **ACs**:
  - AC1: 4 GlassCards in 2x2 grid (md+) / 1-col stack (mobile) per WF-3/WF-3b
  - AC2: Cards: "How You Score" (Heart icon), "Time Matters" (Clock icon), "Boss Encounters" (Shield icon), "Your Vices" (Flame icon) -- all with Nikita-voice copy from spec
  - AC3: Each card is a semantic `<article>` with `<h3>` heading
  - AC4: Cards fade-in staggered 0.3s via useInView animation
  - AC5: Hover/tap interaction: subtle translateY(-2px) lift + glow intensification (CSS transition, not framer-motion)

---

### US-4: Profile Form on Portal (P1)

_As a new player, I want to tell Nikita about myself through an engaging visual form._

| ID | Task | Est | Deps | [P] |
|---|---|---|---|---|
| T4.1 | Portal: `SceneSelector` component | M | T2.5 | [P] |
| T4.2 | Portal: `EdginessSlider` component | M | T2.5 | [P] |
| T4.3 | Portal: `ProfileSection` (Section 4) | M | T4.1, T4.2 | |
| T4.4 | Portal: `MissionSection` (Section 5) | M | T2.5 | [P] |
| T4.5 | Tests: Backend profile endpoint | M | - | [P] |
| T4.6 | Impl: Backend `POST /api/v1/onboarding/profile` | M | T4.5 | |

**T4.1: Create `SceneSelector` component**
- **File**: `portal/src/app/onboarding/components/scene-selector.tsx` (new)
- **Est**: M (2.5hr)
- **ACs**:
  - AC1: Props: `value: string | null`, `onChange: (scene: string) => void`
  - AC2: 5 scene cards (Techno, Art, Food, Cocktails, Nature) with emoji icon, title, and 1-line description per WF-10
  - AC3: Uses shadcn `<RadioGroup>` + `<RadioGroupItem>` (Radix) for accessibility (role="radiogroup", roving tabindex, arrow keys, aria-checked). If not installed, run `npx shadcn add radio-group` first.
  - AC4: Selected card: rose-500 border, bg-rose-500/10, glow-rose shadow, Check icon top-right. Unselected: glass-border.
  - AC5: Desktop: 5-in-a-row flex. Mobile: 2-col grid with last card centered.
  - AC6: Transition: border-color 150ms ease, background-color 150ms ease (CSS, no framer-motion)

**T4.2: Create `EdginessSlider` component**
- **File**: `portal/src/app/onboarding/components/edginess-slider.tsx` (new)
- **Est**: M (2hr)
- **ACs**:
  - AC1: Props: `value: number`, `onChange: (value: number) => void`
  - AC2: Uses existing shadcn `<Slider>` (`portal/src/components/ui/slider.tsx`) with `min={1} max={5} step={1}`
  - AC3: 5 emoji markers positioned above track at 0%, 25%, 50%, 75%, 100%
  - AC4: Large emoji (text-4xl) + label text for current value with crossfade animation (150ms opacity)
  - AC5: `aria-valuetext` set to current label string, `aria-label="Edginess level"`
  - AC6: Custom thumb styling via className for rose-500 color and glow

**T4.3: Create `ProfileSection` (Section 4)**
- **File**: `portal/src/app/onboarding/sections/profile-section.tsx` (new)
- **Est**: M (2hr)
- **Deps**: T4.1, T4.2
- **ACs**:
  - AC1: Section uses `min-h-screen` (not `h-screen`) since form may overflow on mobile per WF-12
  - AC2: Location input in GlassCard with label "Where are you?", placeholder "City, Country", `aria-required="true"`, validation error display with `role="alert"`
  - AC3: SceneSelector in GlassCard with label "What's your scene?"
  - AC4: EdginessSlider in GlassCard with label "How edgy should I be?"
  - AC5: All form fields wired to `react-hook-form` via `form.control` (passed from OnboardingCinematic)
  - AC6: Entrance animation: opacity 0 to 1, translateY(20px) to 0, 0.5s ease-out via useInView

**T4.4: Create `MissionSection` (Section 5)**
- **File**: `portal/src/app/onboarding/sections/mission-section.tsx` (new)
- **Est**: M (1.5hr)
- **ACs**:
  - AC1: "Don't Get Dumped" headline in `text-2xl md:text-4xl font-bold tracking-tight`
  - AC2: NikitaQuote farewell text from spec WF-5
  - AC3: CTA button "Start Talking to Nikita" with `type="submit"` -- primary rose bg, hover glow, spring entrance animation
  - AC4: Shows loading spinner when `submitting` is true, disabled state
  - AC5: Shows inline error message (`role="alert"`) when `error` is not null
  - AC6: Button entrance: scale 0.9 to 1, spring(1, 80, 10) via framer-motion useInView

**T4.5: Write tests for backend profile endpoint**
- **File**: `tests/api/routes/test_onboarding_profile.py` (new)
- **Est**: M (2hr)
- **ACs**:
  - AC1: Happy path: valid body `{"location_city": "Berlin", "social_scene": "techno", "drug_tolerance": 4}` returns 200 + `{"status": "ok", "user_id": "..."}`
  - AC2: Invalid scene `"invalid"` returns 400
  - AC3: Empty `location_city` (`""`) returns 422 (Pydantic `min_length=1`)
  - AC4: `drug_tolerance` < 1 or > 5 returns 422
  - AC5: No JWT returns 401
  - AC6: Idempotency: calling twice with different data updates (not duplicates) profile -- mock `profile_repo.get_by_user_id()` returning existing profile on second call
  - AC7: `user_repo.update_onboarding_status(user_id, "completed")` is called (sets `onboarded_at`)
  - AC8: Venue research exception is caught and logged, does not fail endpoint (non-blocking)
- **Notes**: Follow auth dependency patterns from `nikita/api/routes/portal.py:13` -- import `get_current_user_id` from `nikita.api.dependencies.auth`, `get_async_session` from `nikita.db.database`.

**T4.6: Implement `POST /api/v1/onboarding/profile` endpoint**
- **File**: `nikita/api/routes/onboarding.py` (add to EXISTING file, router already at `/api/v1/onboarding`)
- **Est**: M (2hr)
- **Deps**: T4.5
- **ACs**:
  - AC1: Pydantic model `OnboardingProfileRequest` with `location_city` (str, min 1, max 100), `social_scene` (str), `drug_tolerance` (int, 1-5)
  - AC2: Validates `social_scene` against `VALID_SCENES = {"techno", "art", "food", "cocktails", "nature"}`
  - AC3: Creates or updates `user_profiles` row via `ProfileRepository` -- check `get_by_user_id()` first for idempotency
  - AC4: Calls `user_repo.update_onboarding_status(user_id, "completed")` to set `onboarded_at`
  - AC5: Fire-and-forget venue research via `asyncio.create_task()` -- exception caught, non-blocking
  - AC6: Returns `{"status": "ok", "user_id": str(user_id)}`
  - AC7: Auth via `Depends(get_current_user_id)` -- same JWT auth pattern as portal routes
  - AC8: All 8 tests from T4.5 pass green

---

### US-5: Telegram Return + First Message (P1)

_As a new player who completed the portal tour, I want to return to Telegram to start talking to Nikita._

| ID | Task | Est | Deps | [P] |
|---|---|---|---|---|
| T5.1 | Portal: Deep link handler in MissionSection CTA | S | T4.4 | |

**T5.1: Implement Telegram deep link with fallback**
- **File**: `portal/src/app/onboarding/onboarding-cinematic.tsx` (in `handleSubmit`)
- **Est**: S (30min)
- **Deps**: T4.4
- **ACs**:
  - AC1: After successful POST, `window.open("tg://resolve?domain=Nikita_my_bot", "_self")` fires
  - AC2: 2-second `setTimeout` fallback to `window.open("https://t.me/Nikita_my_bot", "_self")` for desktop browsers without Telegram
  - AC3: If POST fails, error displayed inline, no redirect fires
- **Notes**: The first Nikita message in Telegram is already sent by the existing handoff flow. No backend changes needed.

---

### US-6: Fallback Text Onboarding (P2)

_As a player who didn't click the portal link, I want an alternative onboarding path in Telegram._

| ID | Task | Est | Deps | [P] |
|---|---|---|---|---|
| T6.1 | DB: Add `ONBOARDING_FALLBACK` to `EventType` enum | S | - | [P] |
| T6.2 | Tests: Fallback scheduling + delivery | M | T6.1 | |
| T6.3 | Impl: `_schedule_onboarding_fallback()` + event handler | M | T6.2 | |

**T6.1: Add `ONBOARDING_FALLBACK` to EventType enum**
- **File**: `nikita/db/models/scheduled_event.py` (line 48, add to enum)
- **Est**: S (15min)
- **ACs**:
  - AC1: `ONBOARDING_FALLBACK = "onboarding_fallback"` added to `EventType` enum at line 48
  - AC2: No migration needed -- enum is Python-side only (stored as string in JSONB)

**T6.2: Write tests for fallback scheduling and delivery**
- **Files**: `tests/platforms/telegram/test_otp_handler_fallback.py` (new), `tests/onboarding/test_fallback.py` (new)
- **Est**: M (2hr)
- **ACs**:
  - AC1: Test `_schedule_onboarding_fallback()` creates event in `scheduled_events` with `event_type=ONBOARDING_FALLBACK`, `scheduled_at` ~5 min in future, content contains `chat_id` and `telegram_id`
  - AC2: Test `_schedule_onboarding_fallback()` failure does not raise (logs warning)
  - AC3: Test fallback delivery: when `onboarded_at` IS NULL, sends fallback message + calls `OnboardingHandler.start()`
  - AC4: Test fallback delivery: when `onboarded_at` IS NOT NULL, event discarded silently

**T6.3: Implement `_schedule_onboarding_fallback()` and event handler**
- **Files**: `nikita/platforms/telegram/otp_handler.py` (add method), event delivery handler (modify existing `deliver` task handler)
- **Est**: M (3hr)
- **Deps**: T6.2
- **ACs**:
  - AC1: `_schedule_onboarding_fallback()` creates scheduled event 5 minutes in future using `ScheduledEventRepository.create_event()` with `EventType.ONBOARDING_FALLBACK`
  - AC2: Event content JSON: `{"chat_id": int, "telegram_id": int}`
  - AC3: Failure in scheduling does not block the magic link message (try/except with logger.warning)
  - AC4: Event handler (in `deliver` task) checks `users.onboarded_at` -- if set, discards event. If null, sends fallback message per WF-7 copy and calls `OnboardingHandler.start()`
  - AC5: All 4 tests from T6.2 pass green

---

### US-7: Returning User Redirect (P2)

_As a returning player, I want to go directly to my dashboard when visiting the portal._

| ID | Task | Est | Deps | [P] |
|---|---|---|---|---|
| T7.1 | Backend: Add `onboarded_at` + `welcome_completed` to stats response | M | - | [P] |
| T7.2 | E2E: Returning user redirect test | S | T2.1, T7.1 | |

**T7.1: Update `UserStatsResponse` schema and portal stats endpoint**
- **Files**: `nikita/api/schemas/portal.py` (modify `UserStatsResponse`), `nikita/api/routes/portal.py` (modify `get_user_stats`)
- **Est**: M (1.5hr)
- **ACs**:
  - AC1: `onboarded_at: datetime | None = None` added to `UserStatsResponse` (after existing `last_interaction_at` field at line 38)
  - AC2: `welcome_completed: bool = False` added to `UserStatsResponse`
  - AC3: `get_user_stats()` populates `onboarded_at` from `user.onboarded_at` and `welcome_completed` from `user.welcome_completed`
  - AC4: Existing portal stats tests still pass
- **Notes**: The Server Component in `/onboarding/page.tsx` (T2.1) reads `stats.onboarded_at` to decide redirect.

**T7.2: E2E test for returning user redirect**
- **File**: `portal/e2e/onboarding.spec.ts` (new, add as part of E2E suite)
- **Est**: S (1hr)
- **Deps**: T2.1, T7.1
- **ACs**:
  - AC1: Mock `/api/v1/portal/stats` with `onboarded_at: "2026-03-22T10:00:00Z"` -- navigate to `/onboarding` -- assert redirect to `/dashboard`
  - AC2: Mock `/api/v1/portal/stats` with `onboarded_at: null` -- navigate to `/onboarding` -- assert onboarding page renders

---

### US-8: Progressive Drips Phase 2 (P3)

_Phase 2 -- deferred until portal onboarding is validated._

| ID | Task | Est | Deps | [P] |
|---|---|---|---|---|
| T8.1 | DB: Add `drips_delivered` + `welcome_completed` columns | M | - | |
| T8.2 | DB: Update SQLAlchemy User model | S | T8.1 | |
| T8.3 | Impl: DripManager class | L | T8.2 | |
| T8.4 | Tests: DripManager (14 trigger tests) | L | T8.3 | |
| T8.5 | Impl: pg_cron `check-drips` task endpoint | M | T8.3 | |

**T8.1: DB migration -- add `drips_delivered` and `welcome_completed` columns**
- **Files**: Supabase MCP (apply DDL), `supabase/migrations/20260322100000_add_drips_and_welcome.sql` (2-line comment stub)
- **Est**: M (1hr)
- **ACs**:
  - AC1: `ALTER TABLE users ADD COLUMN drips_delivered JSONB NOT NULL DEFAULT '{}'::jsonb` applied
  - AC2: `ALTER TABLE users ADD COLUMN welcome_completed BOOLEAN NOT NULL DEFAULT false` applied
  - AC3: Comment stub created in migrations directory
  - AC4: Existing RLS policy covers new columns (no additional policy needed)

**T8.2: Update SQLAlchemy User model**
- **File**: `nikita/db/models/user.py` (add 2 mapped columns)
- **Est**: S (30min)
- **Deps**: T8.1
- **ACs**:
  - AC1: `drips_delivered: Mapped[dict]` with `JSONB, default=dict, server_default=text("'{}'::jsonb")`
  - AC2: `welcome_completed: Mapped[bool]` with `Boolean, default=False, server_default=text("false")`
  - AC3: All existing user model tests pass

**T8.3: Implement DripManager class**
- **File**: `nikita/onboarding/drip_manager.py` (new)
- **Est**: L (5hr)
- **Deps**: T8.2
- **ACs**:
  - AC1: 7 drip definitions per spec table (first_score, portal_intro, first_decay, chapter_advance, boss_warning, boss_debrief, nikitas_world)
  - AC2: `evaluate_user(user)` returns list of eligible drips based on user state
  - AC3: Rate limiting: max 1 drip per 2 hours per user (checked against `drips_delivered` timestamps)
  - AC4: Each drip generates magic link portal button (reuses `_generate_portal_magic_link` pattern)

**T8.4: Write DripManager tests**
- **File**: `tests/onboarding/test_drip_manager.py` (new)
- **Est**: L (4hr)
- **Deps**: T8.3
- **ACs**:
  - AC1: 7 positive trigger tests (one per drip condition)
  - AC2: 7 negative tests (condition not met, drip not returned)
  - AC3: Rate limiting test: drip delivered <2hr ago is suppressed
  - AC4: All 14+ tests pass

**T8.5: Implement pg_cron `check-drips` task endpoint**
- **File**: `nikita/api/routes/tasks.py` (add endpoint)
- **Est**: M (2hr)
- **Deps**: T8.3
- **ACs**:
  - AC1: `POST /api/v1/tasks/check-drips` endpoint with task auth
  - AC2: Evaluates all active users with `DripManager.evaluate_user()`
  - AC3: Sends Telegram messages with portal magic link buttons for eligible drips
  - AC4: Records delivered drips in `users.drips_delivered` JSONB

---

## Playwright E2E Test Suite (P1)

| ID | Task | Est | Deps | [P] |
|---|---|---|---|---|
| T9.1 | E2E: Onboarding page structure + sections | M | T2.3, T3.2, T3.3, T4.3, T4.4 | |
| T9.2 | E2E: Form interactions + validation | M | T9.1 | |
| T9.3 | E2E: Profile submission + mobile layout | M | T9.1 | [P] |

**T9.1: E2E tests for page structure (E2E-1 through E2E-4)**
- **File**: `portal/e2e/onboarding.spec.ts` (new)
- **Est**: M (2hr)
- **ACs**:
  - AC1: (E2E-1) All 5 sections render with correct `aria-label` attributes
  - AC2: (E2E-2) Score ring displays with data-testid="chart-score-ring" and `aria-valuenow="75"`
  - AC3: (E2E-3) Chapter stepper shows 5 items with Ch.1 having `aria-current="step"`
  - AC4: (E2E-4) Rules section shows 4 article elements with heading text matching spec
- **Notes**: Follow existing patterns in `portal/e2e/fixtures/api-mocks.ts`. Mock `**/api/v1/portal/stats` with `onboarded_at: null` so onboarding page renders. Mock `**/auth/v1/user` for auth bypass.

**T9.2: E2E tests for form interactions (E2E-5 through E2E-7)**
- **File**: `portal/e2e/onboarding.spec.ts` (add to existing)
- **Est**: M (2hr)
- **Deps**: T9.1
- **ACs**:
  - AC1: (E2E-5) Clicking a scene card selects it -- verify `aria-checked="true"` and rose border class
  - AC2: (E2E-6) Changing slider value updates displayed emoji and label text
  - AC3: (E2E-7) CTA button shows validation error when location empty or scene not selected

**T9.3: E2E tests for submission + mobile (E2E-8 through E2E-10)**
- **File**: `portal/e2e/onboarding.spec.ts` (add to existing)
- **Est**: M (2hr)
- **Deps**: T9.1
- **ACs**:
  - AC1: (E2E-8) CTA submits POST to `/api/v1/onboarding/profile` -- intercept with `page.route()`, verify request body matches form data
  - AC2: (E2E-9) Returning user redirect (covered by T7.2)
  - AC3: (E2E-10) Mobile viewport (375x812): scene cards in 2-col grid, chapter stepper vertical

---

## Deployment Tasks

| ID | Task | Est | Deps | [P] |
|---|---|---|---|---|
| T10.1 | Ensure `portal_url` is set correctly in Cloud Run env | S | - | [P] |
| T10.2 | Install shadcn `radio-group` if missing | S | - | [P] |
| T10.3 | Deploy backend to Cloud Run | S | All backend tasks | |
| T10.4 | Deploy portal to Vercel | S | All portal tasks | |
| T10.5 | Verify end-to-end: OTP -> magic link -> portal -> Telegram | M | T10.3, T10.4 | |

**T10.1: Verify environment configuration**
- **Est**: S (15min)
- **ACs**:
  - AC1: `PORTAL_URL=https://portal-phi-orcin.vercel.app` in Cloud Run env vars
  - AC2: `SUPABASE_SERVICE_KEY` is set (needed for `admin.generate_link()`)

**T10.2: Install shadcn radio-group component**
- **Est**: S (15min)
- **ACs**:
  - AC1: Run `cd portal && npx shadcn add radio-group` if `portal/src/components/ui/radio-group.tsx` doesn't exist
  - AC2: Component imports work in SceneSelector

**T10.3: Deploy backend**
- **Est**: S (15min)
- **Deps**: All backend tasks complete
- **ACs**:
  - AC1: `gcloud run deploy nikita-api --source . --region us-central1 --project gcp-transcribe-test --allow-unauthenticated` succeeds
  - AC2: `POST /api/v1/onboarding/profile` responds 401 without JWT (endpoint active)

**T10.4: Deploy portal**
- **Est**: S (15min)
- **Deps**: All portal tasks complete
- **ACs**:
  - AC1: `cd portal && npm run build && vercel --prod` succeeds
  - AC2: `/onboarding` page loads (redirects to `/login` without auth)

**T10.5: End-to-end verification**
- **Est**: M (1hr)
- **Deps**: T10.3, T10.4
- **ACs**:
  - AC1: Send `/start` to `@Nikita_my_bot` -> OTP flow -> magic link button appears
  - AC2: Click magic link -> portal `/onboarding` loads with all 5 sections
  - AC3: Fill form + submit -> profile saved in DB, `onboarded_at` set
  - AC4: Deep link returns to Telegram

---

## Dependency Graph

```
Phase 1 (P1) — Core Flow:

  T2.5 (schema) ─────────────────────────────────────────┐
  T2.4 (SectionHeader/Quote) ───┬───────────────────────┐ │
  T2.1 (page.tsx) ──> T2.2 (Cinematic) ──┬──> T2.3 (S1) │ │
                                          │              │ │
  T3.1 (ChapterStepper) ──> T3.2 (S2) <──┘              │ │
  T3.3 (S3: Rules) <────────────────────────────────────┘ │
                                                           │
  T4.1 (SceneSelector) ──┬──> T4.3 (S4: Profile) <────────┘
  T4.2 (EdginessSlider) ─┘
  T4.4 (S5: Mission) ──> T5.1 (deep link)

  T1.1 (tests) ──> T1.2 (magic link gen) ──> T1.3 (replace choice)
  T4.5 (tests) ──> T4.6 (profile endpoint)
  T7.1 (stats schema)

  E2E: T9.1 ──> T9.2 ──> T9.3

Phase 2 (P2) — Fallback:

  T6.1 (EventType) ──> T6.2 (tests) ──> T6.3 (fallback impl)
  T7.2 (E2E redirect)

Phase 3 (P3) — Drips:

  T8.1 (migration) ──> T8.2 (model) ──> T8.3 (DripManager) ──> T8.4 (tests)
                                                               ──> T8.5 (cron)

Deployment:

  T10.1, T10.2 (parallel prep)
  All backend ──> T10.3 (deploy backend)
  All portal  ──> T10.4 (deploy portal)
  T10.3 + T10.4 ──> T10.5 (E2E verify)
```

**Parallelizable work streams** (can be developed simultaneously):
- Stream A: Backend (T1.1-T1.3, T4.5-T4.6, T7.1)
- Stream B: Portal components (T2.1-T2.5, T3.1-T3.3, T4.1-T4.4)
- Stream C: After A+B merge -- E2E tests (T9.1-T9.3), fallback (T6.1-T6.3)

---

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| `admin.generate_link()` API signature differs from spec | Blocks magic link | T1.1 tests mock the call; verify against Supabase docs via MCP Ref before implementing T1.2 |
| `snap-proximity` behavior varies across iOS Safari versions | UX degradation on mobile | Test on real iOS device during T10.5; fallback: remove snap entirely if broken |
| ScoreRing `size` prop doesn't support responsive (single number) | Visual mismatch mobile/desktop | Use conditional render or CSS `scale()` transform for mobile size |
| Supabase service role key not available in OTP handler context | Magic link fails | Fallback URL is already built into T1.3 (AC2); graceful degradation |
| shadcn `radio-group` not installed | Build fails | T10.2 checks and installs before portal build |
| Profile endpoint auth differs from portal stats auth | 401 errors | Both use same `get_current_user_id` dependency; verify in T4.5 |
| Fallback 5-min timer fires even after portal completion | Double onboarding | T6.3 AC4: handler checks `onboarded_at` before sending |

---

## Testing Strategy

### Coverage Target
- Backend new code: >= 85% line coverage
- Critical paths (profile endpoint, magic link gen): >= 90%
- Portal components: E2E covers all user-visible flows

### Test Distribution
| Layer | Count | Files |
|---|---|---|
| Unit (Python) | ~12 | `test_otp_handler_onboarding.py`, `test_onboarding_profile.py` |
| Fallback (Python) | ~4 | `test_otp_handler_fallback.py`, `test_fallback.py` |
| Drip (Python, P3) | ~14 | `test_drip_manager.py` |
| E2E (Playwright) | ~10 | `portal/e2e/onboarding.spec.ts` |
| **Total** | **~40** | |

### TDD Order Per Story
1. Write failing tests (RED) -- commit tests
2. Implement minimal code (GREEN) -- commit implementation
3. Refactor -- amend or new commit
4. Verify no regressions: `pytest tests/ -x -q` + `cd portal && npm run build`

### Mock Strategy
- **Supabase Admin API**: `AsyncMock` for `admin.generate_link()` and `admin.get_user_by_id()`
- **TelegramBot**: `AsyncMock` for `send_message_with_keyboard()` -- verify URL button
- **ProfileRepository**: `AsyncMock` for `get_by_user_id()`, `create_profile()`
- **ScheduledEventRepository**: `AsyncMock` for `create_event()` -- verify event_type and scheduled_at
- **E2E API mocks**: `page.route()` interception for portal/stats and onboarding/profile (per `portal/e2e/fixtures/api-mocks.ts` patterns)

---

## Estimated Total Effort

| Phase | Tasks | Total Est |
|---|---|---|
| P1 (Core) | T1.1-T1.3, T2.1-T2.5, T3.1-T3.3, T4.1-T4.6, T5.1, T7.1, T9.1-T9.3 | ~42hr |
| P2 (Fallback + Redirect) | T6.1-T6.3, T7.2 | ~7hr |
| P3 (Drips) | T8.1-T8.5 | ~13hr |
| Deployment | T10.1-T10.5 | ~3hr |
| **Total** | **33 tasks** | **~65hr** |

---

## Notes

1. **No new DB columns for P1**: The existing `onboarded_at` column serves all P1 needs. The `drips_delivered` and `welcome_completed` columns are P3 only (T8.1).
2. **Auth callback already works**: `portal/src/app/auth/callback/route.ts:9` reads `?next=/onboarding` and redirects there after exchanging the code. No changes needed to the callback.
3. **Middleware coverage**: `/onboarding` is automatically protected by existing middleware (`portal/src/lib/supabase/middleware.ts:67` -- all non-public, non-admin routes redirect to `/login` without auth). No middleware changes needed.
4. **Backward compatibility**: The `handle_callback()` method on OTPVerificationHandler (lines 379-424) is retained for any in-flight users who may have received the old voice/text choice buttons before deployment.
5. **Scenario selection deferred**: The backstory scenario selection from Spec 017 is NOT part of this onboarding. Profile fields reduced from 5 to 3 (location, scene, edginess). Life stage and interest are collected later.
6. **framer-motion already bundled**: No new dependencies for animations. ScoreRing already uses it.
7. **Mobile-first**: All sections designed mobile-first per spec wireframes. `snap-proximity` (not `mandatory`) handles variable-height Section 4.
