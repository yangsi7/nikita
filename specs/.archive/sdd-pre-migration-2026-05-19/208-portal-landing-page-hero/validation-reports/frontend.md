## Frontend Validation Report

**Spec:** specs/208-portal-landing-page-hero/spec.md
**Status:** PASS
**Timestamp:** 2026-04-03T00:00:00Z

### Summary
- CRITICAL: 0
- HIGH: 0
- MEDIUM: 3
- LOW: 4

### Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| MEDIUM | Accessibility | `aria-hidden="true"` requirement for decorative elements stated but not specified per component | spec.md §Accessibility | Enumerate per-component: FallingPattern, AuroraOrbs, decorative icons — each needs `aria-hidden="true"` in component interface |
| MEDIUM | Accessibility | Floating nav (`landing-nav.tsx`) lacks keyboard focus trap or skip-to-content behavior — `scrollY`-conditional render can orphan keyboard focus if nav appears mid-tab | spec.md §Floating Nav | Add `role="navigation"` + `aria-label="Site navigation"`. Document that skip link in Providers already handles pre-nav keyboard flow |
| MEDIUM | Responsive | Hero image is spec'd as "hidden on mobile" (`< 768px`) but no explicit breakpoint given for `pitch-section.tsx` (2-column) or `stakes-section.tsx` (2×2 grid) — only hero is explicit | spec.md §Section 2, §Section 4 | Add explicit breakpoint specs: pitch-section stacks at `md`, stakes-section 2×2 → 1-column at `sm` |
| LOW | Performance | `FallingPattern` uses canvas — no explicit lazy-load boundary or `loading="lazy"` strategy specified. Spec says follow `ambient-particles.tsx` pattern (canvas + `useEffect`) but no Suspense boundary or dynamic import noted | spec.md §FallingPattern | Recommend `next/dynamic` with `ssr: false` for canvas component — add to spec |
| LOW | Performance | `next/image` usage for Nikita hero image is implied but not explicitly required. Aspect ratio, `sizes`, and `priority` prop not specified | spec.md §Section 1 | Mandate `<Image>` from `next/image`, specify `priority={true}` (LCP image), define `sizes` for responsive breakpoints |
| LOW | State Management | `LandingNav` uses `scrollY > window.innerHeight * 0.5` — `window` access pattern in server component context not specified. Must be client component | spec.md §Floating Nav | Explicitly mark `landing-nav.tsx` as `"use client"` in spec (currently omitted from file list annotations) |
| LOW | Animation | `useInView` from framer-motion is listed in mock for tests but the `once: true` parameter is not confirmed — infinite re-triggers on scroll-back would be jarring. | spec.md §Animation | Confirm `useInView({ once: true })` in spec animation table |

### Component Inventory

| Component | Type | Shadcn | Notes |
|-----------|------|--------|-------|
| LandingNav | Custom client | None | Uses `useScroll`, must be `"use client"` |
| HeroSection | Custom client | None | Framer-motion animations, FallingPattern canvas |
| PitchSection | Custom client | None | `useInView` scroll trigger |
| SystemSection | Custom client | None | Terminal animation, counter via framer-motion |
| StakesSection | Custom client | Uses GlassCard (custom, not shadcn) | 2×2 grid + chapter timeline |
| CtaSection | Custom client | None | Auth-conditional CTA |
| GlowButton | Custom client | None | Spring physics hover, external link detection |
| AuroraOrbs | Custom (CSS-only) | None | `aria-hidden="true"` required |
| FallingPattern | Custom client (canvas) | None | Should be `next/dynamic` SSR-off |
| TelegramMockup | Custom client | None | Staggered message animation |
| SystemTerminal | Custom client | None | Sequential line reveal, cursor blink |
| ChapterTimeline | Custom | None | 5-dot visual with labels + thresholds |
| GlassCard (reused) | Custom | None | Exists at `portal/src/components/glass/glass-card.tsx` ✓ |

### Accessibility Checklist
- [x] Decorative elements: `aria-hidden="true"` required (spec §Accessibility)
- [x] WCAG AA contrast: white on void ≈ 18:1 — spec states this explicitly
- [x] Reduced motion: `prefers-reduced-motion: reduce` covered in CSS + spec
- [x] Semantic HTML: `<section>`, `<nav>`, `<main>`, heading hierarchy specified
- [x] Skip link: stated as "already in Providers"
- [x] Images: descriptive `alt` text required (spec §Accessibility)
- [ ] Keyboard navigation for floating nav: not fully specified — MEDIUM
- [ ] Per-component `aria-hidden` enumeration: MEDIUM

### Responsive Checklist
- [x] Hero desktop layout: 60/40 split — specified
- [x] Hero mobile: stacked, image hidden at `< 768px` — specified
- [x] CTA mobile: acceptance criteria item — specified
- [ ] Pitch section breakpoint: not explicit — MEDIUM
- [ ] Stakes section breakpoint: not explicit — MEDIUM

### Recommendations

1. **MEDIUM — Keyboard nav for floating nav**: Add `role="navigation"` and `aria-label` to `landing-nav.tsx` spec. Document that it should only appear for sighted/pointer users initially (or ensure keyboard users can reach it post-scroll).

2. **MEDIUM — Breakpoint completeness**: Add a responsive table to spec covering all 5 sections at `sm`, `md`, `lg` breakpoints. At minimum: PitchSection 2-col → 1-col at `md`, StakesSection 2×2 → 1-col at `sm`.

3. **MEDIUM — aria-hidden per component**: Add a table to spec: `FallingPattern aria-hidden=true`, `AuroraOrbs aria-hidden=true`, `ChapterTimeline` visual dots `aria-hidden=true` with text alternative.

4. **LOW — next/dynamic for canvas**: Add `dynamic(() => import('./falling-pattern'), { ssr: false })` pattern to spec to prevent SSR hydration errors.

5. **LOW — next/image spec**: Formalize `<Image src="/images/nikita-hero.png" alt="Nikita" priority sizes="..." />`.
