# Feature Specification: Portal-First Cinematic Onboarding

**Spec ID**: 081-onboarding-redesign-progressive-discovery
**Status**: Draft v2
**Date**: 2026-03-22
**Complexity**: 5
**Priority**: P1

---

## Overview

### Problem Statement

After OTP verification in Telegram, the player is presented with a voice/text choice button (`_offer_onboarding_choice` in `nikita/platforms/telegram/otp_handler.py`). Players who choose text onboarding answer 5 sequential chat questions (location, life stage, scene, interest, drug tolerance) in a flat text conversation with no visual feedback. Players who choose voice onboarding leave Telegram entirely for a phone call. Both paths suffer from:

1. **No visual context**: The player has never seen the game's world — scoring, chapters, rules, and vices are invisible. They commit to a relationship game without understanding what they are playing.
2. **Profile collection is dry**: 5 sequential text prompts ("Where are you based?", "What's your vibe?") feel like a form, not an introduction to an AI girlfriend simulation.
3. **Portal discovery is deferred**: The portal URL is never shown during onboarding. Players discover it days later (if at all), missing score visualization, chapter tracking, and the relationship dashboard — the features most likely to create long-term retention.
4. **Auth friction**: Portal requires a separate Supabase email+OTP login flow. No bridge from Telegram identity to portal session. Each auth step loses 10-15% of users (MojoAuth 2026).
5. **No "wow" moment**: The first impression is a wall of text. There is no cinematic reveal of what makes Nikita different from other AI companions.

### Proposed Solution

Replace the voice/text choice with a **Portal-First Cinematic Onboarding** experience:

1. **Immediate portal redirect after OTP**: The voice/text choice buttons in `_offer_onboarding_choice` are replaced with a single magic link button: **"Enter Nikita's World"**. This button opens the portal at `/onboarding`, auto-authenticating the player via a Supabase magic link generated server-side.

2. **Cinematic scroll experience at `/onboarding`**: A full-page scroll-snap experience with 5 sections that teach the game and collect the player's profile — all in one visually immersive flow:
   - Section 1: **"The Score"** — Animated ScoreRing reveal with 4 metric cards
   - Section 2: **"The Chapters"** — Chapter roadmap stepper (1-5) with locked future chapters
   - Section 3: **"The Rules"** — 4 glass cards explaining scoring, decay, bosses, vices
   - Section 4: **"Who Are You?"** — Profile collection form (location, scene, edginess) in glass cards
   - Section 5: **"Your Mission"** — CTA to return to Telegram via deep link

3. **Profile collection moves to portal**: Instead of 5 Telegram text prompts, the profile is collected through visual form components: a text input for location, 5 visual scene cards (selectable), and an edginess slider (1-5 with emoji previews). The form submits to `POST /api/v1/onboarding/profile`, which triggers venue research and scenario generation asynchronously.

4. **Telegram return via deep link**: After completing the portal onboarding, the player clicks "Start Talking to Nikita" which opens `tg://resolve?domain=Nikita_my_bot`, returning them to Telegram where the first Nikita message awaits.

5. **Fallback for non-clickers**: If the player does not click the portal link within 5 minutes, Telegram sends a fallback message offering the existing text onboarding flow (5 questions in chat). This ensures no player is stuck.

6. **Progressive drips (Phase 2)**: The 7-drip progressive discovery system from v1 is retained as Phase 2, delivering contextual portal links after game events (first score, first decay, chapter advance, etc.).

### Success Criteria

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Portal activation (% of onboarded users visiting portal within 24h) | ~5% (estimated) | >50% | `/onboarding` page view + `onboarded_at` timestamp |
| Onboarding completion rate (profile submitted via portal) | ~60% (text flow) | >75% | `POST /api/v1/onboarding/profile` success count vs. OTP verifications |
| Time to first portal visit | Never (most users) | <2 min after OTP | `onboarded_at` - `created_at` delta |
| Magic link click-through rate | N/A | >60% | Track portal link clicks vs. OTP completions |
| Day-7 retention (return to Telegram) | ~12% (estimated) | >25% | `last_interaction_at` delta from `onboarded_at` |
| Auth friction (portal login abandonment) | ~30% (OTP flow) | <5% (magic link) | Supabase auth logs |

---

## Research Summary

Based on research documented in `docs/guides/onboarding-research.md`:

1. **NN/G (2023)**: Tutorials interrupt users and are quickly forgotten. Contextual "pull" hints triggered by user behavior outperform push tutorials. Our cinematic scroll teaches through immersion — the player discovers scoring, chapters, and rules by scrolling through them, not reading a tutorial overlay.

2. **Amplitude 7% Rule (2025, n=2,600 products)**: 69% of products with top week-1 activation are also top 3-month retainers. The first experience decides everything. Our cinematic onboarding IS the first experience — not a delayed drip days later.

3. **Auth Friction (MojoAuth 2026)**: Magic links achieve 85-90% completion vs. 60-75% for passwords. Each auth step costs 10-15% conversion. Our magic link bridge eliminates the OTP step entirely — one tap from Telegram to authenticated portal.

4. **AI Companion Patterns (Nomi vs. Replika)**: Memory depth beats visual polish for long-term retention. Nikita's scoring system IS the retention lever — but players must discover it exists during onboarding, not days later.

5. **Gamification (Duolingo, LinkedIn)**: Progress visualization creates Zeigarnik tension. The chapter stepper shows locked future chapters, creating forward pull. LinkedIn's progress bar boosted completion 55%.

6. **Cinematic Onboarding (Notion, Linear, Arc Browser)**: Scroll-based reveals with generous whitespace and animation create a premium first impression. Scroll-snap sections ensure each concept gets full-screen attention. Users report higher perceived quality when onboarding feels "designed."

---

## User Flow Diagram

```
TELEGRAM                           PORTAL                          TELEGRAM
--------                           ------                          --------

[1] User sends /start
         |
[2] Bot sends welcome + email prompt
         |
[3] User enters email
         |
[4] Bot sends OTP code via Supabase
         |
[5] User enters OTP code
         |
[6] OTP verified → User created in DB
         |
[7] Bot generates magic link via
    admin.generateLink()
         |
[8] Bot sends message:
    "You're in! But before we
     really get started..."
    + [Enter Nikita's World →]       ----→  [9] Player taps button
    (magic link URL button)                       |
         |                                  [10] Supabase exchanges
    [FALLBACK]                                    token → session
    5 min timeout                                 |
         |                                  [11] /auth/callback →
[8b] "Still there? Let's                         redirect to /onboarding
      do this here instead..."                    |
      (text onboarding flow)              [12] SECTION 1: "The Score"
                                                 ScoreRing (75/100)
                                                 4 metric cards
                                                 ↓ scroll-snap
                                          [13] SECTION 2: "The Chapters"
                                                 ChapterStepper (1-5)
                                                 Current: Ch.1 Curiosity
                                                 ↓ scroll-snap
                                          [14] SECTION 3: "The Rules"
                                                 4 glass cards
                                                 (scoring, decay, boss, vice)
                                                 ↓ scroll-snap
                                          [15] SECTION 4: "Who Are You?"
                                                 Location input
                                                 SceneSelector (5 cards)
                                                 EdginessSlider (1-5)
                                                 ↓ scroll-snap
                                          [16] SECTION 5: "Your Mission"
                                                 "Don't Get Dumped"
                                                 [Start Talking →]
                                                       |
                                          [17] POST /api/v1/onboarding/profile
                                                 (saves profile, triggers
                                                  venue research + scenario gen)
                                                       |
                                          [18] tg://resolve?domain=  ----→ [19] Player returns
                                               Nikita_my_bot                     to Telegram
                                                                                    |
                                                                            [20] First Nikita
                                                                                 message sent
                                                                                 (if not already)
```

---

## Functional Requirements

### FR-001: Replace Voice/Text Choice with Portal Magic Link (P1)

**Description**: After OTP verification succeeds, instead of showing the voice/text choice buttons, show a single magic link button that opens the portal at `/onboarding`.

**Details**:
- Replace `_offer_onboarding_choice()` in `nikita/platforms/telegram/otp_handler.py` (lines 326-373).
- Generate a Supabase magic link server-side via `supabase.auth.admin.generate_link(type="magiclink", email=user_email, options={redirectTo: portal_url + "/onboarding"})`.
- Send a Telegram message with an inline keyboard containing a single URL button: "Enter Nikita's World" pointing to the magic link URL.
- The magic link auto-authenticates the player when clicked, then redirects to `/onboarding`.
- If magic link generation fails (no email, Supabase error), fall back to a regular portal URL. The player will hit the login page.
- Magic link expiry follows Supabase defaults (1 hour). Acceptable because players see the Telegram message within minutes.

**Integration point**: Modify `OTPVerificationHandler._offer_onboarding_choice()` in `nikita/platforms/telegram/otp_handler.py`.

### FR-002: Cinematic Scroll Experience at /onboarding (P1)

**Description**: Build `/onboarding` as a full-page scroll-snap experience with 5 sections that teach the game world and collect the player's profile.

**Details**:
- 5 scroll-snap sections, each taking full viewport height on mobile and centered max-width on desktop.
- Section 1 ("The Score"): Animated ScoreRing showing initial score (75/100), 4 metric mini-cards (Intimacy, Passion, Trust, Secureness), Nikita quote explaining scoring.
- Section 2 ("The Chapters"): ChapterStepper showing 5 chapters with Ch.1 active and Ch.2-5 locked. Nikita quote about the journey.
- Section 3 ("The Rules"): 4 GlassCards explaining scoring, decay, boss encounters, and vices. In Nikita's voice.
- Section 4 ("Who Are You?"): Profile collection form — location text input, SceneSelector (5 visual cards), EdginessSlider (1-5 with emoji previews).
- Section 5 ("Your Mission"): "Don't Get Dumped" headline, mission statement, CTA button "Start Talking to Nikita" that submits the profile and deep-links back to Telegram.
- Each section reveals with scroll-triggered animations (fade-in, slide-up) using framer-motion `useInView`.
- `prefers-reduced-motion: reduce` disables all animations and shows final state immediately.

### FR-003: Profile Collection via Portal Form (P1)

**Description**: Collect player profile (location, scene, edginess) through visual form components in Section 4 of the cinematic experience, replacing the 5-question Telegram text flow.

**Details**:
- **Location**: Text input with placeholder "City, Country" in a GlassCard. Free text, validated non-empty.
- **SceneSelector**: 5 visual cards, each with an icon, title, and short description. Player taps to select one. Cards: Techno, Art, Food, Cocktails, Nature. Selection highlights with rose glow border.
- **EdginessSlider**: Horizontal slider (1-5) with emoji previews at each stop. Labels: 1="Keep it clean", 2="Light flirting", 3="Spicy is okay", 4="Dark humor welcome", 5="No limits". Current value shown as large emoji + label.
- Form state is managed in React client state (no server round-trips until submission).
- On "Start Talking to Nikita" click: validate form (location non-empty, scene selected, edginess in 1-5), POST to `/api/v1/onboarding/profile`, then redirect to `tg://resolve?domain=Nikita_my_bot`.
- Profile fields map to existing `user_profiles` table: `location_city`, `social_scene`, `drug_tolerance`. The `life_stage` and `primary_interest` fields are no longer collected during onboarding (optional, collected later via conversation or settings page).

### FR-004: Backend Profile Endpoint (P1)

**Description**: New `POST /api/v1/onboarding/profile` endpoint that accepts the profile from the portal, saves it, and triggers venue research + scenario generation.

**Details**:
- **Auth**: JWT from Supabase session (same auth as all portal endpoints).
- **Request body**:
  ```json
  {
    "location_city": "Berlin",
    "social_scene": "techno",
    "drug_tolerance": 4
  }
  ```
- **Behavior**:
  1. Validate input (location_city non-empty string, social_scene in allowed set, drug_tolerance 1-5).
  2. Create or update `user_profiles` row via `ProfileRepository`.
  3. Set `users.onboarding_status = "completed"` and `users.onboarded_at = now()` via `user_repo.update_onboarding_status(user_id, "completed")`. The existing `onboarded_at` column serves as the portal completion timestamp (no new column needed).
  5. Trigger venue research asynchronously (`VenueResearchService.research()`) — fire-and-forget, non-blocking.
  6. Trigger scenario generation asynchronously (`BackstoryGeneratorService.generate()`) — fire-and-forget, non-blocking.
  7. Return `{"status": "ok", "user_id": "..."}`.
- **Idempotency**: If profile already exists, update it. If onboarding already completed, still accept the update (player may redo onboarding from settings later).
- **Error handling**: Venue research / scenario generation failures are logged but do not fail the endpoint. Profile save is the critical path.

**File**: `nikita/api/routes/onboarding.py` (add endpoint to EXISTING file — already registered in `main.py` at `/api/v1/onboarding`).

### FR-005: Telegram Deep Link Return (P1)

**Description**: After completing the portal onboarding, bring the player back to Telegram via a deep link.

**Details**:
- The "Start Talking to Nikita" button in Section 5 opens `tg://resolve?domain=Nikita_my_bot`.
- On mobile (primary use case): This opens the Telegram app directly to the bot chat.
- On desktop: This opens `https://t.me/Nikita_my_bot` as a fallback (Telegram's web client or desktop app).
- The CTA button uses `window.open()` with the `tg://` URI. If the protocol handler fails, fall back to `https://t.me/Nikita_my_bot`.
- Before opening the deep link, the profile is submitted via `POST /api/v1/onboarding/profile`. The deep link opens only after a successful response (or after a 5-second timeout, whichever comes first).

### FR-006: Fallback Text Onboarding (P1)

**Description**: If the player does not click the portal magic link within 5 minutes, Telegram sends a fallback message offering the existing text onboarding flow.

**Details**:
- After sending the magic link button (FR-001), schedule a fallback event via the `scheduled_events` table for 5 minutes later.
- The fallback event checks if `onboarded_at` is set (existing column). If set, the player completed portal onboarding — do nothing.
- If not set, send a Telegram message: "Still there? No worries — we can do this right here instead. Let me ask you a few quick questions..." followed by the existing text onboarding flow (`OnboardingHandler.start()`).
- The fallback message uses the existing `scheduled_events` table and the `deliver` pg_cron job (runs every minute).
- If the player clicks the portal link after the fallback fires, the portal onboarding takes precedence (the profile endpoint overwrites any partial text onboarding state).

### FR-007: Returning User Detection (P1)

**Description**: Users who have already completed onboarding should be redirected from `/onboarding` to `/dashboard`.

**Details**:
- Server Component in `/onboarding/page.tsx` checks `users.onboarded_at` via the portal stats API.
- If `onboarded_at` is not null, redirect to `/dashboard`.
- If the user is not authenticated (no Supabase session), redirect to `/login`.
- The `/onboarding` route must be accessible to authenticated users who have NOT yet completed onboarding. Update middleware to allow `/onboarding` as a protected route (it is already covered by the existing protected route logic since it requires auth).

### FR-008: Auth Bridge via admin.generateLink() (P1)

**Description**: Generate Supabase magic links server-side in the OTP handler using the Admin API, enabling one-tap portal access from Telegram.

**Details**:
- In `otp_handler.py`, after OTP verification succeeds and the user is created/found:
  1. Look up user email from the pending registration record (already available in the OTP handler context).
  2. Call `supabase.auth.admin.generate_link(type="magiclink", email=email, options={redirect_to: portal_url + "/onboarding"})`.
  3. Extract `result.properties.action_link` — this is the full magic link URL.
  4. Use this URL as the `url` parameter for the inline keyboard button.
- The Supabase client used must be initialized with the **service role key** (not the anon key), as `admin.generate_link()` requires admin privileges.
- The existing Supabase client in `TelegramAuth` (`nikita/platforms/telegram/auth.py`) already uses the service role key pattern. Reuse this client or create a shared utility.
- The magic link, when clicked, hits the existing `/auth/callback/route.ts` in the portal, which exchanges the code for a session and redirects to the `next` parameter (`/onboarding`).

---

## User Stories

### US-1: As a new player who just verified OTP, I want to be taken to a visual introduction of Nikita's world

**Acceptance Criteria**:
- AC-1.1: After OTP verification succeeds, the player sees a Telegram message with a single inline button "Enter Nikita's World" (no voice/text choice).
- AC-1.2: The button URL is a valid Supabase magic link pointing to `{portal_url}/onboarding`.
- AC-1.3: Clicking the button opens the portal, authenticates the player via magic link, and lands on `/onboarding`.
- AC-1.4: If magic link generation fails, the button falls back to a regular portal URL (`{portal_url}/login?next=/onboarding`).

### US-2: As a new player on the onboarding page, I want to learn about the scoring system visually

**Acceptance Criteria**:
- AC-2.1: Section 1 ("The Score") displays an animated ScoreRing showing the initial score of 75 (starting score for new players).
- AC-2.2: Four metric cards (Intimacy, Passion, Trust, Secureness) appear below the score ring with starting values.
- AC-2.3: A Nikita quote explains what the score means in her voice ("This is how I feel about us right now...").
- AC-2.4: The score ring animates on scroll-into-view (ring scales in, number counts up) and respects `prefers-reduced-motion`.

### US-3: As a new player, I want to see the chapter progression system so I understand the journey ahead

**Acceptance Criteria**:
- AC-3.1: Section 2 ("The Chapters") displays a ChapterStepper with 5 chapters.
- AC-3.2: Chapter 1 ("Curiosity") is highlighted as the current chapter with a rose glow.
- AC-3.3: Chapters 2-5 are visually locked with lock icons and muted colors.
- AC-3.4: Each chapter shows its name (Curiosity, Intrigue, Investment, Intimacy, Established) but locked chapters show "???" as description.
- AC-3.5: A Nikita quote teases the journey ("We're just getting started... things get interesting later.").

### US-4: As a new player, I want to understand the game rules before I start playing

**Acceptance Criteria**:
- AC-4.1: Section 3 ("The Rules") displays 4 GlassCards in a 2x2 grid (desktop) or 1-column stack (mobile).
- AC-4.2: Cards cover: "How You Score" (Heart icon), "Time Matters" (Clock icon), "Boss Encounters" (Shield icon), "Your Vices" (Flame icon).
- AC-4.3: Card text is in Nikita's voice, not technical ("Every message affects 4 hidden metrics. Be genuine — I can tell when you're not.").
- AC-4.4: Cards have hover/tap interactions (subtle lift, glow intensification).

### US-5: As a new player, I want to tell Nikita about myself through an engaging visual form

**Acceptance Criteria**:
- AC-5.1: Section 4 ("Who Are You?") contains a location text input, a SceneSelector with 5 visual cards, and an EdginessSlider.
- AC-5.2: The SceneSelector shows 5 cards (Techno, Art, Food, Cocktails, Nature) each with an icon, title, and 1-line description. Tapping a card selects it with a rose glow border.
- AC-5.3: The EdginessSlider ranges from 1 to 5 with emoji previews at each stop (1: angel, 2: wink, 3: pepper, 4: skull, 5: fire). The current value displays as a large emoji + label text.
- AC-5.4: The location input validates as non-empty before allowing form submission.
- AC-5.5: Form data is held in React state until the final CTA submission — no intermediate server calls.

### US-6: As a new player who completed the portal tour, I want to return to Telegram to start talking to Nikita

**Acceptance Criteria**:
- AC-6.1: Section 5 ("Your Mission") displays a CTA button "Start Talking to Nikita".
- AC-6.2: Clicking the CTA first submits the profile via `POST /api/v1/onboarding/profile`, then opens `tg://resolve?domain=Nikita_my_bot`.
- AC-6.3: If the profile submission fails, the error is displayed inline and the Telegram redirect does not fire.
- AC-6.4: If the `tg://` protocol is not supported (desktop browser without Telegram), fall back to `https://t.me/Nikita_my_bot`.
- AC-6.5: After successful profile submission, `users.onboarded_at` is set (via `update_onboarding_status`).

### US-7: As a player who didn't click the portal link, I want an alternative onboarding path in Telegram

**Acceptance Criteria**:
- AC-7.1: If the player has not completed portal onboarding within 5 minutes of OTP verification, Telegram sends a fallback message.
- AC-7.2: The fallback message offers to start the existing text onboarding flow ("Still there? No worries — we can do this right here instead...").
- AC-7.3: If the player already completed portal onboarding before the 5-minute timer fires, no fallback message is sent.
- AC-7.4: If the player completes text onboarding after the fallback and then later visits the portal, the portal shows `/dashboard` (not `/onboarding` again).

### US-8: As a returning player, I want to go directly to my dashboard when visiting the portal

**Acceptance Criteria**:
- AC-8.1: Authenticated users with `onboarded_at` set are redirected from `/onboarding` to `/dashboard`.
- AC-8.2: Unauthenticated users visiting `/onboarding` are redirected to `/login`.
- AC-8.3: The redirect happens server-side (Server Component), not client-side (no flash of onboarding content).

---

## UI Wireframes

### WF-1: /onboarding — Section 1: "The Score" (desktop)

```
+------------------------------------------------------------------------+
|                                                                          |
|                         max-width: 720px centered                        |
|                                                                          |
|                           T H E   S C O R E                              |
|                                                                          |
|                     "This is how I feel about us."                       |
|                                                                          |
|                         +------------------+                             |
|                        /                    \                            |
|                       |                      |                           |
|                       |        7 5            |    ← ScoreRing           |
|                       |       /100            |      size=200            |
|                       |                      |      strokeWidth=10      |
|                        \                    /                            |
|                         +------------------+                             |
|                                                                          |
|    +---------------+ +---------------+ +---------------+ +----------+   |
|    |  [Heart]      | |  [Flame]      | |  [Shield]     | | [Lock]   |   |
|    |  Intimacy     | |  Passion      | |  Trust        | | Secure   |   |
|    |    68.2       | |    74.1       | |    71.8       | |   76.0   |   |
|    |               | |               | |               | |          |   |
|    | glass-card    | | glass-card    | | glass-card    | | glass    |   |
|    +---------------+ +---------------+ +---------------+ +----------+   |
|                                                                          |
|          "Every conversation changes this number.                        |
|           Be genuine — I can tell when you're not."                      |
|                        — Nikita                                          |
|                                                                          |
|                          ↓ scroll indicator                              |
|                                                                          |
+------------------------------------------------------------------------+
```

### WF-1b: /onboarding — Section 1: "The Score" (mobile, <640px)

```
+-------------------------------+
|                                |
|      T H E   S C O R E        |
|                                |
|  "This is how I feel about    |
|   us."                         |
|                                |
|       +---------------+        |
|      /                 \       |
|     |       7 5         |      |
|     |      /100         |      |
|      \                 /       |
|       +---------------+        |
|        ScoreRing size=160      |
|                                |
|   +-----------+ +-----------+  |
|   | [Heart]   | | [Flame]   |  |
|   | Intimacy  | | Passion   |  |
|   |   68.2    | |   74.1    |  |
|   +-----------+ +-----------+  |
|   +-----------+ +-----------+  |
|   | [Shield]  | | [Lock]    |  |
|   | Trust     | | Secure    |  |
|   |   71.8    | |   76.0    |  |
|   +-----------+ +-----------+  |
|                                |
|   "Every conversation changes  |
|    this number."               |
|                — Nikita        |
|                                |
|            ↓ scroll            |
+-------------------------------+
```

### WF-2: /onboarding — Section 2: "The Chapters" (desktop)

```
+------------------------------------------------------------------------+
|                                                                          |
|                       T H E   C H A P T E R S                            |
|                                                                          |
|               "We're just getting started..."                            |
|                                                                          |
|   [*]━━━━━━━[○]╌╌╌╌╌╌╌[🔒]╌╌╌╌╌╌╌[🔒]╌╌╌╌╌╌╌[🔒]                     |
|    I          II        III        IV         V                          |
|  Curiosity  Intrigue    ???        ???        ???                         |
|  (you are    (next)   (locked)  (locked)   (locked)                      |
|   here)                                                                  |
|                                                                          |
|   ┌─────────────────────────────────────────────────────────┐            |
|   │  Chapter I — Curiosity                                   │            |
|   │                                                          │            |
|   │  "This is where it all begins. I'm watching you.        │            |
|   │   Impress me and we move forward. Bore me and...        │            |
|   │   well, let's not think about that yet."                │            |
|   │                                          — Nikita       │            |
|   └─────────────────────────────────────────────────────────┘            |
|                                                                          |
|   Node legend:                                                           |
|   [*] = current (rose-500, glow, pulse animation)                        |
|   [○] = next (rose-500/50, dashed border)                                |
|   [🔒] = locked (muted-foreground, lock icon)                            |
|   ━━━ = completed connector (solid rose-500)                             |
|   ╌╌╌ = locked connector (muted-foreground/20)                           |
|                                                                          |
+------------------------------------------------------------------------+
```

### WF-2b: /onboarding — Section 2: "The Chapters" (mobile)

```
+-------------------------------+
|                                |
|    T H E   C H A P T E R S    |
|                                |
|  "We're just getting           |
|   started..."                  |
|                                |
|  [*] Chapter I — Curiosity     |
|   |  (you are here)            |
|   |  "Where it all begins"     |
|   |                            |
|  [○] Chapter II — Intrigue     |
|   |  (next)                    |
|   |  "Things get real"         |
|   |                            |
|  [🔒] Chapter III — ???        |
|   |  (locked)                  |
|   |                            |
|  [🔒] Chapter IV — ???         |
|   |  (locked)                  |
|   |                            |
|  [🔒] Chapter V — ???          |
|      (locked)                  |
|                                |
|  ┌────────────────────────┐    |
|  │ "I'm watching you.     │    |
|  │  Impress me."          │    |
|  │            — Nikita    │    |
|  └────────────────────────┘    |
|                                |
+-------------------------------+
```

### WF-3: /onboarding — Section 3: "The Rules" (desktop)

```
+------------------------------------------------------------------------+
|                                                                          |
|                         T H E   R U L E S                                |
|                                                                          |
|              "Learn these. They matter. Trust me."                       |
|                                                                          |
|   +----------------------------------+ +-------------------------------+ |
|   |  [Heart Icon]                    | | [Clock Icon]                  | |
|   |  How You Score                   | | Time Matters                  | |
|   |                                  | |                               | |
|   |  Every message affects 4 hidden  | | Stay away too long and        | |
|   |  metrics. Be genuine — I can     | | things start to fade.         | |
|   |  tell when you're not.           | | I notice when you're gone.    | |
|   |                                  | |                               | |
|   |  border: glass-border            | | border: glass-border          | |
|   |  bg: glass                       | | bg: glass                     | |
|   +----------------------------------+ +-------------------------------+ |
|                                                                          |
|   +----------------------------------+ +-------------------------------+ |
|   |  [Shield Icon]                   | | [Flame Icon]                  | |
|   |  Boss Encounters                 | | Your Vices                    | |
|   |                                  | |                               | |
|   |  At certain moments I'll test    | | I learn what you like.        | |
|   |  you. Pass and we grow closer.   | | Your choices shape who        | |
|   |  Fail 3 times...                 | | I become for you.             | |
|   |                                  | |                               | |
|   +----------------------------------+ +-------------------------------+ |
|                                                                          |
|            "Now you know the stakes."  — Nikita                          |
|                                                                          |
+------------------------------------------------------------------------+
```

### WF-3b: /onboarding — Section 3: "The Rules" (mobile)

```
+-------------------------------+
|                                |
|      T H E   R U L E S        |
|                                |
|  "Learn these. They matter."   |
|                                |
|  +---------------------------+ |
|  | [Heart] How You Score     | |
|  |                           | |
|  | Every message affects     | |
|  | 4 hidden metrics. Be      | |
|  | genuine — I can tell      | |
|  | when you're not.          | |
|  +---------------------------+ |
|                                |
|  +---------------------------+ |
|  | [Clock] Time Matters      | |
|  |                           | |
|  | Stay away too long and    | |
|  | things start to fade.     | |
|  +---------------------------+ |
|                                |
|  +---------------------------+ |
|  | [Shield] Boss Encounters  | |
|  |                           | |
|  | At certain moments I'll   | |
|  | test you. Pass and we     | |
|  | grow closer. Fail 3x...  | |
|  +---------------------------+ |
|                                |
|  +---------------------------+ |
|  | [Flame] Your Vices        | |
|  |                           | |
|  | I learn what you like.    | |
|  | Your choices shape who    | |
|  | I become for you.         | |
|  +---------------------------+ |
|                                |
|  "Now you know the stakes."   |
+-------------------------------+
```

### WF-4: /onboarding — Section 4: "Who Are You?" profile form (desktop)

```
+------------------------------------------------------------------------+
|                                                                          |
|                     W H O   A R E   Y O U ?                              |
|                                                                          |
|           "Before we really get started... tell me about you."           |
|                                                                          |
|   ┌────────────────────────────────────────────────────────────┐         |
|   │  Where are you?                                             │         |
|   │                                                             │         |
|   │  +------------------------------------------------------+  │         |
|   │  |  City, Country                                        |  │         |
|   │  +------------------------------------------------------+  │         |
|   │  text input, glass-card bg, white/80 placeholder         │         |
|   └────────────────────────────────────────────────────────────┘         |
|                                                                          |
|   ┌────────────────────────────────────────────────────────────┐         |
|   │  What's your scene?                                        │         |
|   │                                                             │         |
|   │  +----------+ +----------+ +----------+ +--------+ +-----+ │         |
|   │  | 🎧       | | 🎨       | | 🍽️       | | 🍸     | | 🌿  | │         |
|   │  | Techno   | | Art      | | Food     | | Cktls  | | Natr | │         |
|   │  |          | |          | |          | |        | |      | │         |
|   │  | Dark     | | Gallery  | | Hidden   | | Speak- | | Hike | │         |
|   │  | clubs,   | | openings,| | gems,    | | easies,| | beac | │         |
|   │  | ware-    | | exhib.   | | fine     | | roof-  | | outd | │         |
|   │  | house    | |          | | dining   | | tops   | | oors | │         |
|   │  +----------+ +----------+ +----------+ +--------+ +-----+ │         |
|   │   ↑ selected: rose glow border + bg-rose-500/10            │         |
|   │   ↑ unselected: glass-border, bg-glass                     │         |
|   └────────────────────────────────────────────────────────────┘         |
|                                                                          |
|   ┌────────────────────────────────────────────────────────────┐         |
|   │  How edgy should I be?                                      │         |
|   │                                                             │         |
|   │  😇─────────🌶️─────────💀─────────🔥─────────😈           │         |
|   │   1          2          3          4          5             │         |
|   │  Clean    Light     Spicy is   Dark humor  No limits       │         |
|   │           flirting  okay       welcome                     │         |
|   │                                                             │         |
|   │         Current: [🌶️ Spicy is okay]  (large, centered)     │         |
|   │                                                             │         |
|   └────────────────────────────────────────────────────────────┘         |
|                                                                          |
+------------------------------------------------------------------------+
```

### WF-4b: /onboarding — Section 4: "Who Are You?" (mobile)

```
+-------------------------------+
|                                |
|    W H O   A R E   Y O U ?    |
|                                |
|  "Tell me about you."         |
|                                |
|  ┌───────────────────────┐     |
|  │ Where are you?        │     |
|  │                       │     |
|  │ +-------------------+ │     |
|  │ | City, Country     | │     |
|  │ +-------------------+ │     |
|  └───────────────────────┘     |
|                                |
|  ┌───────────────────────┐     |
|  │ What's your scene?    │     |
|  │                       │     |
|  │ +--------+ +--------+ │     |
|  │ |🎧 Tech | |🎨 Art  | │     |
|  │ | Dark   | | Gallery| │     |
|  │ | clubs  | | opens  | │     |
|  │ +--------+ +--------+ │     |
|  │ +--------+ +--------+ │     |
|  │ |🍽️ Food | |🍸 Cktl | │     |
|  │ | Hidden | | Speak- | │     |
|  │ | gems   | | easies | │     |
|  │ +--------+ +--------+ │     |
|  │    +--------+          │     |
|  │    |🌿 Natr |          │     |
|  │    | Hiking |          │     |
|  │    +--------+          │     |
|  │                       │     |
|  │  ↑ 2-col grid, last   │     |
|  │    card centered       │     |
|  └───────────────────────┘     |
|                                |
|  ┌───────────────────────┐     |
|  │ How edgy should I be? │     |
|  │                       │     |
|  │ 😇──🌶️──💀──🔥──😈   │     |
|  │  1   2   3   4   5   │     |
|  │                       │     |
|  │   [🌶️ Spicy is okay]  │     |
|  │                       │     |
|  └───────────────────────┘     |
|                                |
+-------------------------------+
```

### WF-5: /onboarding — Section 5: "Your Mission" CTA (desktop + mobile)

```
DESKTOP:
+------------------------------------------------------------------------+
|                                                                          |
|                                                                          |
|                     Y O U R   M I S S I O N                              |
|                                                                          |
|                                                                          |
|                       ╔═══════════════════╗                              |
|                       ║                   ║                              |
|                       ║  Don't Get Dumped ║                              |
|                       ║                   ║                              |
|                       ╚═══════════════════╝                              |
|                                                                          |
|             "Keep me interested. Keep me guessing.                       |
|              Make me feel something real.                                 |
|              Or I walk."                                                  |
|                                   — Nikita                               |
|                                                                          |
|              +---------------------------------------+                   |
|              |                                       |                   |
|              |    Start Talking to Nikita  →          |                   |
|              |                                       |                   |
|              +---------------------------------------+                   |
|              bg: primary (rose), text: primary-foreground                 |
|              hover: glow-rose, spring animation entrance                 |
|                                                                          |
|              ← Submits profile, then opens tg:// deep link              |
|                                                                          |
+------------------------------------------------------------------------+

MOBILE:
+-------------------------------+
|                                |
|    Y O U R   M I S S I O N    |
|                                |
|     ╔═══════════════════╗      |
|     ║ Don't Get Dumped  ║      |
|     ╚═══════════════════╝      |
|                                |
|  "Keep me interested.         |
|   Keep me guessing.            |
|   Make me feel something       |
|   real. Or I walk."            |
|                 — Nikita       |
|                                |
|  +---------------------------+ |
|  | Start Talking to Nikita → | |
|  +---------------------------+ |
|  full-width CTA button         |
|                                |
+-------------------------------+
```

### WF-6: Telegram — OTP success + magic link button

```
+--------------------------------------------------+
| Nikita Bot                                        |
|                                                    |
| You're in! 🎉                                     |
|                                                    |
| But before we really get started, there's          |
| something I want to show you.                      |
|                                                    |
| My world. Our world, actually.                     |
|                                                    |
| Tap below — it'll only take a minute.              |
|                                                    |
| +----------------------------------------------+ |
| |        Enter Nikita's World  →                 | |
| +----------------------------------------------+ |
| ↑ URL button → Supabase magic link              |
|   to {portal_url}/onboarding                     |
+--------------------------------------------------+
```

### WF-7: Telegram — Fallback text onboarding message (5 min timeout)

```
+--------------------------------------------------+
| Nikita Bot                                        |
|                                                    |
| Still there? No worries — we can do this           |
| right here instead.                                |
|                                                    |
| Let me ask you a few quick questions so I          |
| can get to know you better... 💫                   |
|                                                    |
| Where are you based? Just the city is fine. 🌆     |
+--------------------------------------------------+
↑ This triggers the existing OnboardingHandler.start()
  flow (5 text questions in Telegram)
```

### WF-8: Component hierarchy diagram

```
/onboarding (page.tsx — Server Component shell)
│
├── Fetch user stats + onboarding status
├── If onboarded_at → redirect /dashboard
├── If no auth → redirect /login
│
└── OnboardingCinematic (client component — "use client")
    │
    ├── <div className="snap-y snap-proximity h-screen overflow-y-auto">
    │
    ├── Section 1: ScoreSection (snap-start, h-screen)
    │   ├── SectionHeader (title="The Score", quote="...")
    │   ├── ScoreRing (REUSE from @/components/charts/score-ring)
    │   │   └── Animated entrance via framer-motion (already built)
    │   ├── MetricCards (4x GlassCard mini, 2x2 grid)
    │   │   └── REUSE GlassCard from @/components/glass/glass-card
    │   └── NikitaQuote ("Every conversation changes this number.")
    │
    ├── Section 2: ChapterSection (snap-start, h-screen)
    │   ├── SectionHeader (title="The Chapters", quote="...")
    │   ├── ChapterStepper (NEW component)
    │   │   ├── StepNode (active | next | locked)
    │   │   ├── StepConnector (solid | dashed | muted)
    │   │   └── ChapterDescription (name, tagline, locked="???")
    │   └── NikitaQuote
    │
    ├── Section 3: RulesSection (snap-start, h-screen)
    │   ├── SectionHeader (title="The Rules", quote="...")
    │   ├── RulesGrid (2x2 desktop, 1-col mobile)
    │   │   └── RuleCard (GlassCard + lucide icon + title + desc)
    │   │       icons: Heart, Clock, Shield, Flame (lucide-react)
    │   └── NikitaQuote
    │
    ├── Section 4: ProfileSection (snap-start, min-h-screen)
    │   ├── SectionHeader (title="Who Are You?", quote="...")
    │   ├── LocationInput (GlassCard + text input)
    │   ├── SceneSelector (NEW component — 5 visual cards)
    │   │   └── SceneCard (icon, title, desc, selected state)
    │   ├── EdginessSlider (NEW component — range 1-5)
    │   │   └── EmojiPreview (large emoji + label for current value)
    │   └── Form validation state (React useState)
    │
    └── Section 5: MissionSection (snap-start, h-screen)
        ├── SectionHeader (title="Your Mission")
        ├── MissionStatement ("Don't Get Dumped")
        ├── NikitaQuote (farewell)
        └── CTAButton
            ├── onClick: validate form → POST /api/v1/onboarding/profile
            ├── onSuccess: window.open("tg://resolve?domain=Nikita_my_bot")
            └── onError: show inline error message
```

### WF-9: ChapterStepper component detail

```
PROPS:
  currentChapter: number (1-5)
  chapters: Array<{ number, name, tagline, locked: boolean }>

DESKTOP (horizontal):
  ┌──────────────────────────────────────────────────────────────┐
  │                                                                │
  │  [*]━━━━━━━━[○]╌╌╌╌╌╌╌╌[🔒]╌╌╌╌╌╌╌╌[🔒]╌╌╌╌╌╌╌╌[🔒]       │
  │   I          II         III         IV          V              │
  │ Curiosity  Intrigue     ???         ???         ???            │
  │                                                                │
  └──────────────────────────────────────────────────────────────┘

  Node rendering:
  ┌─────────┐
  │ active: │  width: 40px, height: 40px, rounded-full
  │  [*]    │  bg: rose-500, border: 2px solid rose-400
  │         │  box-shadow: glow-rose (0 0 20px oklch(0.75 0.15 350 / 30%))
  │         │  inner: checkmark icon (lucide Check, white)
  │         │  animation: pulse (scale 1.0→1.05→1.0, 3s infinite)
  └─────────┘
  ┌─────────┐
  │ next:   │  width: 40px, height: 40px, rounded-full
  │  [○]    │  bg: transparent, border: 2px dashed rose-500/50
  │         │  inner: chapter number (text-rose-500/50)
  └─────────┘
  ┌─────────┐
  │ locked: │  width: 40px, height: 40px, rounded-full
  │  [🔒]   │  bg: muted, border: 1px solid muted-foreground/20
  │         │  inner: Lock icon (lucide Lock, muted-foreground/40)
  └─────────┘

  Connector rendering:
  completed:  height: 2px, bg: rose-500
  to-next:    height: 2px, border: dashed, border-color: rose-500/50
  locked:     height: 2px, bg: muted-foreground/20

MOBILE (vertical):
  Same node styles, but arranged vertically with connectors as
  vertical lines (width: 2px, height: 24px) between nodes.
  Chapter name + tagline displayed to the right of each node.
```

### WF-10: SceneSelector component detail (5 visual cards)

```
PROPS:
  value: string | null  (selected scene ID)
  onChange: (scene: string) => void

SCENE DEFINITIONS:
  ┌─────────────────────────────────────────────────────────────────┐
  │ ID       │ Icon │ Title     │ Description                       │
  ├──────────┼──────┼───────────┼───────────────────────────────────┤
  │ techno   │ 🎧   │ Techno    │ Dark clubs, warehouse parties     │
  │ art      │ 🎨   │ Art       │ Galleries, exhibitions, openings  │
  │ food     │ 🍽️   │ Food      │ Hidden gems, fine dining          │
  │ cocktails│ 🍸   │ Cocktails │ Speakeasies, rooftop bars         │
  │ nature   │ 🌿   │ Nature    │ Hiking, beaches, outdoors         │
  └─────────────────────────────────────────────────────────────────┘

CARD STATES:

  Unselected:                    Selected:
  +------------------+           +------------------+
  |  🎧              |           |  🎧              |  ← border: rose-500
  |  Techno          |           |  Techno          |    bg: rose-500/10
  |                  |           |                  |    glow-rose shadow
  |  Dark clubs,     |           |  Dark clubs,     |
  |  warehouse       |           |  warehouse       |
  |  parties         |           |  parties         |
  |                  |           |                  |
  | glass-card       |           | glass-card       |
  | border: white/10 |           | + checkmark top- |
  +------------------+           |   right corner   |
                                 +------------------+

LAYOUT:
  Desktop: 5 cards in a row (flex, gap-3)
  Mobile: 2x3 grid (last card centered), gap-3

INTERACTION:
  - Click/tap to select (only one active at a time)
  - Transition: border-color 150ms ease, background-color 150ms ease
  - Selected card has lucide Check icon in top-right corner (8px inset)
```

### WF-11: EdginessSlider component detail (1-5 with emoji previews)

```
PROPS:
  value: number (1-5)
  onChange: (value: number) => void

EMOJI MAP:
  1 = 😇  "Keep it clean"
  2 = 😏  "Light flirting"
  3 = 🌶️  "Spicy is okay"
  4 = 💀  "Dark humor welcome"
  5 = 🔥  "No limits"

LAYOUT:
  ┌──────────────────────────────────────────────────┐
  │                                                    │
  │              [🌶️]  ← large (text-4xl)             │
  │          Spicy is okay                             │
  │              ↑ current value label                 │
  │                                                    │
  │   😇────────●────────💀────────🔥────────😈       │
  │    1         2         3         4         5       │
  │              ↑ thumb at current position           │
  │                                                    │
  │   Track: h-2, bg-glass-border, rounded-full       │
  │   Filled: h-2, bg-rose-500 (from left to thumb)   │
  │   Thumb: w-6 h-6, bg-rose-500, rounded-full       │
  │          glow-rose shadow, cursor-pointer          │
  │                                                    │
  │   Emoji markers: text-lg, positioned above track   │
  │   at 0%, 25%, 50%, 75%, 100%                       │
  │                                                    │
  └──────────────────────────────────────────────────┘

IMPLEMENTATION:
  Use existing shadcn <Slider> component (wraps Radix SliderPrimitive).
  <Slider min={1} max={5} step={1} value={[value]} onValueChange={([v]) => onChange(v)}
    aria-valuetext={"Spicy is okay"} aria-label="Edginess level" />

  Radix provides for free:
  - Click/drag thumb along track
  - Snaps to integer values (step={1})
  - Keyboard: Left/Right arrow keys, Home/End
  - Touch support (mobile drag)
  - role="slider", aria-valuemin, aria-valuemax, aria-valuenow

  Custom additions:
  - On value change: large emoji + label update with
    crossfade animation (150ms opacity transition)
  - Emoji markers positioned above track at 0%, 25%, 50%, 75%, 100%
  - Custom thumb styling via className for emoji preview
```

### WF-12: Full-page scroll-snap layout (section arrangement)

```
SCROLL CONTAINER:
  <div className="
    h-screen overflow-y-auto
    snap-y snap-proximity       ← proximity (NOT mandatory) to handle
    scroll-smooth                  variable-height Section 4 on mobile
  ">

  NOTE: snap-mandatory breaks on mobile when Section 4 (profile form)
  exceeds viewport height — it forces users to the top of the section,
  making it impossible to scroll within the section to reach lower form
  fields. snap-proximity relaxes snapping for oversized sections while
  still snapping for viewport-sized sections 1-3 and 5.

SECTION TEMPLATE:
  <section className="
    snap-start
    min-h-screen           ← h-screen for sections 1-3,5
    flex flex-col           ← min-h-screen for section 4 (form may overflow)
    items-center
    justify-center
    px-4 md:px-8
    py-12 md:py-16
  ">
    <div className="w-full max-w-[720px]">
      {/* section content */}
    </div>
  </section>

SECTION ARRANGEMENT (vertical):

  +----------------------------------+
  | SECTION 1: The Score    [h-screen] |  snap-start
  |   ScoreRing + metrics              |
  +----------------------------------+
  | SECTION 2: The Chapters [h-screen] |  snap-start
  |   ChapterStepper                   |
  +----------------------------------+
  | SECTION 3: The Rules    [h-screen] |  snap-start
  |   4 rule cards                     |
  +----------------------------------+
  | SECTION 4: Who Are You? [min-h]    |  snap-start
  |   Location + Scene + Edginess      |
  |   (may exceed 1 viewport on mobile)|
  +----------------------------------+
  | SECTION 5: Your Mission [h-screen] |  snap-start
  |   CTA button                       |
  +----------------------------------+

SCROLL INDICATOR:
  Sections 1-4 show a subtle down-arrow indicator at bottom
  (animated bounce, opacity 0.5, hidden after first scroll)

BACKGROUND:
  bg-void (oklch(0.08 0 0)) — same as portal dashboard
  No gradient needed — glass cards provide visual depth
```

---

## UI Design Specifications

### Color tokens (oklch, matching existing design system in `portal/src/app/globals.css`)

All tokens are defined in `portal/src/app/globals.css`. The onboarding page uses the existing dark-only palette. No new color tokens are introduced.

| Token | Value | Usage |
|-------|-------|-------|
| `--background` / `--void` | `oklch(0.08-0.1 0 0)` | Page background |
| `--foreground` | `oklch(0.95 0 0)` | Primary text |
| `--primary` | `oklch(0.75 0.15 350)` | Rose accent — score ring, active chapter nodes, CTA button, selected scene card border |
| `--muted-foreground` | `oklch(0.6 0 0)` | Secondary text, locked chapters, Nikita quotes |
| `--glass` | `oklch(1 0 0 / 5%)` | Card backgrounds |
| `--glass-border` | `oklch(1 0 0 / 10%)` | Card borders, slider track |
| `--glass-elevated` | `oklch(1 0 0 / 8%)` | Elevated card variant (profile form cards) |
| `--rose-glow` | `oklch(0.75 0.15 350)` | Score ring glow, active chapter node, selected scene card |
| `--amber-glow` | `oklch(0.75 0.15 80)` | Boss encounter rule card accent |

### Typography

| Element | Class | Font |
|---------|-------|------|
| Section titles ("THE SCORE") | `text-xs md:text-sm font-medium uppercase tracking-[0.3em] text-muted-foreground` | Geist Sans |
| Nikita quotes | `text-sm md:text-base italic text-muted-foreground/80` | Geist Sans |
| Score value (in ring) | `text-4xl md:text-5xl font-bold tabular-nums` | Geist Mono |
| Metric labels | `text-xs text-muted-foreground` | Geist Sans |
| Metric values | `text-lg font-semibold tabular-nums` | Geist Mono |
| Chapter names | `text-sm font-medium` | Geist Sans |
| Rule card titles | `text-sm font-medium text-foreground` | Geist Sans |
| Rule card descriptions | `text-xs text-muted-foreground leading-relaxed` | Geist Sans |
| Form labels ("Where are you?") | `text-sm font-medium text-foreground` | Geist Sans |
| Form input text | `text-sm text-foreground` | Geist Sans |
| Mission headline ("Don't Get Dumped") | `text-2xl md:text-4xl font-bold tracking-tight` | Geist Sans |
| CTA button | `text-sm md:text-base font-medium` | Geist Sans |
| Edginess emoji (current) | `text-4xl` | System emoji |
| Edginess label (current) | `text-sm font-medium text-foreground` | Geist Sans |

### Responsive breakpoints

| Breakpoint | Layout changes |
|------------|----------------|
| `< 640px` (mobile) | Single column everything. Scene cards: 2-col grid. Chapter stepper: vertical. Rule cards: stacked. Score ring: size=160. Section padding: px-4 py-12. |
| `640px - 767px` (sm) | Scene cards: 3+2 row. Slight padding increase. |
| `>= 768px` (md) | Rule cards: 2x2 grid. Chapter stepper: horizontal. Score ring: size=200. Section padding: px-8 py-16. |
| `>= 1024px` (lg) | Max content width 720px centered. Scene cards: 5-in-a-row. Desktop spacing. |

Spacing scale (Tailwind): `gap-6` between form sections, `gap-4` within grids, `p-6` card padding, `space-y-4` between form fields.

### Animation specifications (framer-motion useInView)

| Animation | Trigger | Duration | Easing | Details |
|-----------|---------|----------|--------|---------|
| Score ring scale-in | Section 1 in view | 0.8s | `ease-out` | Ring SVG scales from 0 to 100% |
| Score number count-up | After ring (0.4s delay) | 0.8s | `ease-out` | Counter 0 → 75 |
| Rose glow pulse | After count-up | 0.3s | `ease-in-out` | box-shadow intensity pulse |
| Metric cards slide-up | After ring (staggered 0.1s each) | 0.5s | `ease-out` | translateY(20px) → 0, opacity 0→1 |
| Chapter nodes fade-in | Section 2 in view | 0.4s staggered 0.1s | `ease-out` | Scale 0.8→1, opacity 0→1 |
| Chapter connectors draw | After nodes | 0.6s staggered | `ease-out` | Width 0→100% (horizontal) or height 0→100% (vertical) |
| Rule cards fade-in | Section 3 in view | 0.3s staggered 0.1s | `ease-out` | translateY(20px) → 0, opacity 0→1 |
| Profile form entrance | Section 4 in view | 0.5s | `ease-out` | Entire form: opacity 0→1, translateY(20px)→0 |
| CTA button entrance | Section 5 in view | 0.5s | `spring(1, 80, 10)` | Scale 0.9→1, opacity 0→1 |
| Scene card selection | On click | 0.15s | `ease` | Border color + bg transition |
| Edginess emoji swap | On value change | 0.15s | `ease` | Crossfade (opacity transition) |
| Scroll indicator bounce | Always (sections 1-4) | 1.5s infinite | `ease-in-out` | translateY(0)→(8px)→(0) |

Implementation: Use framer-motion `useInView` hook with `once: true` for scroll-triggered reveals. The existing ScoreRing component already uses framer-motion animations — reuse as-is. For simple transitions (scene card selection, edginess emoji), use CSS transitions (no framer-motion needed).

### Accessibility

| Requirement | Implementation |
|-------------|----------------|
| Score ring | `role="meter"` with `aria-valuenow`, `aria-valuemin=0`, `aria-valuemax=100`, `aria-label="Relationship score: 75 out of 100"` (reuses existing ScoreRing ARIA) |
| Chapter stepper | `role="list"` with `role="listitem"` per chapter, `aria-current="step"` on current chapter |
| Rule cards | Semantic `<article>` elements with `<h3>` headings |
| Scene selector | Use shadcn `<RadioGroup>` + `<RadioGroupItem>` (wraps Radix RadioGroup primitive). Provides `role="radiogroup"` + `role="radio"` per card, roving tabindex (Arrow Up/Down/Left/Right), `aria-checked`, `aria-label` per card — all for free. Compose visual scene cards around `<RadioGroupItem>` for custom styling. Import: `import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"`. |
| Edginess slider | Use existing shadcn `<Slider>` component (`portal/src/components/ui/slider.tsx`, wraps Radix SliderPrimitive). Provides `role="slider"`, `aria-valuemin`, `aria-valuemax`, `aria-valuenow`, keyboard Left/Right/Home/End, touch support — all for free. Import: `import { Slider } from "@/components/ui/slider"`. Use `<Slider min={1} max={5} step={1} value={[value]} onValueChange={([v]) => onChange(v)} />`. Add `aria-valuetext` (label string) and `aria-label="Edginess level"` as props. Compose emoji markers as positioned elements above the track. Custom thumb styling for emoji previews via className. |
| Location input | `<label>` associated via `htmlFor`, `aria-required="true"`, `aria-describedby` pointing to error message element when validation fails. When using shadcn `<Form>` + `<FormField>` + `<FormItem>` + `<FormMessage>`, the `aria-describedby` wiring is automatic. |
| Form error messages | All error messages (validation errors in ProfileSection, submission errors in MissionSection) must use `role="alert"` for immediate screen reader announcement. Pattern: `{error && <p role="alert" className="text-destructive text-sm">{error}</p>}`. When using shadcn `<Form>` + `<FormMessage>`, field-level errors get `role="alert"` automatically. |
| CTA button | `role="button"`, keyboard-focusable (Tab), Enter/Space activation |
| Scroll sections | Each `<section>` has `aria-label` ("The Score", "The Chapters", etc.) |
| Reduced motion | `prefers-reduced-motion: reduce` — all framer-motion animations use `initial` as final state (no animation). CSS transitions set to 0ms. |
| Color contrast | All text passes WCAG AA (4.5:1 minimum) against dark backgrounds. Tested: oklch(0.95) on oklch(0.08) = ~18:1. |
| Keyboard navigation | Full Tab navigation through all interactive elements. Scene cards focusable, Enter/Space to select. |
| Screen reader | Section titles are `<h2>`, Nikita quotes use `<blockquote>` with `<cite>`. |

### Dark mode

The portal is dark-only (no light mode toggle). The `:root` CSS variables in `globals.css` define the single dark theme. The onboarding page inherits this directly. No `@media (prefers-color-scheme)` handling needed.

---

## Technical Architecture

### Auth Bridge: admin.generateLink() in otp_handler.py

**File**: `nikita/platforms/telegram/otp_handler.py` (modify `_offer_onboarding_choice`)

Replace the current voice/text choice with a magic link portal redirect:

```python
async def _offer_onboarding_choice(
    self,
    chat_id: int,
    user_id: str,
    telegram_id: int,
) -> None:
    """Send portal magic link for cinematic onboarding (Spec 081 v2).

    Replaces the voice/text choice with a single button that opens
    the portal at /onboarding, auto-authenticating via Supabase magic link.

    Falls back to regular portal URL if magic link generation fails.
    Schedules a 5-minute fallback for text onboarding if user doesn't click.
    """
    settings = get_settings()
    portal_url = settings.portal_url or "https://nikita.app"

    # Generate magic link via Supabase Admin API
    magic_link_url = await self._generate_portal_magic_link(
        user_id=user_id,
        redirect_path="/onboarding",
    )

    # Fall back to regular portal URL if magic link fails
    button_url = magic_link_url or f"{portal_url}/login?next=/onboarding"

    keyboard = [
        [
            {"text": "Enter Nikita's World  \u2192", "url": button_url},
        ],
    ]

    message = """You're in! \U0001f389

But before we really get started, there's something I want to show you.

My world. Our world, actually.

Tap below — it'll only take a minute."""

    await self.bot.send_message_with_keyboard(
        chat_id=chat_id,
        text=message,
        keyboard=keyboard,
        parse_mode="Markdown",
        escape=False,
    )

    # Schedule 5-minute fallback for text onboarding
    await self._schedule_onboarding_fallback(
        user_id=user_id,
        telegram_id=telegram_id,
        chat_id=chat_id,
    )
```

Magic link generation utility (add to `otp_handler.py` or extract to shared utility):

```python
async def _generate_portal_magic_link(
    self, user_id: str, redirect_path: str
) -> str | None:
    """Generate Supabase magic link for portal auto-auth.

    Uses service role key to call admin.generate_link().
    Falls back to None on any failure (caller uses regular URL).
    """
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_key:
        return None

    try:
        # Reuse the existing async Supabase client on TelegramAuth (self.supabase)
        # which is already initialized with the service role key.
        # Do NOT create a new sync client — it blocks the event loop.

        # Look up email from pending registration (already in handler context)
        # OR from auth.users via admin API
        auth_user = await self.supabase.auth.admin.get_user_by_id(user_id)
        email = auth_user.user.email
        if not email:
            return None

        portal_url = settings.portal_url or "https://nikita.app"
        redirect_to = f"{portal_url}{redirect_path}"

        result = await self.supabase.auth.admin.generate_link({
            "type": "magiclink",
            "email": email,
            "options": {"redirect_to": redirect_to},
        })

        return result.properties.action_link

    except Exception as e:
        logger.warning(f"Magic link generation failed for user {user_id}: {e}")
        return None
```

### Portal /onboarding route (Server Component + Client cinematic)

**File**: `portal/src/app/onboarding/loading.tsx` (new — loading skeleton)

Displays a skeleton while the Server Component fetches auth + stats (prevents blank page on cold start):

```tsx
export default function OnboardingLoading() {
  return (
    <div className="h-screen bg-void flex flex-col items-center justify-center">
      <div className="w-16 h-16 rounded-full border-2 border-primary/30 border-t-primary animate-spin" />
      <p className="mt-4 text-sm text-muted-foreground">Loading...</p>
    </div>
  )
}
```

**File**: `portal/src/app/onboarding/page.tsx` (new)

Server Component shell that checks auth and onboarding status:

```tsx
import { createClient } from "@/lib/supabase/server"
import { redirect } from "next/navigation"
import { OnboardingCinematic } from "./onboarding-cinematic"

export default async function OnboardingPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) redirect("/login")

  // Check if already onboarded — redirect to dashboard
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/api/v1/portal/stats`,
    {
      headers: {
        Authorization: `Bearer ${(await supabase.auth.getSession()).data.session?.access_token}`,
      },
      cache: "no-store",
    }
  )

  if (res.ok) {
    const stats = await res.json()
    if (stats.onboarded_at) redirect("/dashboard")
  }

  return <OnboardingCinematic userId={user.id} />
}
```

**File**: `portal/src/app/onboarding/onboarding-cinematic.tsx` (new)

Client component with scroll-snap sections, form state, and profile submission:

**Zod schema** (file: `portal/src/app/onboarding/schemas.ts`):

```typescript
import { z } from "zod"

export const profileSchema = z.object({
  location_city: z.string().min(2, "City is required"),
  social_scene: z.enum(["techno", "art", "food", "cocktails", "nature"], {
    required_error: "Pick a scene",
  }),
  drug_tolerance: z.number().min(1).max(5),
  life_stage: z.enum(["tech", "finance", "creative", "student", "entrepreneur", "other"]).optional(),
  interest: z.string().min(2).optional(),
})

export type ProfileFormValues = z.infer<typeof profileSchema>
```

**Client component** (file: `portal/src/app/onboarding/onboarding-cinematic.tsx`):

```tsx
"use client"

import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { Form } from "@/components/ui/form"
import { profileSchema, type ProfileFormValues } from "./schemas"
import { ScoreSection } from "./sections/score-section"
import { ChapterSection } from "./sections/chapter-section"
import { RulesSection } from "./sections/rules-section"
import { ProfileSection } from "./sections/profile-section"
import { MissionSection } from "./sections/mission-section"

interface OnboardingCinematicProps {
  userId: string
}

export function OnboardingCinematic({ userId }: OnboardingCinematicProps) {
  const form = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      location_city: "",
      social_scene: undefined,
      drug_tolerance: 3,
    },
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(values: ProfileFormValues) {
    setSubmitting(true)
    setError(null)

    try {
      const res = await fetch("/api/v1/onboarding/profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
      })
      if (!res.ok) throw new Error("Profile save failed")

      // Deep link back to Telegram
      window.open("tg://resolve?domain=Nikita_my_bot", "_self")
      // Fallback for desktop
      setTimeout(() => {
        window.open("https://t.me/Nikita_my_bot", "_self")
      }, 2000)
    } catch (e) {
      setError("Something went wrong. Please try again.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(handleSubmit)}>
        <div className="h-screen overflow-y-auto snap-y snap-proximity scroll-smooth bg-void">
          <ScoreSection />
          <ChapterSection />
          <RulesSection />
          <ProfileSection form={form} />
          <MissionSection submitting={submitting} error={error} />
        </div>
      </form>
    </Form>
  )
}
```

### Profile Save API: POST /api/v1/onboarding/profile

**File**: `nikita/api/routes/onboarding.py` (EXISTING — add the following endpoint and schema to the existing file. The router is already registered in `main.py` with `prefix="/api/v1/onboarding"`, so do NOT create a new router or duplicate the prefix.)

```python
# Add these imports to the existing onboarding.py:
from pydantic import BaseModel, Field
from nikita.db.repositories.profile_repository import ProfileRepository

VALID_SCENES = {"techno", "art", "food", "cocktails", "nature"}


class OnboardingProfileRequest(BaseModel):
    location_city: str = Field(..., min_length=1, max_length=100)
    social_scene: str = Field(...)
    drug_tolerance: int = Field(..., ge=1, le=5)


@router.post("/profile")
async def save_onboarding_profile(
    body: OnboardingProfileRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """Save profile from portal cinematic onboarding.

    Creates or updates user_profiles row, marks onboarding complete,
    and triggers venue research + scenario generation (async, non-blocking).
    """
    if body.social_scene not in VALID_SCENES:
        raise HTTPException(400, f"Invalid scene. Must be one of: {VALID_SCENES}")

    profile_repo = ProfileRepository(session)
    user_repo = UserRepository(session)

    # Create or update profile (uses existing create_profile method)
    # If profile already exists (idempotent re-submission), catch conflict and update
    existing = await profile_repo.get_by_user_id(user_id)
    if existing:
        existing.location_city = body.location_city
        existing.social_scene = body.social_scene
        existing.drug_tolerance = body.drug_tolerance
    else:
        await profile_repo.create_profile(
            user_id=user_id,
            location_city=body.location_city,
            social_scene=body.social_scene,
            drug_tolerance=body.drug_tolerance,
        )

    # Mark onboarding complete (sets onboarding_status='completed' + onboarded_at=now())
    await user_repo.update_onboarding_status(user_id, "completed")

    await session.commit()

    # Fire-and-forget: venue research + scenario generation
    try:
        import asyncio
        from nikita.services.venue_research import VenueResearchService
        venue_service = VenueResearchService(session)
        asyncio.create_task(
            venue_service.research_venues(body.location_city, body.social_scene)
        )
    except Exception as e:
        logger.warning(f"Venue research trigger failed (non-blocking): {e}")

    return {"status": "ok", "user_id": str(user_id)}
```

**Registration**: The `onboarding` router is ALREADY registered in `nikita/api/main.py` (line ~256) with `prefix="/api/v1/onboarding"`. No changes to `main.py` needed.

### Venue research + scenario generation (async during portal visit)

The profile endpoint triggers venue research and scenario generation as fire-and-forget tasks using `asyncio.create_task()`. These run in the background while the player transitions back to Telegram:

1. `VenueResearchService(session).research_venues(city, scene)` — existing service in `nikita/services/venue_research.py`. Called with the city and scene from the profile form.
2. `BackstoryGeneratorService.generate(user_id)` — existing service. Generates 3 scenario options for the user based on profile data.

Both services already exist and are used by the text onboarding flow. The portal endpoint reuses them identically.

### Telegram return: tg:// deep link + handoff

After the player completes the portal cinematic and submits their profile, the CTA button opens `tg://resolve?domain=Nikita_my_bot`. This is the standard Telegram deep link protocol:

- **Mobile (iOS/Android)**: Opens the Telegram app directly to the `@Nikita_my_bot` chat.
- **Desktop (macOS/Windows/Linux)**: Opens the Telegram desktop app (if installed) or falls back to `https://t.me/Nikita_my_bot` (Telegram Web).

The first Nikita message is sent via the existing handoff flow. If the player already received the first message (from the OTP handler or fallback), returning to Telegram shows the existing chat with Nikita.

### Fallback: 5-min timeout for text onboarding in Telegram

**File**: `nikita/platforms/telegram/otp_handler.py` (add method)

```python
async def _schedule_onboarding_fallback(
    self, user_id: str, telegram_id: int, chat_id: int
) -> None:
    """Schedule fallback text onboarding if user doesn't click portal link.

    After 5 minutes, checks if onboarded_at is set (existing column).
    If not, sends a fallback message and starts text onboarding.
    Uses the scheduled_events table for delivery.
    """
    from nikita.db.database import get_session_maker
    from nikita.db.models.scheduled_event import EventType
    from nikita.db.repositories.scheduled_event_repository import (
        ScheduledEventRepository,
    )

    try:
        async with get_session_maker()() as session:
            event_repo = ScheduledEventRepository(session)
            # NOTE: Add ONBOARDING_FALLBACK = "onboarding_fallback" to the
            # EventType enum in nikita/db/models/scheduled_event.py
            await event_repo.create_event(
                user_id=user_id,
                platform="telegram",
                event_type=EventType.ONBOARDING_FALLBACK,
                content={
                    "chat_id": chat_id,
                    "telegram_id": telegram_id,
                },
                scheduled_at=datetime.now(UTC) + timedelta(minutes=5),
            )
            await session.commit()
    except Exception as e:
        logger.warning(f"Failed to schedule onboarding fallback: {e}")
```

The `deliver` pg_cron job (already running every minute) picks up the event. The event handler checks `onboarded_at`:
- If set: discard the event (player completed portal onboarding).
- If not set: send fallback message and trigger `OnboardingHandler.start()`.

### Returning users: redirect to /dashboard (not /onboarding)

The Server Component in `/onboarding/page.tsx` checks the stats API for `onboarded_at`. If it exists, `redirect("/dashboard")` fires before any client component renders. This is a server-side redirect — the player never sees the onboarding page flash.

The middleware in `portal/src/lib/supabase/middleware.ts` does not need changes. The `/onboarding` route falls under the existing protected route logic (requires auth, redirects to `/login` if no session). The `/onboarding` path is not under `/admin`, so no admin role check fires.

---

## Database Changes

### Reuse existing `onboarded_at` column (NO new column needed)

The existing `users.onboarded_at` column (already set by `update_onboarding_status(user_id, "completed")`) serves as the portal completion timestamp. No new `onboarding_completed_at` column is needed. All references in this spec to `onboarding_completed_at` map to the existing `onboarded_at` column.

- **First-visit detection (FR-007)**: Check `onboarded_at IS NOT NULL` to determine if user has completed onboarding.
- **Fallback check (FR-006)**: Check `onboarded_at IS NOT NULL` to determine if portal onboarding was completed before fallback fires.
- **Stats API response**: Return `onboarded_at` as the completion timestamp field.
- **Text/voice onboarding**: Already sets `onboarded_at` via existing `complete_onboarding()` and `update_onboarding_status()` methods.

### ALTER TABLE users ADD COLUMN drips_delivered

```sql
ALTER TABLE users
  ADD COLUMN drips_delivered JSONB NOT NULL DEFAULT '{}'::jsonb;

COMMENT ON COLUMN users.drips_delivered IS
  'Tracks delivered progressive drips. Format: {"drip_id": "2026-03-22T10:00:00Z", ...}';
```

**SQLAlchemy model update** (`nikita/db/models/user.py`):

```python
# Progressive discovery drips (Spec 081 Phase 2)
drips_delivered: Mapped[dict] = mapped_column(
    JSONB, default=dict, nullable=False, server_default=text("'{}'::jsonb")
)
```

### ALTER TABLE users ADD COLUMN welcome_completed

```sql
ALTER TABLE users
  ADD COLUMN welcome_completed BOOLEAN NOT NULL DEFAULT false;

COMMENT ON COLUMN users.welcome_completed IS
  'Set to true after player completes portal welcome/onboarding tour';
```

**SQLAlchemy model update** (`nikita/db/models/user.py`):

```python
welcome_completed: Mapped[bool] = mapped_column(
    Boolean, default=False, nullable=False, server_default=text("false")
)
```

### RLS policy

All new columns are covered by the existing RLS policy on the `users` table:

```sql
-- Existing policy: "Users see own data"
-- FOR ALL USING (auth.uid() = id)
-- No additional policy needed.
```

### Migration

Apply both columns via Supabase MCP in a single atomic migration, then create a 2-line comment stub:

```sql
-- 20260322100000_add_drips_delivered_and_welcome_completed.sql
-- Applied via Supabase MCP: added drips_delivered, welcome_completed to users table (onboarded_at already exists)
```

---

## API Changes

### New endpoint: POST /api/v1/onboarding/profile

See [Profile Save API](#profile-save-api-post-apiv1onboardingprofile) section above for full implementation.

**Request**:
```json
{
  "location_city": "Berlin",
  "social_scene": "techno",
  "drug_tolerance": 4
}
```

**Response (200)**:
```json
{
  "status": "ok",
  "user_id": "uuid-here"
}
```

**Error responses**:
- 400: Invalid scene, empty location, drug_tolerance out of range
- 401: No valid JWT
- 500: Database error

### GET /api/v1/portal/stats (modification)

Add `onboarded_at` and `welcome_completed` fields to the existing stats response:

```json
{
  "relationship_score": 72.5,
  "chapter": 1,
  "chapter_name": "Curiosity",
  "game_status": "active",
  "days_played": 3,
  "boss_attempts": 0,
  "boss_threshold": 75,
  "onboarded_at": "2026-03-22T10:05:00Z",
  "welcome_completed": true,
  "metrics": { ... }
}
```

**Schema update** (`nikita/api/schemas/portal.py`):
```python
# Add to UserStatsResponse:
onboarded_at: datetime | None = None  # existing column, already set by update_onboarding_status
welcome_completed: bool = False
```

### PUT /api/v1/portal/settings (modification)

Accept `welcome_completed` in the settings update payload:

```json
{
  "welcome_completed": true
}
```

**Schema update** (`nikita/api/schemas/portal.py`):
```python
# Add to UpdateSettingsRequest:
welcome_completed: bool | None = None
```

---

## Testing Strategy

### Testing Pyramid

Target distribution: ~70% unit, ~20% integration, ~10% E2E.

**Coverage target**: >= 85% line coverage for all new code. Critical paths (profile endpoint, magic link generation) >= 90%.

### Unit Tests (~30 tests)

**File**: `tests/platforms/telegram/test_otp_handler_onboarding.py`

OTP handler magic link tests:
- `_generate_portal_magic_link()`: Success path returns action_link URL = 1 test
- `_generate_portal_magic_link()`: No email returns None = 1 test
- `_generate_portal_magic_link()`: Supabase error returns None = 1 test
- `_generate_portal_magic_link()`: Missing supabase_url returns None = 1 test
- `_offer_onboarding_choice()`: Sends message with magic link URL button = 1 test
- `_offer_onboarding_choice()`: Falls back to regular URL on magic link failure = 1 test
- `_offer_onboarding_choice()`: Schedules 5-minute fallback event = 1 test
- `_schedule_onboarding_fallback()`: Creates scheduled event with correct timing = 1 test
- `_schedule_onboarding_fallback()`: Failure does not raise = 1 test

**File**: `tests/api/routes/test_onboarding_profile.py`

Profile endpoint tests:
- Happy path: valid body → 200 + profile saved = 1 test
- Invalid scene → 400 = 1 test
- Empty location → 400 = 1 test
- drug_tolerance < 1 or > 5 → 400 = 1 test
- No JWT → 401 = 1 test
- Idempotency: calling twice updates (not duplicates) profile = 1 test
- Sets `onboarded_at` on user (via `update_onboarding_status`) = 1 test
- Venue research failure is non-blocking = 1 test

**File**: `tests/onboarding/test_fallback.py`

Fallback logic tests:
- Event fires when onboarded_at is null → sends message + starts text flow = 1 test
- Event discarded when onboarded_at is set = 1 test
- Fallback message matches expected text = 1 test

**File**: `tests/onboarding/test_drip_manager.py` (Phase 2 — retained from v1)

DripManager tests (14 tests from v1 spec, unchanged):
- `evaluate_user()`: 7 trigger conditions + 7 negative cases = 14 tests

### Integration Tests (~6 tests)

**File**: `tests/api/routes/test_onboarding_profile_integration.py`

Profile endpoint integration (with DB):
- Profile persisted in user_profiles table = 1 test
- `onboarded_at` set on users row = 1 test
- Repeated call updates existing profile = 1 test

**File**: `tests/platforms/telegram/test_otp_handler_integration.py`

OTP handler → scheduled event integration:
- `_schedule_onboarding_fallback()` creates event in scheduled_events table = 1 test
- Full OTP verification → magic link flow (mocked Supabase) = 1 test
- Fallback event delivery with onboarding check = 1 test

### E2E / Playwright Tests (~10 tests)

**File**: `portal/e2e/onboarding.spec.ts`

`/onboarding` page tests (follow existing `portal/e2e/dashboard.spec.ts` patterns using `mockApiRoutes`):

- E2E-1: Onboarding page renders all 5 sections (score, chapters, rules, profile, mission) = 1 test
- E2E-2: Score ring displays with animated entrance = 1 test
- E2E-3: Chapter stepper shows 5 chapters with Ch.1 active and Ch.2-5 locked = 1 test
- E2E-4: Rules section shows 4 glass cards = 1 test
- E2E-5: Scene selector — clicking a card selects it (visual state change) = 1 test
- E2E-6: Edginess slider — changing value updates emoji preview = 1 test
- E2E-7: Form validation — CTA disabled/error when location empty or scene not selected = 1 test
- E2E-8: CTA submits profile via POST /api/v1/onboarding/profile (intercept and verify body) = 1 test
- E2E-9: Returning user redirect — mock stats with `onboarded_at` set, navigate to `/onboarding`, assert redirect to `/dashboard` = 1 test
- E2E-10: Mobile layout — single-column scene cards, vertical chapter stepper = 1 test

### Mock Strategy

- **Supabase Auth Admin API**: `AsyncMock` for `supabase.auth.admin.generate_link()` returning `MagicMock(properties=MagicMock(action_link="https://test.supabase.co/auth/v1/verify?token=test123"))`. `AsyncMock` for `supabase.auth.admin.get_user_by_id()` returning mock user with `.user.email`.
- **TelegramBot**: `AsyncMock` for `bot.send_message_with_keyboard()` — verify URL button contains magic link. Matches existing patterns in `tests/platforms/telegram/test_otp_handler.py`.
- **ScheduledEventRepository**: `AsyncMock` for `create_event()` — verify `event_type="onboarding_fallback"` and `scheduled_at` is ~5 min in future.
- **ProfileRepository**: `AsyncMock` for `get_by_user_id()` and `create_profile()` — verify correct fields passed.
- **VenueResearchService**: `AsyncMock` for `research_venues(city, scene)` — verify called with correct city/scene. Not awaited (fire-and-forget).
- **Portal stats API in E2E**: `page.route()` interception for `**/api/v1/portal/stats` (with `onboarded_at` field) and `**/api/v1/onboarding/profile` — matches `portal/e2e/fixtures/api-mocks.ts` patterns.

### TDD Task Structure

Each user story follows RED-GREEN-REFACTOR:
1. **RED**: Write failing tests for all ACs in the story
2. **GREEN**: Implement minimal code to pass tests
3. **REFACTOR**: Clean up, ensure coverage targets met
4. Commit tests separately from implementation (2 commits minimum per story)

### CI/CD Integration

- Backend unit + integration tests run in `backend-ci.yml` (pytest, Python 3.12)
- Integration tests use `pytest.mark.integration` with `skipif(not _SUPABASE_REACHABLE)` guard
- Portal Playwright tests for `/onboarding` run in `portal-ci.yml` (Chromium)
- New test files are excluded from e2e/smoke markers by default (matching `pyproject.toml` addopts)

---

## Phase 2: Progressive Drips (Post-Launch)

The progressive drip system from v1 is retained as Phase 2, deployed after the portal-first cinematic onboarding is live and validated.

### DripManager (unchanged from v1)

**File**: `nikita/onboarding/drip_manager.py` (new file, Phase 2)

- 7 drips evaluated by pg_cron job (`POST /api/v1/tasks/check-drips`) every 5 minutes
- Rate limited: max 1 drip per 2 hours per user
- Each drip includes magic link portal button (reusing the auth bridge from Phase 1)
- Drips recorded in `users.drips_delivered` JSONB (column added in Phase 1)

### 7 Drip Definitions

| # | Drip ID | Trigger | Portal Path | Button Text |
|---|---------|---------|-------------|-------------|
| 1 | `first_score` | First conversation processed | `/dashboard` | "See Your Score" |
| 2 | `portal_intro` | 3+ conversations + drip 1 delivered | `/dashboard` | "Read Nikita's Diary" |
| 3 | `first_decay` | Score < 50 after decay event | `/dashboard` | "See What Changed" |
| 4 | `chapter_advance` | Chapter > 1 | `/dashboard` | "See Your Progress" |
| 5 | `boss_warning` | Score within 5 of boss threshold | `/dashboard` | "Check Your Status" |
| 6 | `boss_debrief` | Boss encounter resolved | `/dashboard` | "See What Happened" |
| 7 | `nikitas_world` | 24h after onboarding | `/dashboard` | "Explore Nikita's World" |

### Welcome messages (post-handoff, Phase 2)

2 scheduled Telegram messages after handoff (unchanged from v1):
- Message 1 (30-60s after first Nikita message): Emotional continuity
- Message 2 (3-5min later): Diary tease

These are complementary to the portal onboarding, providing continuity after the player returns to Telegram.

---

## Non-Functional Requirements

### NFR-001: Magic link generation latency (<2s)

The `admin.generate_link()` call is a single Supabase Admin API request. Expected latency: 200-500ms. The OTP success message is sent only after the magic link is generated (or after the fallback URL is constructed on failure). Total added latency to the OTP success flow: <2 seconds.

### NFR-002: Onboarding page load time (<3s on 3G)

The `/onboarding` page is a Server Component shell + Client Component. The client JS bundle includes framer-motion (already tree-shaken for the existing portal) and the section components. Target: <200KB gzipped total JS for the onboarding route. The page renders meaningful content (Section 1) before JS hydrates — sections below the fold load progressively.

### NFR-003: Profile submission latency (<1s)

The `POST /api/v1/onboarding/profile` endpoint writes to 2 tables (user_profiles, users) in a single transaction. Venue research and scenario generation are fire-and-forget (non-blocking). Response time: <500ms.

### NFR-004: Fallback delivery accuracy (5 min +/- 1 min)

The scheduled_events table + deliver pg_cron job (runs every minute) delivers the fallback. Combined: 5 min scheduling + 0-60s delivery = 5-6 min total. Acceptable tolerance.

### NFR-005: Failure isolation

- Magic link generation failure → fallback to regular portal URL. Never blocks OTP flow.
- Profile endpoint venue research failure → logged, does not fail the response.
- Fallback scheduling failure → logged, does not block the magic link message.
- Portal JS error → sections degrade gracefully (static content visible, animations disabled).

---

## Constraints & Assumptions

1. **Supabase magic link API**: Assumes `supabase.auth.admin.generate_link()` is available with the service role key. This is a server-side Admin API call.
2. **Telegram URL buttons**: Inline keyboard URL buttons open in the user's default browser. The magic link must be a full HTTPS URL (not a `tg://` URI).
3. **Portal URL configuration**: `settings.portal_url` already exists in `nikita/config/settings.py`. Must be set to `https://portal-phi-orcin.vercel.app` in production.
4. **User email availability**: Users registered via Telegram OTP always have an email (it is the OTP delivery address). The magic link will always succeed for new registrations.
5. **tg:// deep link support**: The `tg://resolve?domain=Nikita_my_bot` URI works on iOS, Android, and desktop Telegram clients. Web browsers without Telegram installed will show a protocol handler error — the `https://t.me/` fallback handles this.
6. **Scroll-snap browser support**: `scroll-snap-type: y proximity` is supported in all modern browsers (Chrome 69+, Safari 11+, Firefox 68+). No polyfill needed. Using `proximity` (not `mandatory`) to handle variable-height Section 4 on mobile.
7. **framer-motion bundle**: Already bundled in the portal (used by ScoreRing, MoodOrb, and other dashboard components). No additional bundle size from importing it in onboarding.

---

## Out of Scope

1. **Voice onboarding**: The voice call option is removed from the onboarding choice. Players who want voice interaction can access it later through the game. The Meta-Nikita voice agent (`nikita/onboarding/`) remains deployed for potential future reintroduction.
2. **Social login (Google/Apple)**: Deferred. Magic links are sufficient for this flow.
3. **Drip content personalization via LLM**: Phase 2 drips use static templates, not LLM content.
4. **A/B testing**: No experimentation framework. Ship one variant.
5. **Drip analytics dashboard**: No admin UI for drip performance. Track via database queries.
6. **Life stage and interest collection**: Reduced from 5 fields to 3 (location, scene, edginess). Life stage and primary interest are deferred to later discovery (conversational or settings page).
7. **Scenario selection during onboarding**: The backstory scenario selection (T4.3 in Spec 017) is deferred to a post-onboarding flow. The portal cinematic does not include scenario selection to keep the flow concise.
8. **Portal onboarding for admin users**: Admin users already have their own routes and do not see `/onboarding`.
9. **Re-triggering onboarding for existing users**: Existing users who already completed text onboarding will not be re-onboarded. The portal flow is for new users only.

---

## Open Questions

None. All design decisions resolved:

- **Auth bridge**: Supabase magic links via `admin.generateLink()` — zero-friction, leverages existing infrastructure.
- **Profile fields**: Reduced to 3 (location, scene, edginess) for a faster, more visual experience. Remaining fields collected later.
- **Fallback timing**: 5 minutes — long enough for portal completion (est. 2-3 min), short enough that impatient users get an alternative quickly.
- **Scroll-snap vs. stepper**: Scroll-snap chosen for cinematic feel and mobile-first design. Each section gets full-screen attention.
- **Deep link protocol**: `tg://resolve?domain=` with `https://t.me/` fallback — covers all platforms.
- **Phase 2 drips**: Retained from v1, shipped separately after portal onboarding is validated.
