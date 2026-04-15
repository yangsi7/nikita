# Feature Specification: Portal Onboarding Wizard (Spec 214)

**Spec ID**: 214-portal-onboarding-wizard
**Status**: Draft
**Predecessor**: Spec 213 (onboarding backend foundation, COMPLETE)
**Supersedes**: Spec 081 (OnboardingCinematic progressive discovery)
**Date**: 2026-04-15
**Author**: System agent (from brief `.claude/plans/onboarding-overhaul-brief.md`)

---

## Overview

### Problem Statement

The current portal onboarding (`portal/src/app/onboarding/onboarding-cinematic.tsx`) has four structural deficiencies that combine into a "5 → 1 experience" rating:

1. **Aesthetic downgrade**: 5-section vertical scroll-snap form looks like generic SaaS compared to the landing page's classified dossier aesthetic (`text-[clamp(3rem,7vw,6rem)] font-black tracking-tighter`, void-ambient, aurora-orbs, glass cards). Users arrive from the atmospheric landing page and hit a sterile form.
2. **Missing data fields**: `name`, `age`, and `occupation` are never collected in the portal flow. Backstory generator and first-message personalization degrade to darkness-level-only flavor. `life_stage` and `interest` exist in `schemas.ts` but the UI does not collect them.
3. **No backstory reveal**: `BackstoryGeneratorService` (Spec 213) now generates 3 scenarios for every portal user, but the current wizard never shows them. Users skip the emotional "sunk-cost" moment that drives Telegram conversion.
4. **No pipeline gate**: The current flow fires `POST /onboarding/profile` and immediately redirects to Telegram — before `_bootstrap_pipeline` has run. Users land in Telegram to a generic first message because conversation seeding hasn't completed.
5. **No voice/text distinction**: Both paths show identical "Opening Telegram..." UI even when user provided a phone number for a voice call.
6. **No wizard-state persistence**: Abandoning mid-wizard on mobile (tab-switch, network loss) restarts from step 1.

### Proposed Solution — "The Dossier Form"

A one-at-a-time wizard where Nikita is building a classified file on the user. Power dynamic: she is evaluating them. Each field is a dossier entry. 11 steps (2 pre-wizard auth + 9 wizard screens). Selected 2-1 over "The Drop" (chat-style) and "The Audition" (full-screen video) by the approach-evaluator expert panel.

**Reorder principle**: Backstory reveal (step 8) is the emotional climax and MUST precede the phone ask (step 9). Sequence: investigation → identity → backstory peak → commitment ask → clearance gate → handoff.

The wizard:
- Matches the landing page aesthetic verbatim (same components, same tokens)
- Collects all 7 profile fields across 6 data-collection steps (steps 4-9)
- Calls `POST /onboarding/preview-backstory` at step 8 before final submit
- Polls `GET /pipeline-ready/{user_id}` at step 10 using `PIPELINE_GATE_POLL_INTERVAL_S=2.0` / `PIPELINE_GATE_MAX_WAIT_S=20.0`
- Persists wizard state to `localStorage` (keyed by user_id) and writes `wizard_step` to `OnboardingV2ProfileRequest` via `PATCH /onboarding/profile` at each step transition

### Success Criteria

- **Completion rate**: ≥70% of authenticated users who reach step 3 reach step 11 (baseline: unmeasured, estimated <30% from anecdotal drop-off at profile section)
- **Time-to-first-message**: median ≤90s from step 10 POST until Telegram first message delivered
- **Backstory seed rate**: ≥60% of completed onboardings have a `chosen_option` populated in `users.onboarding_profile`
- **Pipeline gate timeout rate**: ≤5% of completions reach the 20s hard cap (degraded path)
- **Zero sterile SaaS copy**: every wizard screen passes Nikita-voice review (no "Submit", no "Processing...", no "Sign Up")

---

## Functional Requirements

### FR-1 — 11-Step Wizard Flow (P1)

**Description**: Replace `OnboardingCinematic` with a one-at-a-time step wizard. Steps advance via explicit CTA click (no scroll-snap). Navigation is forward-only during the wizard; back navigation via browser history is disallowed (replace history state on each step advance).

**Step enumeration**:

| Step | Name | Content | Progression trigger |
|------|------|---------|---------------------|
| 1 | Landing (Dossier Entry) | Hero: "Nikita has been watching." / CTA: "Show her." | CTA click |
| 2 | Auth (Magic Link) | Email input, Nikita-voiced auth form at `/onboarding/auth` | Magic link email sent |
| 3 | Dossier Header | Classified-file header, real 50/50/50/50 scores, "Prove me wrong." | CTA: "Continue." |
| 4 | Location | City text input, async venue preview below on blur (800ms debounce) | CTA: "That's accurate." |
| 5 | Scene | Pre-filled "Suspected: techno?", SceneSelector button grid | Scene button selection |
| 6 | Darkness | EdginessSlider 1-5 with live Nikita quote updates | CTA: "Confirmed." |
| 7 | Identity (Name / Age / Occupation) | Three optional dossier fields, each with Nikita label/copy | CTA: "File updated." |
| 8 | Backstory Reveal | `POST /onboarding/preview-backstory` → 3 scenario cards → user picks one | CTA: "That's how it happened." |
| 9 | Phone Ask | Binary: [Give her your number] / [Start in Telegram]; tel input expands on voice choice | CTA: "Call me." / auto-advance |
| 10 | Pipeline Ready Gate | `POST /onboarding/profile` → poll `/pipeline-ready` → dossier stamp PENDING→CLEARED | Auto-advance after stamp |
| 11 | Handoff | Voice ring UI or Telegram deeplink + QR; "Application... accepted. Barely." | End of wizard |

Steps 1-2 are pre-wizard (handled by existing landing page + `/onboarding/auth` route). The wizard component (`onboarding-wizard.tsx`) manages steps 3-11.

**Acceptance Criteria**:
- AC-1.1: Each step renders in isolation; no other step's form fields are mounted simultaneously
- AC-1.2: CTA button is disabled until the step's required fields pass client-side validation (zod)
- AC-1.3: Browser back button on any wizard step does NOT navigate to the previous step; `history.replaceState` is used on each advance
- AC-1.4: Step 3 (dossier header) shows real `UserMetrics` fetched server-side OR 50/50/50/50 defaults — never hardcoded 75/100
- AC-1.5: `data-testid="wizard-step-{N}"` attribute present on each step's root element for Playwright targeting

---

### FR-2 — Dossier Metaphor Styling (P1)

**Description**: The wizard inherits the landing-page aesthetic verbatim. No new design system tokens are introduced; all tokens come from the existing Tailwind theme and reusable components.

**Styling contract**:
- Typography: `text-[clamp(3rem,7vw,6rem)] font-black tracking-tighter leading-none` for step headlines (mirrors `portal/src/components/landing/hero-section.tsx:44`)
- Background: `bg-void` + `bg-void-ambient` for inner content areas
- Atmosphere: `<FallingPattern />` + `<AuroraOrbs />` from `portal/src/components/landing/` — imported unchanged, not re-implemented
- Glass cards: `<GlassCard variant="default|elevated">` from `portal/src/components/glass/glass-card.tsx` for dossier field containers
- Primary color: `oklch(0.75 0.15 350)` (rose primary) — existing `text-primary`, `border-primary`, `bg-primary` tokens
- Dossier stamping: `text-primary font-black tracking-widest uppercase` for all stamp text (CLEARANCE, ANALYZED, CONFIRMED)
- Progress indicator: `text-xs tracking-[0.2em] uppercase text-muted-foreground` for "FIELD N OF 7" labels
- Buttons: `<GlowButton>` from `portal/src/components/landing/glow-button.tsx` for primary CTAs
- Framer-motion: existing `EASE_OUT_QUART = [0.16, 1, 0.3, 1]` easing on all step transitions (slide-up + fade-in)
- Font tokens `font-black`, `tracking-tighter`, `tracking-[0.2em]`: already in `portal/tailwind.config.ts` — use as-is

**Acceptance Criteria**:
- AC-2.1: Visual regression screenshot of step 3 (dossier header) shows classified-file aesthetic with 4 metric bars
- AC-2.2: `AuroraOrbs` and `FallingPattern` render on all 11 steps without CSS conflicts
- AC-2.3: No inline styles anywhere in wizard components — all styling via Tailwind utility classes
- AC-2.4: `GlassCard` component is imported from `portal/src/components/glass/glass-card.tsx`, not re-implemented

---

### FR-3 — Nikita-Voiced Copy on Every Screen (P1)

**Description**: All visible user-facing text in the wizard is written in Nikita's first-person voice. Zero sterile SaaS language. Per `.claude/rules/review-findings.md` few-shot echo rule: when setting canonical phrases, grep `nikita/agents/text/persona.py`, `nikita/engine/chapters/prompts.py`, and `portal/src/app/onboarding/` for mirrored phrasing.

**Canonical phrase reference** (from brief — implementation must match):

| SaaS phrase (forbidden) | Nikita-voiced replacement |
|------------------------|--------------------------|
| "Get Started" / "Sign Up" | "Show her." |
| "City" (field label) | "Location: [REDACTED]" |
| "Darkness level" (slider label) | "How far can I push you?" |
| "Processing..." | "CLEARANCE: PENDING" |
| "Profile saved successfully" | "Application... accepted. Barely." |
| "Send Magic Link" | "Send it." |
| "Check your inbox" | "Check your email. She's waiting." |
| "Error" toast | Nikita-voiced in-character message |

**Acceptance Criteria**:
- AC-3.1: No wizard component renders any of the forbidden SaaS phrases; enforced by text content assertions in Jest tests
- AC-3.2: All button labels, field labels, and placeholder text appear in the Nikita copy reference table in this spec or in `docs/content/wizard-copy.md` (created during implementation)
- AC-3.3: Error messages at all steps use Nikita voice (e.g., "That number doesn't work. Try again." not "Invalid phone number")

---

### FR-4 — Backstory Preview Endpoint Consumption (P1)

**Description**: At step 8, the portal calls `POST /api/v1/onboarding/preview-backstory` using `BackstoryPreviewRequest` (from `nikita/onboarding/contracts.py`). The response is `BackstoryPreviewResponse` containing `scenarios: list[BackstoryOption]`.

**Request construction** (step 8 fires with all fields collected through step 7):
```typescript
// BackstoryPreviewRequest mirrors contracts.py:BackstoryPreviewRequest
const previewReq = {
  city: formState.location_city,
  social_scene: formState.social_scene,
  darkness_level: formState.drug_tolerance,  // alias: drug_tolerance → darkness_level
  life_stage: formState.life_stage ?? null,
  interest: formState.interest ?? null,
  age: formState.age ?? null,
  occupation: formState.occupation ?? null,
}
// POST /api/v1/onboarding/preview-backstory
```

**BackstoryChooser UI**:
- Shows 3 `BackstoryOption` cards (id, venue, context, the_moment, unresolved_hook, tone)
- Each card shows: `SCENARIO A/B/C` header, `[tone badge]`, venue name, context (2-3 sentences), the_moment, unresolved_hook
- Selection: radio-style (one active at a time), selected card stamps "CONFIRMED" in `text-primary font-black`
- Degraded path: `BackstoryPreviewResponse.degraded === true` OR `scenarios.length === 0` → skip card display, show "ANALYSIS: PENDING" stamp, CTA: "Understood."

**Acceptance Criteria**:
- AC-4.1: `POST /onboarding/preview-backstory` is called exactly once on step 8 mount (not on every re-render); loading state shows dossier animation
- AC-4.2: All 3 scenario cards render with correct `BackstoryOption` fields; clicking a card sets it as selected with "CONFIRMED" stamp
- AC-4.3: Degraded path (empty scenarios or `degraded: true`) renders "ANALYSIS: PENDING" without error state and advances to step 9 on CTA click
- AC-4.4: Rate limit (HTTP 429 from `PREVIEW_RATE_LIMIT_PER_MIN=5`) displays Nikita-voiced retry message, not a generic error

---

### FR-5 — Pipeline Ready Poll Loop (P1)

**Description**: At step 10, after `POST /onboarding/profile` returns `OnboardingV2ProfileResponse`, the portal begins polling `GET /api/v1/onboarding/pipeline-ready/{user_id}` using `PipelineReadyResponse` (from `nikita/onboarding/contracts.py`). Poll interval and max wait come from `OnboardingV2ProfileResponse.poll_interval_seconds` and `.poll_max_wait_seconds` (which mirror `PIPELINE_GATE_POLL_INTERVAL_S=2.0` and `PIPELINE_GATE_MAX_WAIT_S=20.0` from `nikita/onboarding/tuning.py`).

**Poll state machine**:

| Time | State | UI |
|------|-------|-----|
| t=0 | POST sent | Stamp: "CLEARANCE: PENDING" (pulsing) |
| t=0–15s | Polling, state="pending" | Stamp pulsing, sub-copy: "Your file is being processed." |
| t=15–20s | Polling, state="pending" | Sub-copy: "Almost there..." |
| t=poll returns "ready" | Ready | Stamp animates to "CLEARED" → auto-advance after 1.5s |
| t=poll returns "degraded" | Degraded | Stamp: "PROVISIONAL — CLEARED" → Nikita toast → auto-advance 1.5s |
| t=20s hard cap | Timeout | Stamp: "PROVISIONAL — CLEARED" → auto-advance |

**Implementation**: custom hook `useOnboardingPipelineReady` in `portal/src/app/onboarding/hooks/use-pipeline-ready.ts`.

```typescript
// Hook interface
function useOnboardingPipelineReady(params: {
  userId: string
  enabled: boolean
  pollIntervalMs: number
  maxWaitMs: number
}): {
  state: PipelineReadyState | null
  venueResearchStatus: string
  backstoryAvailable: boolean
  timedOut: boolean
}
```

**Acceptance Criteria**:
- AC-5.1: Poll fires at exactly `poll_interval_seconds * 1000` ms intervals using `setInterval` (not recursive `setTimeout`)
- AC-5.2: Poll stops immediately when `state === "ready"` or `state === "failed"` is received
- AC-5.3: Hard cap at `poll_max_wait_seconds * 1000` ms; portal advances regardless of poll state
- AC-5.4: `data-testid="pipeline-gate-stamp"` with `data-state="{ready|degraded|pending|timeout}"` attribute; Playwright waits for this selector, NOT `networkidle`
- AC-5.5: `venue_research_status` from `PipelineReadyResponse` is exposed for step 4 inline preview update (if step 4 is still visible in wizard state history)

---

### FR-6 — PATCH Profile for Mid-Wizard Updates (P1)

**Description**: At each step transition (steps 4-9), the wizard writes the newly-collected field(s) to the backend via `PATCH /api/v1/onboarding/profile` with partial `OnboardingV2ProfileRequest` payload including `wizard_step` (for NR-1 server-side persistence). The PATCH is fire-and-forget (errors logged but do not block step advance). `wizard_step` is always included so the backend can resume detection work.

**Per-step PATCH payload**:

| Step | Fields in PATCH |
|------|----------------|
| 4 | `{location_city, wizard_step: 4}` |
| 5 | `{social_scene, wizard_step: 5}` |
| 6 | `{drug_tolerance, wizard_step: 6}` |
| 7 | `{name, age, occupation, wizard_step: 7}` |
| 9 | `{phone, wizard_step: 9}` |

**Acceptance Criteria**:
- AC-6.1: PATCH is called on each step advance; failure does not block the wizard (error logged to console, toast shown only if 3 consecutive PATCHes fail)
- AC-6.2: `wizard_step` field is always included in every PATCH payload
- AC-6.3: PATCH uses existing `apiClient` from `portal/src/lib/api/client.ts` with `method: "PATCH"`

---

### FR-7 — Initial Profile Submit via POST /onboarding/profile (P1)

**Description**: At step 10, the wizard sends the full `OnboardingV2ProfileRequest` payload via `POST /api/v1/onboarding/profile` (the Spec 213 endpoint, not the legacy PortalProfileRequest). This is the final commit that triggers `_trigger_portal_handoff` as a background task.

**Full payload**: all 9 fields + `wizard_step: 10` + `cache_key` (not echoed — backend recomputes from profile fields):
```typescript
const fullPayload: OnboardingV2ProfileRequest = {
  location_city: formState.location_city,
  social_scene: formState.social_scene,
  drug_tolerance: formState.drug_tolerance,
  life_stage: formState.life_stage ?? null,
  interest: formState.interest ?? null,
  phone: formState.phone || null,
  name: formState.name ?? null,
  age: formState.age ?? null,
  occupation: formState.occupation ?? null,
  wizard_step: 10,
}
```

**Response handling**: `OnboardingV2ProfileResponse` → extract `poll_endpoint`, `poll_interval_seconds`, `poll_max_wait_seconds`, `user_id` → begin poll loop (FR-5).

**Acceptance Criteria**:
- AC-7.1: POST is called exactly once at step 10 entry; never retried automatically (user may retry via CTA if POST returns 4xx)
- AC-7.2: On HTTP 409 (duplicate phone): rewind to step 9, show inline phone field error in Nikita voice
- AC-7.3: On HTTP 422 (validation): log error, show "Something broke on our end." toast, do NOT advance to step 11
- AC-7.4: Response `backstory_options` is ignored at step 10 (already displayed at step 8)

---

### FR-8 — Backstory Before Phone (Step Order Enforcement) (P1)

**Description**: The step ordering (backstory at step 8, phone at step 9) is fixed and non-configurable. This ordering is the architectural decision that maximizes sunk-cost investment before the commitment ask. Any change to this order requires an ADR update.

**Acceptance Criteria**:
- AC-8.1: `WizardStateMachine` enforces `BACKSTORY_REVEAL` (8) always precedes `PHONE_ASK` (9) — enforced by state transition guard that throws on invalid order
- AC-8.2: Wizard cannot advance from step 7 to step 9 directly — step 8 is mandatory even in degraded-backstory path

---

### FR-9 — BackstoryChooser Selection UI (P1)

**Description**: The backstory chooser is a radio-style card grid. Only one card can be active at a time. Cards render `BackstoryOption` fields from `nikita/onboarding/contracts.py`:

- `id` (used as value, not displayed)
- `tone` (displayed as badge: "romantic" / "intellectual" / "chaotic")
- `venue` (displayed as "WHERE: {venue}")
- `context` (displayed as 2-3 sentence paragraph)
- `the_moment` (displayed as "THE MOMENT: {the_moment}")
- `unresolved_hook` (displayed as "WHAT SHE REMEMBERS: {unresolved_hook}")

After selection, `chosen_option_id` is persisted via `POST /api/v1/onboarding/backstory-choice` (Spec 213 FR-3a new endpoint). Response: `OnboardingV2ProfileResponse` with `chosen_option` populated.

**Acceptance Criteria**:
- AC-9.1: Selecting a card marks it with "CONFIRMED" stamp; deselects all others visually
- AC-9.2: `POST /onboarding/backstory-choice` fires on CTA click, not on card selection; loading state shown while request in-flight
- AC-9.3: Each `BackstoryOption` tone renders as a distinct badge color: romantic=rose, intellectual=blue, chaotic=amber
- AC-9.4: Cards are accessible via keyboard (tab/enter/space); aria-selected on active card

---

### NR-1 — Wizard State Persistence (P1)

**Description**: Partial profile + current step persist in two locations:
1. `localStorage` keyed by `nikita_wizard_{user_id}` (client-side, immediate)
2. `users.onboarding_profile.wizard_step` JSONB via PATCH (server-side, async)

On return visit (same browser, same user), the wizard reads `localStorage` and resumes from `last_completed_step + 1`. If `localStorage` is absent but `onboarding_profile.wizard_step` JSONB key exists (cross-device resume), the landing page `/onboarding?resume=true` redirects to step `wizard_step + 1`.

**localStorage schema**:
```typescript
type WizardPersistedState = {
  user_id: string
  last_step: number                     // last completed step (3-10)
  location_city: string | null
  social_scene: string | null
  drug_tolerance: number | null
  name: string | null
  age: number | null
  occupation: string | null
  phone: string | null
  chosen_option_id: string | null
  saved_at: string                      // ISO-8601
}
```

Security note: `wizard_step` JSONB payload is internal state only; never rendered directly to DOM (XSS risk).

**Acceptance Criteria**:
- AC-NR1.1: After completing step 6 and closing the browser tab, reopening `/onboarding` resumes at step 7 with previously-entered `location_city`, `social_scene`, and `drug_tolerance` pre-filled
- AC-NR1.2: `localStorage.setItem('nikita_wizard_{user_id}', ...)` is called on every step advance
- AC-NR1.3: On wizard completion (step 11), `localStorage.removeItem('nikita_wizard_{user_id}')` is called to prevent stale resume
- AC-NR1.4: Wizard state from a different `user_id` in localStorage is ignored; key is user-scoped

---

### NR-2 — Age and Occupation Explicitly Collected (P1)

**Description**: `age` (number, 18-99, optional) and `occupation` (text, max 100 chars, optional) are collected at step 7 alongside `name`. These fields were missing from the old portal flow. They feed `BackstoryGeneratorService` via `BackstoryPreviewRequest.age` and `.occupation`.

**Acceptance Criteria**:
- AC-NR2.1: Step 7 renders three distinct input fields: name (text), age (number, `min=18 max=99`), occupation (text, `maxLength=100`)
- AC-NR2.2: All three fields are optional; skipping shows "[REDACTED]" / "[CLASSIFIED]" / "[UNVERIFIED]" labels in the dossier header at step 8
- AC-NR2.3: `BackstoryPreviewRequest` sent at step 8 includes `age` and `occupation` values (or `null` if not provided)

---

### NR-3 — Phone Country Pre-flight Validation (P1)

**Description**: At step 9, before the tel input accepts submission, client-side country validation runs against the ElevenLabs/Twilio supported-regions list. If the user's dialed country code is not supported, the tel input hides, "Start in Telegram" is auto-selected, and an inline Nikita-voiced message explains.

**Implementation**: `libphonenumber-js` (already a common Next.js dependency) or equivalent. Supported country codes list maintained in `portal/src/app/onboarding/constants/supported-phone-countries.ts`.

**Acceptance Criteria**:
- AC-NR3.1: Entering a phone number with a country code not in the supported list triggers inline message: "I can't reach you there. Let's use Telegram." and auto-selects Telegram path — without requiring form submission
- AC-NR3.2: Valid E.164 format check (matching `E164_PHONE_REGEX` from `portal/src/app/onboarding/schemas.ts`) runs before country-support check
- AC-NR3.3: `data-testid="phone-country-error"` is visible when unsupported country is detected (for Playwright)
- AC-NR3.4: Country validation is purely client-side; does NOT make a network call

---

### NR-4 — QRHandoff Component for Desktop→Mobile (P1)

**Description**: At step 11, if the user is on a desktop viewport (width ≥ 768px, detected via `useMediaQuery` or server-side user-agent hint), a QR code is displayed alongside the primary CTA. The QR encodes the Telegram deep link `https://t.me/Nikita_my_bot`. No backend dependency.

**Implementation**: `qrcode.react` package (add to `portal/package.json`).

```typescript
// portal/src/components/onboarding/QRHandoff.tsx
interface QRHandoffProps {
  telegramUrl: string     // "https://t.me/Nikita_my_bot"
  label?: string          // "On desktop? Scan to open on your phone."
}
```

**Acceptance Criteria**:
- AC-NR4.1: QR code renders on step 11 when viewport width ≥ 768px; hidden on mobile viewports
- AC-NR4.2: QR code is surrounded by Nikita copy: "On desktop? Scan to open on your phone."
- AC-NR4.3: `QRHandoff` has no server-side dependencies; renders entirely client-side
- AC-NR4.4: QR code is accessible: `aria-label="QR code to open Telegram on mobile"` on the canvas/svg element

---

### NR-5 — Voice Fallback Polling UI (P1)

**Description**: If the user provided a phone number (voice path), step 11 shows a ring animation ("Nikita is calling you now.") and polls the handoff result. If the voice agent is unavailable at call time, the ring animation is replaced by a Telegram deeplink + full-size QR.

**Poll behavior**:
- Portal polls `GET /api/v1/onboarding/pipeline-ready/{user_id}` checking for `state === "degraded"` or `failed`
- On degraded/failed: replace ring with Telegram CTA + QR
- Max poll duration: 30s; after 30s voice path is considered connected and polling stops
- Copy for voice fallback: "My voice is occupied right now. Find me in Telegram — I'll explain." (in-character, no technical language)

**Acceptance Criteria**:
- AC-NR5.1: Step 11 voice path shows pulsing ring animation and "Nikita is calling you now." copy
- AC-NR5.2: When pipeline state transitions to `degraded` or `failed`, ring animation hides and Telegram CTA + QR code display
- AC-NR5.3: Telegram deeplink CTA ("Open Telegram") is always visible on step 11 voice path as secondary option below the ring
- AC-NR5.4: `data-testid="voice-ring-animation"` and `data-testid="voice-fallback-telegram"` for Playwright targeting

---

### Pre-Spec-214 Standalone Fixes (Portal-Side Only)

The following fixes are portal-only changes that can ship independently as small PRs before Spec 214 lands. They are listed here for completeness; their implementation is NOT gated on this spec's audit pass.

| Fix | Description | Portal file |
|-----|-------------|-------------|
| P-FIX-1: Real demo scores | Replace hardcoded 75/100 in `ScoreSection` with 50/50/50/50 and "where you start" label | `portal/src/app/onboarding/sections/score-section.tsx` |
| P-FIX-2: Voice vs Telegram overlay split | `MissionSection` currently shows "Opening Telegram..." for both paths → split into voice-countdown and Telegram-deeplink variants | `portal/src/app/onboarding/sections/mission-section.tsx` |
| P-FIX-3: 3000ms redirect + iOS fallback | Increase 1500ms Telegram redirect to 3000ms and show immediate fallback button for iOS | `portal/src/app/onboarding/sections/mission-section.tsx` |
| P-FIX-4: Nikita-voiced copy rewrite | Pure text replacement in existing sections (no logic changes) | All sections in `portal/src/app/onboarding/sections/` |

Backend-side standalone fix (NOT portal scope): Pending_handoff trigger on `/start` — backend-only, tracked separately.

---

## User Stories

### US-1 — New User on Desktop Completes Wizard (Happy Path)

**As** a new user who discovers Nikita on the landing page,  
**I want** to be guided through 11 wizard steps collecting my profile,  
**so that** I receive a personalized first message in Telegram that references my city, scene, and backstory scenario.

**Acceptance Criteria**:
- AC-US1.1: User navigates from landing page CTA ("Show her.") through all 11 wizard steps without encountering any sterile SaaS copy
- AC-US1.2: The Telegram first message delivered after step 11 references at least one of: user's city, scene, occupation, or chosen backstory venue (verified via Playwright: `waitForSelector('[data-testid="pipeline-gate-stamp"][data-state="ready"]')` then Telegram MCP message check)

---

### US-2 — Desktop User Hands Off to Mobile via QR Code

**As** a desktop user who has completed the wizard,  
**I want** to scan a QR code at step 11 to open Telegram on my phone,  
**so that** I can start the conversation on my preferred mobile device without copying a link.

**Acceptance Criteria**:
- AC-US2.1: On step 11 with viewport width ≥ 768px, a QR code labeled "On desktop? Scan to open on your phone." is visible
- AC-US2.2: The QR code decodes to `https://t.me/Nikita_my_bot` (verified via Playwright `evaluate` on the QR canvas)

---

### US-3 — User Abandons Mid-Wizard and Resumes

**As** a user who closes the browser tab at step 6,  
**I want** to resume from step 7 on next visit with my previously-entered data intact,  
**so that** I don't have to re-enter my city, scene, and darkness level.

**Acceptance Criteria**:
- AC-US3.1: `localStorage` key `nikita_wizard_{user_id}` is written on each step advance with all collected fields
- AC-US3.2: On return visit (authenticated), `/onboarding` detects `localStorage` state and renders the wizard at `last_step + 1` with prior field values pre-populated
- AC-US3.3: Pre-populated values match what was entered in the prior session (no corruption or truncation)

---

### US-4 — User Enters Unsupported Phone Country

**As** a user who enters a phone number from a country not supported by ElevenLabs,  
**I want** to receive an immediate inline explanation and automatic fallback to Telegram,  
**so that** I'm not left at a dead-end phone input with no path forward.

**Acceptance Criteria**:
- AC-US4.1: Entering a phone number with an unsupported country code (e.g., +86 China) shows `data-testid="phone-country-error"` with Nikita-voiced copy within 200ms of input blur
- AC-US4.2: The Telegram path is auto-selected and the tel input hides; wizard can advance to step 10

---

### US-5 — Voice Path Chosen but ElevenLabs Agent Unavailable

**As** a user who provided a phone number,  
**I want** to see the voice-fallback UI with Telegram alternative if the call fails,  
**so that** I'm not stuck on a ringing animation with no path to Nikita.

**Acceptance Criteria**:
- AC-US5.1: When `PipelineReadyResponse.state === "degraded"` or `"failed"` on the voice path, the ring animation at step 11 hides and `data-testid="voice-fallback-telegram"` becomes visible
- AC-US5.2: Fallback copy is Nikita-voiced: "My voice is occupied right now. Find me in Telegram — I'll explain." (no error codes or technical language)

---

### US-6 — User Selects Backstory and Receives Personalized First Message

**As** a user who selected a backstory scenario at step 8,  
**I want** the first message I receive in Telegram to reference the scenario I chose,  
**so that** the "our story" framing feels real from the first interaction.

**Acceptance Criteria**:
- AC-US6.1: `POST /onboarding/backstory-choice` is called with the `chosen_option.id` before advancing to step 9
- AC-US6.2: E2E Playwright test: after completing wizard with scenario selection, verify Telegram first message contains `chosen_option.venue` or `chosen_option.unresolved_hook` substring (via Telegram MCP)

---

## Non-Functional Requirements

### NFR-001 — Performance (P1)

- Wizard step transition: ≤200ms from CTA click to next step render (measured by Playwright `performance.now()` delta across `waitForSelector`)
- `POST /onboarding/preview-backstory` UX: step 8 loading animation shown immediately; expected backend latency 1-3s (p95); max wait before degraded path: 4s frontend timeout
- `GET /pipeline-ready` individual request: ≤200ms p99 server response (tracked by Cloud Run metrics; not portal-enforced)
- API calls use exponential backoff retry: 3 attempts, delays 500ms / 1000ms / 2000ms; non-idempotent (POST) calls are NOT retried automatically
- Portal page JS bundle: no new page-level bundle size increase >50KB gzipped from the wizard refactor (measured by `next build` output)

### NFR-002 — Accessibility (P1)

- WCAG 2.2 AA on all wizard steps
- Keyboard navigation: all interactive elements reachable via Tab; CTA activatable via Enter/Space
- Focus management: on step advance, focus moves to the new step's first interactive element (`autoFocus` or `useEffect` + `ref.focus()`)
- Screen reader: `aria-live="polite"` on pipeline gate stamp element; `role="status"` on loading states
- Dossier stamp animations: respect `prefers-reduced-motion` (remove transition, show final state immediately)
- Color contrast: all text on glass-card backgrounds meets 4.5:1 ratio (rose primary on void-ambient background)
- `aria-invalid` on fields with validation errors; `aria-describedby` linking to error messages

### NFR-003 — Responsive Design (P1)

- Mobile-first implementation; tested at breakpoints: 375px (mobile), 768px (tablet), 1280px (desktop), 1920px (wide)
- QRHandoff component hidden below 768px (CSS `md:hidden` / media query)
- All step content scrollable on 375px height without horizontal overflow
- Touch targets ≥ 44px height on all interactive elements
- Ring animation at step 11: scales correctly at all viewport widths without overflow

### NFR-004 — Dark Mode Default (P2)

- Wizard uses `bg-void` / `bg-void-ambient` (existing dark tokens); no light-mode variant
- All glass-card variants are dark by design (`portal/src/components/glass/glass-card.tsx`)
- No `dark:` Tailwind variants introduced; design is dark-only

### NFR-005 — Test Coverage (P1)

- Wizard state machine (`WizardStateMachine`): ≥85% branch coverage measured by Jest `--coverage`
- Individual step components: ≥70% line coverage
- `useOnboardingPipelineReady` hook: ≥80% branch coverage (all poll state transitions tested)
- Playwright E2E: happy path (US-1), abandonment + resume (US-3), unsupported country (US-4) — 3 mandatory E2E scenarios

### NFR-006 — TypeScript Strict Mode (P1)

- `tsc --noEmit` must pass with zero errors before any PR is opened (enforced via `prebuild` in `portal/package.json`)
- All contract types consumed from `nikita/onboarding/contracts.py` must be mirrored as TypeScript interfaces in `portal/src/app/onboarding/types/contracts.ts` — NOT re-declared per-component

---

## Constraints and Assumptions

### Tech Stack (Fixed)

- **Framework**: Next.js 16 with App Router, React 19, TypeScript strict
- **UI**: shadcn/ui components (from `portal/components.json`) + Tailwind CSS — no inline styles
- **Forms**: `react-hook-form` + `zod` resolver (already in use in `onboarding-cinematic.tsx`)
- **Animations**: `framer-motion` (already installed, used in `hero-section.tsx`)
- **API client**: existing `apiClient` from `portal/src/lib/api/client.ts` — not replaced
- **Auth**: Supabase JWT (already in place; `portal/src/lib/supabase/server.ts`)
- **QR**: `qrcode.react` (new dependency — add to `portal/package.json`)
- **Phone validation**: `libphonenumber-js` (new dependency — add to `portal/package.json`)

### Backend Contracts (Frozen)

The following types from `nikita/onboarding/contracts.py` are consumed read-only by Spec 214. No Spec 214 PR may modify these types:
- `OnboardingV2ProfileRequest` — final submit payload (FR-7)
- `OnboardingV2ProfileResponse` — POST response (FR-5 poll setup)
- `BackstoryOption` — card display fields (FR-9)
- `BackstoryPreviewRequest` / `BackstoryPreviewResponse` — step 8 preview (FR-4)
- `PipelineReadyResponse` — poll response (FR-5)
- `PipelineReadyState` = Literal["pending", "ready", "degraded", "failed"]

Any change to these types requires a Spec 213 amendment ADR before Spec 214 implementation proceeds.

### Tuning Constants (Consumed, Not Owned)

Spec 214 reads but does NOT define these constants (owned by `nikita/onboarding/tuning.py`):
- `PIPELINE_GATE_POLL_INTERVAL_S = 2.0` — poll interval in seconds
- `PIPELINE_GATE_MAX_WAIT_S = 20.0` — hard cap in seconds
- `BACKSTORY_HOOK_PROBABILITY = 0.50` — backend-controlled, portal does NOT gate on this
- `PREVIEW_RATE_LIMIT_PER_MIN = 5` — portal handles 429 but does not enforce the limit

Portal mirrors these values via `OnboardingV2ProfileResponse.poll_interval_seconds` and `.poll_max_wait_seconds` (not hardcoded).

### Assumptions

1. Spec 213 is fully merged to master before Spec 214's `/audit` gate runs. Spec 214 may begin `/feature` and `/plan` phases in parallel with Spec 213 implementation.
2. `POST /api/v1/onboarding/backstory-choice` endpoint (Spec 213 FR-3a new) exists and returns `OnboardingV2ProfileResponse` with `chosen_option` populated.
3. `PATCH /api/v1/onboarding/profile` endpoint accepts partial `OnboardingV2ProfileRequest` fields.
4. Supabase custom email template for magic link is already configured or configurable without Spec 214 code changes (N1 fix — portal does not control the email template directly).
5. `portal/tailwind.config.ts` already contains all required theme tokens (`bg-void`, `bg-void-ambient`, `text-primary` = oklch rose). No new token additions required.

---

## Out of Scope

The following are explicitly NOT in Spec 214 scope:

1. **Backend changes**: all backend endpoints are FROZEN from Spec 213. If a backend change is needed, create a new Spec 215 or amend Spec 213.
2. **Voice prompt first_message backstory injection**: FirstMessageGenerator backstory injection is owned by Spec 213 FR-6/FR-7. Portal cannot control this.
3. **New `user_profiles` columns**: `name`, `age`, `occupation` DB columns were added in Spec 213 migration. Spec 214 does not touch the database.
4. **Custom Supabase email template**: the Nikita-voiced magic link email body is a Supabase dashboard configuration, not a portal code change.
5. **Post-onboarding voice upgrade path**: after-onboarding settings page for adding phone at `/dashboard/settings/contact` — future spec.
6. **Admin portal changes**: no admin pages affected.
7. **Standalone pre-fixes P-FIX-1 through P-FIX-4** (listed in FR-3 section): these ship as independent small PRs before Spec 214 implementation, not as part of Spec 214 PRs.

---

## Edge-Case Decisions

These decisions are recorded here to prevent re-debate during implementation. Any deviation requires updating this spec before committing code.

| Scenario | Decision |
|----------|----------|
| City research times out (step 4 inline preview) | No preview shown — field label un-redacts silently. No error toast. Venue research retries on full profile submit at step 10. Log: `portal_handoff.venue_research.timeout`. |
| Backstory service returns empty list (step 8) | Skip card display. Stamp "ANALYSIS: PENDING". CTA "Understood." advances to step 9. First message uses city/scene flavor only via existing fallback path. |
| Mobile tab-switch mid-wizard | `localStorage` written on every step advance. On remount, wizard resumes from last completed step. PATCH also writes `wizard_step` for cross-device resume. |
| Phone 409 (duplicate number) at step 10 POST | Rewind to step 9. Show inline error on phone field in Nikita voice. PATCH step 9 payload to clear `phone`. |
| Re-onboarding (existing completed user) | Detect via `users.onboarding_status === "completed"` at step 1 → show "Go back to her." CTA → redirect `/dashboard`. No wizard shown. |
| Re-onboarding (partial, wizard_step present) | Detect via `localStorage` or `?resume=true` param → resume from `wizard_step + 1`. Backfill missing `name`/`age`/`occupation` by showing step 7 again even if `wizard_step >= 7`. |
| Pipeline gate feature flag OFF | Feature flag controls gate timeout only. Gate always exists. Flag OFF = 1s optimistic pass-through (not full removal of gate). |
| Pipeline gate 20s hard cap reached | Stamp shows "PROVISIONAL — CLEARED". Auto-advances to step 11. No user-visible error. Structured log: `pipeline_gate_timeout=true, user_id` (no PII). |
| BackstoryPreviewRequest 429 rate limit | Show Nikita-voiced message: "Too eager. Wait a moment." (not "Rate limit exceeded"). Retry CTA after 12s (60s / 5 requests per minute). |
| Voice path on desktop viewport | Ring animation still shows (user may be watching on desktop while phone rings). QR shown below ring. |
| Step 2 magic link expired | Redirect to `/onboarding/auth?error=link_expired`. UI banner in Nikita voice: "That link expired. She gets impatient." CTA "Request a new link." — same form, no new page. |
| Existing voice-onboarded user visits `/onboarding` | Step 3 re-onboarding detection [NR-5]: if `onboarding_status === "completed" AND platform_voice === true` → redirect `/onboarding?state=already_cleared`. UI: "Dossier: ALREADY CLEARED." CTA: "Open Telegram." — bypass wizard. |

---

## Test File Inventory

Each test file with the Acceptance Criteria it guards.

### Unit / Component Tests (Jest + React Testing Library)

| File | ACs Guarded |
|------|-------------|
| `portal/src/app/onboarding/__tests__/WizardStateMachine.test.ts` | AC-1.1, AC-1.2, AC-1.3, AC-8.1, AC-8.2 |
| `portal/src/app/onboarding/__tests__/WizardPersistence.test.ts` | AC-NR1.1, AC-NR1.2, AC-NR1.3, AC-NR1.4 |
| `portal/src/app/onboarding/steps/__tests__/DossierHeader.test.tsx` | AC-1.4, AC-2.1 |
| `portal/src/app/onboarding/steps/__tests__/LocationStep.test.tsx` | AC-6.2, AC-NR2.3 |
| `portal/src/app/onboarding/steps/__tests__/SceneStep.test.tsx` | AC-1.2 |
| `portal/src/app/onboarding/steps/__tests__/DarknessStep.test.tsx` | AC-1.2 |
| `portal/src/app/onboarding/steps/__tests__/IdentityStep.test.tsx` | AC-NR2.1, AC-NR2.2, AC-NR2.3 |
| `portal/src/app/onboarding/steps/__tests__/BackstoryReveal.test.tsx` | AC-4.1, AC-4.2, AC-4.3, AC-4.4, AC-9.1, AC-9.2, AC-9.3, AC-9.4 |
| `portal/src/app/onboarding/steps/__tests__/PhoneStep.test.tsx` | AC-NR3.1, AC-NR3.2, AC-NR3.3, AC-NR3.4, AC-US4.1, AC-US4.2 |
| `portal/src/app/onboarding/steps/__tests__/PipelineGate.test.tsx` | AC-5.1, AC-5.2, AC-5.3, AC-5.4, AC-7.2, AC-7.3 |
| `portal/src/app/onboarding/steps/__tests__/HandoffStep.test.tsx` | AC-NR4.1, AC-NR4.2, AC-NR4.3, AC-NR4.4, AC-NR5.1, AC-NR5.2, AC-NR5.3, AC-NR5.4 |
| `portal/src/app/onboarding/hooks/__tests__/usePipelineReady.test.ts` | AC-5.1, AC-5.2, AC-5.3 |
| `portal/src/components/onboarding/__tests__/QRHandoff.test.tsx` | AC-NR4.1, AC-NR4.2, AC-NR4.3, AC-NR4.4 |
| `portal/src/app/onboarding/__tests__/WizardCopyAudit.test.tsx` | AC-3.1, AC-3.2 |
| `portal/src/app/onboarding/__tests__/WizardAPIClient.test.ts` | AC-6.1, AC-6.2, AC-6.3, AC-7.1, AC-7.4 |

### Playwright E2E Tests

| File | Scenarios Covered |
|------|-------------------|
| `portal/e2e/onboarding-wizard.spec.ts` | US-1 full happy path (step 1-11), US-6 backstory personalization |
| `portal/e2e/onboarding-resume.spec.ts` | US-3 abandonment + resume (localStorage) |
| `portal/e2e/onboarding-phone-country.spec.ts` | US-4 unsupported country validation, US-5 voice fallback |

**Playwright note**: All wizard E2E tests use `waitForSelector('[data-testid="wizard-step-{N}"]')` — NOT `networkidle`. The pipeline gate test uses `waitForSelector('[data-testid="pipeline-gate-stamp"][data-state="ready"]', { timeout: 25000 })`.

---

## Open Questions

All questions below were resolved from the brief and target diagram. No `[NEEDS CLARIFICATION]` items remain.

| Question | Resolution |
|----------|-----------|
| Does `POST /onboarding/backstory-choice` exist in Spec 213? | Yes — Spec 213 FR-3a new (target diagram amendment FR-3a). Portal owns the route; Spec 213 owns the service method. Endpoint: `POST /api/v1/onboarding/backstory-choice`. |
| Does PATCH /onboarding/profile exist? | Confirmed in brief ("Live endpoints" section). Portal calls PATCH for mid-wizard field updates. |
| What TypeScript type mirrors `PipelineReadyState`? | `type PipelineReadyState = "pending" \| "ready" \| "degraded" \| "failed"` — mirrored from `contracts.py` in `portal/src/app/onboarding/types/contracts.ts`. |
| Is `qrcode.react` already installed? | Not present in current `portal/package.json` scan. Must be added as new dependency in PR 214-A. |
| Is `libphonenumber-js` already installed? | Not confirmed. Must be added as new dependency in PR 214-A. |
| What are the ElevenLabs supported country codes? | Maintained in `portal/src/app/onboarding/constants/supported-phone-countries.ts`; populate from ElevenLabs/Twilio docs during PR 214-B implementation. |

---

## Appendix A — PR Decomposition (for /plan phase)

Three PRs, each ≤400 LOC soft cap. Portal components are typically 50-150 LOC each.

### PR 214-A — Foundation (≈300-350 LOC)

**Scope**: No visible UI changes. All plumbing.

| Artifact | Description |
|----------|-------------|
| `portal/src/app/onboarding/types/contracts.ts` | TypeScript mirror of `nikita/onboarding/contracts.py` types: `BackstoryOption`, `OnboardingV2ProfileRequest`, `OnboardingV2ProfileResponse`, `PipelineReadyResponse`, `BackstoryPreviewRequest`, `BackstoryPreviewResponse`, `PipelineReadyState` |
| `portal/src/app/onboarding/types/wizard.ts` | `WizardPersistedState`, `WizardStep` enum (3-11), `WizardFormValues` |
| `portal/src/app/onboarding/state/WizardStateMachine.ts` | Step transition guard, state enum, transition map |
| `portal/src/app/onboarding/state/WizardPersistence.ts` | `localStorage` read/write/clear with user-scoped key |
| `portal/src/app/onboarding/hooks/use-onboarding-api.ts` | `useOnboardingAPI`: `previewBackstory`, `submitProfile`, `patchProfile`, `selectBackstory` with `apiClient` wrappers |
| `portal/src/app/onboarding/hooks/use-pipeline-ready.ts` | `useOnboardingPipelineReady` poll hook |
| `portal/src/app/onboarding/constants/supported-phone-countries.ts` | ElevenLabs/Twilio supported country codes |
| `portal/package.json` | Add `qrcode.react`, `libphonenumber-js`; add `"prebuild": "tsc --noEmit"` |
| Unit tests | `WizardStateMachine.test.ts`, `WizardPersistence.test.ts`, `usePipelineReady.test.ts`, `useOnboardingAPI.test.ts` |

### PR 214-B — Step Components + Dossier Styling (≈350-400 LOC)

**Scope**: All visible wizard UI. Steps 3-11 components.

| Artifact | Description |
|----------|-------------|
| `portal/src/app/onboarding/onboarding-wizard.tsx` | Replaces `onboarding-cinematic.tsx`; orchestrates step rendering + persistence + API calls |
| `portal/src/app/onboarding/steps/DossierHeader.tsx` | Step 3: classified-file header + metric bars |
| `portal/src/app/onboarding/steps/LocationStep.tsx` | Step 4: city input + inline venue preview |
| `portal/src/app/onboarding/steps/SceneStep.tsx` | Step 5: SceneSelector button grid |
| `portal/src/app/onboarding/steps/DarknessStep.tsx` | Step 6: EdginessSlider with live Nikita quotes |
| `portal/src/app/onboarding/steps/IdentityStep.tsx` | Step 7: name/age/occupation three-field dossier |
| `portal/src/app/onboarding/steps/BackstoryReveal.tsx` | Step 8: BackstoryChooser + loading + degraded path |
| `portal/src/app/onboarding/steps/PhoneStep.tsx` | Step 9: binary voice/text choice + tel input + country validation |
| `portal/src/app/onboarding/steps/PipelineGate.tsx` | Step 10: stamp animation + poll state machine UI |
| `portal/src/app/onboarding/steps/HandoffStep.tsx` | Step 11: voice ring UI + Telegram CTA + QRHandoff |
| `portal/src/components/onboarding/QRHandoff.tsx` | Reusable QR component (desktop-only render) |
| `portal/src/app/onboarding/components/DossierStamp.tsx` | Reusable stamp with typewriter animation |
| `portal/src/app/onboarding/components/WizardProgress.tsx` | "FIELD N OF 7" progress label |
| Unit tests | All step tests per Test File Inventory table |
| `docs/content/wizard-copy.md` | Canonical Nikita copy reference for all wizard screens |

### PR 214-C — E2E Tests + Build Chain + Vercel Deploy (≈150-200 LOC)

**Scope**: Integration and deployment.

| Artifact | Description |
|----------|-------------|
| `portal/e2e/onboarding-wizard.spec.ts` | Happy path E2E (US-1, US-6); replaces existing networkidle-based onboarding spec |
| `portal/e2e/onboarding-resume.spec.ts` | Abandonment + resume E2E (US-3) |
| `portal/e2e/onboarding-phone-country.spec.ts` | Unsupported country + voice fallback E2E (US-4, US-5) |
| `portal/src/app/onboarding/schemas.ts` | Extend with `name`, `age`, `occupation`, `wizard_step` fields |
| `portal/src/app/onboarding/page.tsx` | Update to render `OnboardingWizard` instead of `OnboardingCinematic`; resume detection from `?resume=true` param |
| Vercel deploy | `cd portal && npm run build && vercel --prod` after PR merged to master |

---

## Appendix B — Canonical Mapping: TypeScript ↔ Python Contract Types

```
Python (nikita/onboarding/contracts.py)     TypeScript (portal/src/app/onboarding/types/contracts.ts)
─────────────────────────────────────────   ────────────────────────────────────────────────────────
PipelineReadyState (Literal)            →   type PipelineReadyState = "pending" | "ready" | "degraded" | "failed"
BackstoryOption (BaseModel)             →   interface BackstoryOption { id, venue, context, the_moment, unresolved_hook, tone }
OnboardingV2ProfileRequest (BaseModel)  →   interface OnboardingV2ProfileRequest { location_city, social_scene, drug_tolerance, life_stage?, interest?, phone?, name?, age?, occupation?, wizard_step? }
OnboardingV2ProfileResponse (BaseModel) →   interface OnboardingV2ProfileResponse { user_id, pipeline_state, backstory_options, chosen_option?, poll_endpoint, poll_interval_seconds, poll_max_wait_seconds }
BackstoryPreviewRequest (BaseModel)     →   interface BackstoryPreviewRequest { city, social_scene, darkness_level, life_stage?, interest?, age?, occupation? }
BackstoryPreviewResponse (BaseModel)    →   interface BackstoryPreviewResponse { scenarios, venues_used, cache_key, degraded }
PipelineReadyResponse (BaseModel)       →   interface PipelineReadyResponse { state, message?, checked_at, venue_research_status, backstory_available }
ErrorResponse (BaseModel)               →   interface ErrorResponse { detail: string }
```

**Asymmetry note**: `BackstoryPreviewRequest.occupation` has `max_length=100` only (no `min_length`) — explicitly looser than `OnboardingV2ProfileRequest.occupation` which requires `min_length=1`. TypeScript type should use `occupation?: string | null` with no client-side minimum for the preview request. See `contracts.py` SPEC-INTENTIONAL ASYMMETRY comment at line 146.

---

## Appendix C — Dossier Stamp States Reference

| Stamp text | When shown | Tailwind classes |
|-----------|------------|-----------------|
| `CLEARANCE: PENDING` | Step 10 poll in-flight | `text-primary/60 font-black tracking-widest uppercase animate-pulse` |
| `CLEARED` | Poll state="ready" | `text-primary font-black tracking-widest uppercase` + typewriter reveal |
| `PROVISIONAL — CLEARED` | Poll degraded/timeout | `text-primary/80 font-black tracking-widest uppercase` |
| `ANALYZED` | After backstory selected | `text-primary font-black tracking-widest uppercase` + stamp-rotate animation |
| `CONFIRMED` | On backstory card selection | `text-primary font-black tracking-widest uppercase` on individual card |
| `ANALYSIS: PENDING` | Backstory degraded path | `text-muted-foreground font-black tracking-widest uppercase` |

All stamps respect `prefers-reduced-motion`: if reduced motion, skip animation and show final state immediately.

---

## Appendix D — Backend Endpoint Reference

All endpoints are Spec 213 FROZEN contracts. Spec 214 is consumer-only.

| Method | Path | Request | Response | Called at |
|--------|------|---------|----------|-----------|
| `POST` | `/api/v1/onboarding/profile` | `OnboardingV2ProfileRequest` | `OnboardingV2ProfileResponse` | Step 10 |
| `PATCH` | `/api/v1/onboarding/profile` | Partial `OnboardingV2ProfileRequest` | `OnboardingV2ProfileResponse` | Steps 4-9 (fire-and-forget) |
| `POST` | `/api/v1/onboarding/preview-backstory` | `BackstoryPreviewRequest` | `BackstoryPreviewResponse` | Step 8 |
| `POST` | `/api/v1/onboarding/backstory-choice` | `{ user_id: string, chosen_option_id: string }` | `OnboardingV2ProfileResponse` | Step 8 (after card selection CTA) |
| `GET` | `/api/v1/onboarding/pipeline-ready/{user_id}` | — | `PipelineReadyResponse` | Steps 10-11 (poll) |
