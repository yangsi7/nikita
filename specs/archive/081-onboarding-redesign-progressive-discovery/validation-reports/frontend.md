## Frontend Validation Report

**Spec:** `specs/081-onboarding-redesign-progressive-discovery/spec.md`
**Status:** PASS
**Timestamp:** 2026-03-22T14:30:00Z
**Validator:** sdd-frontend-validator

### Summary
- CRITICAL: 0
- HIGH: 0
- MEDIUM: 5
- LOW: 3

### Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| MEDIUM | Accessibility | Spec says ScoreRing should use `role="img"` but existing component uses `role="meter"` with `aria-valuenow/min/max` | spec.md:695 | Keep the existing `role="meter"` pattern -- it is semantically superior for a numeric gauge. Update the spec table to reflect `role="meter"` instead of `role="img"`. The existing component already has proper `aria-label`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`. |
| MEDIUM | Animation | Spec says "No JavaScript animation libraries required" (CSS @keyframes / tw-animate-css only) but the existing ScoreRing uses framer-motion for ring and number animations | spec.md:689 vs score-ring.tsx:3 | Clarify the animation strategy: either (a) reuse the existing framer-motion ScoreRing as-is (recommended -- it already works and is tested), or (b) specify that the welcome page builds a CSS-only variant. Since the spec says "Reuses existing components: ScoreRing" (line 128), using framer-motion is the pragmatic path. Update line 689 to acknowledge framer-motion for the ScoreRing component. |
| MEDIUM | Accessibility | `prefers-reduced-motion` media query is not implemented anywhere in the existing portal codebase (0 matches) | spec.md:700 | The spec correctly requires `prefers-reduced-motion: reduce` to disable animations. This is a new requirement that must be implemented. Add a global CSS rule in `globals.css` and/or wrap framer-motion animations in a `useReducedMotion()` hook. Document the implementation approach in the plan. |
| MEDIUM | State Management | Dashboard page (`page.tsx`) is a `"use client"` component but does not currently use `useRouter`. The spec proposes adding `router.push("/dashboard/welcome")` for first-visit redirect. | spec.md:978-984 | The redirect logic requires adding `useRouter` from `next/navigation` to the existing dashboard page. This is a client-side redirect pattern which will cause a brief flash of the dashboard loading skeleton before redirect. Consider: (a) moving the redirect to the Server Component shell (create `dashboard/page.tsx` as server component wrapping a client component), or (b) accepting the brief flash as tolerable since it only happens once per user. Document the chosen approach in the plan. |
| MEDIUM | Component Naming | `ChapterStepper` is a new custom component that resembles the shadcn/ui `Stepper` pattern but is not a standard shadcn component | spec.md:529 | This is fine as a custom component. Ensure it follows the existing pattern: place in `portal/src/components/dashboard/chapter-stepper.tsx`, use GlassCard conventions, accept typed props with `interface ChapterStepperProps`. The component hierarchy in WF-5 is clear. |
| LOW | Performance | Welcome page Server Component fetches stats via `fetch()` with a hardcoded API URL, but the auth token extraction is left as a comment (`/* session token */`) | spec.md:957 | Clarify the server-side auth token pattern. The existing portal uses Supabase SSR client (`createClient()` from `@/lib/supabase/server`). The plan should specify using `supabase.auth.getSession()` to get the access token for the fetch call, consistent with other server-side data fetching in the portal. |
| LOW | Responsive | Mobile wireframe (WF-2) shows metric cards in a 2x2 grid on mobile, but text is abbreviated ("Intim.", "Pass."). No specification for how truncation or abbreviation is handled | spec.md:326-332 | Add a note about metric label truncation strategy on mobile. Options: (a) use `truncate` class with tooltip on hover, (b) define short labels as a prop (e.g., `shortLabel`), (c) use responsive text (`text-[10px] sm:text-xs`). This is a polish detail that can be resolved during implementation. |
| LOW | Animation | CTA button specifies `spring(1, 80, 10)` easing which is a framer-motion spring config, contradicting the "CSS @keyframes only" statement on line 689 | spec.md:687 | Minor inconsistency. If framer-motion is already used for ScoreRing (see MEDIUM finding above), using it for the CTA spring animation is fine. Update line 689 to say "CSS @keyframes for simple animations; framer-motion for spring physics where already imported." |

### Component Inventory

| Component | Type | Shadcn | Status | Notes |
|-----------|------|--------|--------|-------|
| WelcomePage (page.tsx) | Server Component | -- | New | Server shell with auth check + stats fetch |
| WelcomeClient | Client Component | -- | New | Main interactive welcome experience |
| WelcomeHeader | Custom | -- | New | Logo + Skip button |
| ScoreSection | Custom | -- | New | Wraps ScoreRing + MetricCards + NikitaQuote |
| ScoreRing | Existing | -- | Reuse | `@/components/charts/score-ring` -- uses framer-motion, has proper ARIA |
| MetricCards | Custom | GlassCard | New | 4 mini GlassCards for metrics |
| NikitaQuote | Custom | -- | New | Italic in-character commentary |
| ChapterSection | Custom | -- | New | Chapter roadmap step |
| ChapterStepper | Custom | -- | New | Horizontal (desktop) / vertical (mobile) stepper |
| StepNode | Custom | -- | New | Active/completed/locked chapter node |
| StepConnector | Custom | -- | New | Animated connecting line |
| RulesSection | Custom | -- | New | Game rules step |
| RulesGrid | Custom | GlassCard | New | 2x2 (desktop) / 1-col (mobile) grid |
| RuleCard | Custom | GlassCard | New | Icon + title + description card |
| CTASection | Custom | GlassCard, Button | New | "Go to Dashboard" CTA |
| GlassCard | Existing | -- | Reuse | `@/components/glass/glass-card` -- supports default/elevated/danger/amber variants |
| Button | Existing | shadcn Button | Reuse | `@/components/ui/button` |
| Badge | Existing | shadcn Badge | Reuse | `@/components/ui/badge` |
| Progress | Existing | shadcn Progress | Reuse | `@/components/ui/progress` |
| LoadingSkeleton | Existing | -- | Reuse | `@/components/shared/loading-skeleton` |
| ErrorDisplay | Existing | -- | Reuse | `@/components/shared/error-boundary` |

### Accessibility Checklist
- [x] Score ring ARIA -- existing component has `role="meter"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`, `aria-label` (spec says `role="img"` which is inferior; existing pattern is better)
- [x] Chapter stepper ARIA -- spec defines `role="list"` + `role="listitem"` + `aria-current="step"` (line 696)
- [x] Rule cards semantics -- spec defines `<article>` elements with heading hierarchy (line 697)
- [x] Skip link ARIA -- spec defines `aria-label="Skip welcome tour"` (line 698); skip-link component already exists in codebase
- [x] CTA button -- spec defines keyboard-focusable, Enter/Space activation (line 699); shadcn Button handles this natively
- [ ] `prefers-reduced-motion` -- spec requires it (line 700) but currently 0 instances in codebase -- MEDIUM, new implementation needed
- [x] Color contrast -- spec asserts WCAG AA (4.5:1) against dark backgrounds (line 701); existing oklch tokens verified
- [x] Keyboard navigation -- full tab navigation specified (line 702)
- [x] Focus indicators -- no stripped focus rings found in codebase (0 `focus:outline-none` without ring)
- [x] Screen reader announcements -- `sr-announcer.tsx` exists in shared components
- [x] Skip-to-content link -- exists at `portal/src/components/shared/skip-link.tsx`

### Responsive Checklist
- [x] Desktop layout defined -- WF-1 wireframe with max-width 720px centered (line 673)
- [x] Tablet layout defined -- 2-column rule cards grid, horizontal stepper at >= 768px (line 672)
- [x] Mobile layout defined -- WF-2 wireframe, single column, vertical stepper, stacked cards (line 671)
- [x] Breakpoints specified -- `< 640px`, `>= 768px`, `>= 1024px` (lines 671-673)
- [x] Touch targets -- shadcn Button defaults to 44px+ height; Skip link and CTA are standard buttons
- [x] Spacing scale -- `space-y-6` between sections, `gap-4` within grids, `p-6` card padding (line 675)

### Dark Mode Checklist
- [x] Dark-only design confirmed (line 704-706) -- no theme toggle needed
- [x] All color tokens use existing design system variables (lines 636-652)
- [x] No new color tokens introduced (line 652)
- [x] Glass tokens verified in globals.css (`--glass`, `--glass-border`, `--glass-elevated`, `--rose-glow`, `--amber-glow`)

### Form & State Checklist
- [x] No forms on the welcome page (no validation needed)
- [x] Loading state -- spec reuses existing `LoadingSkeleton` component; Server Component handles initial data fetch
- [x] Error state -- implicit via existing `ErrorDisplay` pattern; spec could be more explicit but dashboard page pattern is well-established
- [x] Client state -- `welcome_completed` flag managed via API call, not client state
- [x] Server state -- stats fetched server-side in Server Component shell, passed as props to WelcomeClient

### Performance Checklist
- [x] Server Component shell for initial render (line 127, 514)
- [x] Client interactivity isolated in WelcomeClient component
- [x] Existing components reused (ScoreRing, GlassCard, Badge, Progress) -- no new bundle additions
- [x] Icons from lucide-react (Heart, Clock, Shield, Flame) -- already in the project dependency tree
- [ ] No explicit Suspense boundary for WelcomeClient -- LOW priority, single fetch in Server Component is sufficient

### Recommendations

1. **MEDIUM: Update spec ARIA role for ScoreRing**
   - Change line 695 from `role="img"` to `role="meter"` to match the existing, semantically superior implementation.
   - The existing ScoreRing component at `portal/src/components/charts/score-ring.tsx` already uses `role="meter"` with `aria-valuenow`, `aria-valuemin`, `aria-valuemax`, `aria-label`.

2. **MEDIUM: Clarify animation library strategy**
   - Line 689 says "No JavaScript animation libraries required" but the existing ScoreRing uses framer-motion, and the CTA button spec uses a spring easing function.
   - Recommendation: Update line 689 to say "Prefer CSS @keyframes for simple animations. The existing ScoreRing's framer-motion animations are reused as-is. Spring physics for CTA entrance may use framer-motion."

3. **MEDIUM: Implement `prefers-reduced-motion` support**
   - Line 700 correctly requires this, but no existing implementation exists in the portal.
   - Add to `globals.css`: `@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; } }`
   - For framer-motion: use the `useReducedMotion()` hook to conditionally disable animations.
   - This is a portal-wide improvement, not just welcome-page-specific.

4. **MEDIUM: Resolve dashboard redirect flash**
   - The spec proposes a client-side `router.push()` redirect in the existing `"use client"` dashboard page.
   - This means first-time users will briefly see the dashboard loading skeleton before being redirected.
   - Consider refactoring dashboard to a Server Component shell that checks `welcome_completed` server-side and calls `redirect()` before rendering, similar to the welcome page itself (which already does this pattern in reverse at line 962).

5. **MEDIUM: ChapterStepper component design**
   - The spec provides clear wireframes for horizontal (desktop) and vertical (mobile) layouts.
   - During implementation, follow the established pattern: create `portal/src/components/dashboard/chapter-stepper.tsx` with a typed props interface including chapter data, current chapter, and layout direction.
   - Use the `role="list"` / `role="listitem"` / `aria-current="step"` pattern specified in the spec.

6. **LOW: Clarify server-side auth token pattern**
   - The welcome page Server Component code sample (line 957) has a placeholder comment for the auth token.
   - The plan should specify using the Supabase SSR client pattern established in the codebase: `const supabase = await createClient(); const { data: { session } } = await supabase.auth.getSession()` then use `session.access_token` in the fetch Authorization header.

7. **LOW: Metric label truncation on mobile**
   - WF-2 shows abbreviated labels ("Intim.", "Pass.") but no truncation strategy is specified.
   - Resolve during implementation: either define `shortLabel` props or use responsive text sizing.

8. **LOW: Spring easing inconsistency**
   - CTA button uses `spring(1, 80, 10)` which is framer-motion syntax, contradicting "CSS @keyframes only".
   - Resolve by updating the animation strategy as described in Recommendation 2.

### Verified Existing Patterns

The spec correctly references and builds upon these verified existing patterns:

1. **ScoreRing** (`portal/src/components/charts/score-ring.tsx`) -- confirmed exists with framer-motion animations and proper ARIA attributes (`role="meter"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`, `aria-label`).

2. **GlassCard** (`portal/src/components/glass/glass-card.tsx`) -- confirmed exists with `default`, `elevated`, `danger`, `amber` variants. Uses `forwardRef` pattern.

3. **Design tokens** (`portal/src/app/globals.css`) -- confirmed: `--glass`, `--glass-border`, `--glass-elevated`, `--rose-glow`, `--amber-glow` all exist with oklch values.

4. **LoadingSkeleton** (`portal/src/components/shared/loading-skeleton.tsx`) -- confirmed exists with `ring`, `chart`, `card-grid`, `table`, `kpi`, `card` variants.

5. **ErrorDisplay** (`portal/src/components/shared/error-boundary.tsx`) -- confirmed exists.

6. **Skip-link** (`portal/src/components/shared/skip-link.tsx`) -- confirmed exists.

7. **Middleware routing** (`portal/src/lib/supabase/middleware.ts`) -- confirmed `/dashboard/*` routes are already protected. No middleware changes needed.

8. **shadcn/ui components** -- confirmed Button, Badge, Progress all installed in `portal/src/components/ui/`.

### Conclusion

This is a well-specified frontend feature. The `/dashboard/welcome` page is thoroughly wireframed for both desktop and mobile with clear component hierarchy, color tokens, typography, spacing, animation specs, and accessibility requirements. The spec correctly identifies existing components for reuse and stays within the established design system.

The 5 MEDIUM findings are all resolvable spec clarifications (ARIA role mismatch with existing code, animation library strategy, reduced-motion implementation, redirect flash, component naming). None represent missing critical functionality or accessibility blockers.

**Status: PASS** -- 0 CRITICAL, 0 HIGH findings. Proceed to planning phase.
