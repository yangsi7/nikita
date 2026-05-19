# Frontend Validation Report — ITERATION 2

**Spec:** `specs/216-onboarding-redesign-cinematic/subspecs/216-C-cinematic-frontend/spec.md`
**Master:** `specs/216-onboarding-redesign-cinematic/spec.md` (FR cross-ref + §HTTP API Contracts)
**Wireframes:** `wireframes/{ascii.md, figma.md, motion-spec.md}`
**Status:** **PASS**
**Iteration:** 2 (re-validation after spec patches addressing iteration 1's 4 HIGH + 5 MED + 2 LOW)
**Timestamp:** 2026-04-29

---

## Summary

| Severity | Iter 1 | Iter 2 | Delta |
|----------|--------|--------|-------|
| CRITICAL | 0      | 0      | —     |
| HIGH     | 4      | **0**  | -4 (all CLOSED) |
| MEDIUM   | 5      | 0      | -5 (all CLOSED) |
| LOW      | 2      | 0      | -2 (CLOSED) |

**Verdict:** Zero blocking findings. Subspec 216-C is GATE-2 ready for implementation planning. PASS.

---

## Iteration 1 → Iteration 2 Closure Verification

### HIGH Findings — all CLOSED

| Iter-1 Finding | Resolution | Where Verified |
|----------------|-----------|----------------|
| **HIGH-1**: A11y contracts vague — only "WCAG 2.1 AA" stated; no per-control ARIA / keyboard / focus-mgmt / touch-target specs. | **CLOSED** by AC C1.12. Per-control contracts now codified: `HobbyChips` (`role="group"` + `aria-pressed` chips + `role="combobox"` autocomplete + `aria-live` count); `BackstoryArchetypeCards` (Radix `RadioGroup`, `role="radio"` + roving tabindex); `controls/Slider` (Radix `<Slider>`, `aria-valuetext`); `controls/Tel` (`inputMode="tel"`, `autocomplete="tel"`, `aria-describedby`, `aria-invalid`); `ProgressRail` (`role="progressbar"` + `aria-valuenow/min/max` + `aria-label`); `NikitaReaction` (`aria-live="polite" aria-atomic="true"` + reduced-motion instant fill); `WizardShell` focus auto-moves to `<h1 tabIndex={-1}>`, ESC blocked, Tab order documented; `focus-visible:ring` on GlowButton/chips/cards; `<main id="wizard">` landmark; ≥44px mobile touch targets on all multi-tap surfaces. | spec.md AC C1.12 |
| **HIGH-2**: AC C1.6 "+ other" 40-char rule was warn-only, no `maxLength` — implementation could ship without enforcement. | **CLOSED** by AC C1.6. Now: `maxLength=40` hard cap, inline `${len}/40` helper, rose at len ≥35, trim leading/trailing whitespace pre-submit, reject empty-after-trim. Explicit "Resolves frontend-validator HIGH-2" annotation in AC. | spec.md AC C1.6 |
| **HIGH-3**: City-slot Aceternity/Magicui inputs + 3-chip suggestion row mentioned in wireframes but NO component listed in Critical Files — would silently get cut. | **CLOSED**. `controls/CityInput.tsx` (Aceternity `placeholders-and-vanish-input` + Magicui `text-shimmer`), `SuggestionChips.tsx`, `PersonalizingBadge.tsx`, `BackLink.tsx`, `NikitaThinkingDots.tsx`, `FallingPattern.tsx` (REUSED) all now enumerated in Critical Files with explicit "closes frontend-validator HIGH-3" annotations. | spec.md Critical Files L56-61 |
| **HIGH-4**: Auth guard on `/onboarding` unspecified — risked client-side flicker → redirect race; magic-link second-click idempotency undefined. | **CLOSED** by AC C1.13. `/onboarding/page.tsx` is a Server Component reading `nikita-session` cookie via Next.js `cookies()` API; missing/expired JWT → `redirect('/onboarding/auth')` BEFORE any client component mounts; `WizardShell` never sees unauthenticated render; second-click idempotency delegated to master spec §HTTP API Contracts (302 if live, 400 if not — verified to exist at master spec L194-302 with `magic_link_consumed` error code); 0-hydration-mismatch verification via `read_console_messages`. | spec.md AC C1.13; master L194-302 |

### MEDIUM Findings — all CLOSED

| Iter-1 Finding | Resolution |
|----------------|-----------|
| **MED-1**: Pending/error UI states unspecified (Continue submit → spinner; >2s → thinking dots; 4xx banner; cost_circuit silent fallback). | **CLOSED** by AC C1.14: full state matrix codified including 401-redirect carve-out and `meta.fallback_reason="cost_circuit"` silent fallback (matches master spec L235, L280). |
| **MED-2**: Resume mid-wizard UX (NR-07) ambiguous — Q4 left "Welcome back banner OR silent" undecided. | **CLOSED** by AC C1.15: silent resume via `GET /api/v1/onboarding/state` (master spec L245), `ProgressRail` animates 0 → resumed_pct, `NikitaReaction` renders resumed reaction or "welcome back" greeting on first hydrated turn. NO banner. |
| **MED-3**: AnimatePresence `key` collision risk on dynamic follow-ups sharing `slot_kind`. | **CLOSED** by AC C1.16: `<motion.div key={turn_id}>` — `turn_id` is server-issued UUID per turn; documented in motion-spec.md. |
| **MED-4**: ProgressRail spring under reduced-motion would still bounce. | **CLOSED** by AC C1.17: `useReducedMotion()` true → linear 0.2s transition; monotonic; no overshoot. |
| **MED-5**: Banned vocab regex was string-match, not word-boundary — would false-flag e.g. "PROFILE" containing "FILE". | **CLOSED** by AC C1.11: regex tightened to `\b(dossier\|clearance)\b\|\b(FILE\|FIELD)\b` with explicit "word-boundary; uppercase-only for FILE/FIELD" annotation. |

### LOW Findings — all CLOSED

| Iter-1 Finding | Resolution |
|----------------|-----------|
| **LOW-1**: Vitest coverage gap on a11y assertions. | Implicitly closed: `__tests__/HobbyChips.test.tsx`, `BackstoryArchetypeCards.test.tsx`, `WizardShell.test.tsx`, `ProgressRail.test.tsx`, `NikitaReaction.test.tsx` now testable against the explicit ARIA contracts in C1.12 — no spec-side gap remains. |
| **LOW-2**: Q4 (resume UX) blocking. | Closed by AC C1.15 superseding Q4. |

---

## Component Inventory (Iteration 2 — final)

| Component | Type | Source | A11y Contract | Status |
|-----------|------|--------|---------------|--------|
| `WizardShell` | NEW | 216-C | Focus auto-mgmt, landmark `<main>`, ESC blocked, Tab order | spec'd |
| `QuestionCard` | NEW | 216-C | Glass surface; passive | spec'd |
| `ProgressRail` | NEW | 216-C | `role="progressbar"` + `aria-valuenow/min/max/label` + reduced-motion swap | spec'd |
| `NikitaReaction` | NEW | 216-C | `aria-live="polite" aria-atomic="true"` typewriter | spec'd |
| `WhyWeAsk` | NEW | 216-C | Expandable helper | spec'd |
| `HobbyChips` | NEW | 216-C | `role="group"` + `aria-pressed` chips + `role="combobox"` + live-region count + 44px touch + 40-char hard cap | spec'd |
| `BackstoryArchetypeCards` | NEW | 216-C | Radix `RadioGroup`, `role="radio"` + roving tabindex + 44px touch | spec'd |
| `controls/TextInput` | NEW | 216-C | Native `<input>` | spec'd |
| `controls/Slider` | NEW | 216-C | Radix `<Slider>` + `aria-valuetext` | spec'd |
| `controls/Chips` | NEW | 216-C | Same a11y pattern as HobbyChips | spec'd |
| `controls/Scenarios` | NEW | 216-C | 3-card option, `role="radiogroup"` | spec'd |
| `controls/Radio` | NEW | 216-C | Native `<input type="radio">` group | spec'd |
| `controls/Tel` | NEW | 216-C | `inputMode="tel"` + `autocomplete="tel"` + `aria-describedby` + `aria-invalid` | spec'd |
| `controls/CityInput` | NEW | 216-C | Aceternity placeholders-and-vanish + Magicui text-shimmer | spec'd |
| `SuggestionChips` | NEW | 216-C | 3-chip glass row, click-to-fill | spec'd |
| `PersonalizingBadge` | NEW | 216-C | Top-right pulsing-dot during agent.run | spec'd |
| `BackLink` | NEW | 216-C | Back-arrow on screens 2+ | spec'd |
| `NikitaThinkingDots` | NEW | 216-C | Loading ellipsis at >2s pending | spec'd |
| `FallingPattern` | REUSED | Spec 208 | Sparse char rain | reuse |
| `AuroraOrbs`, `GlowButton`, `easing.ts`, `globals.css` | REUSED | Spec 208 | No edits | reuse |

---

## Accessibility Checklist (final)

- [x] Per-control ARIA contracts (HobbyChips, BackstoryArchetypeCards, Slider, Tel, ProgressRail, NikitaReaction, WizardShell)
- [x] Keyboard nav: Tab order documented (Back → headline → control → Continue); Radix roving tabindex on radiogroups
- [x] Focus management: auto-move to `<h1 tabIndex={-1}>` after AnimatePresence exit
- [x] Focus indicators: `focus-visible:ring` on all interactive elements; never `focus:outline-none` without alternative
- [x] Live regions: HobbyChips count + NikitaReaction typewriter
- [x] Reduced motion: AuroraOrbs paused, transitions instant, ProgressRail linear 0.2s, NikitaReaction instant text
- [x] Mobile touch targets ≥44px on multi-tap surfaces
- [x] Landmark: `<main id="wizard" aria-label="onboarding wizard">`
- [x] Form labels (Tel `aria-describedby`, Slider `aria-valuetext`)
- [x] Error announcement: AC C1.14 inline rose-toned banner — recommend `role="alert"` or `aria-live="assertive"` at implementation time (not blocking; standard shadcn pattern)

## Responsive Checklist

- [x] Mobile 390×844 + desktop 1440×900 (AC C1.5)
- [x] Verified via `mcp__claude-in-chrome__resize_window` (testable)
- [x] No horizontal scroll
- [x] All CTAs reachable without zoom
- [x] Touch targets ≥44px

## Dark Mode / Tokens

- [x] `--bg-void`, `--rose`, `--glass-card-*`, `--ease-out-quart` inherited verbatim from Spec 208 (AC C1.2)
- [x] No new tokens introduced
- [x] AuroraOrbs opacity dimmed via prop (not new component)

## Performance

- [x] AnimatePresence `mode="wait"` (single screen at a time)
- [x] Stable `key={turn_id}` prevents unnecessary remounts on dynamic follow-ups (AC C1.16)
- [x] Server Component auth guard prevents wasted client mount on unauthenticated render (AC C1.13)
- [x] Resume hydrates from `GET /onboarding/state` once on mount (AC C1.15)

---

## Cross-Reference Sanity (master spec contracts)

| AC reference | Master spec target | Found |
|--------------|--------------------|-------|
| C1.13 — `nikita-session` cookie | spec.md L200, L298 | yes |
| C1.13 — magic-link 2nd-click 302/400 | spec.md L194-302 (`magic_link_consumed`) | yes |
| C1.14 — `meta.fallback_reason="cost_circuit"` | spec.md L235, L280 | yes |
| C1.15 — `GET /api/v1/onboarding/state` | spec.md L245 | yes |
| C1.13 — `auth_required` 401 envelope | spec.md L236, L275 | yes |

All AC references resolve cleanly against master spec.

---

## Open Questions (residual, non-blocking)

- **Q1**: Hobby chip exact list per category — TBD by UX review during 216-C implementation. **Non-blocking**: master taxonomy (10 cat × 10 chips) is locked, draft list ships with placeholder.
- **Q2**: Archetype card flip vs always-visible prose — defaulted to 150-char visible. **Non-blocking**.
- **Q3**: Voice-tone preference radio vs chips — defaulted to 3 inline radios. **Non-blocking**.
- ~~**Q4**: Resume UX banner vs silent~~ — **CLOSED by AC C1.15** (silent + greet via NikitaReaction).

---

## Recommendations for Implementation Phase (advisory, not blocking)

1. **Use `role="alert"` on the C1.14 error banner** — the spec says "inline rose-toned error banner" without specifying ARIA. Standard shadcn `<Alert variant="destructive" role="alert">` covers it; add explicitly during implementation.
2. **Verify Radix `<RadioGroup>` and `<Slider>` are in `components.json`** — install via `npx shadcn@latest add radio-group slider` if missing. Spec assumes available.
3. **Aceternity `placeholders-and-vanish-input`** — confirm vendoring path during implementation; component is not on shadcn registry. Vendor under `portal/src/components/aceternity/` or copy verbatim per Aceternity license.
4. **Wireframe pixel-diff (C1.1)** — set up Playwright visual-regression snapshot once Figma frames are imageable; ≤2% drift threshold is testable but tooling needs to be wired.
5. **Banned-vocab regex (C1.11)** — consider extending the curl check into a CI step (`npm run check:vocab`) so regressions don't ship.

None of these gate GATE 2.

---

## Final Verdict

**PASS.** Zero CRITICAL, zero HIGH findings. All iteration-1 issues closed via AC additions/refinements. Component inventory complete (Aceternity/Magicui/SuggestionChips/PersonalizingBadge/BackLink/NikitaThinkingDots/FallingPattern enumerated). A11y contracts codified per-control. Auth guard moved to Server Component. Resume UX deterministic. Banned-vocab regex word-boundary-safe. Pending/error states explicit. AnimatePresence keying contention-free. ProgressRail reduced-motion handled.

Subspec 216-C is **GATE 2 ready** from a frontend-validation perspective. Proceed to planning.
