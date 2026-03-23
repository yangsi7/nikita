## Frontend Validation Report

**Spec:** `specs/081-onboarding-redesign-progressive-discovery/spec.md` (v2)
**Status:** FAIL
**Timestamp:** 2026-03-22T14:30:00Z
**Validator:** sdd-frontend-validator (Opus 4.6)

### Summary
- CRITICAL: 2
- HIGH: 5
- MEDIUM: 6
- LOW: 4

---

### Findings

| # | Severity | Category | Issue | Location | Recommendation |
|---|----------|----------|-------|----------|----------------|
| 1 | CRITICAL | Forms | No Zod schema specified for client-side form validation; spec uses raw `useState` + manual checks in `handleSubmit` with no `aria-describedby` or `role="alert"` on inline errors | spec.md:1270-1296 | Define Zod schema (`z.object({ location_city: z.string().min(1), social_scene: z.enum([...]), drug_tolerance: z.number().int().min(1).max(5) })`) and use shadcn `<Form>` + `zodResolver` for auto-wired `aria-describedby`/`aria-invalid`. The error string at line 1293 renders with no ARIA markup. |
| 2 | CRITICAL | Accessibility | SceneSelector specifies `role="radiogroup"` + `role="radio"` but no existing shadcn RadioGroup is used, and spec does not define keyboard navigation (Arrow keys to move between cards, Tab to move out of group) or `tabIndex` management within the radiogroup | spec.md:1080, WF-10 (855-897) | Spec must define Arrow Up/Down/Left/Right navigation within `role="radiogroup"` per WAI-ARIA radio group pattern. Each `role="radio"` card needs `tabIndex={selected ? 0 : -1}` roving tabindex. Consider using Radix `RadioGroup` primitive under the visual card UI for free keyboard + ARIA semantics. |
| 3 | HIGH | Accessibility | EdginessSlider spec defines custom `role="slider"` with manual keyboard handling but the portal already has a shadcn `<Slider>` component (Radix primitive) at `portal/src/components/ui/slider.tsx` that provides ARIA, keyboard, and touch for free | spec.md:899-948 | Use the existing shadcn `<Slider>` with `min={1} max={5} step={1}` and customize visuals via className props. This avoids re-implementing slider a11y (Radix handles `role="slider"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`, arrow keys, Home/End, touch). If custom emoji markers are needed, compose them around the Radix Slider primitive. |
| 4 | HIGH | Accessibility | No `aria-live` region for form submission error; the error at line 1293 (`"Something went wrong. Please try again."`) and the validation error at line 1273 are set via `setError` but the spec does not specify `role="alert"` or `aria-live="assertive"` on the error container | spec.md:1268-1296 | Add `role="alert"` to the error message container in MissionSection. When `error` state is non-null, the message must be announced to screen readers immediately. Pattern: `{error && <p role="alert" className="text-destructive text-sm">{error}</p>}` |
| 5 | HIGH | Accessibility | Location input in Section 4 specifies `aria-required="true"` (line 1082) but no `aria-describedby` for validation error, and no error message component is specified for the individual field | spec.md:1082, FR-003 (177) | Specify field-level error display: when location is empty on submit, show "Location is required" below the input with `aria-describedby` linking to the error. Using shadcn `<Form>` + `<FormField>` + `<FormMessage>` handles this automatically. |
| 6 | HIGH | Responsive | Section 4 (profile form) uses `min-h-screen` with `snap-start` but scroll-snap-mandatory with variable-height sections causes broken snap behavior on mobile; when the form content exceeds viewport height, the snap point forces users to the top of the section, making it impossible to scroll within the section to reach lower form fields | spec.md:964, 987-989 | Change Section 4 to `snap-align: start` with `snap-stop: normal` (not `always`) so users can scroll freely within the oversized section. Alternatively, use `scroll-snap-type: y proximity` instead of `mandatory` for the entire container, or break Section 4 into sub-sections. Document the expected behavior when content overflows viewport. |
| 7 | HIGH | Performance | No `Suspense` boundary or loading skeleton specified for the `/onboarding` page; the Server Component shell fetches stats API (line 1224-1237) but no loading.tsx or Suspense fallback is defined for the route, meaning users see a blank page during the server-side fetch | spec.md:1206-1241 | Add `portal/src/app/onboarding/loading.tsx` with a full-screen skeleton matching the void background. This is standard Next.js App Router pattern. The Server Component fetch to `/api/v1/portal/stats` may take 500ms+ on cold start -- users need visual feedback. |
| 8 | MEDIUM | Components | Spec defines a custom `NikitaQuote` component used in all 5 sections but never specifies its implementation; it should use `<blockquote>` + `<cite>` semantics (line 1088 mentions this) but no props interface, className pattern, or reuse strategy is documented | spec.md:773, 781, 788, etc. | Add a WF entry for NikitaQuote: `interface NikitaQuoteProps { children: string; cite?: string }` rendering as `<blockquote className="text-sm italic text-muted-foreground/80"><p>{children}</p><cite className="not-italic text-xs">-- Nikita</cite></blockquote>`. Place in `portal/src/app/onboarding/components/nikita-quote.tsx`. |
| 9 | MEDIUM | Components | Spec defines `SectionHeader` used in all 5 sections but provides no component detail; only className for the title is given in Typography table (line 1028) | spec.md:771, 775, 783, 791, 800 | Add WF entry: `interface SectionHeaderProps { title: string; quote?: string }`. Renders `<h2>` with tracking + uppercase classes, optional NikitaQuote below. This is the most reused component -- worth specifying once. |
| 10 | MEDIUM | Accessibility | ChapterStepper specifies `role="list"` + `role="listitem"` + `aria-current="step"` (line 1078) but no `aria-label` on the overall list ("Chapter progression") and locked chapters with "???" text provide no screen reader context that the content is intentionally hidden | spec.md:1078, WF-9 (809-853) | Add `aria-label="Chapter progression, currently on chapter 1 of 5"` to the `role="list"` container. For locked chapters, add `aria-label="Chapter 3, locked"` so screen readers convey the lock state, not just "???" which is meaningless audibly. |
| 11 | MEDIUM | State | No specification for handling browser back/forward navigation within the scroll-snap experience; if a user navigates away (e.g., to `/login`) and returns, the scroll position and form state are lost | spec.md:1300-1308 | Consider persisting form state to `sessionStorage` so returning users resume where they left off. Document expected behavior: on back-navigation, scroll resets to Section 1 with empty form (acceptable) OR form state persists (better UX). |
| 12 | MEDIUM | Performance | The spec code sample fetches `/api/v1/portal/stats` from the Server Component using raw `fetch()` with hardcoded `process.env.NEXT_PUBLIC_API_URL` (a public env var); server-side fetches should use a server-only env var to avoid exposing the API URL to the client bundle | spec.md:1225 | Use `process.env.API_URL` (server-only, no `NEXT_PUBLIC_` prefix) for server-side fetches, or use the existing Vercel rewrite proxy (`/api/v1/*` rewrites to Cloud Run). The `NEXT_PUBLIC_` prefix exposes the value to the client bundle unnecessarily for a server-only call. |
| 13 | MEDIUM | Animation | `prefers-reduced-motion` support is mentioned (line 1085, 1170) but no implementation pattern is specified; framer-motion's `useReducedMotion()` hook should be referenced, and CSS transitions on scene cards and emoji swaps need `@media (prefers-reduced-motion: reduce)` overrides | spec.md:1085, 1170 | Specify: (1) framer-motion animations use `useReducedMotion()` to conditionally set `initial` as `animate` target; (2) CSS transitions add `@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; } }` in globals.css or per-component. Currently zero `prefers-reduced-motion` references exist in the portal codebase. |
| 14 | LOW | Testing | E2E test list (lines 1663-1678) does not include a test for `prefers-reduced-motion` behavior or keyboard-only navigation through the full onboarding flow | spec.md:1663-1678 | Add E2E-11: Keyboard-only navigation test (Tab through all interactive elements, Enter/Space to select scene card, arrow keys on slider). Add E2E-12: Reduced motion test (emulate `prefers-reduced-motion: reduce`, verify no animations fire). |
| 15 | LOW | Components | Scroll indicator (bouncing down arrow, lines 996-997) has no component specification, no ARIA (`aria-hidden="true"` since decorative), and no `data-testid` | spec.md:996-997 | Add: decorative scroll indicator with `aria-hidden="true"`, `className="animate-bounce opacity-50"`, hidden after first scroll event via IntersectionObserver or scroll listener. |
| 16 | LOW | State | The `tg://` deep link fallback (lines 1287-1291) uses `setTimeout(() => window.open(...), 2000)` which fires even if the `tg://` protocol succeeded; this opens a duplicate tab on desktop browsers with Telegram installed | spec.md:1287-1291 | Use `window.addEventListener("blur", ...)` to detect if the app switched away (protocol handler succeeded). Only fire the `https://t.me/` fallback if the window is still focused after 2 seconds. Or use a visibility change listener. |
| 17 | LOW | Components | No `data-testid` attributes specified for any of the new onboarding components; the existing portal uses `data-testid` on 14 components (26 occurrences) | spec.md:1247-1308 | Add `data-testid` strategy: `onboarding-section-score`, `onboarding-section-chapters`, `onboarding-scene-card-{id}`, `onboarding-edginess-slider`, `onboarding-location-input`, `onboarding-cta-submit`. This enables E2E test selectors without fragile CSS queries. |

---

### Component Inventory

| Component | Type | Shadcn/Existing | Status | Notes |
|-----------|------|-----------------|--------|-------|
| `/onboarding/page.tsx` | Server Component | N/A | NEW | Auth check + redirect logic. Needs `loading.tsx`. |
| `OnboardingCinematic` | Client Component | N/A | NEW | Scroll-snap container + form state. `"use client"`. |
| `ScoreSection` | Client Component | Reuses `ScoreRing`, `GlassCard` | NEW | Reuse pattern is sound. |
| `ScoreRing` | Existing | `@/components/charts/score-ring` | REUSE | Already has `role="meter"`, ARIA, framer-motion. |
| `GlassCard` | Existing | `@/components/glass/glass-card` | REUSE | 4 variants, forwardRef, clean API. |
| `MetricCards` | Client Component | Uses `GlassCard` | NEW | 4 mini cards in 2x2 grid. |
| `ChapterSection` | Client Component | N/A | NEW | Scroll-triggered animations. |
| `ChapterStepper` | Client Component | N/A | NEW | Horizontal (desktop) / vertical (mobile). Needs `aria-label` on list. |
| `StepNode` | Client Component | N/A | NEW | 3 variants: active, next, locked. |
| `RulesSection` | Client Component | Uses `GlassCard` | NEW | 2x2 grid (md+) / stack (mobile). |
| `RuleCard` | Client Component | Uses `GlassCard` + lucide icons | NEW | Semantic `<article>` + `<h3>`. |
| `ProfileSection` | Client Component | N/A | NEW | Form container. Should use shadcn `<Form>`. |
| `LocationInput` | Client Component | shadcn `<Input>` + `<Label>` | NEW | Needs `<FormField>` wrapper for a11y. |
| `SceneSelector` | Client Component | N/A (needs Radix RadioGroup) | NEW | **CRITICAL**: Needs roving tabindex / Radix RadioGroup. |
| `SceneCard` | Client Component | N/A | NEW | Visual radio button. |
| `EdginessSlider` | Client Component | Should use shadcn `<Slider>` | NEW | **HIGH**: Reuse existing Radix Slider primitive. |
| `EmojiPreview` | Client Component | N/A | NEW | Large emoji + label display. |
| `MissionSection` | Client Component | shadcn `<Button>` | NEW | CTA + error display. Needs `role="alert"`. |
| `NikitaQuote` | Client Component | N/A | NEW | **MEDIUM**: Unspecified. Needs `<blockquote>` + `<cite>`. |
| `SectionHeader` | Client Component | N/A | NEW | **MEDIUM**: Unspecified. Needs `<h2>` + optional quote. |
| `ScrollIndicator` | Client Component | N/A | NEW | Decorative. `aria-hidden="true"`. |

**Total new components:** 18 | **Reused:** 2 (ScoreRing, GlassCard) | **Shadcn to install:** 0 (Slider, Input, Button, Label already installed)

---

### Accessibility Checklist

- [x] Score ring ARIA (`role="meter"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`, `aria-label`) -- reused from existing component (score-ring.tsx:28-32)
- [ ] Scene selector keyboard navigation (Arrow keys within radiogroup) -- **CRITICAL**: Not specified
- [ ] Scene selector roving tabindex (`tabIndex={selected ? 0 : -1}`) -- **CRITICAL**: Not specified
- [x] Edginess slider ARIA (`role="slider"`, `aria-valuemin`, `aria-valuemax`, `aria-valuenow`, `aria-valuetext`) -- specified at spec.md:942-947
- [ ] Edginess slider keyboard (Left/Right arrows) -- specified in text (line 939) but should use Radix Slider
- [x] Location input label (`<label>` + `htmlFor`, `aria-required`) -- specified at spec.md:1082
- [ ] Location input error description (`aria-describedby`) -- **HIGH**: Not specified
- [ ] Form error announcement (`role="alert"` on error container) -- **HIGH**: Not specified
- [x] Chapter stepper (`role="list"` + `role="listitem"` + `aria-current="step"`) -- specified at spec.md:1078
- [ ] Chapter stepper overall `aria-label` -- **MEDIUM**: Missing
- [x] Section `aria-label` on each `<section>` -- specified at spec.md:1084
- [x] Semantic headings (`<h2>` for section titles) -- specified at spec.md:1088
- [x] Nikita quotes (`<blockquote>` + `<cite>`) -- specified at spec.md:1088
- [x] CTA button keyboard-focusable (Tab, Enter/Space) -- specified at spec.md:1083
- [x] Color contrast (oklch(0.95) on oklch(0.08) = ~18:1, WCAG AAA) -- specified at spec.md:1086
- [ ] Reduced motion (`prefers-reduced-motion`) implementation pattern -- **MEDIUM**: Mentioned but no concrete implementation
- [x] Rule cards as `<article>` with `<h3>` headings -- specified at spec.md:1079
- [ ] Skip-to-content link -- Not specified (not present in portal codebase at all)
- [x] Focus indicators -- Portal uses shadcn defaults (`focus-visible:ring-ring/50 focus-visible:ring-[3px]`), no stripped focus rings confirmed

---

### Responsive Checklist

- [x] Desktop layout defined (max-w-[720px] centered, 2x2 grids, horizontal stepper) -- WF-1 through WF-5
- [x] Tablet layout defined (md breakpoint, 768px) -- spec.md:1049
- [x] Mobile layout defined (<640px, single column, vertical stepper) -- WF-1b through WF-5b (mobile wireframes)
- [x] Touch targets specified (40px nodes in ChapterStepper, full card tap targets in SceneSelector) -- WF-9 (827-842)
- [x] Breakpoints documented (mobile <640, sm 640-767, md 768+, lg 1024+) -- spec.md:1043-1052
- [ ] Scroll-snap overflow behavior on long Section 4 -- **HIGH**: Not resolved for mobile viewports
- [x] Scene card grid responsive (5-in-row desktop, 2-col mobile) -- WF-10 (889-891), WF-4b (625-641)
- [x] Score ring size responsive (200px desktop, 160px mobile) -- WF-1 (346), WF-1b (384)
- [x] Section padding responsive (px-4 py-12 mobile, px-8 py-16 desktop) -- spec.md:967-968

---

### Form Validation Checklist

- [x] Form fields specified with types (location: text, scene: radio selection, edginess: slider 1-5) -- FR-003
- [ ] Zod schema defined -- **CRITICAL**: Missing. Manual validation in handleSubmit is fragile and bypasses shadcn Form a11y.
- [ ] Field-level error messages -- **HIGH**: Only a single combined error string exists
- [x] Loading state specified (`submitting` boolean, button disabled during submit) -- spec.md:1267, 1275
- [x] Error state specified (inline error display) -- spec.md:1268, 1292-1294
- [x] Form state management (React useState, no server round-trips until submit) -- spec.md:180, 1262-1268
- [x] Validation rules documented (location non-empty, scene selected, edginess 1-5) -- FR-003, AC-5.4
- [ ] Error announcement to screen readers -- **HIGH**: No `role="alert"` or `aria-live`

---

### Dark Mode Checklist

- [x] Dark-only app, no theme toggle needed -- spec.md:1090-1092
- [x] Uses existing oklch design tokens from globals.css -- spec.md:1008-1022
- [x] No new color tokens introduced -- spec.md:1010
- [x] Glass card utilities reused (glass-card, glass-card-elevated) -- globals.css:155-166
- [x] Glow utilities reused (glow-rose, glow-cyan, glow-amber) -- globals.css:167-175

---

### Performance Checklist

- [ ] Loading skeleton / Suspense boundary for route -- **HIGH**: No loading.tsx specified
- [x] framer-motion already bundled (used by ScoreRing, MoodOrb) -- spec.md:1776
- [x] Bundle size target documented (<200KB gzipped) -- NFR-002 (spec.md:1749)
- [x] Server Component shell + Client Component split (server handles auth, client handles interactivity) -- spec.md:1206-1241
- [x] No unnecessary server round-trips (form state held client-side until submission) -- spec.md:180
- [ ] Image optimization -- N/A (no images in this spec, all icons are lucide-react)
- [x] Scroll-snap browser support documented (Chrome 69+, Safari 11+, Firefox 68+) -- spec.md:1775

---

### Recommendations

#### 1. CRITICAL: Add Zod Schema + shadcn Form for Profile Collection

The spec defines manual validation in `handleSubmit` (lines 1271-1274) with a single error string. This bypasses the portal's established pattern of using shadcn `<Form>` + `zodResolver` which auto-wires `aria-describedby` and `aria-invalid` on every field.

**Add to spec:**
```typescript
// portal/src/app/onboarding/schemas.ts
import { z } from "zod"

export const onboardingProfileSchema = z.object({
  location_city: z.string().min(1, "Location is required"),
  social_scene: z.enum(["techno", "art", "food", "cocktails", "nature"], {
    required_error: "Pick a scene",
  }),
  drug_tolerance: z.coerce.number().int().min(1).max(5),
})
```

Use `useForm` + `zodResolver` + shadcn `<Form>`, `<FormField>`, `<FormItem>`, `<FormMessage>` for each field. This gives per-field errors with automatic ARIA wiring.

#### 2. CRITICAL: Define Keyboard Navigation for SceneSelector Radiogroup

The spec specifies `role="radiogroup"` + `role="radio"` (line 1080) but omits the required keyboard interaction pattern per WAI-ARIA:
- Arrow Up/Down/Left/Right moves focus between radio items
- Only the selected (or first) item is in the Tab order (`tabIndex={0}`), others are `tabIndex={-1}`
- Space selects the focused item

**Recommended approach:** Use Radix `RadioGroup` primitive (already a dependency via shadcn) as the semantic layer, with custom visual rendering for the scene cards. This gets keyboard + ARIA for free without manual implementation.

#### 3. HIGH: Use Existing shadcn Slider for EdginessSlider

`portal/src/components/ui/slider.tsx` already wraps `Radix SliderPrimitive` with full keyboard, touch, and ARIA support. The spec should compose around it rather than building a custom slider:

```tsx
<Slider min={1} max={5} step={1} value={[value]} onValueChange={([v]) => onChange(v)} />
```

Add emoji markers as positioned elements above the track. The thumb, ARIA, and keyboard handling come from Radix.

#### 4. HIGH: Add `role="alert"` to Error Messages

Every location where `error` state is rendered needs `role="alert"`:
- Validation error in ProfileSection ("Please fill in your location and pick a scene.")
- Submission error in MissionSection ("Something went wrong. Please try again.")
- Field-level errors (if Zod + Form approach adopted)

#### 5. HIGH: Add `aria-describedby` to Location Input Error

When using shadcn `<Form>` (recommendation 1), this is automatic. If staying with manual approach, add:
```tsx
<input aria-describedby={error ? "location-error" : undefined} aria-invalid={!!error} />
{error && <p id="location-error" role="alert">{error}</p>}
```

#### 6. HIGH: Fix Scroll-Snap + Variable Height Section Conflict

`snap-y snap-mandatory` with a `min-h-screen` section (Section 4) creates a broken UX on small mobile viewports where the form exceeds one screen. Options:
- Use `scroll-snap-type: y proximity` globally (relaxes snapping for oversized sections)
- Split Section 4 into two snap sections (location+scene, edginess)
- Add `scroll-snap-align: none` to Section 4 only

Document the chosen approach in the spec.

#### 7. HIGH: Add loading.tsx for Onboarding Route

```tsx
// portal/src/app/onboarding/loading.tsx
export default function OnboardingLoading() {
  return (
    <div className="h-screen bg-void flex items-center justify-center">
      <div className="shimmer w-48 h-48 rounded-full" />
    </div>
  )
}
```

This prevents a blank white flash during the server-side auth check + stats fetch.

#### 8-13. MEDIUM Items

- **NikitaQuote component**: Add a WF entry with props interface, semantic HTML, and className pattern.
- **SectionHeader component**: Add a WF entry. Used 5 times -- worth a single specification.
- **ChapterStepper aria-label**: Add `aria-label="Chapter progression, currently on chapter {n} of 5"`.
- **Browser navigation state**: Document that form state is ephemeral (lost on navigation) or persist to sessionStorage.
- **Server-side fetch env var**: Use non-public env var for server-side API calls.
- **Reduced motion implementation**: Add concrete framer-motion `useReducedMotion()` pattern and CSS fallback.

---

### Pass/Fail Assessment

**Status: FAIL**

**Blocking issues that must be resolved before planning:**

1. **CRITICAL-1**: The form validation approach (manual useState + string error) is inconsistent with the portal's established shadcn Form + Zod pattern and produces inaccessible error states. Define a Zod schema and use shadcn Form components.

2. **CRITICAL-2**: The SceneSelector `role="radiogroup"` pattern lacks required keyboard navigation (arrow keys, roving tabindex). Use Radix RadioGroup primitive or fully specify the keyboard interaction model.

3. **HIGH-3 through HIGH-7**: Five HIGH issues (slider reimplementation, error announcement, field error descriptions, scroll-snap overflow, loading skeleton) must be addressed. Each creates a broken or inaccessible experience for a subset of users.

**To achieve PASS:** Fix both CRITICALs and all 5 HIGHs. MEDIUM and LOW items can be tracked as GitHub issues and addressed during implementation.
