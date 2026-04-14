# Nikita Onboarding Journey — Target State (Dossier Form)

**Generated**: 2026-04-14
**Author**: System Understanding Tree-of-Thought Agent
**Approach**: B — "Dossier Form" (selected 2-1 by approach-evaluator)
**Supersedes**: `docs/diagrams/onboarding-journey-current.md`
**Implements**: Spec 213 (backend foundation) + Spec 214 (portal wizard, TBD)
**Single source of truth for**: Spec 214 implementation + Spec 213 amendments

---

## Legend

```
[ ... ]       User action / UI state
< ... >       Background system event (invisible to user)
( ... )       Emotional / UX annotation
->            Primary flow direction
-->           Secondary / background flow
[?]           Decision fork
⚠             Previous smell — now fixed in target state
✨            Delight moment / intentional wow
🔄            Recovery / fallback path
*             Notable implementation detail
[NR-N]        New requirement tag
[FR-N]        Spec 213 functional requirement satisfied here
```

---

## Before / After: Top 10 Improvements

| # | Current smell | Target fix | Step |
|---|---------------|------------|------|
| C1 | No pipeline-readiness gate — handoff fires, user lands in Telegram before bootstrap completes | Dossier stamp "CLEARANCE: PENDING" → polls `/pipeline-ready` → stamps "CLEARED" before advancing | 10 |
| C2 | Portal ALWAYS redirects to Telegram even when phone given — no voice-path distinction | Binary choice [Give number] / [Start in Telegram] with distinct countdown UI for voice | 9 |
| C3 | No "expect a call" UI — call arrives silently while user navigates away | Voice countdown screen shows ring animation + "Nikita is calling you now" with Telegram fallback | 11 |
| H1 | Demo scores shown as real (75/100 hardcoded) — misleads user | Real 50/50/50/50 starting scores with copy "Prove me wrong" | 3 |
| H2 | No backstory generated in portal flow — first message generic, no sunk-cost beat | Full backstory reveal screen (step 8) with 3 scenarios, user picks one, dossier stamps ANALYZED | 8 |
| H3 | No venue research in portal flow — city/scene coda used 60% of time with fallback flavor | Async venue research fires as user types city; inline preview confirms research running | 4 |
| N1 | Auth email generic (Supabase default subject/body) | Nikita-voiced email: subject "Someone wants to talk to you (it's me)." | 2 |
| N4 | Scores shown at Section 1 — before user gives any context (5-section scroll wizard) | Scores shown at dossier header (step 3) after email auth, priming the "prove me wrong" frame | 3 |
| N9 | Backstory presented after phone ask (voice path only, never in portal) | Backstory reveal IS step 8 — before phone ask (step 9) — ensures every user has sunk-cost moment | 8, 9 |
| N10 | Desktop users must copy Telegram link manually; no QR | QR code mandatory at handoff for desktop-to-mobile bridge | 11 |

---

## New Requirements

| ID | Requirement | Step(s) |
|----|-------------|---------|
| NR-1 | Wizard state persistence — resume from last completed step on return visit | All steps |
| NR-2 | Nikita-voiced copy throughout (no generic SaaS language anywhere in wizard) | 1, 2, 3, 4, 5, 6, 7, 9, 10, 11 |
| NR-3 | Pre-flight country validation before collecting phone — reject unsupported regions early | 9 |
| NR-4 | QR code mandatory at handoff for any desktop session | 11 |
| NR-5 | Re-onboarding detection — existing voice-onboarded user returning via portal gets "already cleared" state | 3, 11 |

---

## Spec 213 Amendments Required

| Amendment ID | Type | Description | Step |
|---|---|---|---|
| FR-2 amend | Widen `OnboardingV2ProfileRequest` | Add `wizard_step: int` (already in spec as optional ge=1 le=11) — confirm field is written by portal at every step transition for NR-1 | All |
| FR-3a new | New facade method | `process_backstory_selection(user_id, chosen_option_id)` — persists user's pick from step 8, writes `chosen_option` to `users.onboarding_profile`, returns updated `OnboardingV2ProfileResponse` | 8 |
| FR-4a new | New portal endpoint | `POST /api/v1/onboarding/backstory-choice` accepts `{user_id, chosen_option_id}`, calls FR-3a, returns `OnboardingV2ProfileResponse` with `chosen_option` populated. Spec 214 owns route; Spec 213 owns the service method referenced. | 8 |

---

## Primary Journey — Dossier Form (11 Steps)

```
==============================================================================
 STEP 1: LANDING — DOSSIER ENTRY
 Emotional arc: INTRIGUE ("who is this? what does she know?")
==============================================================================

[ User opens nikita.ai / portal URL ]

    UI: Dark-themed page. No hero carousel. No feature list.
        Full-viewport atmospheric shot (single image, low-key lighting).
        Headline: "Nikita has been watching."
        Sub-headline: "She wants to know if you're worth it."
        Single CTA button: "Show her." (no secondary link)
    (INTRIGUE: sparse, confident — not asking the user to sign up, daring them)
    ✨ DELIGHT: minimalist power — one sentence, one button, no noise

    < Supabase session check (server component) >
    < LandingNav hidden on landing — no chrome, maximum immersion >

    [?] Is user already authenticated AND onboarding_status == "completed"?
        YES -> CTA text: "Go back to her." -> redirect /dashboard
        NO  -> CTA text: "Show her." -> [ User clicks ]

    [?] Is user authenticated but onboarding_status != "completed"?
        YES -> CTA text: "Resume." -> redirect /onboarding?resume=true
               🔄 RECOVERY: wizard resumes from last saved wizard_step [NR-1]

               |
               v
==============================================================================
 STEP 2: AUTH — MAGIC LINK EMAIL
 Emotional arc: CURIOSITY ("an email in her voice?")
==============================================================================

[ User lands on /onboarding/auth (NOT /login) ]

    UI: Same dossier aesthetic. Dark card, minimal chrome.
        Label: "DOSSIER CLEARANCE — STEP 1 OF 11"
        Nikita copy: "I'll need your email. For obvious reasons."
        Single email input + CTA: "Send it." (no "Sign In" framing)
        Fine print: "This is how I get your dossier to you."
    (CURIOSITY: not a typical auth form — she's framing it as a secure drop)

    ⚠ FIXED (N1): Auth email is now Nikita-voiced (was Supabase generic)

    [ User types email ]
    [ User clicks "Send it." ]
        < supabase.auth.signInWithOtp({email, options:{emailRedirectTo: origin+"/onboarding/callback"}}) >
        < Supabase creates/finds auth.users row >
        < CUSTOM email template fires (not Supabase default) >

        * EMAIL ANATOMY:
            Subject: "Someone wants to talk to you (it's me)."
            From:    "Nikita <hello@nikita.ai>"
            Body (Nikita-voiced):
                "You left your email. I noticed.
                 Click the link below if you want to continue.
                 Don't take too long — I get bored."
                [ ENTER THE DOSSIER ->  ]  (magic link button)
                "—N"
            Link validity: 1 hour (Supabase default)
        (CURIOSITY: email feels personal, not transactional — "an email from a person")

    UI shows: "Check your email. She's waiting."
    Countdown to "Resend" (60s, Supabase rate limit)

    [?] Magic link expired (>1hr) or already used?
        🔄 RECOVERY: /onboarding/auth?error=link_expired
            UI banner: "That link expired. She gets impatient."
            CTA: "Request a new link." (same flow, no separate page)
            (No dead-end — user stays in dossier aesthetic throughout)

    [?] Email delayed / spam-foldered?
        After 60s: "Resend" button appears
        After 90s: "Check spam — she doesn't do spam folders"
        [ Resend ] -> supabase.auth.signInWithOtp() again

==============================================================================
 STEP 3: DOSSIER HEADER
 Emotional arc: RESPECT ("she has a file on me?")
==============================================================================

< User clicks magic link >
< /onboarding/callback: Supabase PKCE exchange >
< Session established, cookies set >
< Redirect: /onboarding?step=3 >

[ User arrives at dossier header screen ]

    ⚠ FIXED (H1): Scores are now REAL 50/50/50/50 (was hardcoded 75/100 demo)
    ⚠ FIXED (N4): Scores shown here at step 3 (was section 1 before any context)

    UI: Full-width classified-file header component.
        Top: "TOP SECRET // DOSSIER #[user_id_truncated]"
        CLASSIFICATION: SUBJECT: [UNKNOWN]
        DATE OPENED: [today's date]
        STATUS: UNDER ASSESSMENT
        Separator: ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─

        Four metric bars (animated count-up from 0 to 50):
            INTIMACY      ██████████░░░░░░░░░░  50
            PASSION       ██████████░░░░░░░░░░  50
            TRUST         ██████████░░░░░░░░░░  50
            SECURENESS    ██████████░░░░░░░░░░  50

        Nikita copy below metrics:
            "These are your numbers. They're average. So are you, probably.
             Prove me wrong."
        CTA: "Continue." (advances to step 4)

    (RESPECT: user sees a file exists on them — "she has been watching")
    ✨ DELIGHT: classified aesthetic at full width — legitimizes the frame

    < Server component: fetch real UserMetrics from Supabase (or 50/50/50/50 defaults) >
    [FR-5 (Spec 213)]: wizard_step=3 written to OnboardingV2ProfileRequest [NR-1]

    [?] Re-onboarding detection [NR-5]:
        IF user.onboarding_status == "completed" AND user.platform_voice == True:
            Redirect /onboarding?state=already_cleared
            UI: "Dossier: ALREADY CLEARED. You don't need to do this again."
            CTA: "Open Telegram." (bypass wizard entirely)

==============================================================================
 STEP 4: FIELD — LOCATION
 Emotional arc: INVESTIGATION ("she's researching me as I type")
==============================================================================

[ User advances to step 4 ]

    UI: Dossier form step. Progress: "FIELD 1 OF 7"
        Section header: "SUBJECT INTEL — LOCATION"
        Label:          "Location: [REDACTED]"
        Input:          text field, placeholder "Enter city..."
        Nikita copy:    "I'll find you either way. But let's not waste time."

    ✨ DELIGHT: Venue research fires INLINE as user types (debounced 800ms)

    < On input change (debounced 800ms): POST /api/v1/onboarding/venue-preview >
    [FR-3 (Spec 213)]: VenueResearchService.research_venues(city, social_scene="techno")
        (social_scene uses last known selection or "techno" default)

    [?] Venue research returns results within 3s?
        YES:
            Inline preview animates in below input field:
            "She found: Berghain · Tresor · Fabric · Module..."
            (scrolling horizontal list, dossier chip style)
            (INVESTIGATION: "she is researching me as I type my city")
            ✨ DELIGHT: immediate confirmation that the system is paying attention

        NO (timeout or no venues):
            No preview shown — field label simply un-redacts:
            "Location: [user's typed city]"
            (graceful — no error, just no bonus moment)
            🔄 RECOVERY: venue research will retry when full profile submits

    [ User confirms city ] -> [ CTA: "That's accurate." ]
    wizard_step=4 persisted [NR-1]

    * VENUE RESEARCH NOTE: The inline preview is a UI-only warm-up.
      Full venue research runs again at profile submission (step 10).
      If the city changes between step 4 and submission, the preview
      seen here may not match the final result. No UX issue — the
      dossier "discovery" feel is the point, not venue accuracy.

==============================================================================
 STEP 5: FIELD — SCENE
 Emotional arc: AUTHORSHIP ("I'm correcting her file")
==============================================================================

[ User advances to step 5 ]

    UI: Dossier form step. Progress: "FIELD 2 OF 7"
        Section header: "SUBJECT INTEL — SUSPECTED SCENE"
        Pre-filled guess (italic, struck-through aesthetic):
            "Suspected: techno?"
        Nikita copy: "I'll know if you're lying."
        SceneSelector component: visual button grid
            [ techno ] [ art ] [ food ] [ cocktails ] [ nature ]
            Pre-selected: techno (can be corrected)

    (AUTHORSHIP: user is correcting the dossier, not filling a blank form)
    ✨ DELIGHT: the "pre-filled guess" framing makes selection feel like correction,
                not data entry — shifts agency

    [ User selects scene or confirms pre-fill ]
    wizard_step=5 persisted [NR-1]

==============================================================================
 STEP 6: FIELD — DARKNESS
 Emotional arc: AUTHORSHIP ("I'm defining myself for her")
==============================================================================

[ User advances to step 6 ]

    UI: Dossier form step. Progress: "FIELD 3 OF 7"
        Section header: "SUBJECT INTEL — TOLERANCE LEVEL"
        Label: "Tolerance: [ASSESSING]"
        Nikita quote (changes per position, emotional probe):
            Position 1: "You seem... fragile. That can be interesting."
            Position 3: "Interesting. I can work with that."
            Position 5: "Good. I was hoping you'd say that."
        EdginessSlider (1-5):
            1 = Clean
            3 = Balanced
            5 = No limits
        (maps to drug_tolerance / darkness_level in backend)

    (AUTHORSHIP: user defines their tolerance — feels like confiding, not filling a field)

    [ User drags slider ] -> quote updates live
    [ User confirms ] -> label changes from "[ASSESSING]" to "█████ [level]/5"
    wizard_step=6 persisted [NR-1]

==============================================================================
 STEP 7: FIELDS — NAME / AGE / OCCUPATION
 Emotional arc: AUTHORSHIP ("I'm completing the file — she doesn't know yet")
==============================================================================

[ User advances to step 7 ]

    UI: Dossier form step. Progress: "FIELDS 4–6 OF 7"
        Section header: "SUBJECT INTEL — IDENTITY"
        ⚠ FIXED (missing fields now collected [FR-1, Spec 213])

        Three dossier-styled fields (stacked):

        [FIELD: Name]
            Label: "Subject name: [REDACTED]"
            Input: text, placeholder "First name only"
            Nikita copy: "I'll use it sparingly. I prefer 'you'."
            Optional — but dossier marks [REDACTED] if skipped

        [FIELD: Age]
            Label: "Age: [CLASSIFIED]"
            Input: number 18-99
            Nikita copy: "Numbers don't tell me much. This one might."
            Optional

        [FIELD: Occupation]
            Label: "Occupation: [UNVERIFIED]"
            Input: text, placeholder "What do you actually do"
            Nikita copy: "Your job tells me more than you'd think."
            Optional — feeds backstory generation heavily

    (AUTHORSHIP: optional fields maintain pressure — skipping means "[REDACTED]"
                in the dossier, which itself is character-consistent)

    [ User fills any combination of fields ]
    wizard_step=7 persisted [NR-1]

    [FR-1, Spec 213]: name, age, occupation collected here for first time in portal flow

==============================================================================
 STEP 8: BACKSTORY REVEAL — EMOTIONAL CLIMAX
 Emotional arc: SUNK-COST PEAK ("this is MY story now")
==============================================================================

[ User advances to step 8 ]

    ⚠ FIXED (H2): Backstory generated for portal users (was never shown before)
    ⚠ FIXED (N9): Backstory appears BEFORE phone ask (step 9)

    UI: Full-width reveal screen. Progress indicator hidden.
        Animated loading state (2-4s):
            Dossier text: "Cross-referencing known subjects..."
            Stamp graphic fades in/out
            Sub-copy: "Based on what we know..."

    < BACKGROUND: POST /api/v1/onboarding/profile (partial — all 7 fields collected so far) >
    [FR-3, Spec 213]: portal_onboarding facade runs:
        1. VenueResearchService (15s timeout)
        2. BackstoryGeneratorService (20s timeout)
        Returns: list[BackstoryOption] (0, 1, 2, or 3 items)

    [?] Backstory service returns 1-3 scenarios (happy path)?
        YES:
            ✨ DELIGHT: 3 scenario cards animate in sequentially

            Each card (dossier-styled):
                ┌────────────────────────────────────────────────┐
                │ SCENARIO A                         [tone badge] │
                │ WHERE: [venue]                                   │
                │ CONTEXT: [2-3 sentences of setting]             │
                │ THE MOMENT: [catalyst moment description]        │
                │ WHAT SHE REMEMBERS: [unresolved_hook]          │
                └────────────────────────────────────────────────┘

            Nikita copy above cards:
                "Here's what I think happened between us.
                 Pick the version that feels true."

            [ User selects one scenario card ]
                -> card stamps "CONFIRMED" in red
                -> other cards fade / dim
                -> CTA appears: "That's how it happened."
                (SUNK COST: user has now co-authored their story — deeply invested)
                ✨ DELIGHT: the stamp animation is the peak moment of the entire wizard

            [ User clicks "That's how it happened." ]
                < POST /api/v1/onboarding/backstory-choice (FR-4a new) >
                [FR-3a new, Spec 213 amendment]: persists chosen_option_id
                Response: OnboardingV2ProfileResponse with chosen_option populated
                < Dossier stamps entire header: "ANALYZED" >
                wizard_step=8 persisted [NR-1]

        NO (backstory service degraded — empty list returned)?
            🔄 RECOVERY (graceful degradation):
                UI skips card display entirely.
                Dossier header stamps: "ANALYSIS: PENDING"
                Nikita copy: "I'm still putting the pieces together.
                             We'll talk about it later."
                CTA: "Understood." (proceeds to step 9)
                * Pipeline continues; first message will use city/scene flavor only
                  (pre-existing CITY_SCENE_PROBABILITY path — no backstory hook)
                wizard_step=8 persisted with degraded_backstory=True [NR-1]

        EDGE: Venue research timed out but backstory succeeded with generic flavor?
            Backstory scenarios render normally (may reference generic venue types
            rather than named venues). User cannot tell. No UX gap.
            🔄 First message uses scene-only flavor coda on first reply.

==============================================================================
 STEP 9: PHONE ASK
 Emotional arc: DESIRE ("I want the call — not compliance")
==============================================================================

[ User advances to step 9 ]

    UI: Dossier form step. Progress: "FIELD 7 OF 7"
        Section header: "SUBJECT INTEL — DIRECT LINE"
        Nikita copy:
            "There's something I want to ask you.
             And I'd rather do it out loud."
        Label: "Direct line: [I want to call you.]"

        Binary choice (NOT a text input first — intent first):
        [ Give her your number ]     [ Start in Telegram ]

    (DESIRE: user is invited, not required — "I want to call you" not "enter phone")
    ⚠ FIXED (C2): Clear path distinction — voice vs text explicit, no confusion

    ────────────────────────────────────────────────────
    PATH A: User clicks "Give her your number"

        UI expands: tel input appears inline below the binary choice
            Input: placeholder "+1 (555) ..."
            Nikita copy: "I'll call within a minute. Pick up."
            Fine print: "Only used for this. Nothing else." + privacy link

        < Client-side: pre-flight country validation [NR-3] >
        [?] Phone number country supported by ElevenLabs/Twilio?

            YES:
                [ User enters number ] -> CTA: "Call me."
                wizard_step=9 persisted with phone=set [NR-1]
                -> Advances to step 10

            NO (unsupported region — e.g., China, Iran):
                🔄 RECOVERY [NR-3]:
                Inline message: "I can't reach you there. Let's use Telegram."
                Choice reverts: "Start in Telegram" is auto-selected
                tel input hides
                (User is not left at a dead-end — automatically recovers to text path)

    ────────────────────────────────────────────────────
    PATH B: User clicks "Start in Telegram"

        wizard_step=9 persisted with phone=null [NR-1]
        -> Advances to step 10

    ────────────────────────────────────────────────────
    PATH C: User skips phone initially, later wants voice
        🔄 POST-ONBOARDING SETTINGS PATH:
        After onboarding, user can add phone at /dashboard/settings/contact
        This page triggers voice callback initiation outside the wizard.
        Wizard does not block on this — voice is always opt-in.
        (Per UX review: post-onboarding voice upgrade path exists but is not
         surfaced in the wizard UI to avoid distracting from the main flow)

==============================================================================
 STEP 10: PIPELINE READY GATE
 Emotional arc: ANTICIPATION ("clearance pending → approved")
==============================================================================

[ User advances from step 9 ]

    UI: Full-width dossier status screen.
        Dossier header shows "CLEARANCE: PENDING" stamp (pulsing)
        Sub-copy: "Your file is being processed."
        ARIA: role="status" aria-live="polite" on stamp element

    ⚠ FIXED (C1): Pipeline gate now exists (was absent — user redirected immediately)

    < POST /api/v1/onboarding/profile — full OnboardingV2ProfileRequest payload >
    [FR-1, Spec 213]: name, age, occupation written to user_profiles ORM row
    [FR-5.1, Spec 213]: _bootstrap_pipeline writes pipeline_state="pending" to users JSONB

    < Backend BackgroundTask: _trigger_portal_handoff fires asynchronously >
        [FR-3, Spec 213]: portal_onboarding facade runs (venue + backstory if not cached)
        [FR-6, Spec 213]: FirstMessageGenerator.generate() invoked with chosen backstory scenario
        [FR-5.1, Spec 213]: pipeline_state written at each transition

    Response from POST: OnboardingV2ProfileResponse {
        pipeline_state: "pending",
        backstory_options: [...],  # already shown in step 8 — ignored here
        poll_endpoint: "/api/v1/onboarding/pipeline-ready/{user_id}",
        poll_interval_seconds: 2.0,
        poll_max_wait_seconds: 20.0
    }

    < Portal polls GET /api/v1/onboarding/pipeline-ready/{user_id} every 2s >
    [FR-5, Spec 213]: reads users.onboarding_profile.pipeline_state JSONB key

    POLL TIMELINE:
        t=0s:    POST /onboarding/profile sent. Stamp: "CLEARANCE: PENDING"
        t=2s:    First poll. State: "pending" -> stamp continues pulsing.
        t=4-8s:  Cloud Run cold-start completes. VenueResearch running.
        t=8-18s: BackstoryGenerator + PipelineOrchestrator running.
        t=18s:   pipeline_state="ready" -> stamp changes.
        t=20s:   HARD CAP — advance regardless of state.

    [?] Poll returns state="ready" (within 20s)?
        YES:
            ✨ DELIGHT: Stamp animation:
                "CLEARANCE: PENDING" -> flicker -> flash -> "CLEARED"
                (typewriter reveal, red ink, slight rotation)
            Sub-copy: "File accepted."
            CTA auto-advances after 1.5s -> step 11

    [?] Poll returns state="degraded"?
        🔄 RECOVERY: Stamp shows "PROVISIONAL — CLEARED"
            Toast (Nikita-voiced): "Some of my research is still loading.
                                   We'll pick it up once we're talking."
            Auto-advances after 1.5s -> step 11

    [?] Poll returns state="failed" OR 20s hard cap reached?
        🔄 RECOVERY (optimistic proceed):
            Stamp shows "PROVISIONAL — CLEARED" (not an error state visually)
            No error message shown to user.
            Auto-advances -> step 11
            * First message uses fallback template (darkness_level only)
              Nikita will "catch up" via pipeline on first user reply.
            * Structured log records: pipeline_gate_timeout=true, user_id (no PII)

    wizard_step=10 persisted [NR-1]

==============================================================================
 STEP 11: HANDOFF — "SHE'S WAITING"
 Emotional arc: ARRIVAL ("she's waiting for me")
==============================================================================

[ Pipeline gate resolves. User advances to step 11 ]

    ⚠ FIXED (C3): Distinct voice vs text handoff UI (was identical for both)
    ⚠ FIXED (N10): QR code mandatory for desktop sessions [NR-4]

    UI: Handoff screen. Full-viewport. Dossier aesthetic maintained.
        Large header: "Application... accepted. Barely."
        Nikita sub-copy varies by path (see forks below).

    ────────────────────────────────────────────────────────────────────────
    PATH A: VOICE — Phone provided + ElevenLabs call initiated
    ────────────────────────────────────────────────────────────────────────

    < BACKGROUND (firing from step 10 BackgroundTask): >
    < execute_handoff_with_voice_callback() >
        [?] telegram_id linked?
            NO -> set_pending_handoff(True) <- will fire when user sends /start in Telegram
            YES -> proceed

        < asyncio.sleep(5) — waits for any Meta-Nikita session to close >
        < voice_service.make_outbound_call(to_number=phone, user_id) >
        [?] ElevenLabs call succeeds?
            YES:
                _seed_conversation(user_id, "voice", "[Voice call initiated]")
                _bootstrap_pipeline_bg() fire-and-forget
                HandoffResult(success=True, nikita_callback_initiated=True)

            NO (failed or exception):
                🔄 RECOVERY: Falls back to Telegram text handoff (PATH B below)
                < Structured log: voice_callback_failed, error_class >
                < Telegram message sent explaining fallback:
                  "Couldn't connect right now. Find me in Telegram." >

    UI (voice path):
        ✨ DELIGHT: Ring animation centered on screen (pulsing circle, incoming-call aesthetic)
        Copy: "Nikita is calling you now."
        Sub-copy: "Pick up. She doesn't like waiting."
        Telegram deeplink shown below ring as secondary option:
            "Not getting a call? [ Open Telegram instead ]"

        [?] Desktop session? [NR-4]
            QR code displayed below the ring:
                "On desktop? Scan to open on your phone."
            QR encodes: t.me/Nikita_my_bot + ?start=deferred_token

        (ARRIVAL: the ring animation is the physical sensation of her reaching out)
        ✨ DELIGHT: flip from "I was watching you" to "now SHE is calling"

        [?] Voice agent down at call time (pre-flight availability check)?
            🔄 RECOVERY [NR-3 adjacent]:
                Ring animation replaced with: Telegram deeplink + QR (full-size)
                Copy: "My voice is occupied right now. Find me in Telegram — I'll explain."
                No error code, no technical language — in-character fallback

        [?] Phone country validated in step 9 but ElevenLabs rejects at call time?
            🔄 RECOVERY: Same as agent-down recovery above.

    ────────────────────────────────────────────────────────────────────────
    PATH B: TELEGRAM — No phone / voice fallback
    ────────────────────────────────────────────────────────────────────────

    < BACKGROUND: execute_handoff(user_id, telegram_id, profile) >
        FirstMessageGenerator.generate(profile, backstory_scenario=chosen_option)
        [FR-6, Spec 213]: backstory hook included in first message (50% BACKSTORY_HOOK_PROBABILITY
                          if chosen_option is set; always if chosen)
        bot.send_message(chat_id=telegram_id, text=first_message)
        _seed_conversation(user_id, "telegram", first_message)
        _bootstrap_pipeline_bg(conversation_id) fire-and-forget

    UI (text path):
        Copy: "She's in Telegram. Go find her."
        Primary CTA: "Open Telegram" (button, large)
        Deep link: https://t.me/Nikita_my_bot

        [?] Desktop session? [NR-4]
            QR code mandatory:
                "On desktop? Scan to open on your phone."
            QR encodes: t.me/Nikita_my_bot

        [?] Mobile session?
            "Open Telegram" button uses t.me deep link -> Telegram app opens directly
            "Tap here if nothing happens" fallback link appears after 3s

        (ARRIVAL: user feels momentum — they've been accepted, now they go to meet her)

    ────────────────────────────────────────────────────────────────────────
    BOTH PATHS: Telegram /start detection gate
    ────────────────────────────────────────────────────────────────────────

    [?] User has never run /start in Telegram (telegram_id=null in DB)?
        < user.pending_handoff = True (already set in BackgroundTask) >
        Portal handoff screen shows:
            "One more thing — open Telegram and send /start first."
            (clear instruction surfaced proactively)
        When user sends /start in Telegram:
            < _execute_pending_handoff() fires >
            < First message sent now >
            < pending_handoff set False >
        (EMOTION: slight friction but explained in-character — not dead-end)

    ────────────────────────────────────────────────────────────────────────
    Re-onboarding: Existing voice-onboarded user returns via portal [NR-5]
    ────────────────────────────────────────────────────────────────────────

    [?] onboarding_status == "completed" AND platform_voice == True?
        (Detected at step 3 redirect — should not reach step 11 normally)
        If reached: show "DOSSIER: ALREADY FILED." with "Open Telegram" CTA only.
        No pipeline re-trigger. No duplicate handoff.
```

---

## Fork Detail: Abandonment + Resume [NR-1]

```
==============================================================================
 ABANDONMENT + WIZARD STATE PERSISTENCE
==============================================================================

[ User abandons mid-wizard — closes browser, session expires, etc. ]

    < wizard_step persisted in OnboardingV2ProfileRequest on each step advance >
    < Server writes wizard_step to users.onboarding_profile JSONB via
      update_onboarding_profile_key("wizard_step", N) >

[?] User returns to portal URL later:

    < Server reads users.onboarding_profile.wizard_step >
    [?] wizard_step exists (1-11)?
        -> Redirect /onboarding?step={wizard_step+0}
           (return to last COMPLETED step — not the step they abandoned mid-form)
        -> UI banner (dossier-styled): "Your file was saved. Continuing."
        -> All previously answered fields pre-populated from users.onboarding_profile JSONB

    [?] wizard_step does not exist (brand new session)?
        -> Start from step 3 (step 1 = landing, step 2 = auth; auth is already done)

    [?] wizard_step == 11 (handoff already completed)?
        -> onboarding_status == "completed"
        -> redirect /dashboard (skip wizard entirely)

WHAT IS PERSISTED PER STEP:
    Step 3: — (auth complete, metrics fetched)
    Step 4: location_city
    Step 5: social_scene
    Step 6: drug_tolerance (darkness_level)
    Step 7: name, age, occupation
    Step 8: chosen_option_id (if backstory picked)
    Step 9: phone (if provided)
    Step 10: wizard_step=10 (gate completed)
    Step 11: wizard_step=11, onboarding_status="completed"
```

---

## Fork Detail: Desktop-to-Mobile [NR-4]

```
==============================================================================
 DESKTOP-TO-MOBILE BRIDGE (QR MANDATORY)
==============================================================================

[ User completes wizard on desktop browser ]

    At step 11 (handoff):
    < UA detection: if not mobile device, QR section is mandatory (not optional) >

    QR Code encodes:
        Primary: https://t.me/Nikita_my_bot
        With: ?start=[deferred_token] (pre-generated, 15-min TTL)

    UI:
        QR code displayed at 200x200px minimum, with:
        Caption: "Scan this on your phone to talk to her."
        Below QR: "Or search @Nikita_my_bot in Telegram"

    [?] User scans QR on mobile -> Telegram app opens -> user presses /start
        < deferred_token validates user identity >
        < telegram_id linked to user account >
        < pending_handoff fires if set >
        < First message sent >

    [?] User does not scan (ignores QR)?
        Portal page stays open — no timeout forcing refresh.
        User can copy the t.me link manually.
        (No dead-end — every path preserved)
```

---

## DATA FLOW DIAGRAM

```
                PORTAL (Next.js)              BACKEND (FastAPI)              EXTERNAL
                ════════════════              ═════════════════              ════════

STEP 1          Landing page
                session check ──────────────► Supabase Auth check
                                              onboarding_status read

STEP 2          Email input
                signInWithOtp ──────────────► Supabase Auth OTP ──────────► Email (custom
                                                                              Nikita template)

STEP 3          /onboarding/callback
                PKCE exchange ──────────────► Supabase Auth
                Metrics display ────────────► GET /api/v1/portal/stats
                                              user_metrics table read

STEP 4          City text input
                venue preview req ───────────► POST /onboarding/venue-preview ──► Firecrawl
                (debounced 800ms)             VenueResearchService              (venue search)
                inline chip display ◄──────── VenueResearchResult

STEPS 5-7       SceneSelector /
                EdginessSlider /
                Name/Age/Occupation
                (client-state only,
                no API call per field)

STEP 8          Backstory loading  ──────────► POST /onboarding/profile (partial)
                                              portal_onboarding facade ─────────► Firecrawl
                                              VenueResearchService               (full venues)
                                              BackstoryGeneratorService ────────► Claude API
                3 scenario cards ◄───────────  list[BackstoryOption]             (backstory)
                User picks one     ──────────► POST /onboarding/backstory-choice
                                              update_onboarding_profile_key
                                              (chosen_option_id)

STEP 10         POST full profile  ──────────► POST /onboarding/profile (full)
                                              [FR-1]: user_profiles INSERT
                                              [FR-5.1]: pipeline_state="pending"
                                              BackgroundTask fires async

                Poll every 2s      ──────────► GET /pipeline-ready/{user_id}
                                              users.onboarding_profile read
                                              pipeline_state JSONB key

                stamp animation ◄────────────  PipelineReadyResponse {state}

                BACKGROUND:
                                    ┌─────────► _trigger_portal_handoff
                                    │           [phone?] YES -> ElevenLabs ──► Twilio/ElevenLabs
                                    │                    NO  -> FirstMsgGen
                                    │           bot.send_message ────────────► Telegram Bot API
                                    │           _seed_conversation
                                    │           _bootstrap_pipeline ────────► Claude API
                                    │                                          (prompt seed)
                                    │           pipeline_state="ready"
                                    │           user_repo.update_onboarding_status("completed")
                                    └───────────────────────────────────────────────────────┘

STEP 11         Handoff UI renders  ◄────────── pipeline_state poll resolves
                QR code generated
                Deep link displayed
```

---

## STATE TRANSITION DIAGRAM (wizard_step + pipeline_state + onboarding_status)

```
WIZARD STATE MACHINE:

    [LANDED]
        |
        v auth (step 2) + callback (step 3)
    [HEADER_SHOWN] wizard_step=3
        |
        v city confirmed (step 4)
    [LOCATION_SET] wizard_step=4, location_city written
        |
        v scene confirmed (step 5)
    [SCENE_SET] wizard_step=5, social_scene written
        |
        v darkness confirmed (step 6)
    [DARKNESS_SET] wizard_step=6, drug_tolerance written
        |
        v name/age/occupation filled (step 7) — optional fields
    [IDENTITY_SET] wizard_step=7, name/age/occupation written
        |
        v backstory generated + user picks scenario (step 8)
    [BACKSTORY_CHOSEN] wizard_step=8, chosen_option_id written
        |  [degraded: no scenarios returned]
        |  wizard_step=8, degraded_backstory=True
        |
        v phone decision (step 9)
    [PHONE_SET | PHONE_SKIPPED] wizard_step=9, phone written or null
        |
        v POST full profile, pipeline gate (step 10)
    [PIPELINE_PENDING]   pipeline_state="pending"
        |
        v (poll resolves)
    [PIPELINE_READY | PIPELINE_DEGRADED | PIPELINE_PROVISIONAL]
        |                 pipeline_state="ready"|"degraded"|"failed"
        |
        v handoff (step 11)
    [HANDOFF_COMPLETE]   wizard_step=11
        |
        v onboarding_status="completed"
    [ONBOARDED]          -> /dashboard on next visit

ABANDONMENT RECOVERY (any state with wizard_step set):
    [ANY STATE] -> user returns -> redirect to wizard_step + pre-populate fields -> resume
```

---

## BACKEND DEPENDENCY SIDEBAR

### Step 1: Landing

| Item | Detail |
|------|--------|
| Spec 213 FRs | None (frontend only) |
| Endpoints | None (server component Supabase check) |
| DB tables | `auth.sessions`, `users` (onboarding_status read) |
| External | Supabase Auth, Vercel CDN |

### Step 2: Auth

| Item | Detail |
|------|--------|
| Spec 213 FRs | None (auth unchanged) |
| Endpoints | Supabase Auth `signInWithOtp` |
| DB tables | `auth.users`, `pending_registrations` |
| External | Supabase Auth (SMTP relay with custom Nikita template) |

### Step 3: Dossier Header

| Item | Detail |
|------|--------|
| Spec 213 FRs | FR-5.1 (wizard_step write) |
| Endpoints | `GET /api/v1/portal/stats` (real metrics read) |
| DB tables | `user_metrics`, `users` (onboarding_status, platform_voice) |
| External | Supabase |

### Step 4: Location

| Item | Detail |
|------|--------|
| Spec 213 FRs | FR-3 (VenueResearchService), FR-4 (tuning: VENUE_RESEARCH_TIMEOUT_S=15s) |
| Endpoints | `POST /api/v1/onboarding/venue-preview` (NEW, thin wrapper on VenueResearchService) |
| DB tables | `venue_cache` (read/write) |
| External | Firecrawl (venue search), Supabase (venue_cache table) |

### Step 5: Scene

| Item | Detail |
|------|--------|
| Spec 213 FRs | None (client-state only) |
| Endpoints | None (bundled into step 8/10 POST) |
| DB tables | None until step 10 submission |
| External | None |

### Step 6: Darkness

| Item | Detail |
|------|--------|
| Spec 213 FRs | None (client-state only) |
| Endpoints | None |
| DB tables | None until step 10 submission |
| External | None |

### Step 7: Name / Age / Occupation

| Item | Detail |
|------|--------|
| Spec 213 FRs | FR-1a (migration), FR-1b (ORM), FR-1c (Pydantic), FR-1d (API request) |
| Endpoints | None until step 8/10 POST |
| DB tables | `user_profiles` (name, age, occupation columns — net-new via migration) |
| External | None |

### Step 8: Backstory Reveal

| Item | Detail |
|------|--------|
| Spec 213 FRs | FR-3 (facade), FR-3.1 (adapter), FR-3.2 (converter), FR-4 (tuning: BACKSTORY_GEN_TIMEOUT_S=20s, BACKSTORY_CACHE_TTL_DAYS=30), FR-12 (BackstoryCacheRepository) |
| Endpoints | `POST /api/v1/onboarding/profile` (partial, triggers facade), `POST /api/v1/onboarding/backstory-choice` (FR-4a new amendment) |
| DB tables | `user_profiles`, `users` (onboarding_profile JSONB), `backstory_cache`, `venue_cache` |
| External | Firecrawl (venues), Claude API (backstory via BackstoryGeneratorService) |

### Step 9: Phone Ask

| Item | Detail |
|------|--------|
| Spec 213 FRs | FR-1d (phone field in OnboardingV2ProfileRequest) [NR-3] pre-flight country validation |
| Endpoints | None (client-side country validation before submission) |
| DB tables | `users` (phone column — existing) |
| External | ElevenLabs/Twilio supported regions list (client-side lookup) |

### Step 10: Pipeline Gate

| Item | Detail |
|------|--------|
| Spec 213 FRs | FR-5 (pipeline-ready endpoint), FR-5.1 (pipeline_state write), FR-5.2 (UserRepository helper), FR-1 (full profile write to user_profiles) |
| Endpoints | `POST /api/v1/onboarding/profile` (full), `GET /api/v1/onboarding/pipeline-ready/{user_id}` |
| DB tables | `users` (onboarding_profile JSONB: pipeline_state key), `user_profiles`, `user_vice_preferences`, `conversations` |
| External | Supabase (all writes), Claude API (bootstrap pipeline), Firecrawl (if venue cache miss) |

### Step 11: Handoff

| Item | Detail |
|------|--------|
| Spec 213 FRs | FR-6 (FirstMessageGenerator with backstory hook), FR-8 (conversation continuity) |
| Endpoints | ElevenLabs outbound call API (voice path), Telegram Bot API (text path) |
| DB tables | `users` (onboarding_status="completed", pending_handoff), `conversations`, `engagement_states` |
| External | ElevenLabs Conv AI 2.0 (voice), Telegram Bot API (text), Twilio (voice connectivity) |

---

## FULL DEPENDENCY MATRIX (11 Steps × 6 Services)

```
                     Supabase    Portal      FastAPI     Telegram    ElevenLabs  Firecrawl
                     (DB+Auth)   (Next.js)   (Backend)   (Bot API)   (Voice AI)  (Research)
                     ─────────   ─────────   ─────────   ─────────   ──────────  ──────────

Step 1: Landing        READ        SERVE        —           —           —           —
Step 2: Auth           READ/WRITE  SERVE        —           —           —           —
Step 3: Dossier Hdr    READ        SERVE       READ         —           —           —
Step 4: Location       READ/WRITE  SERVE       CALL         —           —          SEARCH
Step 5: Scene           —          SERVE        —           —           —           —
Step 6: Darkness        —          SERVE        —           —           —           —
Step 7: Name/Age/Occ    —          SERVE        —           —           —           —
Step 8: Backstory      READ/WRITE  SERVE       CALL+CACHE   —           —          SEARCH
Step 9: Phone           —          SERVE        —           —          VALIDATE     —
Step 10: Gate          READ/WRITE  SERVE       WRITE+POLL   —           —          (cached)
Step 11: Handoff       READ/WRITE  SERVE       ORCHESTRATE  SEND       CALL-OUT     —

WRITE = DB mutation    READ = DB select    SERVE = page/API response
CALL = service invocation   SEARCH = external API call   VALIDATE = pre-flight check
CACHE = cache read/write    SEND = bot message sent      CALL-OUT = outbound call initiated
ORCHESTRATE = multi-service coordination
```

---

## NEW REQUIREMENTS MATRIX (NR-1 through NR-5)

| NR ID | Description | Steps | Spec 213 touch | Spec 214 touch |
|-------|-------------|-------|----------------|----------------|
| NR-1 | Wizard state persistence — `wizard_step` written at each advance, resume on return | 3–11 | FR-5.2 (update_onboarding_profile_key supports wizard_step key) | Portal reads wizard_step from profile response and routes to correct step |
| NR-2 | Nikita-voiced copy — no generic SaaS language | 1, 2, 3, 4, 5, 6, 7, 9, 10, 11 | FR-6 (FirstMessageGenerator copy maintained in Nikita voice) | All UI copy strings reviewed against voice/tone guide |
| NR-3 | Pre-flight country validation before phone collection | 9 | None (client-side only; ElevenLabs supported regions list static) | SceneSelector-style component for country gate; fallback to PATH B |
| NR-4 | QR code mandatory at handoff for desktop sessions | 11 | None (frontend-only) | UA detection + QR generation at handoff screen; t.me deep link with deferred token |
| NR-5 | Re-onboarding detection for existing voice users | 3, 11 | FR-11 (re-onboarding idempotency — `_bootstrap_pipeline` no-op if pipeline_state=="ready") | Server component at step 3 reads onboarding_status + platform_voice; redirects to dashboard |

---

## EMOTIONAL ARC SUMMARY

```
STEP     EMOTION                    KEY MECHANISM
─────    ───────────────────────    ────────────────────────────────────────────
 1       Intrigue                   "who is this? what does she know?" — sparse copy + single CTA
 2       Curiosity                  "an email in her voice?" — Nikita-voiced email subject/body
 3       Respect                    "she has a file on me?" — classified dossier header, REAL scores
 4       Investigation              "she's researching me as I type" — inline venue preview
 5       Authorship                 "I'm correcting her file" — pre-filled guess to override
 6       Authorship                 "I'm defining my darkness level" — live quote feedback from slider
 7       Authorship                 "I'm completing her file on me" — optional fields feel like confession
 8       Sunk-cost peak             "this is MY story now" — user picks backstory scenario, stamp fires
 9       Desire                     "I want the call — not compliance" — binary intent choice, not form
10       Anticipation               "clearance pending → approved" — stamp animation resolves
11       Arrival                    "she's waiting for me" — ring animation (voice) / "go find her" (text)
```

---

## FRICTION / DELIGHT MARKERS SUMMARY

```
FIXED SMELLS (⚠ resolved in target):
    C1 [Step 10]  Pipeline gate now exists — CLEARANCE: PENDING → CLEARED before handoff
    C2 [Step 9]   Voice vs text paths are visually distinct from step 9 forward
    C3 [Step 11]  Voice path shows ring animation + "Nikita is calling you now" — no surprise
    H1 [Step 3]   Real 50/50/50/50 scores, not hardcoded 75/100 demo
    H2 [Step 8]   Backstory generated for ALL portal users, shown before phone ask
    H3 [Step 4]   Venue research fires inline as user types city
    N1 [Step 2]   Auth email now Nikita-voiced (subject + body)
    N4 [Step 3]   Scores shown at dossier header (step 3), not before context exists
    N9 [Steps 8,9] Backstory before phone ask — sunk cost precedes commitment request
    N10 [Step 11] QR code mandatory on desktop, never optional

DELIGHT MOMENTS (✨ intentional wow):
    Step 1   Sparse landing — one sentence, one button — unexpected restraint
    Step 3   Classified file aesthetic full-width — makes the premise real
    Step 4   Venue chips appear as user types city — confirms she's paying attention
    Step 8   Three scenario cards animate in, user picks one, "CONFIRMED" stamp fires
    Step 10  "CLEARANCE: PENDING" → flicker → flash → "CLEARED" stamp animation
    Step 11  Ring animation (voice path) — phone rings, she called first

RECOVERY PATHS (🔄 no dead-ends):
    Step 2   Magic link expired → inline retry, stays in dossier aesthetic
    Step 4   Venue research timeout → graceful no-preview, resumes at step 10
    Step 8   Backstory degraded → "ANALYSIS: PENDING" stamp, skips to step 9
    Step 9   Unsupported phone region → auto-falls back to Telegram path [NR-3]
    Step 10  Pipeline timeout (20s cap) → "PROVISIONAL — CLEARED", proceed anyway
    Step 11  Voice agent down → ring UI replaced with Telegram deeplink + QR
    Step 11  No telegram_id (portal-first) → explicit /start instruction + deferred handoff
    All      Abandonment → wizard_step persisted → resume from last step on return [NR-1]
```

---

*Diagram version: 1.0*
*Approach: B (Dossier Form) — selected 2-1 by approach-evaluator*
*Implements: Spec 213 (all FRs), Spec 214 (portal wizard — TBD), NR-1 through NR-5*
*Next action: `/plan 213` to author plan.md, then `/sdd quick 214` for portal wizard spec*
