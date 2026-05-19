# Frontend Validation Report

**Spec:** `specs/214-portal-onboarding-wizard/spec.md`
**Status:** PASS
**Timestamp:** 2026-04-15T15:10:00Z
**Validator:** sdd-frontend-validator
**Iteration:** 3 (re-validation after commit 1caaea8)

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH     | 0 |
| MEDIUM   | 0 |
| LOW      | 0 |

**Gate result:** PASS — zero findings across all severities. Spec is ready for planning.

---

## Iter-2 Finding — Disposition

| Iter-2 Severity | Finding | Status |
|----------------|---------|--------|
| LOW-1 | `DossierStamp.tsx` spec row referenced non-existent path `portal/src/components/system/system-terminal.tsx` | RESOLVED in commit 1caaea8 — corrected to `portal/src/components/landing/system-terminal.tsx` (verified: file exists at that path) |

---

## Commit 1caaea8 — New Additions Reviewed

The following additions were introduced in 1caaea8 and reviewed for secondary issues:

| Change | Verdict |
|--------|---------|
| AC-8.1: state transition guard returns `{ ok: false, reason: "INVALID_ORDER" }` instead of throwing | Correct — caller-rendered error pattern, no throw-propagation risk |
| AC-9.5 refactored to cross-reference AC-4.5 | Correct — avoids duplication, no information lost |
| Rate limit spec changed from `voice_rate_limit` (5/min, vague) to `choice_rate_limit` (10/min, `_ChoiceRateLimiter`) | Correct — fully specified with pseudocode and `CHOICE_RATE_LIMIT_PER_MIN` constant |
| `_ChoiceRateLimiter._get_day_window()` override added | Correct — matches `_PreviewRateLimiter` pattern; both `_get_minute_window` and `_get_day_window` now present |
| `limiter.check(current_user_id)` (bare UUID) instead of `f"user:{current_user_id}"` | Correct — `choice:` isolation is in `_get_minute_window`, no double-prefix risk |
| `_PipelineReadyRateLimiter` full pseudocode added with `_get_minute_window` + `_get_day_window` + handler signature | Correct — symmetric with `_ChoiceRateLimiter`; AC-5.6 now has a complete implementation spec |
| `pipeline_ready_rate_limit` dependency added to `get_pipeline_ready` handler signature | Correct — implements AC-5.6 |
| AC-5.6 test row inserted into Test File Inventory (standalone `tests/api/routes/test_portal_onboarding.py` row) | Correct — not a duplication; line 830 states the specific new assertion, line 882 shows full PR 214-D test file scope. Consistent. |
| AC-NR1.5 added to `WizardPersistence.test.ts` row | Correct — AC-NR1.5 was specified in FR-NR1; now has test coverage assignment |
| AC-4.5 added to `BackstoryReveal.test.tsx` row | Correct — AC-4.5 was specified in FR-4; now has test coverage assignment |
| AC-NR5.5 added to `HandoffStep.test.tsx` row | Correct — AC-NR5.5 was specified in NR-5; now has test coverage assignment |
| AC-2.5 added to `WizardCopyAudit.test.tsx` row | Correct — AC-2.5 was specified in FR-2; now has test coverage assignment |
| `WizardPersistence.ts` table row updated: write `cache_key` from `BackstoryPreviewResponse` to localStorage | Correct — `cache_key` was already in `WizardPersistedState` type (line 494); `WizardPersistence.ts` description now explicitly covers it |
| `contracts.ts` row note added: "API shape interfaces only — no runtime validation. Zod lives in `schemas.ts`. Do NOT duplicate types." | Correct — prevents a common implementor error (Zod in contracts.ts) |
| `onboarding-wizard.tsx` row updated: DELETE `onboarding-cinematic.tsx` + `sections/` in PR 214-B | Correct — prevents dead code accumulation; no scope expansion |
| Out-of-scope note 3 expanded with `user_profiles` RLS gap detail | Backend scope note — does not affect frontend validation |
| Appendix D updated: marks FR-10.1 (new) and FR-10.2 (extended) endpoints correctly | Correct — Appendix D is now accurate vs. spec 213 frozen contracts |

---

## Findings

No findings.

---

## Component Inventory

| Component | Type | Shadcn / Library | Notes |
|-----------|------|-----------------|-------|
| `OnboardingWizard` | Custom | Orchestrator — no direct Shadcn | Replaces `OnboardingCinematic`; `"use client"` required |
| `WizardStateMachine` | Custom TS class | None | Step transition guard returns `{ ok: false, reason }` (no throw) |
| `WizardPersistence` | Custom utility | None | localStorage read/write/clear; writes `cache_key` alongside `chosen_option_id`; `useEffect`-gated reads |
| `DossierHeader` | Custom step | GlassCard, metric bar pattern | Step 3; real UserMetrics from server props |
| `LocationStep` | Custom step | GlassCard, Input (shadcn), FormField | Step 4; 800ms debounce on blur; inline venue preview via city-only POST |
| `SceneStep` | Custom step | SceneSelector (existing Radix RadioGroup) | Step 5; reuses existing component; derives `life_stage` |
| `DarknessStep` | Custom step | EdginessSlider (existing Radix Slider) | Step 6; live Nikita quote updates |
| `IdentityStep` | Custom step | GlassCard, Input (shadcn), FormField | Step 7; name/age (18-99)/occupation (max 100) optional |
| `BackstoryReveal` | Custom step | GlassCard, BackstoryChooser | Step 8; POST + radio card grid; focus to first card after load |
| `BackstoryChooser` | Custom | Radix RadioGroup.Root + Item | `role="radiogroup"`, `aria-checked` (NOT `aria-selected`); matches SceneSelector pattern |
| `PhoneStep` | Custom step | GlassCard, Input (shadcn, type=tel) | Step 9; libphonenumber-js validation; country pre-flight |
| `PipelineGate` | Custom step | DossierStamp, framer-motion | Step 10; `setInterval` poll loop |
| `HandoffStep` | Custom step | QRHandoff, shadcn Button (link variant) | Step 11; voice ring or Telegram CTA; `aria-live` region for voice fallback |
| `QRHandoff` | Custom component | qrcode.react (new dep) | Desktop-only; `<figure>` + `<figcaption>`; `useMediaQuery(defaultValue:false)` |
| `DossierStamp` | Custom component | framer-motion | Typewriter (CLEARED); rotate (ANALYZED); `prefers-reduced-motion` guard; reference: `portal/src/components/landing/system-terminal.tsx` |
| `WizardProgress` | Custom component | None | "FIELD N OF 7" text label |
| `GlowButton` | Existing landing | None (motion.div + Link) | `href`-only; forbidden on step-advance CTAs (AC-2.5) |
| `GlassCard` | Existing component | None (CSS class pattern) | Import from `portal/src/components/glass/glass-card.tsx` |
| `AuroraOrbs` | Existing landing | None | Import unchanged from `portal/src/components/landing/` |
| `FallingPattern` | Existing landing | None | Import unchanged from `portal/src/components/landing/` |
| `useOnboardingPipelineReady` | Custom hook | None | `setInterval` poll; `hooks/use-pipeline-ready.ts`; all state transitions covered |
| `useOnboardingAPI` | Custom hook | None | Wraps apiClient; owns `withRetry` (3-attempt, 500ms/1s/2s); POST excluded from retry |

---

## Accessibility Checklist

- [x] ARIA labels specified for interactive components
- [x] `aria-invalid` + `aria-describedby` on form error states — NFR-002
- [x] `aria-live="polite"` + `role="status"` on pipeline gate stamp — NFR-002
- [x] `aria-live="polite"` + `role="status"` on voice ring fallback region — AC-NR5.5
- [x] Keyboard navigation: Tab + Enter/Space for CTAs — NFR-002
- [x] Focus management on step advance — NFR-002
- [x] Focus management for BackstoryChooser cards after step 8 POST — AC-4.5, AC-9.5
- [x] `prefers-reduced-motion` for all stamp animations — NFR-002, Appendix C
- [x] BackstoryChooser: `role="radiogroup"` + `role="radio"` + `aria-checked` — AC-9.4
- [x] QRHandoff: `<figure>` + `<figcaption>` (no canvas aria-label) — AC-NR4.4
- [x] `data-testid` on all wizard steps and key elements — AC-1.5, AC-5.4, AC-NR3.3, AC-NR5.4
- [x] Voice ring degraded state announced via `aria-live` region — AC-NR5.5
- [x] `loading.tsx` updated to Nikita-voiced copy — PR 214-C
- [x] No focus trap needed — full-page flow, not a modal

---

## Responsive Design Checklist

- [x] Breakpoints specified: 375px, 768px, 1280px, 1920px — NFR-003
- [x] Mobile-first approach — NFR-003
- [x] Touch targets >= 44px — NFR-003
- [x] QRHandoff hidden below 768px (`md:hidden`) — AC-NR4.1
- [x] Ring animation scales at all viewports — NFR-003
- [x] All step content scrollable on 375px without horizontal overflow — NFR-003
- [~] BackstoryChooser card grid column count at 768px unspecified — informational only; NFR-003 general responsiveness requirement covers it; implementor discretion within that constraint

---

## Tailwind Token / Dark Mode Checklist

- [x] `bg-void` / `bg-void-ambient` tokens — confirmed in `portal/tailwind.config.ts`
- [x] `text-primary` / `border-primary` / `bg-primary` = oklch rose — confirmed
- [x] Dark-only design — no `dark:` variants introduced — NFR-004
- [x] No inline styles — AC-2.3, NFR-004
- [x] `GlassCard` import from `portal/src/components/glass/glass-card.tsx` — AC-2.4
- [x] `EASE_OUT_QUART` easing token — confirmed in codebase

---

## Form Validation Checklist

- [x] `react-hook-form` + `zodResolver` specified — FR-1
- [x] Existing `profileSchema` in `schemas.ts` covers primary fields
- [x] New fields: name (text), age (18-99), occupation (max 100) — NR-2; `schemas.ts` extension in PR 214-C
- [x] E164_PHONE_REGEX reused — NR-3 / AC-NR3.2
- [x] Phone country validation before country-support check — AC-NR3.2
- [x] Error messages in Nikita voice — FR-3, AC-3.3
- [x] CTA disabled until step validation passes — AC-1.2
- [x] `life_stage` derived from SceneSelector (not a separate field) — NR-1a

---

## React 19 / Next.js 16 Pattern Checklist

- [x] `"use client"` required on wizard orchestrator and all step components
- [x] Page component stays Server Component
- [x] `history.replaceState` for back-nav prevention — AC-1.3
- [x] No Pages Router patterns
- [x] `setInterval` for poll loop (not recursive `setTimeout`) — AC-5.1
- [x] localStorage reads are `useEffect`-gated — AC-NR1.5
- [x] `useMediaQuery(defaultValue:false)` for QR hydration — NR-4
- [x] `supabase.auth.getUser()` for auth decisions (not `getSession()`) — PR 214-C page.tsx note

---

## Performance Checklist

- [x] Step transitions <= 200ms — NFR-001
- [x] Bundle size cap: +50KB gzipped — NFR-001
- [x] POST /preview-backstory frontend timeout: 4s degraded path — NFR-001
- [x] API retry: 3 attempts 500ms/1000ms/2000ms; POST excluded — `use-onboarding-api.ts` `withRetry`
- [x] Non-idempotent POST calls NOT retried — NFR-001

---

## Pass/Fail Decision

**Status: PASS**

Zero findings across all severities (CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0).

The iter-2 LOW finding (wrong path for `system-terminal.tsx` reference in DossierStamp spec row) is confirmed resolved in commit 1caaea8. All 13 additional changes in that commit were reviewed; none introduce new frontend specification gaps.

GATE 2 frontend validation is cleared. The spec is ready to proceed to planning.
