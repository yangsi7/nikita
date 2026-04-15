## Architecture Validation Report

**Spec:** `specs/214-portal-onboarding-wizard/spec.md`
**Status:** PASS
**Timestamp:** 2026-04-15T00:00:00Z
**Validator:** sdd-architecture-validator
**Iteration:** 3 (re-validation of iter-2 fixes, commit 1caaea8)

---

### Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 0 |
| LOW | 0 |

**Verdict: PASS** — 0 findings across all severities. Spec cleared for planning phase.

---

### Iter-2 Finding Resolution

| Finding | Iter-2 Severity | Resolution |
|---------|----------------|------------|
| `WizardStateMachine` guard throws on invalid order with no documented catch path | LOW | FIXED — AC-8.1 (line 263) now reads "returns an error state (`{ ok: false, reason: 'INVALID_ORDER' }`) instead of throwing; caller renders an inline Nikita-voiced error and does not advance." No error boundary required; caller handles the error state inline. |
| No explicit deletion instruction for `onboarding-cinematic.tsx` | LOW | FIXED — PR 214-B artifact table (line 908) now reads "**DELETE** `portal/src/app/onboarding/onboarding-cinematic.tsx`, its `sections/` subdirectory, and any legacy unused components in this PR." Explicit directive present. |
| `_ChoiceRateLimiter.check()` pseudocode key format inconsistent with `_PreviewRateLimiter` pattern | LOW | FIXED — Line 395 now reads `await limiter.check(current_user_id)  # bare UUID; 'choice:' isolation is in _get_minute_window()`. `_PipelineReadyRateLimiter` (line 444) also uses bare UUID. Both match the established `_PreviewRateLimiter` pattern exactly. |
| `contracts.ts` vs `schemas.ts` role not disambiguated in artifact description | LOW | FIXED — PR 214-A artifact table (line 891) now includes: "**Note**: `contracts.ts` contains API shape interfaces only — no runtime validation. Zod validation lives in `schemas.ts`. Do NOT duplicate types." Disambiguation embedded in spec's implementation guide for implementors. |

---

### Findings

None. Zero findings across all severities.

---

### Proposed Structure

```
portal/src/app/onboarding/
├── page.tsx                          # Server component: auth + resume detection
├── loading.tsx                       # Nikita-voiced Suspense skeleton ("ACCESSING FILE...")
├── onboarding-wizard.tsx             # Client component: step orchestrator
├── onboarding-cinematic.tsx          # DELETE in PR 214-B (and sections/ subdirectory)
├── schemas.ts                        # EXTENDED in PR 214-C: + name, age, occupation, wizard_step zod fields
├── types/
│   ├── contracts.ts                  # TypeScript mirror of nikita/onboarding/contracts.py
│   │                                   # Note (in artifact desc): "API shape interfaces only —
│   │                                   # no runtime validation. Zod validation lives in schemas.ts."
│   └── wizard.ts                     # WizardPersistedState, WizardStep enum, WizardFormValues
├── state/
│   ├── WizardStateMachine.ts         # Step transition guard — returns { ok: false, reason } NOT throw
│   └── WizardPersistence.ts          # localStorage read/write/clear; readPersistedState() for useEffect only
├── hooks/
│   ├── use-onboarding-api.ts         # previewBackstory, submitProfile, patchProfile, selectBackstory
│   │                                   # withRetry wrapper (3 attempts, 500/1000/2000ms; POST excluded)
│   └── use-pipeline-ready.ts         # Poll hook: setInterval-based, all state transitions
├── constants/
│   └── supported-phone-countries.ts  # ElevenLabs/Twilio supported country codes list
├── components/
│   ├── DossierStamp.tsx              # Stamp with typewriter + rotate animations; prefers-reduced-motion guard
│   ├── WizardProgress.tsx            # "FIELD N OF 7" label
│   └── QRHandoff.tsx                 # QR component; useMediaQuery(defaultValue: false) for SSR safety
├── steps/
│   ├── DossierHeader.tsx             # Step 3
│   ├── LocationStep.tsx              # Step 4
│   ├── SceneStep.tsx                 # Step 5
│   ├── DarknessStep.tsx              # Step 6
│   ├── IdentityStep.tsx              # Step 7
│   ├── BackstoryReveal.tsx           # Step 8
│   ├── PhoneStep.tsx                 # Step 9
│   ├── PipelineGate.tsx              # Step 10
│   └── HandoffStep.tsx               # Step 11
└── __tests__/
    ├── WizardStateMachine.test.ts
    ├── WizardPersistence.test.ts
    ├── WizardCopyAudit.test.tsx
    └── hooks/
        ├── useOnboardingAPI.test.ts
        └── usePipelineReady.test.ts

portal/src/components/onboarding/    # (voided — QRHandoff lives at app/onboarding/components/)
portal/src/lib/api/client.ts         # EXTEND: add api.patch<T>() method in PR 214-A

nikita/api/routes/portal_onboarding.py   # ADD: PUT /profile/chosen-option handler
                                          # EXTEND: get_pipeline_ready reads wizard_step JSONB
                                          # APPLY: pipeline_ready_rate_limit dependency
nikita/onboarding/contracts.py           # ADD: BackstoryChoiceRequest
                                          # EXTEND: PipelineReadyResponse.wizard_step
nikita/services/portal_onboarding.py    # ADD: PortalOnboardingFacade.set_chosen_option()
nikita/api/middleware/rate_limit.py      # ADD: _ChoiceRateLimiter, choice_rate_limit
                                          # ADD: _PipelineReadyRateLimiter, pipeline_ready_rate_limit
nikita/onboarding/tuning.py              # ADD: CHOICE_RATE_LIMIT_PER_MIN, PIPELINE_POLL_RATE_LIMIT_PER_MIN
```

---

### Module Dependency Graph

```
portal/src/app/onboarding/
  page.tsx (Server)
    └── onboarding-wizard.tsx (Client)
          ├── state/WizardStateMachine.ts        (pure TS, no React deps; returns error state, not throw)
          ├── state/WizardPersistence.ts         (pure TS, window.localStorage)
          │     readPersistedState() called ONLY from useEffect (AC-NR1.5)
          ├── hooks/use-onboarding-api.ts
          │     └── @/lib/api/client.ts          (existing + new api.patch)
          ├── hooks/use-pipeline-ready.ts
          │     └── @/lib/api/client.ts
          ├── types/contracts.ts                  (zero imports — plain interfaces)
          ├── types/wizard.ts                     (zero imports — plain types)
          ├── constants/supported-phone-countries.ts (zero imports)
          ├── components/DossierStamp.tsx
          ├── components/WizardProgress.tsx
          ├── components/QRHandoff.tsx            (client-only, useMediaQuery defaultValue: false)
          └── steps/*.tsx
                ├── types/contracts.ts
                └── @/components/landing/{AuroraOrbs,FallingPattern,GlowButton}
                    @/components/glass/glass-card
                    @/components/ui/*

nikita/ (backend, PR 214-D)
  onboarding/contracts.py
    ← api/routes/portal_onboarding.py (route handler)
    ← services/portal_onboarding.py (PortalOnboardingFacade)
         ← db/repositories/backstory_cache_repository.py (existing)
         ← db/repositories/user_repository.py (existing — for cache_key recompute)

  api/middleware/rate_limit.py
    DatabaseRateLimiter (from platforms/telegram/rate_limiter.py)
    ├── _PreviewRateLimiter (existing, Spec 213)
    ├── _ChoiceRateLimiter  (new, Spec 214 FR-10.1)
    │     check(bare_uuid); key: choice:minute:{YYYY-MM-DD-HH-MM} — isolated from preview namespace
    └── _PipelineReadyRateLimiter (new, Spec 214 FR-10.1)
          check(bare_uuid); key: poll:minute:{YYYY-MM-DD-HH-MM}
```

No circular dependencies. `contracts.ts` has zero imports by design. `WizardStateMachine.ts` has zero React imports (pure TypeScript, safe to test without JSDOM).

---

### Separation of Concerns Analysis

| Layer | Responsibility | Files | Violations |
|-------|---------------|-------|------------|
| Server Component | Auth, redirect, resume detection | `page.tsx` | None |
| State Orchestrator | Step sequencing, form state, persistence coordination | `onboarding-wizard.tsx` | None |
| State Machine | Transition rules, step ordering guard — returns error state, not throw | `state/WizardStateMachine.ts` | None |
| Persistence | localStorage read/write/clear | `state/WizardPersistence.ts` | None — `readPersistedState()` restricted to `useEffect` (AC-NR1.5) |
| API Hooks | HTTP calls, retry logic, error handling, loading state | `hooks/use-onboarding-api.ts`, `hooks/use-pipeline-ready.ts` | None |
| Step Components | View-only: render field, emit events up | `steps/*.tsx` | None |
| Shared UI Components | Wizard-internal reusable visual primitives | `components/DossierStamp.tsx`, `WizardProgress.tsx`, `QRHandoff.tsx` | None |
| Contract Types | API shape definitions (no logic, no imports) | `types/contracts.ts` | None — role vs `schemas.ts` disambiguated in artifact description |
| Backend Route | HTTP request parsing + response shaping | `nikita/api/routes/portal_onboarding.py` | None |
| Backend Facade | Validate + persist + emit event | `nikita/services/portal_onboarding.py` | None |
| Rate Limiters | Per-endpoint, per-user rate limiting | `nikita/api/middleware/rate_limit.py` | None — key format consistency confirmed |

---

### Import Pattern Checklist

- [x] TypeScript path alias `@/*` maps to `./src/*` in `portal/tsconfig.json`
- [x] All proposed new files in `portal/src/app/onboarding/` import shared components via `@/components/...`
- [x] `types/contracts.ts` is zero-import (plain interfaces only) — prevents accidental coupling to runtime modules
- [x] `state/WizardStateMachine.ts` has no React imports — pure TypeScript module, safe to test without JSDOM
- [x] `state/WizardPersistence.ts` exports only `readPersistedState()` for use in `useEffect` only (AC-NR1.5)
- [x] `hooks/use-pipeline-ready.ts` imports only from `types/contracts.ts` and `@/lib/api/client` — no step-level coupling
- [x] `api.patch` method added to `@/lib/api/client.ts` in PR 214-A — consistent with `get/post/put/delete` pattern
- [x] `QRHandoff` is client-only; `useMediaQuery(defaultValue: false)` prevents SSR hydration mismatch
- [x] `_ChoiceRateLimiter.check()` and `_PipelineReadyRateLimiter.check()` both pass bare UUID — consistent with `_PreviewRateLimiter` pattern

---

### Security Architecture

- [x] `localStorage` key is user-scoped: `nikita_wizard_{user_id}` — prevents cross-user state leakage on shared devices (AC-NR1.4)
- [x] `wizard_step` JSONB value is internal state only; never rendered directly to DOM (XSS risk flagged and mitigated, line 499)
- [x] Structured log event `onboarding.backstory_chosen` emits tone/venue only — no user-provided PII (AC-10.6). Negative-assertion tests required (AC-10.5 note)
- [x] `BackstoryChoiceRequest.cache_key` guards against stale selections (ownership via cache_key recompute — no `user_id` column on `backstory_cache`). 403 on mismatch (AC-10.3)
- [x] `PUT /profile/chosen-option` validates via `(user_id, cache_key, chosen_option_id)` triple — no IDOR risk
- [x] PATCH is fire-and-forget but JWT-authenticated (same `apiClient` with Bearer token)
- [x] Both new rate limiters include `Retry-After: 60` header on 429 per RFC 6585 (AC-10.9, AC-5.6)
- [x] `readPersistedState()` restricted to `useEffect` — no server-side localStorage access (SSR safety, AC-NR1.5)
- [x] `page.tsx` uses `supabase.auth.getUser()` for auth decisions and `getSession()` only for token extraction (prevents session-spoofing regression from Spec 081, line 934)
- [x] `qrcode.react` CSP requirement documented: `img-src data: blob:` in `vercel.json` for canvas/SVG mode (line 936)
- [x] `portal/src/lib/supabase/middleware.ts` public-route block updated to include `/onboarding/auth` — prevents unauthenticated redirect loop at magic-link step (line 935)

One nuance unchanged from iter-2: `WizardPersistedState` stores `phone` in localStorage. Mild PII, consistent with form-persistence patterns, cleared on completion (AC-NR1.3). Acceptable.

---

### PR Decomposition Dependency Validation

| PR | Depends On | Dependency Correct? | Notes |
|----|-----------|---------------------|-------|
| 214-D (backend) | Spec 213 (deployed) | Yes | Additive only: `BackstoryChoiceRequest` + `PipelineReadyResponse.wizard_step` + `PUT` route + two new rate limiters |
| 214-A (portal foundation) | 214-D merged | Yes | `contracts.ts` needs `BackstoryChoiceRequest` + extended `PipelineReadyResponse`; `api.patch` added |
| 214-B (step components) | 214-A merged | Yes | Steps consume WizardStateMachine, hooks, types from 214-A; deletion of `onboarding-cinematic.tsx` here |
| 214-C (E2E + deploy) | 214-B merged | Yes | E2E tests require full UI from 214-B; `schemas.ts` extension here |

Dependency ordering correct. PRs 214-B and 214-C can be authored in parallel after 214-A merges. LOC estimates (≤400 soft cap per PR): 214-D ≈200-250, 214-A ≈300-350, 214-B ≈350-400, 214-C ≈150-200. All within bounds.

---

### Architecture Alignment with Existing Codebase

| Check | Finding | Status |
|-------|---------|--------|
| App Router conventions | New files in `portal/src/app/onboarding/` follow co-location pattern; server page + client wizard matches existing pattern | Pass |
| `@/` alias usage | All proposed imports use `@/components/...`, `@/lib/api/client` — consistent with existing code | Pass |
| `apiClient` + `api.patch` | `api.patch` added to existing `api` object — one-line addition consistent with `get/post/put/delete` pattern | Pass |
| QRHandoff placement | Co-located at `app/onboarding/components/` — all onboarding-specific components together | Pass |
| Backend repository pattern | `PortalOnboardingFacade.set_chosen_option` uses existing `BackstoryCacheRepository` + `UserRepository` — no new repositories | Pass |
| Rate limiter pattern | `_ChoiceRateLimiter` and `_PipelineReadyRateLimiter` subclass `DatabaseRateLimiter`; both call `check(bare_uuid)` matching `_PreviewRateLimiter` | Pass |
| Contracts module isolation | `nikita/onboarding/contracts.py` docstring extended to note Spec 214 additive extensions — frozen-contract intent preserved | Pass |
| `PipelineReadyResponse.wizard_step` non-breaking | `ge=1, le=11` with `default=None` — non-breaking confirmed | Pass |
| WizardStateMachine error handling | Guard returns `{ ok: false, reason }` — no unhandled throw; caller renders inline Nikita-voiced error | Pass |
| Explicit legacy deletion | PR 214-B artifact table includes explicit DELETE directive for `onboarding-cinematic.tsx` and `sections/` | Pass |
| SSR hydration safety | AC-NR1.5: `readPersistedState()` restricted to `useEffect`; `QRHandoff` uses `useMediaQuery(defaultValue: false)` | Pass |
| `contracts.ts` / `schemas.ts` disambiguation | Artifact description (line 891) explicitly states role separation; no type duplication expected | Pass |

---

### Recommendations

None. All iter-2 findings resolved. No new gaps detected.
