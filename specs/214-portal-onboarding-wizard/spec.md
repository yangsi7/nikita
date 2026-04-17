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
| 3 | Dossier Header | Classified-file header, real 50/50/50/50 scores, "Prove me wrong." | CTA: "Open the file." |
| 4 | Location | City text input, async venue preview below on blur (800ms debounce) | CTA: "That's accurate." |
| 5 | Scene | Pre-filled "Suspected: techno?", SceneSelector button grid; collects `social_scene` (primary) AND `life_stage` (secondary — inferred from scene selection via existing `SceneSelector` → life_stage mapping in `profile-section.tsx`) | Scene button selection |
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
- Buttons: `<GlowButton href=...>` for FINAL-NAVIGATION CTAs only (step 2 magic-link, step 11 "Open Telegram"); for all step-advance click CTAs (steps 3-10 CTA buttons), use shadcn `Button` variant with matching dossier styling (`className="text-primary font-black tracking-[0.2em] uppercase"`). `GlowButton` only supports `href` (renders as `<Link>`) and cannot be used for click handlers or form submit CTAs.
- Framer-motion: existing `EASE_OUT_QUART = [0.16, 1, 0.3, 1]` easing on all step transitions (slide-up + fade-in)
- Font tokens `font-black`, `tracking-tighter`, `tracking-[0.2em]`: already in `portal/tailwind.config.ts` — use as-is

**Acceptance Criteria**:
- AC-2.1: Visual regression screenshot of step 3 (dossier header) shows classified-file aesthetic with 4 metric bars
- AC-2.2: `AuroraOrbs` and `FallingPattern` render on all 11 steps without CSS conflicts
- AC-2.3: No inline styles anywhere in wizard components — all styling via Tailwind utility classes
- AC-2.4: `GlassCard` component is imported from `portal/src/components/glass/glass-card.tsx`, not re-implemented
- AC-2.5: `GlowButton` is used ONLY for final-navigation CTAs (`href` prop required); all step-advance CTAs use shadcn `Button` with dossier styling — no `GlowButton` may appear with an `onClick` or `type="submit"` prop

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
- AC-4.0: Step 4 inline venue preview uses a debounced (800ms on blur) call to `POST /preview-backstory` with a minimal payload (city only, all other fields null/default); `venues_used` from the response is rendered below the city input. The debounce is implemented using `React.useDeferredValue` or a `setTimeout`/`clearTimeout` pattern inside `useEffect`. This preview call does NOT count toward the rate-limit quota for the full backstory preview at step 8 (same endpoint, same 5/min limit — note this consumes from the shared quota).
- AC-4.1: `POST /onboarding/preview-backstory` is called exactly once on step 8 mount (not on every re-render); loading state shows dossier animation
- AC-4.2: All 3 scenario cards render with correct `BackstoryOption` fields; clicking a card sets it as selected with "CONFIRMED" stamp
- AC-4.3: Degraded path (empty scenarios or `degraded: true`) renders "ANALYSIS: PENDING" without error state and advances to step 9 on CTA click
- AC-4.4: Rate limit (HTTP 429 from `PREVIEW_RATE_LIMIT_PER_MIN=5`) displays Nikita-voiced retry message, not a generic error
- AC-4.5: On step 8 POST resolution, focus moves to the first scenario card (`role="radio"`, `tabIndex=0`); subsequent cards have `tabIndex=-1` (WAI-ARIA radiogroup pattern). Focus is set via `ref.focus()` inside `useEffect` after the card grid mounts. During loading, focus remains on the dossier animation container.

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
- AC-5.6: `GET /pipeline-ready/{user_id}` is rate-limited to `PIPELINE_POLL_RATE_LIMIT_PER_MIN=30` requests per authenticated user per minute via a `DatabaseRateLimiter` subclass with `poll:` key prefix; 429 response includes `Retry-After: 60` header

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
- AC-8.1: `WizardStateMachine` enforces `BACKSTORY_REVEAL` (8) always precedes `PHONE_ASK` (9) — enforced by state transition guard that returns an error state (`{ ok: false, reason: "INVALID_ORDER" }`) instead of throwing; caller renders an inline Nikita-voiced error and does not advance
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

After selection, `chosen_option_id` is persisted via `PUT /api/v1/onboarding/profile/chosen-option` (NEW in this spec — see FR-10). The endpoint is idempotent (same `chosen_option_id` → same result, safe to retry), validates the `chosen_option_id` belongs to the calling user's backstory cache row, and emits a structured `onboarding.backstory_chosen` event. Response: `OnboardingV2ProfileResponse` with `chosen_option` populated.

**Acceptance Criteria**:
- AC-9.1: Selecting a card marks it with "CONFIRMED" stamp; deselects all others visually
- AC-9.2: `PUT /onboarding/profile/chosen-option` fires on CTA click, not on card selection; loading state shown while request in-flight; retries allowed on network failure (endpoint is idempotent)
- AC-9.3: Each `BackstoryOption` tone renders as a distinct badge color: romantic=rose, intellectual=blue, chaotic=amber
- AC-9.4: Cards rendered inside `<div role="radiogroup" aria-label="Backstory scenarios">`. Each card `role="radio"`, `aria-checked={selected}`, tabindex managed per WAI-ARIA radiogroup pattern (first or selected card tabbable, others -1). Matches existing `SceneSelector` pattern in `portal/src/app/onboarding/sections/profile-section.tsx`. Note: `aria-selected` is NOT used (only valid on `gridcell`, `option`, `row`, `tab` — not `div` cards).
- AC-9.5: See AC-4.5 (focus management after step 8 POST resolution — first scenario card focused, subsequent cards `tabIndex=-1`).
- **AC-9.6 (GH #313 regression guard, added 2026-04-17):** CTA click MUST call `patchProfile({location_city, social_scene, drug_tolerance, life_stage, interest, name, age, occupation, wizard_step: 8})` BEFORE `selectBackstory(chosen_option_id, cache_key)`, and MUST `await` the PATCH to settlement (fulfillment or rejection) before any further action. Fire-and-forget is insufficient. Rationale: the backend's clearance check recomputes `compute_backstory_cache_key` from `users.onboarding_profile` JSONB (see AC-10.3) and rejects when the recomputed key does not match the submitted one. Without a synchronous PATCH-before-PUT, the JSONB stays empty, the server recomputes `unknown|unknown|unknown|...`, and every fresh user gets a `403 "Clearance mismatch. Start over."` blocking onboarding at step 6/7. If `patchProfile` rejects, `selectBackstory` MUST NOT be called and `onAdvance` MUST NOT fire. Instead, re-enable the CTA so the user can retry without a half-persisted race. The 8 profile fields above are exactly the cache-key recipe in `nikita/onboarding/tuning.py::compute_backstory_cache_key`; `phone` is deliberately omitted because it is not part of the recipe. Adding a new field to that recipe without updating the PATCH payload here (or vice versa) reintroduces this bug class. Falsifiable test: `BackstoryReveal.test.tsx` asserts (i) `patchProfile` is called with the full collected profile, (ii) order is `patch` then `select` via a `callOrder` array, (iii) a rejected `patchProfile` leaves `selectBackstory` uncalled and the CTA re-enabled.

---

### FR-10 — Backend Sub-Amendment (New Endpoint + Contract Extension) (P1)

**Description**: Spec 214 additively extends Spec 213's frozen backend contracts with one new endpoint and one response-field addition. These changes are strictly additive (no breaking changes to existing 213 contract consumers). Implementation ships as **PR 214-D (backend)** and MUST merge before PR 214-A (portal foundation) depends on the new types.

#### 10.1 — `PUT /api/v1/onboarding/profile/chosen-option`

**Route**: `PUT /api/v1/onboarding/profile/chosen-option`
**Auth**: Supabase JWT (existing `get_current_user_id` dependency)
**Rate limit**: `choice_rate_limit` dependency (10/min per authenticated user via `_ChoiceRateLimiter`; `CHOICE_RATE_LIMIT_PER_MIN` in tuning.py); `Retry-After: 60` header on 429. See rate-limiter pseudocode below.

**Request body** (new Pydantic model in `nikita/onboarding/contracts.py`):
```python
class BackstoryChoiceRequest(BaseModel):
    chosen_option_id: str = Field(..., min_length=1, max_length=64)
    # actual ids are always exactly 12 hex chars (sha256[:12])
    cache_key: str = Field(..., min_length=1, max_length=128)
    # Explicitly echoed here (unlike POST /profile which recomputes cache_key server-side);
    # required for the idempotency guard + stale-selection rejection to function across retries.
    # This is the ONLY endpoint that echoes cache_key — future cleanup must preserve this field.
```

**Response body**: existing `OnboardingV2ProfileResponse` with `chosen_option: BackstoryOption` populated (replaces `None`).

**Semantics**:
- Idempotent: PUT with same `(user_id, chosen_option_id, cache_key)` → same state, same response (200 OK on every call). Safe to retry.
- Validates ownership via `cache_key` recompute: `backstory_cache` has NO `user_id` column — it is keyed only by `cache_key` (TEXT). Ownership is inferred by recomputing `cache_key` from the authenticated user's `users.onboarding_profile` JSONB (NOT `user_profiles` table — portal wizard writes to `onboarding_profile` via PATCH; `user_profiles` is voice-onboarding scope only). Load via `UserRepository(session).get(user_id)`, then build a `SimpleNamespace` bridging JSONB keys to the attribute names expected by `compute_backstory_cache_key()` (`location_city → city`, `drug_tolerance → darkness_level`), and compare against the echoed `cache_key`. Mismatch → HTTP 403 "Clearance mismatch. Start over." Note: if the user mutates their profile between `POST /preview-backstory` and `PUT /profile/chosen-option`, the recomputed `cache_key` will differ — this is correct behavior (stale selection rejected). See `set_chosen_option` docstring below for the full attribute-bridging code.
- Validates: `chosen_option_id` must appear in the `BackstoryCacheRepository` row for the given `cache_key`. Unknown id → HTTP 409 Conflict (not 422 — the id is syntactically valid but conflicts with stored state).
- Writes: `users.onboarding_profile` JSONB field `chosen_option` (full `BackstoryOption` dict, not just the id — snapshotted so backstory_cache eviction doesn't orphan the selection).
- Emits: structured log event `onboarding.backstory_chosen` with `{user_id, chosen_option_id, tone, venue}` (no PII — tone/venue are from the generated scenario, not user-provided).
- Does NOT re-trigger `_trigger_portal_handoff` — handoff runs at `POST /profile` time (step 10). This endpoint just records the selection.

**Error response shapes** (distinct from Pydantic 422):
- Handler-raised errors use flat `{"detail": string}` (matching `ErrorResponse` contract).
- Pydantic validation 422 (schema shape violation) uses list `{"detail": [{...}]}`.
- Consumers must handle `typeof detail === 'string'` vs `Array.isArray(detail)` — use the `ErrorResponse` shape for all handler-raised cases.

**Facade method** (`PortalOnboardingFacade.set_chosen_option`):
```python
async def set_chosen_option(
    self,
    user_id: UUID,
    chosen_option_id: str,
    cache_key: str,
    session: AsyncSession,
) -> BackstoryOption:
    """Validate + persist user's backstory selection. Returns the snapshotted option.
    
    Validation path:
    1. Load `users.onboarding_profile` JSONB (NOT `user_profiles` table — portal
       wizard writes to `users.onboarding_profile` via PATCH; `user_profiles`
       is voice-onboarding scope):
           user = await UserRepository(session).get(user_id)
           profile_jsonb = user.onboarding_profile or {}
    2. Build a duck-typed SimpleNamespace bridging JSONB keys to the attribute
       names expected by `compute_backstory_cache_key()` (mirrors the existing
       `generate_preview` pattern at `portal_onboarding.py:155-163`). Note the
       key→attr mapping: `location_city → city`, `drug_tolerance → darkness_level`.
           from types import SimpleNamespace
           pseudo = SimpleNamespace(
               city=profile_jsonb.get("location_city"),
               darkness_level=profile_jsonb.get("drug_tolerance"),
               social_scene=profile_jsonb.get("social_scene"),
               life_stage=profile_jsonb.get("life_stage"),
               interest=profile_jsonb.get("interest"),
               age=profile_jsonb.get("age"),
               occupation=profile_jsonb.get("occupation"),
           )
    3. Compute current cache_key = compute_backstory_cache_key(pseudo).
    4. If computed != supplied cache_key → raise HTTPException(403, "Clearance mismatch. Start over.").
    5. Load BackstoryCacheRepository.get(cache_key) → 404 if missing.
    6. Check chosen_option_id in cache row's scenarios → 409 if missing.
    7. Snapshot full BackstoryOption to users.onboarding_profile.chosen_option JSONB.
    8. Emit onboarding.backstory_chosen event.
    """
```

**Full handler pseudocode** (PR 214-D, `nikita/api/routes/portal_onboarding.py`):
```python
@router.put("/profile/chosen-option", response_model=OnboardingV2ProfileResponse)
async def put_chosen_option(
    body: BackstoryChoiceRequest,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_async_session),
    _: None = Depends(choice_rate_limit),
) -> OnboardingV2ProfileResponse:
    user_repo = UserRepository(session)
    facade = PortalOnboardingFacade()
    chosen_option = await facade.set_chosen_option(
        user_id=current_user_id,
        chosen_option_id=body.chosen_option_id,
        cache_key=body.cache_key,
        session=session,
    )
    user = await user_repo.get(current_user_id)  # refresh for pipeline_state
    profile_jsonb = user.onboarding_profile or {}
    return OnboardingV2ProfileResponse(
        user_id=current_user_id,
        pipeline_state=profile_jsonb.get("pipeline_state", "pending"),
        backstory_options=[],  # already delivered in preview; not re-sent
        chosen_option=chosen_option,
        poll_endpoint=f"/api/v1/onboarding/pipeline-ready/{current_user_id}",
        poll_interval_seconds=PIPELINE_GATE_POLL_INTERVAL_S,
        poll_max_wait_seconds=PIPELINE_GATE_MAX_WAIT_S,
    )
```

**Rate limiting** — dedicated `choice_rate_limit` dependency:
```python
# nikita/onboarding/tuning.py additions:
CHOICE_RATE_LIMIT_PER_MIN: Final[int] = 10  # per authenticated user per minute
# (choosing a backstory is a one-shot action, not a generation cost; 10/min is generous)

# nikita/api/middleware/rate_limit.py additions:
class _ChoiceRateLimiter(DatabaseRateLimiter):
    MAX_PER_MINUTE = CHOICE_RATE_LIMIT_PER_MIN
    def _get_minute_window(self) -> str:
        return f"choice:{super()._get_minute_window()}"
    def _get_day_window(self) -> str:
        return f"choice:{super()._get_day_window()}"

async def choice_rate_limit(
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    limiter = _ChoiceRateLimiter(session)
    await limiter.check(current_user_id)  # bare UUID; 'choice:' isolation is in _get_minute_window()
```

**Error responses**:
- 200: success (idempotent; always 200 not 201 on repeated PUT)
- 403: `cache_key` recompute mismatch (stale profile or cross-user attempt) — Nikita-voiced detail
- 404: no `backstory_cache` row for `cache_key`
- 409: `chosen_option_id` not in the cache row's scenarios — detail: `"That scenario doesn't exist. Pick one she actually generated for you."`
- 429: rate limit exceeded — `Retry-After: 60` header REQUIRED (RFC 6585); same header as `preview_rate_limit` pattern

#### 10.2 — Extend `PipelineReadyResponse` with `wizard_step: int | None`

**Rationale**: Supports NR-1 cross-device wizard resume. Currently, `users.onboarding_profile.wizard_step` JSONB key is writable via PATCH (FR-6) but there's no read path. Rather than add a separate `GET /onboarding/profile` endpoint, piggyback on the existing `GET /pipeline-ready/{user_id}` since it's already called during resume detection.

**Contract change** in `nikita/onboarding/contracts.py`:
```python
class PipelineReadyResponse(BaseModel):
    state: PipelineReadyState
    message: str | None = None
    checked_at: datetime
    venue_research_status: str = Field(default="pending")  # existing
    backstory_available: bool = Field(default=False)  # existing
    wizard_step: int | None = Field(default=None, ge=1, le=11)  # NEW
    # Range ge=1 matches the PATCH write schema (OnboardingV2ProfilePatchRequest.wizard_step ge=1, le=11)
    # so no JSONB values are silently coerced to None. Wizard never PATCHes steps 1-2
    # (landing/auth are pre-wizard), but a defensive lower bound of 1 is correct.
    # Read from onboarding_profile.wizard_step JSONB key; None if user never advanced past step 3.
```

**Read path**: `portal_onboarding.get_pipeline_ready` handler reads `onboarding_profile.wizard_step` JSONB key; defaults to `None` if missing.

**Pipeline-ready rate limiter** (`_PipelineReadyRateLimiter`) — pseudocode, mirrors `_PreviewRateLimiter` pattern at `rate_limit.py:123-131`:
```python
# nikita/onboarding/tuning.py
PIPELINE_POLL_RATE_LIMIT_PER_MIN: Final[int] = 30

# nikita/api/middleware/rate_limit.py
class _PipelineReadyRateLimiter(DatabaseRateLimiter):
    MAX_PER_MINUTE = PIPELINE_POLL_RATE_LIMIT_PER_MIN
    def _get_minute_window(self) -> str:
        return f"poll:{super()._get_minute_window()}"
    def _get_day_window(self) -> str:
        return f"poll:{super()._get_day_window()}"

async def pipeline_ready_rate_limit(
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    limiter = _PipelineReadyRateLimiter(session)
    await limiter.check(current_user_id)  # bare UUID, not prefixed
```

**Handler signature update** for `get_pipeline_ready` (PR 214-D, `nikita/api/routes/portal_onboarding.py`):
```python
async def get_pipeline_ready(
    user_id: UUID,
    current_user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_async_session),
    _: None = Depends(pipeline_ready_rate_limit),  # NEW per FR-10.2 / AC-5.6
) -> PipelineReadyResponse:
    ...
```

**Breaking change check**: Adding an optional field with `default=None` is non-breaking for existing consumers (portal today, smoke probes, Spec 214 types-to-be). No Spec 213 amendment required beyond the contract extension itself.

**Acceptance Criteria**:
- AC-10.1: `PUT /profile/chosen-option` with a valid (cache_key, chosen_option_id) pair for the authenticated user returns 200 with `chosen_option` populated in the response
- AC-10.2: PUT with an unknown `chosen_option_id` (syntactically valid but not in the cache row's scenarios) returns **409 Conflict** with detail `"That scenario doesn't exist. Pick one she actually generated for you."`. Note: 422 is reserved for Pydantic schema violations (list-shape detail); handler-raised business-rule errors use distinct status codes (403, 404, 409).
- AC-10.3: PUT with a `cache_key` that does not match the recomputed key for the authenticated user's current profile returns 403 with Nikita-voiced detail. Validation path (MUST match facade docstring at FR-10.1): load `users.onboarding_profile` JSONB (NOT `user_profiles` table — see Semantics note above), build `SimpleNamespace(city=jsonb.get("location_city"), darkness_level=jsonb.get("drug_tolerance"), social_scene=jsonb.get("social_scene"), life_stage=jsonb.get("life_stage"), interest=jsonb.get("interest"), age=jsonb.get("age"), occupation=jsonb.get("occupation"))`, call `compute_backstory_cache_key(pseudo)`, compare to supplied `cache_key`. Mismatch → 403 "Clearance mismatch. Start over." There is NO `user_id` column on `backstory_cache` — ownership is inferred solely via this recompute-and-compare check.
- AC-10.4: PUT is idempotent — calling twice with same body produces identical state and response
- AC-10.5: `users.onboarding_profile.chosen_option` JSONB contains the FULL `BackstoryOption` dict after successful PUT (not just the id)
- AC-10.6: `onboarding.backstory_chosen` structured log event is emitted with tone + venue only (no user-provided fields like name/age/occupation/phone/city)
- AC-10.7: `GET /pipeline-ready/{user_id}` response includes `wizard_step` field populated from `onboarding_profile.wizard_step` (or `None` if not yet set)
- AC-10.8: Existing portal code paths and smoke probes that consumed `PipelineReadyResponse` without `wizard_step` continue to work (field is optional on the consumer side)
- AC-10.9: 429 response from `PUT /profile/chosen-option` (rate limit exceeded) MUST include `Retry-After: 60` header per RFC 6585. This matches the `preview_rate_limit` pattern in `nikita/api/middleware/rate_limit.py`.

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
  cache_key: string | null              // from BackstoryPreviewResponse; required for PUT /profile/chosen-option
  saved_at: string                      // ISO-8601
}
```

Security note: `wizard_step` JSONB payload is internal state only; never rendered directly to DOM (XSS risk).

**Acceptance Criteria**:
- AC-NR1.1: After completing step 6 and closing the browser tab, reopening `/onboarding` resumes at step 7 with previously-entered `location_city`, `social_scene`, and `drug_tolerance` pre-filled
- AC-NR1.2: `localStorage.setItem('nikita_wizard_{user_id}', ...)` is called on every step advance
- AC-NR1.3: On wizard completion (step 11), `localStorage.removeItem('nikita_wizard_{user_id}')` is called to prevent stale resume
- AC-NR1.4: Wizard state from a different `user_id` in localStorage is ignored; key is user-scoped
- AC-NR1.5: All `localStorage` reads (for resume state) MUST occur inside `useEffect` only. Initial server-render and client first-paint MUST show step 3 (the authenticated landing step); post-mount the wizard upgrades to the resumed step via state update. `WizardPersistence.ts` exports only `readPersistedState(): WizardPersistedState | null` which is safe to call from `useEffect`, not from render functions. Tests assert `waitFor(() => screen.getByTestId('wizard-step-{resumed_step}'))` after tick.

---

### NR-1a — `life_stage` Collection Clarification

`life_stage` (one of `["tech", "finance", "creative", "student", "entrepreneur", "other"]`) is NOT collected as a new wizard step. It is already captured via the `SceneSelector` at step 5 — the user's scene selection implies `life_stage` via the existing tag mapping in `portal/src/app/onboarding/sections/profile-section.tsx`. `BackstoryPreviewRequest.life_stage` is populated from `formState.life_stage` which is derived from the scene selection. If no scene maps to a `life_stage`, send `null`. Spec 214 does NOT add a dedicated `life_stage` input field.

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

**QRHandoff placement**: co-located with wizard-internal components at `portal/src/app/onboarding/components/QRHandoff.tsx` (NOT `portal/src/components/onboarding/`). All onboarding-specific components live together; no cross-wizard reuse is planned.

**useMediaQuery SSR strategy**: `QRHandoff` uses a `useMediaQuery('(min-width: 768px)')` hook with `defaultValue: false` (renders hidden on server, visible on client after hydration). This avoids hydration mismatch at the cost of a one-frame QR flash-in on desktop, which is acceptable. Prevents incorrect QR render on mobile-SSR then desktop-client transition.

```typescript
// portal/src/app/onboarding/components/QRHandoff.tsx
interface QRHandoffProps {
  telegramUrl: string     // "https://t.me/Nikita_my_bot"
  label?: string          // "On desktop? Scan to open on your phone."
}
```

**Acceptance Criteria**:
- AC-NR4.1: QR code renders on step 11 when viewport width ≥ 768px; hidden on mobile viewports
- AC-NR4.2: QR code is surrounded by Nikita copy: "On desktop? Scan to open on your phone."
- AC-NR4.3: `QRHandoff` has no server-side dependencies; renders entirely client-side
- AC-NR4.4: QR code is wrapped in `<figure>` with `<figcaption>` containing the Nikita copy (not `aria-label` on canvas — `<canvas>` is not natively interactive and `aria-label` alone is insufficient for screen readers). The `<figcaption>` text satisfies WCAG without requiring tabindex on a non-interactive element.

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
- AC-NR5.5: When ring-animation → fallback transition occurs, a `<div role="status" aria-live="polite">` region announces: "Voice unavailable. Use Telegram below." so screen reader users receive the state change. The region is always present in the DOM (initially empty); text is injected on state transition.

---

### FR-11b, Telegram Deep-Link Binding (P1), Amendment (GH #321)

**Description**: Step 11's Telegram handoff CTA MUST carry a single-use deep-link token that the bot consumes via `/start <token>` to atomically bind `users.telegram_id` to the portal user. Without this binding, a portal-registered user who taps the CTA lands as an unauthenticated visitor; the bot falls through to the email-OTP path and silently creates an orphan row with no link to the existing portal account. GH #321 exists to eliminate that bug class.

**Behavior**:

- On HandoffStep mount, the portal calls `POST /portal/link-telegram` via `useOnboardingAPI().linkTelegram()`. Response shape: `{ code, expires_at, instructions }`. Code is 6-char uppercase alphanumeric with a 10-minute TTL, single-use.
- The Telegram CTA's href becomes `https://t.me/Nikita_my_bot?start=<code>`. The QR payload uses the same URL so desktop→phone handoff carries the token too.
- The bot's `/start <payload>` handler (`nikita.platforms.telegram.commands.CommandHandler._handle_start`) validates `^[A-Z0-9]{6}$`, calls `TelegramLinkRepository.verify_code` (atomic `DELETE ... WHERE ... RETURNING` per REQ-3a), then `UserRepository.update_telegram_id` (atomic predicate UPDATE per REQ-4).
- Any payload reject (invalid format, expired/unknown code, cross-user conflict) MUST short-circuit with a user-facing error and MUST NOT fall through to the email-OTP (branch-3) flow of vanilla `/start`. Fallthrough on a bad payload reproduces the orphan-row bug this amendment exists to eliminate.
- Vanilla `/start` (no payload) preserves the pre-#321 3-branch behavior exactly (welcome-back, fresh-start, new-user email prompt) so Telegram-first registration remains unaffected.

**Acceptance Criteria**:

- AC-11b.1: HandoffStep MUST call `POST /portal/link-telegram` on mount. Verified via unit test on `useOnboardingAPI.linkTelegram()` and HandoffStep `useEffect` invocation; end-to-end verified via preview-env dogfood walk asserting network trace.
- AC-11b.2: The Telegram CTA `href` attribute MUST match `^https://t\.me/Nikita_my_bot\?start=[A-Z0-9]{6}$`. The QR payload MUST carry the same URL with the same token. Bare `https://t.me/Nikita_my_bot` without `?start=<code>` is NOT permitted as a fallback (brief Q-3: bare-URL fallback reproduces the #321 bug class).
- AC-11b.3: Bot `_handle_start` MUST consume valid payloads: regex gate `^[A-Z0-9]{6}$` → atomic `verify_code` → atomic `update_telegram_id`. Post-bind, `users.telegram_id` row reflects the Telegram numeric id, and the `telegram_link_codes` row is consumed (row deleted via the `DELETE ... RETURNING`).
- AC-11b.4: Expired, invalid-format, or already-consumed payloads MUST short-circuit with a clear user-facing error (e.g. "That link expired. Open the portal and tap the button again.") and MUST NOT initiate the email-OTP (branch-3) flow. Cross-user conflicts MUST raise `TelegramIdAlreadyBoundByOtherUserError` in the repository layer and render a "this Telegram account is already linked to another profile" message to the user. No silent overwrites.
- AC-11b.5: On `linkTelegram()` failure, HandoffStep MUST NOT render a bare-URL Telegram CTA. Required degraded states (text-idle and voice-unavailable paths): (a) a visible `role="alert"` error region announcing the failure, (b) an inline retry affordance (`<button>` that re-fires `linkTelegram()` without losing wizard state; no full-page refresh). On the voice-ringing path (voice is primary), the error alert and retry button are SUPPRESSED to avoid interrupting a live voice call with Telegram-path chatter. Bare-URL fallback is forbidden in all states.
- AC-11b.6: `verify_code` MUST compile to a single `DELETE FROM telegram_link_codes WHERE code = :code AND expires_at > now() RETURNING user_id` statement (REQ-3a). Any SELECT-then-DELETE pattern is a regression; concurrent `/start <same-code>` calls MUST see exactly one winner.
- AC-11b.7: `update_telegram_id` MUST use a predicate-filter `UPDATE ... WHERE (telegram_id IS NULL OR telegram_id = :tid) ... RETURNING telegram_id` (REQ-4) so the UNIQUE constraint is never hit as a raw `IntegrityError`; cross-user conflicts surface via `rowcount == 0` + disambiguation SELECT + typed exception.

**Verification**:

- Unit: `tests/db/repositories/test_telegram_link_repository_atomic.py`, `tests/db/repositories/test_user_repository_update_telegram_id.py`, `tests/platforms/telegram/test_commands.py::TestHandleStartWithPayload`, `portal/src/app/onboarding/hooks/__tests__/useOnboardingAPI.test.ts` (linkTelegram describe), `portal/src/app/onboarding/steps/__tests__/HandoffStep.test.tsx` (GH #321 REQ-1 describe).
- Integration: `tests/db/integration/test_repositories_integration.py::TestUserRepositoryIntegration::test_update_telegram_id_three_cases` (real-DB regression for #316/#318 bug class).
- End-to-end (preview-env + prod): Agent I-2 walk asserting CTA href matches regex, POST `/portal/link-telegram` 200, `/start <code>` binds `users.telegram_id`, `telegram_link_codes` row consumed, Nikita bot greeting arrives referencing user's wizard-supplied name.

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
- AC-US6.1: `PUT /onboarding/profile/chosen-option` (FR-10.1) is called with the `chosen_option_id` + `cache_key` before advancing to step 9
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

### Backend Contracts (Consumed + 1 Additive Extension)

The following types from `nikita/onboarding/contracts.py` are consumed by Spec 214. Spec 214 PRs modify only via additive extensions (no breaking changes to fields already consumed by 213 or by live smoke probes):

- `OnboardingV2ProfileRequest` — final submit payload (FR-7) — **unchanged**
- `OnboardingV2ProfileResponse` — POST response (FR-5 poll setup) — **unchanged**
- `BackstoryOption` — card display fields (FR-9) — **unchanged**
- `BackstoryPreviewRequest` / `BackstoryPreviewResponse` — step 8 preview (FR-4) — **unchanged**
- `PipelineReadyResponse` — poll response (FR-5) — **EXTENDED with `wizard_step: int | None` (FR-10.2)**
- `PipelineReadyState` = Literal["pending", "ready", "degraded", "failed"] — **unchanged**
- `BackstoryChoiceRequest` — **NEW in FR-10.1** (sibling to BackstoryPreviewRequest)

The `PipelineReadyResponse.wizard_step` extension is strictly additive (optional field with `default=None`) — existing consumers that ignore the field keep working. This avoids a full Spec 213 amendment ADR; change is bounded to the contract file + handler + one new test.

Any non-additive change to these types (e.g., making an existing field required, renaming, changing types) DOES require a Spec 213 amendment ADR before Spec 214 implementation proceeds.

### Tuning Constants (Consumed, Not Owned)

Spec 214 reads but does NOT define the following portal-consumed constants (owned by `nikita/onboarding/tuning.py`):
- `PIPELINE_GATE_POLL_INTERVAL_S = 2.0` — poll interval in seconds
- `PIPELINE_GATE_MAX_WAIT_S = 20.0` — hard cap in seconds
- `BACKSTORY_HOOK_PROBABILITY = 0.50` — backend-controlled, portal does NOT gate on this
- `PREVIEW_RATE_LIMIT_PER_MIN = 5` — portal handles 429 but does not enforce the limit

Spec 214 (PR 214-D) ADDS the following new constants to `nikita/onboarding/tuning.py`:
- `CHOICE_RATE_LIMIT_PER_MIN: Final[int] = 10` — rate limit for `PUT /profile/chosen-option` per authenticated user per minute
- `PIPELINE_POLL_RATE_LIMIT_PER_MIN: Final[int] = 30` — rate limit for `GET /pipeline-ready/{user_id}` per authenticated user per minute (accommodates 15 legitimate poll requests in a 30s window at 2s interval)

Portal mirrors these values via `OnboardingV2ProfileResponse.poll_interval_seconds` and `.poll_max_wait_seconds` (not hardcoded).

### Assumptions

1. Spec 213 is fully merged to master and deployed (Cloud Run revision `nikita-api-00250-4mm`, 2026-04-15). Spec 214 PR 214-D (backend) is implemented in this spec cycle and deploys before PR 214-A lands in production.
2. `PATCH /api/v1/onboarding/profile` endpoint (Spec 213, shipped) accepts partial `OnboardingV2ProfileRequest` fields via jsonb_set merge.
3. `portal/tailwind.config.ts` already contains all required theme tokens (`bg-void`, `bg-void-ambient`, `text-primary` = oklch rose). No new token additions required.

---

## Out of Scope

The following are explicitly NOT in Spec 214 scope:

1. **Backend changes beyond FR-10**: only the two backend extensions specified in FR-10 (new `PUT /profile/chosen-option` endpoint and additive `PipelineReadyResponse.wizard_step` field) are in scope. Any other backend change requires a separate spec.
2. **Voice prompt first_message backstory injection**: FirstMessageGenerator backstory injection is owned by Spec 213 FR-6/FR-7. Portal cannot control this.
3. **New `user_profiles` columns**: `name`, `age`, `occupation` DB columns were added in Spec 213 migration. Spec 214 does not touch the database schema. (Note: FR-10 writes to `onboarding_profile` JSONB — no new columns needed; `chosen_option` is a JSONB key.)
   **Data layer note**: `users` UPDATE RLS is covered by the OR-permissive `users_own_data` policy WITH CHECK `(id = (SELECT auth.uid()))` (Spec 083). The separate "Users can update own data" UPDATE policy has `with_check = NULL` — pre-existing gap, covered by `users_own_data`, tracked separately. No Spec 214 change needed. The same pattern exists on `user_profiles`: `Users can update own profile` (public role) UPDATE policy has `with_check = NULL`; the correct `Users update own profile` (authenticated role) WITH CHECK covers all authenticated writes. Track in the same standalone RLS hardening GH issue.
4. **Custom Supabase email template**: the Nikita-voiced magic link email body is a Supabase Dashboard configuration (infra setting), explicitly deferred to a manual operator task. Tracked as a separate pre-deploy checklist item for PR 214-C — NOT a portal code change and NOT in this spec's implementation scope. If template is not customized, default Supabase email still works (functional but not on-brand); acceptance is at most "copy provided in `docs/content/magic-link-email.md` for operator to paste into Supabase Dashboard".
5. **Post-onboarding voice upgrade path**: after-onboarding settings page for adding phone at `/dashboard/settings/contact` — future spec.
6. **Admin portal changes**: no admin pages affected.
7. **Standalone pre-fixes P-FIX-1 through P-FIX-4** (listed in FR-3 section): these ship as independent small PRs before Spec 214 implementation, not as part of Spec 214 PRs.
8. **Backstory re-selection after onboarding**: users cannot re-choose a different backstory after completing the wizard. Future spec if needed.

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
| `portal/src/app/onboarding/__tests__/WizardPersistence.test.ts` | AC-NR1.1, AC-NR1.2, AC-NR1.3, AC-NR1.4, AC-NR1.5 |
| `portal/src/app/onboarding/steps/__tests__/DossierHeader.test.tsx` | AC-1.4, AC-2.1 |
| `portal/src/app/onboarding/steps/__tests__/LocationStep.test.tsx` | AC-4.0, AC-6.2, AC-NR2.3 |
| `portal/src/app/onboarding/steps/__tests__/SceneStep.test.tsx` | AC-1.2 |
| `portal/src/app/onboarding/steps/__tests__/DarknessStep.test.tsx` | AC-1.2 |
| `portal/src/app/onboarding/steps/__tests__/IdentityStep.test.tsx` | AC-NR2.1, AC-NR2.2, AC-NR2.3 |
| `portal/src/app/onboarding/steps/__tests__/BackstoryReveal.test.tsx` | AC-4.1, AC-4.2, AC-4.3, AC-4.4, AC-4.5, AC-9.1, AC-9.2, AC-9.3, AC-9.4, AC-3.3 (error state: 429 path must assert exact Nikita-voiced string "Too eager. Wait a moment.") |
| `portal/src/app/onboarding/steps/__tests__/PhoneStep.test.tsx` | AC-NR3.1, AC-NR3.2, AC-NR3.3, AC-NR3.4, AC-US4.1, AC-US4.2, AC-3.3 (error state: invalid phone must assert exact Nikita-voiced string "That number doesn't work. Try again.") |
| `portal/src/app/onboarding/steps/__tests__/PipelineGate.test.tsx` | AC-5.1, AC-5.2, AC-5.3, AC-5.4, AC-7.2, AC-7.3, AC-3.3 (error state: 422 path must assert Nikita-voiced toast copy) |
| `tests/api/routes/test_portal_onboarding.py` (backend) | AC-5.6: verify `GET /pipeline-ready/{user_id}` returns 429 + `Retry-After: 60` header when `_PipelineReadyRateLimiter` limit (30/min) is exceeded |
| `tests/services/test_portal_onboarding_facade.py` (backend) — NEW FILE; service-layer unit tests. Do NOT modify existing Spec 213 `tests/services/test_portal_onboarding.py`; route-level coverage lives in `test_portal_onboarding.py`. | AC-10.1 (success path — full `BackstoryOption` snapshot round-trips all 6 fields), AC-10.2 (409 unknown `option_id` not found in cache scenarios), AC-10.3 (403 `cache_key` mismatch — computed vs supplied), AC-10.4 (idempotency — repeated call with same params returns same result without duplicate event emission) |
| `portal/src/app/onboarding/steps/__tests__/HandoffStep.test.tsx` | AC-NR4.1, AC-NR4.2, AC-NR4.3, AC-NR4.4, AC-NR5.1, AC-NR5.2, AC-NR5.3, AC-NR5.4, AC-NR5.5 |
| `portal/src/app/onboarding/hooks/__tests__/usePipelineReady.test.ts` | AC-5.1, AC-5.2, AC-5.3 — MUST use `jest.useFakeTimers()` + `jest.advanceTimersByTime()`. Mock only `fetch`/`apiClient` — never mock the hook under test. Cover all state transitions: pending→ready, pending→degraded, pending→failed, 20s hard cap. AC-5.5: assert `venueResearchStatus` return value equals `venue_research_status` from mock poll response; assert initial value before first poll is `''` or `'pending'`. |
| `portal/src/app/onboarding/components/__tests__/QRHandoff.test.tsx` | AC-NR4.1, AC-NR4.2, AC-NR4.3, AC-NR4.4 — note: QRHandoff is at `app/onboarding/components/`, not `components/onboarding/` |
| `portal/src/app/onboarding/__tests__/WizardCopyAudit.test.tsx` | AC-2.5, AC-3.1, AC-3.2 — also maps: AC-1.5 (static grep scan across all step component sources for `data-testid="wizard-step-` — mirrors AC-2.3 grep pattern at zero runtime cost), AC-2.2 (component identity assertion that `AuroraOrbs`/`FallingPattern` are same references as landing components, not re-implementations), AC-2.3 (negative grep on `style=` attributes in component sources), AC-2.4 (GlassCard import-path assertion) |
| `portal/src/app/onboarding/hooks/__tests__/useOnboardingAPI.test.ts` | AC-6.1, AC-6.2, AC-6.3, AC-7.1, AC-7.4, AC-9.2 (`selectBackstory` call on CTA click) — **Note**: this replaces the name `WizardAPIClient.test.ts` used in the PR 214-A artifact table; use `useOnboardingAPI.test.ts` as the canonical filename in both locations. |

### Playwright E2E Tests

| File | Scenarios Covered |
|------|-------------------|
| `portal/e2e/onboarding-wizard.spec.ts` | US-1 full happy path (step 1-11), US-6 backstory personalization, US-2 QR code desktop render and decode (assert `page.evaluate()` on step 11 QR element returns non-null and data encodes `https://t.me/Nikita_my_bot`) |
| `portal/e2e/onboarding-resume.spec.ts` | US-3 abandonment + resume (localStorage) |
| `portal/e2e/onboarding-phone-country.spec.ts` | US-4 unsupported country validation, US-5 voice fallback |

**Playwright note**: All wizard E2E tests use `waitForSelector('[data-testid="wizard-step-{N}"]')` — NOT `networkidle`. The pipeline gate test uses `waitForSelector('[data-testid="pipeline-gate-stamp"][data-state="ready"]', { timeout: 25000 })`.

---

## Open Questions

All questions below were resolved from the brief and target diagram. No `[NEEDS CLARIFICATION]` items remain.

| Question | Resolution |
|----------|-----------|
| How does portal persist `chosen_option_id` to backend? | FR-10.1: new `PUT /api/v1/onboarding/profile/chosen-option` endpoint, added as PR 214-D (backend sub-amendment). Idempotent + validates against `BackstoryCacheRepository`. |
| How does wizard detect cross-device resume (last completed step)? | FR-10.2: extend `PipelineReadyResponse` with optional `wizard_step: int \| None`, populated from `onboarding_profile.wizard_step` JSONB key. Non-breaking additive change. |
| Does PATCH /onboarding/profile exist? | Confirmed in brief ("Live endpoints" section). Portal calls PATCH for mid-wizard field updates. |
| What TypeScript type mirrors `PipelineReadyState`? | `type PipelineReadyState = "pending" \| "ready" \| "degraded" \| "failed"` — mirrored from `contracts.py` in `portal/src/app/onboarding/types/contracts.ts`. |
| Is `qrcode.react` already installed? | Not present in current `portal/package.json` scan. Must be added as new dependency in PR 214-A. |
| Is `libphonenumber-js` already installed? | Not confirmed. Must be added as new dependency in PR 214-A. |
| What are the ElevenLabs supported country codes? | Maintained in `portal/src/app/onboarding/constants/supported-phone-countries.ts`; populate from ElevenLabs/Twilio docs during PR 214-B implementation. |

---

## Appendix A — PR Decomposition (for /plan phase)

Four PRs, each ≤400 LOC soft cap. Portal components are typically 50-150 LOC each.

**Ordering**: PR 214-D (backend) → PR 214-A (portal foundation) → PR 214-B (components) → PR 214-C (E2E + deploy). PR 214-D must merge first because PR 214-A's TypeScript contract mirror depends on the new `BackstoryChoiceRequest` and extended `PipelineReadyResponse`. PRs 214-B and 214-C can be author-parallel after A merges.

### PR 214-D — Backend Sub-Amendment (≈200-250 LOC)

**Scope**: New endpoint + additive contract extension (FR-10). Backend-only.

| Artifact | Description |
|----------|-------------|
| `nikita/onboarding/contracts.py` | Add `BackstoryChoiceRequest` Pydantic model (additive). Extend `PipelineReadyResponse` with `wizard_step: int \| None = Field(default=None, ge=1, le=11)` (non-breaking). Update module docstring to note: "(Spec 214 additive extension: BackstoryChoiceRequest + PipelineReadyResponse.wizard_step)" — preserves frozen-contract intent while documenting extension. |
| `nikita/onboarding/tuning.py` | Add `CHOICE_RATE_LIMIT_PER_MIN: Final[int] = 10` and `PIPELINE_POLL_RATE_LIMIT_PER_MIN: Final[int] = 30` constants with docstrings. |
| `nikita/api/middleware/rate_limit.py` | Add `_ChoiceRateLimiter` (DatabaseRateLimiter subclass, `choice:` key prefix) and `choice_rate_limit` FastAPI dependency (see FR-10.1 rate limiting block). Add `_PipelineReadyRateLimiter` (30/min, `poll:` prefix) and `pipeline_ready_rate_limit` dependency for `GET /pipeline-ready/{user_id}`. Both 429 responses MUST include `Retry-After: 60` header. |
| `nikita/api/routes/portal_onboarding.py` | Add `PUT /profile/chosen-option` handler (see FR-10.1 handler pseudocode). Extend `get_pipeline_ready` to read `onboarding_profile.wizard_step` JSONB key. Apply `pipeline_ready_rate_limit` dependency to `GET /pipeline-ready/{user_id}`. |
| `nikita/services/portal_onboarding.py` | Add `PortalOnboardingFacade.set_chosen_option(user_id, chosen_option_id, cache_key, session) -> BackstoryOption`. Matches existing `process(user_id, profile, session)` and `generate_preview(user_id, request, session)` patterns — session injected by caller, never opened by facade. Validates via cache_key recompute (see FR-10.1 facade docstring). Writes full snapshot to `onboarding_profile.chosen_option`. Emits structured `onboarding.backstory_chosen` event. |
| `tests/api/routes/test_portal_onboarding.py` | AC-10.1..10.9 coverage (idempotency, cross-user 403, stale cache_key 404, unknown option_id 409, snapshot shape, event emission, wizard_step pass-through, 429 Retry-After header). AC-10.5 test MUST construct a full `BackstoryOption` fixture (all 6 fields: id, venue, context, the_moment, unresolved_hook, tone) and assert each field round-trips through the JSONB write. Also add negative-assertion tests that 403/422/409/404 response bodies contain NO name/age/occupation/phone/city substrings. **AC-5.6**: add test asserting `GET /pipeline-ready/{user_id}` returns HTTP 429 with `Retry-After: 60` header when `_PipelineReadyRateLimiter` limit (30/min) is exceeded. |
| `tests/services/test_portal_onboarding_facade.py` | **NEW FILE** — do NOT modify existing Spec 213 `tests/services/test_portal_onboarding.py`. Unit tests for `set_chosen_option` covering all validation branches: cache_key mismatch (403), unknown option_id (409), missing cache row (404), success path. |

### PR 214-A — Portal Foundation (≈300-350 LOC)

**Scope**: No visible UI changes. All plumbing.

| Artifact | Description |
|----------|-------------|
| `portal/src/app/onboarding/types/contracts.ts` | TypeScript mirror of `nikita/onboarding/contracts.py` types: `BackstoryOption`, `OnboardingV2ProfileRequest`, `OnboardingV2ProfileResponse`, `PipelineReadyResponse` (incl. new `wizard_step` optional), `BackstoryPreviewRequest`, `BackstoryPreviewResponse`, `PipelineReadyState`, **`BackstoryChoiceRequest`** (new from PR 214-D). **Note**: `contracts.ts` contains API shape interfaces only — no runtime validation. Zod validation lives in `schemas.ts`. Do NOT duplicate types. |
| `portal/src/app/onboarding/types/wizard.ts` | `WizardPersistedState`, `WizardStep` enum (3-11), `WizardFormValues` |
| `portal/src/app/onboarding/state/WizardStateMachine.ts` | Step transition guard, state enum, transition map |
| `portal/src/app/onboarding/state/WizardPersistence.ts` | `localStorage` read/write/clear with user-scoped key. Write `cache_key` from `BackstoryPreviewResponse` to localStorage alongside `chosen_option_id` on backstory card CTA click. |
| `portal/src/app/onboarding/hooks/use-onboarding-api.ts` | `useOnboardingAPI`: `previewBackstory`, `submitProfile`, `patchProfile`, `selectBackstory(chosen_option_id, cache_key)` (wraps PUT /profile/chosen-option) with `apiClient` wrappers |
| `portal/src/app/onboarding/hooks/use-pipeline-ready.ts` | `useOnboardingPipelineReady` poll hook |
| `portal/src/app/onboarding/constants/supported-phone-countries.ts` | ElevenLabs/Twilio supported country codes |
| `portal/package.json` | Add `qrcode.react`, `libphonenumber-js`; add `"prebuild": "tsc --noEmit"` script (enforces NFR-006 in Vercel CI — npm lifecycle runs `prebuild` automatically before `build`). The existing `"type-check": "tsc --noEmit"` script remains for local dev invocation. |
| `portal/src/lib/api/client.ts` | Extend `apiClient` helper `api` object with `patch<T>(path: string, body: unknown)` method matching existing `get/post/put` pattern: `patch: <T>(path, body) => apiClient<T>(path, { method: "PATCH", body: JSON.stringify(body) })`. Required for AC-6.3 consistency. |
| Unit tests | `WizardStateMachine.test.ts`, `WizardPersistence.test.ts`, `usePipelineReady.test.ts`, `useOnboardingAPI.test.ts` (canonical name — also referenced in Test File Inventory; `use-onboarding-api.ts` owns `withRetry` shared wrapper implementing 3-attempt exponential backoff (500ms/1000ms/2000ms); non-idempotent POST calls excluded from retry) |

### PR 214-B — Step Components + Dossier Styling (≈350-400 LOC)

**Scope**: All visible wizard UI. Steps 3-11 components.

| Artifact | Description |
|----------|-------------|
| `portal/src/app/onboarding/onboarding-wizard.tsx` | Replaces `onboarding-cinematic.tsx`; orchestrates step rendering + persistence + API calls. **DELETE** `portal/src/app/onboarding/onboarding-cinematic.tsx`, its `sections/` subdirectory, and any legacy unused components in this PR. |
| `portal/src/app/onboarding/steps/DossierHeader.tsx` | Step 3: classified-file header + metric bars |
| `portal/src/app/onboarding/steps/LocationStep.tsx` | Step 4: city input + inline venue preview |
| `portal/src/app/onboarding/steps/SceneStep.tsx` | Step 5: SceneSelector button grid |
| `portal/src/app/onboarding/steps/DarknessStep.tsx` | Step 6: EdginessSlider with live Nikita quotes |
| `portal/src/app/onboarding/steps/IdentityStep.tsx` | Step 7: name/age/occupation three-field dossier |
| `portal/src/app/onboarding/steps/BackstoryReveal.tsx` | Step 8: BackstoryChooser + loading + degraded path |
| `portal/src/app/onboarding/steps/PhoneStep.tsx` | Step 9: binary voice/text choice + tel input + country validation |
| `portal/src/app/onboarding/steps/PipelineGate.tsx` | Step 10: stamp animation + poll state machine UI |
| `portal/src/app/onboarding/steps/HandoffStep.tsx` | Step 11: voice ring UI + Telegram CTA + QRHandoff |
| `portal/src/app/onboarding/components/QRHandoff.tsx` | QR component (desktop-only render) — co-located with wizard-internal components, NOT `portal/src/components/onboarding/` |
| `portal/src/app/onboarding/components/DossierStamp.tsx` | Reusable stamp with typewriter animation. Typewriter reveal (CLEARED stamp) follows the `portal/src/components/landing/system-terminal.tsx` pattern (character-by-character reveal with 40ms tick) — import shared timing constant if one exists, else localize. Stamp-rotate animation (ANALYZED stamp) uses framer-motion `rotate: [0, -2, 2, 0]` transition. Both MUST have `prefers-reduced-motion` guard. |
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
| `portal/src/app/onboarding/page.tsx` | Update to render `OnboardingWizard` instead of `OnboardingCinematic`; resume detection from `?resume=true` param. AC: MUST use `supabase.auth.getUser()` for auth decisions and `getSession()` ONLY for token extraction (prevents session-spoofing regression from Spec 081). |
| `portal/src/lib/supabase/middleware.ts` | Add `pathname.startsWith("/onboarding/auth")` to the public-route block alongside `/login` and `/auth/*`. Without this, unauthenticated users (arriving at the magic-link step) are redirected to `/login` before they can request a link. |
| Vercel deploy | `cd portal && npm run build && vercel --prod` after PR merged to master. Pre-deploy checklist: verify `vercel.json` CSP `img-src` allows `data:` and `blob:` (required for qrcode.react canvas/SVG output if canvas mode is used). |
| `docs/content/magic-link-email.md` | Nikita-voiced copy for operator to paste into Supabase Dashboard email template; template config is a manual infra task tracked in PR 214-C checklist, not a code change |
| `portal/src/app/onboarding/loading.tsx` | Update from generic "Loading..." to Nikita-voiced copy (e.g., "ACCESSING FILE...") with dossier-style skeleton. This file is shown during route-segment Suspense loading — FR-3's zero-SaaS-copy rule applies. Copy should also be documented in `docs/content/wizard-copy.md`. |

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
BackstoryPreviewResponse (BaseModel)    →   interface BackstoryPreviewResponse { scenarios: BackstoryOption[], venues_used: string[], cache_key: string, degraded: boolean }
                                            // cache_key MUST be stored in wizard state between step 8 and PUT call — it is the required field of BackstoryChoiceRequest
PipelineReadyResponse (BaseModel)       →   interface PipelineReadyResponse { state: PipelineReadyState, message?: string | null, checked_at: string, venue_research_status: string, backstory_available: boolean, wizard_step?: number | null }
                                            // wizard_step NEW: FR-10.2. Read from onboarding_profile.wizard_step JSONB; None if not yet set.
BackstoryChoiceRequest (NEW, Spec 214)  →   interface BackstoryChoiceRequest { chosen_option_id: string; cache_key: string }
                                            // BackstoryChoiceRequest is the request body for PUT /profile/chosen-option (FR-10.1)
ErrorResponse (BaseModel)               →   interface ErrorResponse { detail: string }
                                            // Handler-raised errors (403, 404, 409, 429) use flat { detail: string }.
                                            // Pydantic 422 uses list { detail: [{loc, msg, type}] }. Portal must handle both shapes.
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

Backend endpoint reference for portal consumption. Endpoints marked (new, FR-10.1) and (extended, FR-10.2) are added by Spec 214 PR 214-D; all others are Spec 213 FROZEN contracts.

| Method | Path | Request | Response | Called at |
|--------|------|---------|----------|-----------|
| `POST` | `/api/v1/onboarding/profile` | `OnboardingV2ProfileRequest` | `OnboardingV2ProfileResponse` | Step 10 |
| `PATCH` | `/api/v1/onboarding/profile` | Partial `OnboardingV2ProfileRequest` | `OnboardingV2ProfileResponse` | Steps 4-9 (fire-and-forget) |
| `POST` | `/api/v1/onboarding/preview-backstory` | `BackstoryPreviewRequest` | `BackstoryPreviewResponse` | Step 8 |
| `PUT` | `/api/v1/onboarding/profile/chosen-option` | `BackstoryChoiceRequest` **(new, FR-10.1)** | `OnboardingV2ProfileResponse` | Step 8 (after card selection CTA) |
| `GET` | `/api/v1/onboarding/pipeline-ready/{user_id}` | — | `PipelineReadyResponse` **(extended with `wizard_step`, FR-10.2)** | Steps 10-11 (poll); also resume detection |
