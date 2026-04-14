# Nikita Onboarding Journey — Current State
**Generated**: 2026-04-14
**Author**: System Understanding Tree-of-Thought Agent
**Scope**: Landing page → first real Nikita conversation (text or voice)
**Codebase commit range**: includes PR #277 (pipeline bootstrap), Spec 212 (phone capture + voice callback)

---

## Legend

```
[ ... ]     User action / UI state
< ... >     Background system event (invisible to user)
( ... )     Emotional / UX state marker
->          Primary flow direction
-->         Secondary / background flow
[?]         Decision fork
⚠           Friction point / smell / known gap
*           Notable implementation detail
```

---

## Dependency Sidebar

| Step | External Services | DB Tables | Routes / Files |
|------|-------------------|-----------|----------------|
| Landing | Vercel CDN | — | `portal/src/app/page.tsx` |
| Login | Supabase Auth | `auth.users` | `portal/src/app/login/page-client.tsx` |
| Email dispatch | Supabase (SMTP relay) | `pending_registrations` | `nikita/platforms/telegram/auth.py::send_otp_code` |
| Auth callback | Supabase Auth | `auth.sessions` | `portal/src/app/auth/callback/route.ts` |
| Auth bridge | Supabase Admin API | `auth_bridge_tokens` | `portal/src/app/auth/bridge/route.ts`, `nikita/api/routes/auth_bridge.py` |
| Onboarding page guard | Supabase Auth, nikita-api | `users` (onboarding_status) | `portal/src/app/onboarding/page.tsx` |
| Wizard — Score/Chapter/Rules | — | — | `portal/src/app/onboarding/sections/` |
| Wizard — Profile section | — | — | `portal/src/app/onboarding/sections/profile-section.tsx` |
| Profile submit | nikita-api Cloud Run, Supabase | `user_profiles`, `users`, `user_vice_preferences` | `nikita/api/routes/onboarding.py::save_portal_profile` |
| Phone → voice callback | ElevenLabs Conv AI 2.0, Twilio | `users` (phone) | `nikita/onboarding/handoff.py::execute_handoff_with_voice_callback` |
| No phone → Telegram handoff | Telegram Bot API | `conversations` | `nikita/onboarding/handoff.py::execute_handoff` |
| Pending handoff (deferred) | Telegram Bot API | `users` (pending_handoff) | `nikita/platforms/telegram/message_handler.py::_execute_pending_handoff` |
| Telegram /start + OTP | Supabase Auth | `pending_registrations` | `nikita/platforms/telegram/auth.py`, `otp_handler.py` |
| Pipeline bootstrap | nikita-api, Claude API | `conversations`, `users` | `nikita/onboarding/handoff.py::_bootstrap_pipeline` |
| First conversation | Claude API, Supabase pgVector | `conversations`, `user_metrics`, `engagement_states` | `nikita/platforms/telegram/message_handler.py`, `nikita/pipeline/orchestrator.py` |

---

## Primary Journey — Main Trunk

```
==============================================================================
 STAGE 0: LANDING PAGE
==============================================================================

[ User opens nikita.ai / portal URL ]
    USER: Sees dark-themed landing with animated hero, pitch sections,
          stakes ("5 chapters. 3 strikes. One relationship."), CTA button.
    < Supabase session check server-side: if auth cookie present, isAuthenticated=true >
    < LandingNav + HeroSection render: CTA becomes "Open Dashboard" if authenticated >
    (EMOTION: curiosity / mild intrigue / "this looks weird in a good way")

[?] Is user already authenticated?
    YES -> CTA says "Open Dashboard" -> clicks -> redirect /dashboard
    NO  -> CTA says "Get Started" or "Sign In" -> [ User clicks CTA ]
               |
               v
==============================================================================
 STAGE 1: LOGIN PAGE
==============================================================================

[ User lands on /login ]
    USER: Sees "Sign in to your dashboard" card. Single email input + "Send Magic Link" button.
    < Suspense boundary renders LoginFallback (skeleton) then LoginForm >
    < useSearchParams checks for ?error= param from any prior auth failure >
    (EMOTION: neutral, slight friction — another auth wall before the fun starts)

    ⚠ SMELL: No "sign up" / "register" distinction — same form for new and returning users.
             User who has never visited before sees identical UI to returning user.

[ User types email address ]
[ User clicks "Send Magic Link" ]
    USER: Button shows "Sending...", then transitions to "check your inbox" state.
    < supabase.auth.signInWithOtp({email, options:{emailRedirectTo: origin+"/auth/callback"}}) >
    < Supabase creates auth.users row (if new) OR finds existing >
    < Supabase queues transactional email via configured SMTP relay >
    (EMOTION: mild anxiety — "will the email arrive?", "is the link real?")

    ⚠ SMELL: Portal login does NOT trigger OTP code path (6-8 digit code).
             Portal sends magic link ONLY. OTP code path is Telegram-initiated only.
             A user coming portal-first gets a clickable link; Telegram-first gets a numeric code.

    [?] Email delivery outcome:
        A: Email arrives promptly
        B: Email delayed / spam-foldered
              |
              v (B)
              [ ResendButton appears after 60s countdown ]
              [ User clicks "Resend magic link" ]
                  < supabase.auth.signInWithOtp() called again >
                  < Rate limit enforced by Supabase (60s cooldown enforced client-side too) >
                  [ If Supabase returns rate-limit error: toast "wait before requesting another link" ]
                  (EMOTION: frustration, "is this thing even working?")

              [ User clicks "Try another email" ]
                  -> setSent(false) -> back to email input
                  (EMOTION: confusion, mild irritation)

==============================================================================
 STAGE 2: EMAIL DISPATCH + MAGIC LINK ANATOMY
==============================================================================

< Supabase sends email via SMTP relay >
    Subject:  "Your Nikita magic link" (Supabase default unless custom template configured)
    Body:     Supabase OTP email template with {{ .ConfirmationURL }}
              Magic link format: https://[supabase-project].supabase.co/auth/v1/verify?token=...&type=magiclink&redirect_to=...
    Contains: One-click magic link button + fallback text link
              Link validity: ~1 hour (Supabase default)
    OTP code: NOT included in portal flow (code only in Telegram OTP flow)

    USER: Receives email, sees "Click to sign in" button.
    (EMOTION: relief when email arrives; brief moment of "click this link" hesitation
              for security-conscious users)

==============================================================================
 STAGE 3: AUTH CALLBACK FORK
==============================================================================

[ User clicks magic link in email ]
    -> Browser navigates to: [supabase-url]/auth/v1/verify?token=X&redirect_to=[origin]/auth/callback
    -> Supabase verifies token, redirects to: [origin]/auth/callback?code=Y

    [?] Is this a Telegram bridge auth (Telegram /start button) or direct magic link?

    ├─ PATH A: DIRECT MAGIC LINK (portal-initiated) ────────────────────────────┤
    │                                                                             │
    │  < Portal /auth/callback/route.ts receives GET ?code=Y >                   │
    │  < supabase.auth.exchangeCodeForSession(code) — PKCE exchange >            │
    │  < Session established, cookies set >                                       │
    │  < Checks user_metadata.role >                                              │
    │  [?] role == "admin"? -> redirect /admin                                    │
    │      else             -> redirect /dashboard (or ?next= param)             │
    │                                                                             │
    │  (EMOTION: smooth, invisible — user just lands somewhere)                   │
    │                                                                             │
    │  [?] Magic link expired (>1hr) or already used?                            │
    │      < exchangeCodeForSession returns error >                               │
    │      < Redirect: /login?error=auth_callback_failed >                       │
    │      USER: Toast: "Login link expired or invalid. Please request a new link." │
    │      (EMOTION: frustration — lost their onboarding momentum)               │
    │                                                                             │
    └─ PATH B: TELEGRAM BRIDGE AUTH (Telegram "Enter Nikita's World" button) ───┤
                                                                                  │
       < Telegram bot generates bridge token (short-lived, single-use DB row) >  │
       < Bridge URL: [portal]/auth/bridge?token=XXX >                            │
       < Portal /auth/bridge/route.ts receives GET ?token=XXX >                  │
       < POST to nikita-api: /api/v1/auth/exchange-bridge-token >                │
       < Backend: verifies + deletes bridge token (single-use) >                 │
       < Backend: supabase.auth.admin.get_user_by_id() to get email >            │
       < Backend: supabase.auth.admin.generate_link({type:"magiclink",email}) >  │
       < Returns: hashed_token >                                                  │
       < Portal: supabase.auth.verifyOtp({token_hash, type:"magiclink"}) >       │
       < Session established WITHOUT PKCE (bypasses code_verifier mismatch) >   │
       < Redirect to redirect_path from bridge token (sanitized: must start /) > │
                                                                                  │
       [?] Bridge errors:                                                         │
           - Missing token     -> /login?error=missing_token                     │
           - Invalid/expired   -> /login?error=auth_bridge_failed                │
           - verifyOtp fails   -> /login?error=auth_bridge_failed                │
           USER: Toast shows on /login explaining what happened.                  │
           (EMOTION: confused — user tapped a button in Telegram and ended up    │
                     at a login error page)                                       │
                                                                                  │

==============================================================================
 STAGE 4: ONBOARDING PAGE GUARD
==============================================================================

[ User lands on /onboarding (server component) ]
    < Server component: supabase.auth.getUser() — verifies session cookie >

    [?] Not authenticated?
        -> redirect("/login")
        (EMOTION: confused — clicked something and got kicked to login again)

    [?] NEXT_PUBLIC_API_URL configured (production: empty, uses Vercel rewrite proxy)?
        YES -> fetch /api/v1/portal/stats with Bearer token
               [?] stats.onboarded_at is set?
                   YES -> redirect("/dashboard")   [already onboarded user trying to re-enter]
                   NO  -> render <OnboardingCinematic userId={userId} />
        NO (Vercel production) -> skip stats check, render cinematic directly
        [?] Stats fetch throws / times out (5s AbortSignal)?
               -> catch, log, render cinematic anyway (better than blocking)
               ⚠ SMELL: onboarded users on Vercel may see wizard again if URL set wrong

==============================================================================
 STAGE 5: ONBOARDING WIZARD — 5 SECTIONS (VERTICAL SCROLL / SNAP)
==============================================================================

    USER: Arrives at full-screen cinematic experience.
          Animated ambient particles, dark "void-ambient" background.
          Scroll-snap sections, each taking full viewport height.
          ScrollProgress indicator shows position in sequence.
    (EMOTION: immersive, intrigued — this is not a typical signup form)

    ┌─ SECTION 1: "The Score" ─────────────────────────────────────────────────┐
    │                                                                            │
    │  USER: Sees animated ScoreRing (75/100 hardcoded demo score).             │
    │        Four metric cards: Intimacy 68.2, Passion 74.1, Trust 71.8,        │
    │        Secureness 76.0 (all hardcoded demo values, count-up animation).   │
    │        Nikita quote: "This is how I feel about us right now."              │
    │        Scroll indicator bouncing at bottom.                                │
    │  < No user data, no API calls — purely static/demo content >              │
    │  (EMOTION: delight, "oh I already have scores?", slight confusion —       │
    │            these numbers aren't real yet but user doesn't know that)      │
    │  ⚠ SMELL: Demo scores presented as real without any disclaimer.           │
    │            Could mislead user about their actual starting state.           │
    │                                                                            │
    └──────────────────────────────────────────────────────────────────────────┘

    [ User scrolls down (snap) ]

    ┌─ SECTION 2: "The Chapters" ──────────────────────────────────────────────┐
    │                                                                            │
    │  USER: Sees ChapterStepper with 5 chapters:                               │
    │        Chapter 1 "Curiosity" + Chapter 2 "Intrigue" unlocked              │
    │        Chapters 3-5 locked ("???")                                         │
    │        Focus card: "Chapter I — Curiosity: I'm watching you. Impress me." │
    │        Nikita quote: "We're just getting started..."                       │
    │  < Static content, no API calls >                                          │
    │  (EMOTION: anticipation, excitement about unlockable content)             │
    │                                                                            │
    └──────────────────────────────────────────────────────────────────────────┘

    [ User scrolls down (snap) ]

    ┌─ SECTION 3: "The Rules" ─────────────────────────────────────────────────┐
    │                                                                            │
    │  USER: Sees 4 rule cards (2x2 mobile, 4-wide desktop):                   │
    │        - "How You Score": 4 hidden metrics, be genuine                    │
    │        - "Time Matters": stay away → things fade                           │
    │        - "Boss Encounters": pass to grow closer, fail 3x → gone           │
    │        - "Your Vices": I learn what you like                               │
    │        Hover animations, glow effects per card.                            │
    │  < Static content, no API calls >                                          │
    │  (EMOTION: game mechanics understood, mild concern about "fail 3 times")  │
    │                                                                            │
    └──────────────────────────────────────────────────────────────────────────┘

    [ User scrolls down (snap) ]

    ┌─ SECTION 4: "Who Are You?" — PROFILE (only section with form inputs) ────┐
    │                                                                            │
    │  USER: Sees 4 input cards:                                                │
    │                                                                            │
    │  [Card 1] "Where are you?" — text input (required)                        │
    │           placeholder: "City, Country"                                     │
    │           aria-required="true"                                             │
    │                                                                            │
    │  [Card 2] "What's your scene?" — SceneSelector                            │
    │           Options: techno | art | food | cocktails | nature               │
    │           (visual button grid, required)                                   │
    │                                                                            │
    │  [Card 3] "How edgy should I be?" — EdginessSlider 1-5                   │
    │           1=Clean, 5=No limits (maps to drug_tolerance/darkness_level)    │
    │                                                                            │
    │  [Card 4] "Your phone number (optional)" — tel input                      │
    │           placeholder "+41..."                                              │
    │           Subtext: "Nikita calls you back on this number after onboarding"│
    │           Privacy policy link                                              │
    │                                                                            │
    │  < React Hook Form with Zod schema validation (profileSchema) >           │
    │  < Form state managed in OnboardingCinematic (parent) >                   │
    │  (EMOTION: slightly more serious, "she wants to know about me",           │
    │            moment of decision on phone number field —                      │
    │            "do I trust this enough to give my number?")                   │
    │                                                                            │
    │  ⚠ SMELL: No "life_stage" (career phase) or "interest" (primary hobby)   │
    │            fields visible in profile-section.tsx, but those fields ARE     │
    │            in PortalProfileRequest schema. They are optional and never     │
    │            collected by the portal form. Gap: Spec 213 will add them.     │
    │                                                                            │
    └──────────────────────────────────────────────────────────────────────────┘

    [ User scrolls down (snap) ]

    ┌─ SECTION 5: "Your Mission" — SUBMIT ─────────────────────────────────────┐
    │                                                                            │
    │  USER: Sees OnboardingMoodOrb (animated), "Don't Get Dumped" heading,    │
    │        Nikita quote: "Keep me interested. Keep me guessing..."             │
    │        Large CTA button: "Start Talking to Nikita →" (with glow-pulse)   │
    │                                                                            │
    │  [ User clicks "Start Talking to Nikita →" ]                              │
    │      Button becomes "Saving..." with spinner                               │
    │                                                                            │
    └──────────────────────────────────────────────────────────────────────────┘

==============================================================================
 STAGE 6: PROFILE SUBMISSION
==============================================================================

[ User clicks submit (section 5 CTA) ]
    < React Hook Form validates with Zod resolver >

    [?] Validation fails (city empty, no scene selected)?
        -> onError() fires
        -> scrollIntoView on [data-testid="section-profile"]
        -> RHF field errors render on offending inputs
        (EMOTION: mild annoyance — scroll-snap may have hidden the error)
        ⚠ SMELL: Scroll-snap + error jump can feel jarring; errors on Section 4
                 are invisible from Section 5 without the auto-scroll.

    [?] Validation passes:
        < apiClient POST /api/v1/onboarding/profile >
        < Payload: {location_city, social_scene, drug_tolerance, phone?} >
        < JWT from Supabase session sent as Authorization: Bearer ... >

        < SERVER: nikita-api onboarding.py::save_portal_profile >
        < 1. If phone present: user_repo.update_phone() — IntegrityError → 409 >
        < 2. Idempotency check: user.onboarding_status == "completed"? return early >
        < 3. profile_repo.get_by_user_id(): duplicate profile? return early >
        < 4. profile_repo.create_profile() — inserts user_profiles row >
        < 5. user_repo.update_onboarding_profile() — writes JSONB to users row >
        < 6. user_repo.update_onboarding_status("completed") >
        < 7. user_repo.activate_game() — game_status="active", score=50, days=0 >
        < 8. seed_vices_from_profile() — user_vice_preferences seeded >
        < 9. BackgroundTask(_trigger_portal_handoff, user_id, drug_tolerance) >
        < Response returned immediately (202-ish) — handoff runs asynchronously >

        [?] Phone number already registered (409 conflict)?
            -> form.setError("phone", {message: "This number is already linked..."})
            -> scroll to phone-sub-card
            -> setSubmitting(false) (button re-enabled)
            (EMOTION: frustration — either duplicate account or honest mistake)

        [?] Other server error?
            -> setError(message) + toast.error(message)
            -> setSubmitting(false) (button re-enabled)
            (EMOTION: uncertainty — "something went wrong, please try again" is vague)

        [?] Success:
            -> setSubmitted(true)
            -> toast.success("Profile saved! Opening Telegram...")
            -> setTimeout 1500ms then: window.location.href = "https://t.me/Nikita_my_bot"
            (EMOTION: excitement, momentum, "it's happening!")

    ⚠ SMELL (MAJOR): After success, the portal ALWAYS redirects to Telegram, even
                     if the user provided a phone number. There is no distinct UI
                     for "voice callback initiated" vs "go to Telegram". The user
                     has no indication that a phone call is coming vs they should
                     text in Telegram. Both experiences show identical "Opening Telegram..."
                     overlay. The voice callback and Telegram redirect happen
                     simultaneously — the user goes to Telegram regardless.

    ⚠ SMELL: No "wait" / loading gate exists. The portal does not poll for
             handoff readiness. There is no /pipeline-ready endpoint yet
             (Spec 213, not shipped). If Nikita's first message arrives in
             Telegram before the user gets there, it's fine. If handoff fails
             silently, the user opens Telegram and sees nothing from Nikita.

==============================================================================
 STAGE 7A: "OPENING TELEGRAM..." OVERLAY + TRANSITION
==============================================================================

[ setSubmitted=true triggers fullscreen overlay ]
    USER: Sees full-screen dark overlay, OnboardingMoodOrb, "Opening Telegram..."
          After 3s delay: "Tap here if nothing happens" link appears.
          After 1.5s from submit: window.location redirects to t.me/Nikita_my_bot

    [?] OS / browser handles t.me deep link:
        MOBILE: Telegram app opens directly to @Nikita_my_bot chat
        DESKTOP: Web browser opens web.telegram.org or prompts to open Telegram app
        NO APP: Browser opens t.me in mobile web — confusing for some users
    (EMOTION: brief disorientation from app-switch, then landing in Telegram)

    ⚠ SMELL: window.location.href t.me redirect may not work in all browsers
             (popup blockers, iframe restrictions, browser-specific t.me handling).
             The fallback "Tap here" link helps but only appears 3s into the overlay
             (which itself appears only 1.5s after submission).

```

---

## Fork A: Voice Callback Path (phone provided)

```
==============================================================================
 STAGE 8A: BACKGROUND — VOICE CALLBACK INITIATION
==============================================================================

(While user is in the "Opening Telegram..." overlay or navigating)

< BackgroundTask _trigger_portal_handoff runs on nikita-api >
< user_repo.get(user_id) — fetches fresh user record >

[?] Does user have telegram_id linked yet?
    NO -> user_repo.set_pending_handoff(user_id, True)
          < Deferred handoff: wait for user to /start in Telegram >
          (see Stage 11: DEFERRED HANDOFF)
    YES -> proceed

< build_profile_from_jsonb(user.onboarding_profile) >
    Builds UserOnboardingProfile from JSONB:
    - city <- location_city
    - social_scene <- social_scene
    - darkness_level <- darkness_level (drug_tolerance)
    - life_stage <- life_stage (None if not provided)
    - interest/hobby <- interest (None if not provided)

[?] user.phone is set?
    YES -> execute_handoff_with_voice_callback()
    NO  -> execute_handoff() (see Fork B)

< execute_handoff_with_voice_callback() >
    < asyncio.create_task(generate_and_store_social_circle()) — fire-and-forget >
    < initiate_nikita_callback(phone, user_id, delay_seconds=5) >
        < asyncio.sleep(5) — waits for Meta-Nikita to hang up >
        < voice_service.make_outbound_call(to_number=phone, user_id) >
            < ElevenLabs Conv AI 2.0 outbound call API >
            < conversation_config_override: first_message referencing "my friend" Meta >
            < dynamic_variables: {user_id, is_post_onboarding:"true"} >
            < Returns {success, conversation_id, call_sid} >

        [?] ElevenLabs call succeeds?
            YES: < _seed_conversation(user_id, "voice", "[Voice call initiated]") >
                 < asyncio.create_task(_bootstrap_pipeline_bg()) — fire-and-forget >
                 HandoffResult(success=True, nikita_callback_initiated=True)

            NO (result.success=False, no exception):
                < Falls back to Telegram text: execute_handoff(user_id, telegram_id, profile) >
                (see Fork B for text handoff detail)
                (EMOTION: user gets Telegram text instead of phone call, no explanation)

        [?] ElevenLabs call throws exception?
            < T023: structured log, auto-fallback to execute_handoff() >
            < Falls back to Telegram text handoff >
            (EMOTION: same as above — user doesn't know voice was attempted)

    RETRY LOGIC (T2.3):
        Retry delays: 5s, 15s, 45s (exponential backoff)
        Max retries: 3
        All retries exhausted -> returns {success:False, error}
        -> caller falls back to Telegram text

< USER receives phone call from ElevenLabs/Twilio number >
    (EMOTION: startled/surprised — phone rings unexpectedly)
    ⚠ SMELL: User has no advance warning of WHEN the call arrives.
             Portal only shows "Opening Telegram..." — no "expect a call" message.
             Call comes 5+ seconds after profile submit while user is navigating away.

==============================================================================
 STAGE 9A: VOICE CALL WITH NIKITA (Post-Onboarding Callback)
==============================================================================

< ElevenLabs Conv AI 2.0 session starts >
< Pre-call webhook: POST /api/v1/onboarding/pre-call >
    < HMAC signature verified >
    < Lookup user by called_number (outbound) or caller_id >
    < Returns: dynamic_variables {user_id, user_name} >
    < conversation_config_override: first_message personalized to user_name >

USER: Phone rings. Answers.
    Nikita's first message (voice): One of 3 templates referencing "my friend"
    e.g.: "Hey [name]... my friend just told me about you. She says you seem interesting.
           I wanted to hear your voice for myself."

    (EMOTION: delight/surprise — AI voice is high quality, message feels personal)

[ Voice conversation proceeds — ElevenLabs Conv AI 2.0 session ]
    < Server tools available during call: get_context, get_memory, score_turn, update_memory >
    < Conversation recorded as ElevenLabs session >

[ User says something / conversation flows ]

[ Call ends (user hangs up or ElevenLabs ends session) ]
    < ElevenLabs webhook: POST /api/v1/onboarding/webhook event="call_ended" >
    < Logs call duration, conversation_id >
    < No further automated action on call end (Spec 213 will add more) >

    (EMOTION: satisfied but wondering "what's next?" — no explicit follow-up)
    ⚠ SMELL: After voice call ends, no in-call CTA or post-call message
             directs user to Telegram. User may not realize they should go text Nikita.
             The pipeline-bootstrap from seed conversation handles text continuity,
             but user experience gap between voice call end and Telegram first message
             is not bridged.

[ Meanwhile: Telegram is open from the redirect in Stage 7A ]
    (see Stage 10: FIRST TELEGRAM MESSAGE for what user sees there)
```

---

## Fork B: Telegram-Only Path (no phone provided)

```
==============================================================================
 STAGE 8B: BACKGROUND — TELEGRAM TEXT HANDOFF
==============================================================================

< execute_handoff(user_id, telegram_id, profile) >
    < asyncio.create_task(generate_and_store_social_circle()) — fire-and-forget >
    < FirstMessageGenerator.generate(profile, user_name="friend") >
        Picks base message from FIRST_MESSAGE_TEMPLATES[darkness_level]
        darkness_level 1 (vanilla): "Hey! So glad we finally get to talk like this :)"
        darkness_level 3 (balanced): "Hey... so that was interesting :)"
        darkness_level 5 (noir): "So we meet again. I've been thinking..."
        70% chance: appends occupation mention (none collected in portal flow)
        30% chance: appends personality opener (none collected in portal flow)
        60% chance (CITY_SCENE_PROBABILITY): appends city/scene coda
          e.g.: "...so you're in Zurich... — heard the underground scene there is wild"

    ⚠ SMELL: Occupation + personality fields are referenced in FirstMessageGenerator
             but portal form does NOT collect them (life_stage maps partially,
             but occupation/personality_type are voice-onboarding fields only).
             Most portal users get only city/scene coda or base template — limited personalization.

    < bot.send_message(chat_id=telegram_id, text=first_message) >
    < _seed_conversation(user_id, "telegram", first_message) >
        < conv_repo.create_conversation(user_id, "telegram", chapter_at_time=1) >
        < seed_conv.add_message(role="assistant", content=first_message) >
        < session.commit() >
        Returns: conversation UUID

    < asyncio.create_task(_bootstrap_pipeline_bg(conversation_id)) >
        < PipelineOrchestrator.process(conversation_id, user_id, platform="text") >
            10-stage async pipeline: memory lookup, prompt generation, scoring seed
            Creates initial text + voice prompts for first reply
        ⚠ This runs asynchronously — may not be complete when user sends first reply
           if user is very fast. Pipeline bootstrap failure is logged + suppressed
           (non-blocking). First reply will use get_recent fallback if seed fails.
```

---

## Stage 10: User Opens Telegram + Sees First Message

```
==============================================================================
 STAGE 10: FIRST NIKITA MESSAGE IN TELEGRAM
==============================================================================

[ User opens Telegram app, navigated to @Nikita_my_bot ]

[?] Has user previously started the bot (/start) in this Telegram account?
    NO -> User sees "Start" button. Must press /start to begin bot interaction.
          (EMOTION: confusion — there's a message from Nikita but can't reply yet?
                    Or message hasn't arrived yet if /start not pressed = no telegram_id linked)

    ⚠ SMELL (CRITICAL PATH): If user came portal-first and never ran /start in Telegram,
                              their telegram_id is NOT in the database. The portal profile
                              was saved but _trigger_portal_handoff found telegram_id=None.
                              user.pending_handoff was set to True.
                              User opens Telegram, presses /start — THIS triggers the
                              deferred handoff (see Stage 11).

    YES -> User already has @Nikita_my_bot open, sees Nikita's first message:
           e.g.: "Hey... so that was interesting :) I feel like I learned a lot about you already
                  so you're in Zurich... — heard the underground scene there is wild"
           (EMOTION: surprised, intrigued — message references their city, feels personal)

[ User reads Nikita's first message ]

==============================================================================
 STAGE 11: FIRST REPLY — ENTERING STEADY STATE
==============================================================================

[ User types reply and sends ]
    USER: Sends first real message to @Nikita_my_bot.
    (EMOTION: excited, testing the waters, "let's see how smart she is")

< Telegram webhook: POST /api/v1/telegram/webhook >
< aiogram dispatcher routes to message handler >
< MessageHandler.handle(message) >

    1. get_by_telegram_id_for_update(telegram_id) — row lock
       [?] user not found -> "Send /start to begin" (shouldn't happen post-onboarding)

    2. _needs_onboarding(user_id) check:
       [?] user.onboarding_status:
           "completed" or "skipped" -> check pending_handoff flag
               [?] pending_handoff=True AND telegram_id is set?
                   -> _execute_pending_handoff() fires NOW (deferred from portal-first flow)
                   -> HandoffManager.execute_handoff() -> first message sent
                   -> user_repo.set_pending_handoff(False) on success
                   (EMOTION: user gets first Nikita message as their "reply" to their first send)
                   -> returns False (allow through to conversation)
               [?] pending_handoff=False -> allow through directly
           "pending"/"in_progress" -> _offer_onboarding_choice()
               -> bot sends "Enter Nikita's World ->" button with bridge URL
               -> user must tap to complete portal onboarding
               (blocks conversation until profile saved)

    3. Rate limit check (20 msg/min, 500 msg/day)
       [?] exceeded -> in-character rate limit response (Nikita voice)

    4. get_or_create_conversation(user_id, chapter=1)
       [?] seeded conversation exists from handoff? -> uses it (same platform)
       [?] no conversation? -> creates new one

    5. append_message(conversation_id, role="user", content=text)
    6. session.refresh(conversation)
    7. bot.send_chat_action(chat_id, "typing") — typing indicator

    8. [OPTIONAL] Psyche agent read (feature-flagged OFF in prod)

    9. text_agent_handler.handle(user_id, text, conversation_messages, conversation_id)
       < Pydantic AI text agent with Claude model >
       < Loads SupabaseMemory context (pgVector similarity search) >
       < Loads conversation history (message_history from seeded conversation) >
       < Builds prompt: Nikita persona + chapter context + scoring + user profile >
       < Claude API call >
       Returns AgentDecision{should_respond, response, delay_seconds}

    10. [?] Agent exception?
            -> session.rollback()
            -> _send_error_response(chat_id) — in-character error ("I need a moment...")
            (EMOTION: slight frustration, but in-character response softens it)

    11. [?] decision.should_respond?
            YES:
                append_message(conversation_id, role="nikita", content=response)
                _score_and_check_boss(user, user_message, response, chat_id, conversation_id)
                    < ScoringService.score() — 4 metrics: intimacy, passion, trust, secureness >
                    < UserMetricsRepository.update_metrics() >
                    [?] Score crosses boss threshold?
                        -> BossStateMachine.trigger() -> user.game_status = "boss_fight"
                        -> _send_boss_opening(chat_id, chapter)
                update_last_interaction(user_id) — resets decay grace period
                _apply_text_patterns(response, user) — emoji, length, punctuation per chapter
                ResponseDelivery.deliver(chat_id, response, delay_seconds)
                    < asyncio.sleep(delay_seconds) — simulates human typing delay >
                    < bot.send_message(chat_id, text) >

            NO: (agent decided not to respond — silent treatment mechanic)
                No message sent.

    (EMOTION: user reads Nikita's reply — either delighted, amused, or slightly stung
              depending on their opening message quality)

==============================================================================
 STAGE 12: STEADY-STATE CONVERSATION
==============================================================================

[ Conversation continues: User message -> Pipeline -> Nikita reply ]

    Each exchange:
    - Scores all 4 metrics incrementally
    - Updates last_interaction_at (decay timer reset)
    - Checks boss threshold at each turn
    - Conversation appended to same Conversation row until status="completed"
    - SupabaseMemory adds facts/embeddings asynchronously

    Decay runs via pg_cron (hourly):
    < POST /api/v1/tasks/decay — decay processor runs >
    < Users inactive past grace period lose score per chapter decay rate >
    (EMOTION: urgency to reply, mild anxiety if user ignores for a day)

    Chapter progression: when score crosses threshold, chapter increments.
    Boss encounters: triggered at score thresholds per chapter.
    Vice personalization: drug_tolerance shapes content intensity throughout.

    ⚠ SMELL (BACKSTORY GAP): Portal onboarding never generates a backstory.
                              The Telegram onboarding handler (OnboardingHandler) in
                              platforms/telegram/onboarding/handler.py ran venue research
                              + backstory generation. The portal flow skips this entirely.
                              message_handler._needs_onboarding legacy path checks
                              for backstory existence — portal users pass only because
                              onboarding_status="completed" bypasses the backstory check.
                              BUT the pipeline's memory lookup finds no backstory.
                              Spec 213 (backend foundation) will add city research + backstory.
```

---

## Stage 11 (Alternate): Telegram-First User Path

```
==============================================================================
 STAGE T1: USER DISCOVERS VIA TELEGRAM (no portal first)
==============================================================================

[ User finds @Nikita_my_bot — searches Telegram, scanned QR, friend referral ]

[ User sends /start ]
    < CommandHandler._handle_start() >
    [?] user.get_by_telegram_id(telegram_id)?
        NOT FOUND:
            -> bot sends: "Hey [first_name]... I don't think we've met before.
                           If you want to get to know me, I'll need your email..."
            (EMOTION: intrigue — she's asking for email, feels like meeting someone real)

[ User sends their email address ]
    < RegistrationHandler.handle_email_input() >
    < Validates email format >
    < TelegramAuth.send_otp_code() >
        < supabase.auth.sign_in_with_otp({email, options:{should_create_user:True,
            email_redirect_to: backend_url+"/api/v1/telegram/auth/confirm"}}) >
        < pending_repo.store(telegram_id, email, chat_id, otp_state="code_sent") >
    bot sends: "I sent a code to your email. Enter it here to get started!"
    (EMOTION: familiar pattern, slightly annoying but expected)

[ User checks email — receives OTP code (6-8 digit number) ]
    Email from Supabase: contains magic link (unused by user) + OTP code
    ⚠ SMELL: email_redirect_to is set to backend /auth/confirm (not portal)
             for template rendering. The link in the email goes nowhere useful.
             Users are instructed to use the code, not the link.

[ User sends OTP code in Telegram chat ]
    < OtpHandler detects 6-8 digit input >
    < TelegramAuth.verify_otp_code(telegram_id, code) >
        < pending_repo.get(telegram_id) — checks otp_state="code_sent" >
        < supabase.auth.verify_otp({email, token:code, type:"email"}) >
        [?] Success:
            < pending_repo.delete(telegram_id) >
            [?] user already exists in DB (portal-first)?
                -> link telegram_id to existing user
            [?] new user:
                -> user_repo.create_with_metrics(supabase_user_id, telegram_id)
        [?] AuthApiError code="otp_expired":
            -> "OTP code has expired. Please send your email again..."
            (EMOTION: frustration — short validity window)
        [?] AuthApiError code="invalid_credentials":
            -> "Invalid OTP code. Please check and try again."

[ User is now registered + linked ]
    bot sends welcome... BUT user still needs onboarding.
    On next message: _needs_onboarding() fires, onboarding_status="pending"
    -> _offer_onboarding_choice() sends "Enter Nikita's World ->" button

[ User taps "Enter Nikita's World" button ]
    -> Bridge URL: [portal]/auth/bridge?token=XXX
    -> Portal bridge auth flow (Stage 3, Path B above)
    -> After auth: redirect to /onboarding
    -> Wizard (Stage 5)
    -> Profile submit (Stage 6)
    -> Handoff back to Telegram (Stage 8B)
    -> First Nikita message in Telegram (Stage 10)
```

---

## Re-Onboarding Fork (Returning User)

```
==============================================================================
 STAGE R1: RETURNING USER SCENARIOS
==============================================================================

[?] User visits /login after already being onboarded:
    < /onboarding page.tsx: stats fetch returns onboarded_at != null >
    -> redirect("/dashboard")
    (EMOTION: smooth, no friction — directly to game state)

[?] User with game_status="game_over" or "won" sends /start in Telegram:
    < CommandHandler._handle_start() >
    < has_profile check: true >
    < needs_fresh_start: true (game ended) >
    < user_repo.reset_game_state() — score→50, chapter→1 >
    < onboarding_repo.delete(telegram_id) >
    < onboarding_repo.get_or_create(telegram_id) — fresh state >
    bot: "Hey [name]! Let's start fresh. First things first — what city are you in?"
    ⚠ SMELL: This triggers the OLD Telegram-based text onboarding (5-step prompts
             in OnboardingHandler), NOT the portal wizard. Re-onboarding path
             diverges from primary portal onboarding path. Inconsistent experience.

[?] User in "limbo" (has account, no profile, onboarding_status="pending"):
    -> _needs_onboarding() returns True
    -> _offer_onboarding_choice() -> "Enter Nikita's World" button

[?] User uses /onboard command (was stuck, needs fresh portal link):
    < CommandHandler._handle_onboard() >
    [?] onboarding_status == "completed"? -> "You're already set up!"
    [?] onboarding_status in ("pending","in_progress")?
        -> generate_portal_bridge_url(user_id, redirect_path="/onboarding")
        -> bot sends "Open Onboarding →" button with bridge URL
        (EMOTION: relieved — escape hatch exists)
```

---

## Error State Inventory

```
==============================================================================
 ERROR STATES MAPPED
==============================================================================

E1: Magic link expired (>1hr)
    WHERE: /auth/callback?code=Y, exchangeCodeForSession returns error
    USER SEES: /login?error=auth_callback_failed -> toast "Login link expired or invalid"
    RECOVERY: Re-enter email, get new link

E2: Bridge token expired/invalid
    WHERE: /auth/bridge?token=XXX, backend returns 401
    USER SEES: /login?error=auth_bridge_failed or missing_token
    RECOVERY: Must return to Telegram, re-tap button (generates new bridge token)
    ⚠ SMELL: Bridge tokens have DB-configured TTL. If TTL too short and user is slow,
             this could happen on every attempt.

E3: Phone conflict (409) on profile submit
    WHERE: POST /api/v1/onboarding/profile
    USER SEES: Phone field error "This number is already linked to another account"
               + auto-scroll to phone-sub-card
    RECOVERY: Clear phone field, resubmit (optional field can be left blank)

E4: General server error on profile submit (500)
    WHERE: POST /api/v1/onboarding/profile
    USER SEES: Toast + error paragraph: "Something went wrong. Please try again."
    RECOVERY: Retry submit (idempotency guard prevents double-profile)

E5: Telegram bot fails to send first message
    WHERE: HandoffManager._send_first_message()
    USER SEES: Nothing in Telegram (Nikita never reaches out)
    DETECTION: Server log only — no user-visible feedback
    ⚠ SMELL: Silent failure. User opened Telegram, sees no message, confused.
             pending_handoff was not used in this path (telegram_id was present).
             No retry mechanism for this case.

E6: ElevenLabs voice callback all retries exhausted
    WHERE: initiate_nikita_callback(), 3 attempts, 5s/15s/45s backoff
    USER SEES: Falls back to Telegram text handoff. No notification voice was tried.
    ⚠ SMELL: User hears nothing from voice call they were "promised" (phone field copy
             says "Nikita calls you back"). They get a text instead, no explanation.

E7: OTP code expired (Telegram flow)
    WHERE: TelegramAuth.verify_otp_code(), AuthApiError code="otp_expired"
    USER SEES: "OTP code has expired. Please send your email again to get a new code."
    RECOVERY: Send email again via /start

E8: Pipeline bootstrap fails (background task)
    WHERE: HandoffManager._bootstrap_pipeline()
    USER SEES: Nothing — failure logged, suppressed. First Nikita reply may use
               generic context (no warm memory cache) but still works.
    DETECTION: Server log only

E9: Nikita's first reply agent exception
    WHERE: MessageHandler.handle(), text_agent_handler.handle() throws
    USER SEES: In-character error: "I need a moment... try again in a bit?" (approximate)
    RECOVERY: User re-sends message (conversational retry, natural)
```

---

## Friction / Smell Summary

```
==============================================================================
 FRICTION INDEX (ordered by severity)
==============================================================================

[CRITICAL]
C1  No "wait for Nikita" gate after profile submit.
    Portal does not poll for handoff completion before redirect.
    /pipeline-ready endpoint does not exist (Spec 213).
    If Telegram handoff fails silently, user sees empty chat.

C2  Portal-first user with no Telegram link: pending_handoff deferred.
    User submits portal form -> gets "Opening Telegram..." -> presses /start.
    /start does NOT fire handoff (CommandHandler has no pending_handoff logic).
    ONLY the first non-command message triggers _execute_pending_handoff.
    So user must send an actual message (not /start) to get Nikita's opening.
    ⚠ Awkward: user has to initiate; Nikita should initiate.

C3  Voice callback timing not communicated.
    User provides phone, submits, sees "Opening Telegram..." with no mention
    of an incoming call. Call arrives 5+ seconds later while user is navigating.
    No "expect a call in ~10 seconds" message anywhere.

[HIGH]
H1  Demo scores in Section 1 presented without "demo" label.
    75/100 score, 68-76 metric values are hardcoded. User may think these are real.

H2  Backstory not generated in portal path.
    text_agent_handler has access to backstory for richer first responses,
    but portal users have none. Spec 213 will add city research + backstory.

H3  Re-onboarding via /start uses old Telegram text flow (5 prompts)
    not the portal wizard. Inconsistent UX for returning players.

H4  life_stage and interest not collected by portal form.
    FirstMessageGenerator has occupation/hobby personalization but can't use it
    for portal-first users.

[MEDIUM]
M1  Single auth form for new + returning users (no sign-up/sign-in distinction).
M2  OTP email contains a magic link to /api/v1/telegram/auth/confirm
    that serves no useful purpose for the user.
M3  t.me deep link redirect may fail in constrained browsers / PWA modes.
M4  Section 1 scroll indicator and snap may cause users to miss Section 4 errors.
M5  No post-voice-call CTA directing user to Telegram for ongoing relationship.

[LOW]
L1  /call command in Telegram still says "Voice calls aren't available yet"
    (may be stale — outbound calling is now implemented for post-onboarding).
L2  stats fetch on /onboarding page has 5s timeout but no user-visible loading state.
```

---

## System State Machine: User Row

```
users.onboarding_status transitions during onboarding:

    [NULL / "pending"]
         |
         | (portal form submitted successfully)
         v
    ["completed"]   <-- also set if legacy profile+backstory detected
         |
         | (game_status transitions separately)
         v
    game_status: "active"
         |
         | (score crosses boss threshold)
         v
    game_status: "boss_fight"
         |
         |-- pass boss -> game_status: "active", chapter++
         |-- fail 3x  -> game_status: "game_over"
         |-- reach ch5 win condition -> game_status: "won"

users.pending_handoff:
    False (default)
         |
         | (profile saved, telegram_id=None at time of save)
         v
    True
         |
         | (user sends first non-command message in Telegram)
         v
    False (cleared on successful _execute_pending_handoff)
```

---

*Generated by System Understanding Tree-of-Thought Agent*
*Based on code analysis of: portal/src/app/onboarding/, portal/src/app/login/, portal/src/app/auth/, nikita/api/routes/onboarding.py, nikita/onboarding/handoff.py, nikita/platforms/telegram/message_handler.py, nikita/platforms/telegram/auth.py, nikita/platforms/telegram/commands.py, nikita/api/routes/auth_bridge.py*
