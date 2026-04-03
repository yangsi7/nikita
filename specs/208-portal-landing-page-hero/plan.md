# Implementation Plan: Spec 208 — Portal Landing Page Hero

**Spec**: `specs/208-portal-landing-page-hero/spec.md`
**Branch**: `feature/208-portal-landing-page`
**Complexity**: Large (7)
**Total Tasks**: 42
**Estimated Total**: ~52h

---

## Requirements Coverage

| Requirement | Source | Tasks |
|-------------|--------|-------|
| REQ-001: `/` shows landing page for all users (no redirect) | Routing Change | T1.2, T7.1 |
| REQ-002: Middleware early-return for `/` | Middleware Fix | T1.2 |
| REQ-003: CSS keyframes/utilities (cursor-blink, aurora, mask-fade) | CSS Additions | T1.3 |
| REQ-004: Magic UI components installed | Dependencies | T1.4 |
| REQ-005: Nikita hero image generated | Image Generation | T2.1 |
| REQ-006: 9 mood variants generated | Image Generation | T2.2 |
| REQ-007: GlowButton shared component | Shared Components | T3.1, T6.1 |
| REQ-008: AuroraOrbs shared component | Shared Components | T3.2, T6.2 |
| REQ-009: FallingPattern shared component | Shared Components | T3.3, T6.3 |
| REQ-010: TelegramMockup sub-component | Section Components | T4.1, T6.4 |
| REQ-011: SystemTerminal sub-component | Section Components | T4.2, T6.5 |
| REQ-012: ChapterTimeline sub-component | Section Components | T4.3, T6.6 |
| REQ-013: HeroSection (FallingPattern, stagger anim, auth CTA) | Section Components | T4.4, T6.7 |
| REQ-014: PitchSection (3 differentiators, mockup) | Section Components | T4.5, T6.8 |
| REQ-015: SystemSection (terminal, stats counter) | Section Components | T4.6, T6.9 |
| REQ-016: StakesSection (4 glass cards, chapter timeline) | Section Components | T4.7, T6.10 |
| REQ-017: CtaSection (final CTA, aurora orbs) | Section Components | T4.8, T6.11 |
| REQ-018: LandingNav (scroll-aware floating bar) | Section Components | T4.9, T6.12 |
| REQ-019: Root page.tsx rewrite | Root Page | T5.1 |
| REQ-020: OG/Twitter metadata | Root Page | T5.2 |
| REQ-021: Mobile responsive layout | All sections | T4.4–T4.9 |
| REQ-022: prefers-reduced-motion respected | All animated components | T3.3, T4.2, T4.4 |
| REQ-023: All section heading copy exact | All sections | T4.4–T4.9 |
| REQ-024: Vitest unit tests (9 test files) | Unit Tests | T6.1–T6.12 |
| REQ-025: Playwright E2E landing suite | E2E Tests | T7.1 |
| REQ-026: auth-flow.spec.ts updated | E2E Tests | T7.2 |
| REQ-027: Figma Code Connect mappings | Figma | T8.1, T8.2 |
| REQ-028: npm run build passes zero errors | Build QA | T9.1 |
| REQ-029: Existing routes unchanged | Build QA | T9.2 |

---

## Task Breakdown

### Phase 1: Infrastructure

---

#### T1.1 — Create feature branch
**Estimated**: 0.5h
**Dependencies**: None

**Acceptance Criteria**:
- AC1: Branch `feature/208-portal-landing-page` created from current master and pushed to remote.
- AC2: `git status` on branch shows clean working tree; `git log --oneline -1` shows branch diverged from master at the correct commit.

---

#### T1.2 — Middleware: add `/` public route early-return
**Estimated**: 1h
**Dependencies**: T1.1

**File**: `portal/src/lib/supabase/middleware.ts` — `handleRouting()`

Add an early-return block inside `handleRouting()` BEFORE the existing `pathname === "/login"` block:

```typescript
// Allow landing page for ALL users — never redirect from /
if (pathname === "/") {
  return supabaseResponse
}
```

This must appear before the login block so that authenticated users are not later caught by the protected-routes redirect.

**Acceptance Criteria**:
- AC1: Unauthenticated request to `/` returns `supabaseResponse` (200), not a redirect to `/login`. Verify with a unit test or manual `curl`.
- AC2: Authenticated request to `/` also returns `supabaseResponse` (200), not a redirect to `/dashboard`. The existing login/protected blocks are unchanged for all other routes.

---

#### T1.3 — CSS: add aurora, cursor-blink, mask-fade-left keyframes + utilities
**Estimated**: 1h
**Dependencies**: T1.1

**File**: `portal/src/app/globals.css`

Append to the end of the file (after the existing `glow-rose-pulse` animation):

```css
/* Landing page additions */
@keyframes cursor-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
.terminal-cursor {
  display: inline-block;
  width: 8px;
  height: 16px;
  background: oklch(0.75 0.15 350);
  animation: cursor-blink 1s step-end infinite;
}

@keyframes aurora-drift-1 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(5%, -8%) scale(1.1); }
  66% { transform: translate(-3%, 5%) scale(0.95); }
}
@keyframes aurora-drift-2 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(-8%, 5%) scale(0.9); }
  66% { transform: translate(5%, -3%) scale(1.05); }
}
.aurora-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
  opacity: 0.15;
}
.aurora-orb-1 {
  width: 600px; height: 600px;
  background: oklch(0.75 0.15 350);
  top: -200px; right: -100px;
  animation: aurora-drift-1 25s ease-in-out infinite;
}
.aurora-orb-2 {
  width: 500px; height: 500px;
  background: oklch(0.65 0.12 280);
  bottom: -150px; left: -100px;
  animation: aurora-drift-2 20s ease-in-out infinite;
}
.mask-fade-left {
  mask-image: linear-gradient(to right, transparent, black 40%);
  -webkit-mask-image: linear-gradient(to right, transparent, black 40%);
}

@media (prefers-reduced-motion: reduce) {
  .aurora-orb, .terminal-cursor, .glow-rose-pulse { animation: none; }
}
```

**Acceptance Criteria**:
- AC1: `npm run build` passes after CSS addition. No PostCSS/Tailwind compilation errors.
- AC2: `.terminal-cursor`, `.aurora-orb-1`, `.aurora-orb-2`, `.mask-fade-left`, `aurora-drift-1`, `aurora-drift-2`, and `cursor-blink` are all present in the compiled CSS output (verify with `grep` on `.next/static/css/`).

---

#### T1.4 — Install Magic UI components via shadcn registry
**Estimated**: 1h
**Dependencies**: T1.1

Run in `portal/`:

```bash
npx shadcn@latest add "https://magicui.design/r/blur-fade"
npx shadcn@latest add "https://magicui.design/r/number-ticker"
npx shadcn@latest add "https://magicui.design/r/text-shimmer"
```

If any component fails due to Tailwind v4 incompatibility, document the failure and implement a custom framer-motion equivalent instead — note the decision in a comment at the top of the affected component file.

**Acceptance Criteria**:
- AC1: Either the installed component file exists at `portal/src/components/magicui/` (or the shadcn-specified path) OR a custom equivalent is implemented and documented.
- AC2: `npm run build` passes after install. No import resolution errors related to the new packages.

---

### Phase 2: Image Generation

---

#### T2.1 — Generate Nikita hero base image
**Estimated**: 1h
**Dependencies**: T1.1

Use the nano-banana image editing tool with `docs/images-of-nikita/nikita.png` as source. Apply prompt from spec Section "Image Generation". Save result as `portal/public/images/nikita-hero.png`.

**Acceptance Criteria**:
- AC1: File `portal/public/images/nikita-hero.png` exists and is a valid PNG (non-zero byte size, readable by `next/image`).
- AC2: Image depicts the subject against a dark background with dramatic cinematic lighting; reviewed visually and approved.

---

#### T2.2 — Generate 9 mood variant images
**Estimated**: 2h
**Dependencies**: T2.1

Use `continue_editing` from the hero base for each of the 9 moods defined in the spec: playful, lustful, cold, intimate, angry, stressed, frustrated, crying, excited. Save to `portal/public/images/nikita-moods/{mood}.png`.

**Acceptance Criteria**:
- AC1: All 9 files exist in `portal/public/images/nikita-moods/` with the exact filenames from the spec.
- AC2: Each image is visually distinct and matches the mood descriptor in the spec (reviewed and approved before proceeding to Phase 4).

---

### Phase 3: Shared Components (TDD — tests first)

TDD protocol for this phase: write failing tests FIRST, commit with message `test(portal): [component] failing tests`, then implement, then commit with `feat(portal): [component] implementation`. Minimum two commits per component.

---

#### T3.1 — GlowButton: tests then implementation
**Estimated**: 2h
**Dependencies**: T1.3, T1.4

**Test file** (write first): `portal/src/components/landing/__tests__/glow-button.test.tsx`

Key test cases per spec:
- Renders with default "Meet Nikita" label
- External link (`href` starting with `http`) renders `ArrowUpRight` icon
- Internal link does not render `ArrowUpRight`
- `size` prop variant changes className (default vs sm vs lg)
- Has `rounded-full bg-primary glow-rose-pulse` classes
- No console errors on mount

**Implementation**: `portal/src/components/landing/glow-button.tsx`

Spring physics hover via framer-motion `useSpring` (`stiffness: 400, damping: 17`). `ArrowUpRight` from lucide-react for external links. Accepts `href`, `size`, `className`, `children`.

**Acceptance Criteria**:
- AC1: All tests in `glow-button.test.tsx` pass (`vitest run`).
- AC2: Component renders with `rounded-full`, `bg-primary`, `text-primary-foreground`, and `glow-rose-pulse` classes applied. External links include `target="_blank" rel="noopener noreferrer"` and the `ArrowUpRight` icon.

---

#### T3.2 — AuroraOrbs: tests then implementation
**Estimated**: 1.5h
**Dependencies**: T1.3

**Test file** (write first): `portal/src/components/landing/__tests__/aurora-orbs.test.tsx`

Key test cases:
- Renders two orb elements with classes `aurora-orb-1` and `aurora-orb-2`
- Both orbs have `aria-hidden="true"`
- Component has `pointer-events-none` on wrapper
- No framer-motion dependency (CSS-only animation)

**Implementation**: `portal/src/components/landing/aurora-orbs.tsx`

Two `<div>` elements with `.aurora-orb .aurora-orb-1` and `.aurora-orb .aurora-orb-2`. Wrapper is `position: absolute, inset-0, overflow-hidden, pointer-events-none`. Fully CSS-driven — no JS animation logic.

**Acceptance Criteria**:
- AC1: All tests pass. Both orb divs are present in the DOM and carry the correct CSS class names.
- AC2: No JS animation code exists in the component — animation is entirely driven by the CSS keyframes added in T1.3. `aria-hidden="true"` confirmed on both orb elements.

---

#### T3.3 — FallingPattern: tests then implementation
**Estimated**: 3h
**Dependencies**: T1.3

**Test file** (write first): `portal/src/components/landing/__tests__/falling-pattern.test.tsx`

Key test cases:
- Renders a `<canvas>` element
- Canvas has `aria-hidden="true"`
- Canvas has `pointer-events-none`
- When `matchMedia` mock returns `prefers-reduced-motion: reduce`, animation loop is not started (spy on `requestAnimationFrame`)

**Implementation**: `portal/src/components/landing/falling-pattern.tsx`

Adapt pattern from `portal/src/app/onboarding/components/ambient-particles.tsx`. Canvas-based matrix rain:
- Columns of falling characters at rose color `oklch(0.75 0.15 350 / 15%)` on void background
- Accepts `color` and `backgroundColor` props (with spec defaults)
- Checks `window.matchMedia("(prefers-reduced-motion: reduce)")` on mount — if true, draws static frame only
- Listens for MQL change events
- Cleans up `cancelAnimationFrame` and event listeners on unmount

**Acceptance Criteria**:
- AC1: All tests pass. Canvas element is present with `aria-hidden="true"` and `pointer-events-none`. With reduced-motion mock active, `requestAnimationFrame` is called zero times after the static draw.
- AC2: In a running browser (`npm run dev`), the matrix rain is visible in rose color at low opacity over the void background with no console errors.

---

### Phase 4: Section Components (TDD — tests first per component)

All components live in `portal/src/components/landing/`. Two commits per component: failing tests then implementation.

---

#### T4.1 — TelegramMockup: tests then implementation
**Estimated**: 2h
**Dependencies**: T3.1 (for GlowButton pattern reference), T1.3

**Test file**: `portal/src/components/landing/__tests__/telegram-mockup.test.tsx`

Key test cases:
- Renders all 3 conversation messages from spec (quantum entanglement, "That's actually really sweet", "-2 points" messages)
- "Her" messages visually distinguished from "You" messages via CSS class or data attribute
- Component has `aria-label` or is wrapped in a `<section>` for accessibility
- No framer-motion mock needed for message content (text is always in DOM; animation is optional enhancement)

**Implementation**: `portal/src/components/landing/telegram-mockup.tsx`

Glass card wrapper (`GlassCard` from `portal/src/components/glass/glass-card.tsx`). Static message bubbles styled like Telegram Dark theme. Framer-motion `useInView` triggers staggered message appearance (messages animate in sequentially with 300ms stagger). JetBrains Mono font for sender labels. Exact copy from spec Section 2.

**Acceptance Criteria**:
- AC1: All tests pass. All 3 message strings from spec are present in the DOM.
- AC2: "Her" message bubbles and "You" message bubbles are visually distinct (different background color or alignment). Component uses `GlassCard` as the outer container.

---

#### T4.2 — SystemTerminal: tests then implementation
**Estimated**: 2.5h
**Dependencies**: T1.3, T3.1

**Test file**: `portal/src/components/landing/__tests__/system-terminal.test.tsx`

Key test cases:
- All 14 system names from spec are present in the DOM (e.g., `conversation_pipeline`, `emotional_state_engine`, etc.)
- Terminal cursor element exists and has class `terminal-cursor`
- Stats bar renders 3 stat values: `742`, `5,533`, `86`
- `prefers-reduced-motion: reduce` — all lines render immediately (no sequential delay)

**Implementation**: `portal/src/components/landing/system-terminal.tsx`

Terminal window with JetBrains Mono font. `useInView` hook triggers sequential line reveal (50ms interval per line via `useState` + `useEffect` with `setInterval`). Checkmark characters (`✓`) turn green on reveal. Cursor blinks via `.terminal-cursor` class. Stats bar uses Magic UI `NumberTicker` (or custom framer-motion counter if Magic UI incompatible). `prefers-reduced-motion` check skips interval, reveals all lines immediately.

**Acceptance Criteria**:
- AC1: All tests pass. All 14 system names present in DOM. `terminal-cursor` class exists on cursor element. Stats bar shows `742`, `5,533`, `86`.
- AC2: On scroll into view in a live browser, terminal lines appear sequentially with ~50ms interval. Stats counter animates from 0 to final value. Reduced-motion users see all lines rendered immediately.

---

#### T4.3 — ChapterTimeline: tests then implementation
**Estimated**: 1.5h
**Dependencies**: T1.3

**Test file**: `portal/src/components/landing/__tests__/chapter-timeline.test.tsx`

Key test cases:
- Exactly 5 chapter dots render
- Labels `Ch1` through `Ch5` are all present in the DOM
- Chapter names `Spark`, `Intrigue`, `Investment`, `Intimacy`, `Home` all present
- Threshold values `55%`, `60%`, `65%`, `70%`, `75%` all present in the DOM
- Connector lines between dots are present (5 dots = 4 connectors)

**Implementation**: `portal/src/components/landing/chapter-timeline.tsx`

Horizontal timeline with 5 circular dots connected by lines. Data array contains all 5 chapters with names and thresholds. On mobile (< 768px), enables horizontal scroll (`overflow-x-auto`). Static component — no framer-motion dependency.

**Acceptance Criteria**:
- AC1: All tests pass. 5 dots, all labels, all names, all thresholds confirmed in DOM.
- AC2: On mobile viewport (375px width), component scrolls horizontally without breaking layout. On desktop, all 5 chapters are visible without scrolling.

---

#### T4.4 — HeroSection: tests then implementation
**Estimated**: 3h
**Dependencies**: T3.1, T3.3, T2.1

**Test file**: `portal/src/components/landing/__tests__/hero-section.test.tsx`

Key test cases:
- When `isAuthenticated={false}`: CTA button renders "Meet Nikita" with `href="https://t.me/Nikita_my_bot"`
- When `isAuthenticated={true}`: CTA button renders "Go to Dashboard" with `href="/dashboard"`
- H1 contains text "Don't Get Dumped"
- Eyebrow contains "She's watching" and "18+"
- Subheadline contains "She remembers everything"
- Scroll indicator element is present in DOM
- Nikita hero image has descriptive `alt` text
- `FallingPattern` is rendered (canvas element present)

**Implementation**: `portal/src/components/landing/hero-section.tsx`

Full viewport section (`min-h-screen`). 2-column layout on desktop (60/40), stacked on mobile. Left column: eyebrow + H1 (`clamp(3rem, 6vw, 6rem)`, font-black, tracking-tighter) + subheadline + `GlowButton`. Right column: `next/image` with `nikita-hero.png` + `.mask-fade-left` gradient. `FallingPattern` fills full viewport as background. Staggered framer-motion entrance: eyebrow (0ms) → H1 (150ms) → sub (300ms) → CTA (450ms) → image (200ms, 1200ms duration) → scroll indicator (2s delay). Ease: `[0.16, 1, 0.3, 1]`. All animations use `once: true`. Mobile: hero image shown above text at 50vh height.

Exact copy from spec:
- Eyebrow: `18+ · She's watching`
- H1: `Don't Get\nDumped.`
- Sub: `She remembers everything. She has her own life. And she will leave you.`

**Acceptance Criteria**:
- AC1: All tests pass. Auth-conditional CTA verified for both `isAuthenticated` states. H1, eyebrow, and subheadline exact text confirmed.
- AC2: In a live browser at desktop viewport (1280px), hero image visible on right with mask fade at left edge. At mobile viewport (375px), image stacks above text. `FallingPattern` canvas renders behind content.

---

#### T4.5 — PitchSection: tests then implementation
**Estimated**: 2h
**Dependencies**: T4.1 (TelegramMockup)

**Test file**: `portal/src/components/landing/__tests__/pitch-section.test.tsx`

Key test cases:
- 3 differentiator quotes are present: "She has opinions", "Forget her birthday", "Other apps are afraid"
- Bold-wrapped text within each quote is present (e.g., "And she's not afraid to tell you")
- `TelegramMockup` renders (all 3 conversation messages present)
- Section uses `<section>` semantic HTML

**Implementation**: `portal/src/components/landing/pitch-section.tsx`

2-column on desktop (50/50), single column on tablet/mobile with `TelegramMockup` below text. Left column: 3 differentiator quotes with bold emphasis as per spec. `useInView` triggers stagger on quote entry. `TelegramMockup` is imported and rendered in right column.

Exact copy:
1. "She has opinions. Strong ones. **And she's not afraid to tell you.**"
2. "Forget her birthday? Ignore her texts? **She keeps score.**"
3. "Other apps are afraid to say no. **Nikita will walk out the door.**"

**Acceptance Criteria**:
- AC1: All tests pass. All 3 quote strings confirmed in DOM. All 3 TelegramMockup messages confirmed.
- AC2: At desktop viewport (1280px), quotes and mockup are side-by-side (2 columns). At tablet (768px), they stack vertically.

---

#### T4.6 — SystemSection: tests then implementation
**Estimated**: 2h
**Dependencies**: T4.2 (SystemTerminal)

**Test file**: `portal/src/components/landing/__tests__/system-section.test.tsx`

Key test cases:
- All 14 system names from spec are present in the DOM (via SystemTerminal render)
- Section background is darker than default (`oklch(0.06 0 0)`)
- Stats bar is present with the 3 stat labels
- Section uses `<section>` semantic HTML with an accessible heading

**Implementation**: `portal/src/components/landing/system-section.tsx`

Full-width dark section (`background: oklch(0.06 0 0)`). Contains `SystemTerminal`. Stats bar below terminal: 3 columns showing `742 Python files`, `5,533 Tests passing`, `86 Specifications`. Section heading (visually hidden or styled as terminal prompt) for semantic structure.

**Acceptance Criteria**:
- AC1: All tests pass. All 14 system names present. Stats bar with 3 stat values confirmed.
- AC2: In a live browser, section background is visibly darker than surrounding sections. Terminal lines animate sequentially on scroll entry.

---

#### T4.7 — StakesSection: tests then implementation
**Estimated**: 2h
**Dependencies**: T4.3 (ChapterTimeline)

**Test file**: `portal/src/components/landing/__tests__/stakes-section.test.tsx`

Key test cases:
- Exactly 4 glass feature cards render
- Card titles "She Keeps Score", "She Tests You", "She Remembers", "She Calls You" all present
- `ChapterTimeline` renders with 5 dots
- Cards use `GlassCard` component (check for `glass-card` CSS class on card elements)
- Section uses `<section>` semantic HTML

**Implementation**: `portal/src/components/landing/stakes-section.tsx`

4 glass cards in 2×2 grid on desktop/tablet, 1×4 on mobile (`<640px`). Cards use `GlassCard variant="default"` with icon + title + description. Cards from spec:
1. "She Keeps Score" — Score decay, daily neglect penalty
2. "She Tests You" — Boss encounters, 3 strikes = game over
3. "She Remembers" — pgVector memory, past arguments recalled
4. "She Calls You" — ElevenLabs voice, real phone-like calls

`ChapterTimeline` rendered below cards.

**Acceptance Criteria**:
- AC1: All tests pass. All 4 card titles and `ChapterTimeline` 5 dots confirmed in DOM.
- AC2: Cards carry `glass-card` CSS class. At mobile viewport (375px), cards render in single column. `ChapterTimeline` is positioned below all cards.

---

#### T4.8 — CtaSection: tests then implementation
**Estimated**: 1.5h
**Dependencies**: T3.1 (GlowButton), T3.2 (AuroraOrbs)

**Test file**: `portal/src/components/landing/__tests__/cta-section.test.tsx`

Key test cases:
- When `isAuthenticated={false}`: `GlowButton` href is `https://t.me/Nikita_my_bot`
- When `isAuthenticated={true}`: `GlowButton` href is `/dashboard`
- H2 text "Think you can handle her?" is present
- Sub-text "She's on Telegram. She's waiting." is present
- Footer contains "© 2026 Nanoleq" and links to "Privacy" and "Terms"
- `AuroraOrbs` renders (both orb divs present)

**Implementation**: `portal/src/components/landing/cta-section.tsx`

Full-width section with `AuroraOrbs` as background (relative container, overflow-hidden). Centered content: H2 + `GlowButton` + subtext + footer text. `isAuthenticated` prop passed to `GlowButton` for conditional href. Footer: `© 2026 Nanoleq · Privacy · Terms`.

**Acceptance Criteria**:
- AC1: All tests pass. Auth-conditional href confirmed for both states. H2, subtext, and footer confirmed in DOM.
- AC2: `AuroraOrbs` renders behind section content. `overflow-hidden` on section container prevents orbs from extending outside section bounds.

---

#### T4.9 — LandingNav: tests then implementation
**Estimated**: 2h
**Dependencies**: T3.1 (GlowButton)

**Test file**: `portal/src/components/landing/__tests__/landing-nav.test.tsx`

Key test cases:
- When `isAuthenticated={false}`: nav CTA renders "Meet Nikita" with Telegram link
- When `isAuthenticated={true}`: nav CTA renders "Go to Dashboard"
- Nav wrapper has `position: fixed` and appropriate `z-index`
- Nav has glass card styling (check for `glass-card` or equivalent)
- Nav is initially hidden (`opacity-0` or `translate-y-full`) before scroll — mock `useMotionValue`

**Implementation**: `portal/src/components/landing/landing-nav.tsx`

`"use client"` component. Uses framer-motion `useScroll` to get `scrollY`. Nav becomes visible when `scrollY > window.innerHeight * 0.5`. Glass panel: `bg-white/5 backdrop-blur-md border-white/10`, no border-x/border-t/border-radius (spec: flush edge-to-edge bar). Fixed at top, full width. Contains brand name "Nikita" on left, `GlowButton` on right.

**Acceptance Criteria**:
- AC1: All tests pass. Auth-conditional CTA confirmed. Glass CSS class confirmed. Fixed positioning confirmed.
- AC2: In a live browser, nav is invisible on initial page load and smoothly fades in after scrolling past 50% of viewport height.

---

### Phase 5: Root Page Rewrite + Metadata

---

#### T5.1 — Rewrite `portal/src/app/page.tsx`
**Estimated**: 1h
**Dependencies**: T1.2, T4.4, T4.5, T4.6, T4.7, T4.8, T4.9

Replace the current redirect-only server component with the landing page server component per spec:

```tsx
import { createClient } from "@/lib/supabase/server"
import { LandingNav } from "@/components/landing/landing-nav"
import { HeroSection } from "@/components/landing/hero-section"
import { PitchSection } from "@/components/landing/pitch-section"
import { SystemSection } from "@/components/landing/system-section"
import { StakesSection } from "@/components/landing/stakes-section"
import { CtaSection } from "@/components/landing/cta-section"

export default async function LandingPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  const isAuthenticated = !!user
  return (
    <main className="bg-void min-h-screen">
      <LandingNav isAuthenticated={isAuthenticated} />
      <HeroSection isAuthenticated={isAuthenticated} />
      <PitchSection />
      <SystemSection />
      <StakesSection />
      <CtaSection isAuthenticated={isAuthenticated} />
    </main>
  )
}
```

**Acceptance Criteria**:
- AC1: `portal/src/app/page.tsx` no longer contains any `redirect()` calls. It exports a default async server component.
- AC2: Running `npm run build` with the new `page.tsx` produces no TypeScript errors. All 6 section components are imported and rendered.

---

#### T5.2 — Add OG/Twitter metadata to `portal/src/app/layout.tsx`
**Estimated**: 0.5h
**Dependencies**: T1.1

Update the exported `metadata` object in `portal/src/app/layout.tsx` per spec:

```tsx
export const metadata: Metadata = {
  title: "Nikita — Don't Get Dumped",
  description: "She remembers everything. She has her own life. And she will leave you. 5 chapters. 3 strikes. One relationship.",
  openGraph: {
    title: "Nikita — Don't Get Dumped",
    description: "She remembers everything. She has her own life. And she will leave you.",
    images: ["/opengraph-image.png"],
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
  },
}
```

Note: `/opengraph-image.png` does not need to exist for the build to pass — Next.js treats the metadata declaration as valid regardless.

**Acceptance Criteria**:
- AC1: `portal/src/app/layout.tsx` metadata object includes `openGraph.title`, `openGraph.description`, `openGraph.images`, `openGraph.type`, and `twitter.card`.
- AC2: `npm run build` passes. Page `<head>` rendered HTML (viewable via `curl localhost:3000` or build output) includes `<meta property="og:title" ...>` and `<meta name="twitter:card" content="summary_large_image">`.

---

### Phase 6: Unit Tests (Vitest) — Completion Pass

This phase covers any test files not yet complete from Phase 3/4 TDD cycles, and adds integration-level assertions.

---

#### T6.1–T6.12 — Verify all 9 unit test files pass

**Files**:
```
portal/src/components/landing/__tests__/glow-button.test.tsx       (T3.1)
portal/src/components/landing/__tests__/aurora-orbs.test.tsx       (T3.2)
portal/src/components/landing/__tests__/falling-pattern.test.tsx   (T3.3)
portal/src/components/landing/__tests__/telegram-mockup.test.tsx   (T4.1)
portal/src/components/landing/__tests__/system-terminal.test.tsx   (T4.2)
portal/src/components/landing/__tests__/chapter-timeline.test.tsx  (T4.3)
portal/src/components/landing/__tests__/hero-section.test.tsx      (T4.4)
portal/src/components/landing/__tests__/pitch-section.test.tsx     (T4.5)
portal/src/components/landing/__tests__/system-section.test.tsx    (T4.6)
portal/src/components/landing/__tests__/stakes-section.test.tsx    (T4.7)
portal/src/components/landing/__tests__/cta-section.test.tsx       (T4.8)
portal/src/components/landing/__tests__/landing-nav.test.tsx       (T4.9)
```

**framer-motion mock** (add to `portal/vitest.setup.ts` or per-file `vi.mock`):

```tsx
vi.mock("framer-motion", () => {
  const createMotionComponent = (tag: string) =>
    ({ children, ...props }: any) => createElement(tag, props, children)
  const motion = new Proxy({}, {
    get: (_, tag: string) => createMotionComponent(tag),
  })
  return {
    motion,
    AnimatePresence: ({ children }: any) => children,
    useScroll: () => ({ scrollY: { get: () => 0 } }),
    useTransform: (_: any, __: any, values: any[]) => values[0],
    useInView: () => true,
    useMotionValue: (v: any) => ({ get: () => v }),
    useSpring: (v: any) => v,
  }
})
```

**Estimated**: 2h (gap-fill and final polish across all test files)
**Dependencies**: T3.1–T3.3, T4.1–T4.9

**Acceptance Criteria**:
- AC1: `cd portal && npm run test:ci` exits with code 0. All 9 test files pass with zero failures.
- AC2: All 7 key spec test cases pass: (1) unauthed CTA links Telegram, (2) authed CTA links dashboard, (3) all sections render without crash, (4) reduced-motion respected, (5) images have alt text, (6) chapter timeline 5 dots with labels + thresholds, (7) system terminal 14 system names present.

---

### Phase 7: E2E Tests (Playwright)

---

#### T7.1 — Create `portal/e2e/landing.spec.ts`
**Estimated**: 2h
**Dependencies**: T5.1, T1.2

**File**: `portal/e2e/landing.spec.ts`

Test cases per spec:
1. Unauthenticated visit to `/` renders landing page (not a redirect to `/login`) — assert URL stays at `/` and at least one landing-page heading is visible
2. Authenticated visit to `/` renders landing page with "Go to Dashboard" CTA — requires E2E auth bypass cookie (`e2e-role=player`)
3. `/dashboard` still works for authenticated users (existing route unchanged)
4. Scroll past 50% viewport → floating nav becomes visible (use `page.evaluate` to scroll)
5. Mobile viewport (375×812) → hero is stacked, page renders without horizontal overflow
6. All section headings visible after scrolling: "Don't Get Dumped", "Who Is Nikita" (or pitch section heading), "Under the Hood" (or system heading), and CTA heading "Think you can handle her?"

**Acceptance Criteria**:
- AC1: All 6 test cases pass in CI (`npm run test:e2e -- --project=chromium landing.spec.ts`). No flakiness (tests pass 2 consecutive runs).
- AC2: Test at line 1 explicitly asserts `page.url()` does NOT contain `/login` and at least one heading element is visible. Test at line 4 uses `page.evaluate(() => window.scrollTo(0, window.innerHeight))` then waits for nav visibility.

---

#### T7.2 — Update `portal/e2e/auth-flow.spec.ts`
**Estimated**: 1h
**Dependencies**: T1.2, T5.1

Current test at line 15–23 asserts: unauthenticated visit to `/` either redirects to `/login` OR stays at `/`. After the middleware change, the landing page ALWAYS renders at `/` — the redirect branch of that assertion is no longer correct.

Update the test to:

```typescript
test("unauthenticated user at / sees landing page", async ({ page }) => {
  await page.goto("/", { waitUntil: "domcontentloaded", timeout: 30_000 })
  await page.waitForTimeout(1_000)
  // Landing page renders — URL stays at / and hero heading is visible
  expect(page.url()).toMatch(/\/$/)
  await expect(page.getByRole("heading", { name: /Don't Get Dumped/i })).toBeVisible()
})
```

All other tests in `auth-flow.spec.ts` are unaffected (they target `/login`, `/dashboard`, `/admin`).

**Acceptance Criteria**:
- AC1: Updated test passes. The old assertion accepting `/login` redirect is removed.
- AC2: Full `auth-flow.spec.ts` suite runs without failures after the update (`npm run test:e2e -- auth-flow.spec.ts`).

---

### Phase 8: Figma Code Connect

---

#### T8.1 — Create `.figma.js` Code Connect templates for 4 components
**Estimated**: 1.5h
**Dependencies**: T3.1, T4.1, T4.2, T4.9

Per spec Section "Figma Design System" (file key: `dGAxXIglEjfFiTOnwtoSxv`):

Create Code Connect mapping files:

```
portal/src/components/landing/glow-button.figma.js
portal/src/components/glass/glass-card.figma.js
portal/src/components/landing/system-terminal.figma.js
portal/src/components/landing/telegram-mockup.figma.js
```

Each file follows the Figma Code Connect template format linking the Figma component node to the React source file. Use the `figma:figma-code-connect` skill or write templates manually per the Figma Code Connect SDK.

**Acceptance Criteria**:
- AC1: All 4 `.figma.js` files exist with valid Code Connect structure (import `figma` from `@figma/code-connect`, call `figma.connect(...)` with the correct file key and node ID placeholder).
- AC2: Files do not cause TypeScript or lint errors (`npm run lint` passes, `tsc --noEmit` passes).

---

#### T8.2 — Publish Code Connect mappings
**Estimated**: 0.5h
**Dependencies**: T8.1

Run `figma connect publish` (or use the Figma MCP `send_code_connect_mappings` tool) to push the 4 mappings to the Figma file. Requires `FIGMA_ACCESS_TOKEN` in environment.

**Acceptance Criteria**:
- AC1: Publish command exits with code 0 or MCP tool returns success response.
- AC2: In the Figma file (key `dGAxXIglEjfFiTOnwtoSxv`), at least one component's Code panel shows the mapped React snippet.

---

### Phase 9: Build Verification + Visual QA

---

#### T9.1 — Full production build verification
**Estimated**: 1h
**Dependencies**: All Phase 3–5 tasks complete

Run in `portal/`:

```bash
npm run build
npm run lint
npm run type-check
npm run test:ci
```

Fix any TypeScript errors, ESLint violations, or build-time errors before proceeding.

**Acceptance Criteria**:
- AC1: `npm run build` exits with code 0. Zero errors in Next.js build output. No `Module not found` or TypeScript errors.
- AC2: `npm run lint` exits with code 0. `npm run test:ci` exits with code 0.

---

#### T9.2 — Existing routes smoke test
**Estimated**: 1h
**Dependencies**: T9.1

Verify all existing routes still function after the landing page is introduced:

```bash
npm run test:e2e -- --project=chromium auth-flow.spec.ts login.spec.ts dashboard.spec.ts admin.spec.ts
```

Manually verify (or via Playwright) that:
- `/login` still renders the magic-link login form
- `/dashboard` still redirects unauthenticated users to `/login`
- `/admin` still redirects non-admin users to `/dashboard`
- `/onboarding` route still renders

**Acceptance Criteria**:
- AC1: All 4 existing E2E spec files pass without regressions after the middleware and page.tsx changes.
- AC2: Manual (or Playwright) verification confirms that authenticated admin users are redirected to `/admin` (not the landing page) when they log in via `/login`.

---

#### T9.3 — Visual QA review
**Estimated**: 1.5h
**Dependencies**: T9.1

Review each section at 3 viewports in a running dev server (`npm run dev`):
- Mobile: 375×812
- Tablet: 768×1024
- Desktop: 1440×900

Checklist:
- [ ] FallingPattern renders behind hero content
- [ ] Hero image fades left-to-void correctly
- [ ] H1 font-size scales appropriately at each viewport
- [ ] LandingNav appears on scroll, hidden at top
- [ ] Telegram mockup messages visually distinct
- [ ] System terminal lines animate on scroll
- [ ] Stats counter animates
- [ ] Chapter timeline horizontal-scrolls on mobile
- [ ] Aurora orbs visible in CTA section
- [ ] No horizontal overflow on any viewport
- [ ] Rose glow pulse on hero CTA button

**Acceptance Criteria**:
- AC1: All checklist items above verified and checked off. Zero console errors on any viewport.
- AC2: No horizontal scroll bar visible at 375px viewport width. `document.documentElement.scrollWidth === window.innerWidth` (verify via browser devtools).

---

### Phase 10: PR + QA Review

---

#### T10.1 — Create PR
**Estimated**: 0.5h
**Dependencies**: T9.1, T9.2, T9.3

```bash
gh pr create \
  --title "feat(portal): landing page hero — Spec 208" \
  --body "..."
```

PR body must include:
- Summary bullets referencing the spec
- Test plan (unit tests + E2E tests)
- Screenshots at 3 viewports (mobile, tablet, desktop)
- `Closes #208` reference

**Acceptance Criteria**:
- AC1: PR exists on GitHub targeting master. All CI checks (backend-ci, portal-ci, e2e) are triggered.
- AC2: PR body includes at least one screenshot attachment per viewport (mobile, tablet, desktop) showing the rendered landing page.

---

#### T10.2 — QA review loop
**Estimated**: 2h
**Dependencies**: T10.1

Run `/qa-review --pr [N]`. Fix all blocking and important issues found. Re-run until 0 blocking + 0 important issues.

**Acceptance Criteria**:
- AC1: `/qa-review` returns 0 blocking issues and 0 important issues.
- AC2: All CI checks are green. Squash-merge to master proceeds per PR workflow rules.

---

## Dependency Graph

```
T1.1 (branch)
  ├── T1.2 (middleware fix)
  ├── T1.3 (CSS additions)
  ├── T1.4 (Magic UI install)
  └── T2.1 (hero image)
       └── T2.2 (mood variants)

T1.3 → T3.1 (GlowButton tests+impl)
T1.3 → T3.2 (AuroraOrbs tests+impl)
T1.3 → T3.3 (FallingPattern tests+impl)

T3.1, T3.3, T2.1 → T4.4 (HeroSection)
T3.1 → T4.1 (TelegramMockup)
T1.3 → T4.2 (SystemTerminal)
T1.3 → T4.3 (ChapterTimeline)
T4.1 → T4.5 (PitchSection)
T4.2 → T4.6 (SystemSection)
T4.3 → T4.7 (StakesSection)
T3.1, T3.2 → T4.8 (CtaSection)
T3.1 → T4.9 (LandingNav)

T1.2, T4.4, T4.5, T4.6, T4.7, T4.8, T4.9 → T5.1 (page.tsx rewrite)
T1.1 → T5.2 (metadata)

T3.1–T3.3, T4.1–T4.9 → T6.1–T6.12 (unit test verification pass)

T5.1, T1.2 → T7.1 (landing E2E spec)
T1.2, T5.1 → T7.2 (auth-flow update)

T3.1, T4.1, T4.2, T4.9 → T8.1 → T8.2 (Figma Code Connect)

T3.1–T3.3, T4.1–T4.9, T5.1, T5.2 → T9.1 (build verify)
T9.1 → T9.2 (existing routes smoke test)
T9.1 → T9.3 (visual QA)

T9.1, T9.2, T9.3 → T10.1 → T10.2
```

Parallelizable groups:
- T1.2, T1.3, T1.4, T2.1 can run in parallel after T1.1
- T3.1, T3.2, T3.3 can run in parallel after T1.3
- T4.1, T4.2, T4.3 can run in parallel after their dependencies are met
- T4.4, T4.5, T4.6, T4.7, T4.8, T4.9 can run in parallel once their sub-dependencies are met
- T5.1 and T5.2 can run in parallel
- T7.1 and T7.2 can run in parallel
- T8.1, T9.1 can run in parallel after all Phase 4/5 tasks

---

## Files Modified / Created

### Modified (3 files)
```
portal/src/app/page.tsx                          # Rewrite: redirect → landing page server component
portal/src/lib/supabase/middleware.ts            # Add / public route early-return in handleRouting()
portal/src/app/globals.css                       # Add cursor-blink, aurora-drift-1/2, mask-fade-left
portal/src/app/layout.tsx                        # Update metadata: OG + Twitter tags
portal/e2e/auth-flow.spec.ts                     # Update "/" test: assert landing page, not redirect
```

### Created — Components (12 files)
```
portal/src/components/landing/glow-button.tsx
portal/src/components/landing/aurora-orbs.tsx
portal/src/components/landing/falling-pattern.tsx
portal/src/components/landing/telegram-mockup.tsx
portal/src/components/landing/system-terminal.tsx
portal/src/components/landing/chapter-timeline.tsx
portal/src/components/landing/hero-section.tsx
portal/src/components/landing/pitch-section.tsx
portal/src/components/landing/system-section.tsx
portal/src/components/landing/stakes-section.tsx
portal/src/components/landing/cta-section.tsx
portal/src/components/landing/landing-nav.tsx
```

### Created — Unit Tests (9 files)
```
portal/src/components/landing/__tests__/glow-button.test.tsx
portal/src/components/landing/__tests__/aurora-orbs.test.tsx
portal/src/components/landing/__tests__/falling-pattern.test.tsx
portal/src/components/landing/__tests__/telegram-mockup.test.tsx
portal/src/components/landing/__tests__/system-terminal.test.tsx
portal/src/components/landing/__tests__/chapter-timeline.test.tsx
portal/src/components/landing/__tests__/hero-section.test.tsx
portal/src/components/landing/__tests__/pitch-section.test.tsx
portal/src/components/landing/__tests__/system-section.test.tsx
portal/src/components/landing/__tests__/stakes-section.test.tsx
portal/src/components/landing/__tests__/cta-section.test.tsx
portal/src/components/landing/__tests__/landing-nav.test.tsx
```

### Created — E2E Tests (1 file)
```
portal/e2e/landing.spec.ts
```

### Created — Images (10 files)
```
portal/public/images/nikita-hero.png
portal/public/images/nikita-moods/playful.png
portal/public/images/nikita-moods/lustful.png
portal/public/images/nikita-moods/cold.png
portal/public/images/nikita-moods/intimate.png
portal/public/images/nikita-moods/angry.png
portal/public/images/nikita-moods/stressed.png
portal/public/images/nikita-moods/frustrated.png
portal/public/images/nikita-moods/crying.png
portal/public/images/nikita-moods/excited.png
```

### Created — Figma Code Connect (4 files)
```
portal/src/components/landing/glow-button.figma.js
portal/src/components/glass/glass-card.figma.js
portal/src/components/landing/system-terminal.figma.js
portal/src/components/landing/telegram-mockup.figma.js
```

### Possibly Created — Magic UI (if install succeeds, 3 files)
```
portal/src/components/magicui/blur-fade.tsx
portal/src/components/magicui/number-ticker.tsx
portal/src/components/magicui/text-shimmer.tsx
```

---

## Notes

**N1 — Middleware insertion point**: The early-return for `/` must go inside `handleRouting()` BEFORE the `pathname === "/login"` block. If placed at the end, authenticated users will still be caught by the protected-routes redirect block (line 67-69 in the current file). The spec is explicit about this ordering.

**N2 — TDD commit discipline**: Every component in Phases 3 and 4 requires a minimum of two git commits: one for failing tests, one for passing implementation. This is enforced by the SDD rules in `.claude/CLAUDE.md`. Do not squash these commits locally — the PR history must show both.

**N3 — Magic UI Tailwind v4 compatibility**: Magic UI components were built for Tailwind v3 with `tailwind.config.ts`. This project uses Tailwind v4 CSS-first with `@theme inline`. If an installed Magic UI component uses `tailwind.config.js` imports or `theme()` functions, it will need manual adaptation. In that case: delete the Magic UI file, implement the equivalent using framer-motion `useSpring`/`useMotionValue` directly, and add a comment explaining the fallback.

**N4 — FallingPattern matrix rain approach**: The `ambient-particles.tsx` reference uses upward-drifting particles. The FallingPattern needs downward-falling characters (matrix style). The core canvas loop structure is reusable but the draw logic and character set will differ. Rose color at 15% opacity is very subtle — verify it is visible against the void background in the actual browser before proceeding to HeroSection.

**N5 — auth-flow.spec.ts update scope**: Only the first test in the "Unauthenticated Redirects" describe block needs updating (line 15–23). The other two tests in that block (`/dashboard` and `/admin`) are unaffected by this change. Do not modify them.

**N6 — `isAuthenticated` prop flow**: The root `page.tsx` is a server component that reads auth state. It passes `isAuthenticated` as a boolean prop to `LandingNav`, `HeroSection`, and `CtaSection`. Client components that need this prop accept it as a standard prop (not via `useUser` hook or context) — this avoids a client/server boundary for what is purely static-at-render data.

**N7 — Mood images scope**: The 9 mood variant images in Phase 2 are generated and placed in `portal/public/images/nikita-moods/` but are NOT referenced by any landing page component in this spec. They are generated now for future use (Spec 209 or similar). Do not add `<Image>` references to them in any landing component.

**N8 — Accessibility: `<section>` semantic requirement**: Every landing section component (`HeroSection`, `PitchSection`, `SystemSection`, `StakesSection`, `CtaSection`) must use `<section>` as the root element and include either a visible or visually-hidden heading (`<h2>` or `aria-label`) for screen-reader navigation. The `LandingNav` must use `<nav>` with `aria-label="Site navigation"`.

**N9 — Copy tone enforcement**: No component copy may contain "AI", "artificial", "virtual", "simulation", "chatbot", "machine learning", or "language model". If reviewing the spec copy for any section, treat Nikita as a real person throughout. The SystemSection is the single exception — it describes technical systems, but even there, system names like `emotional_state_engine` refer to Nikita's internal states, not "AI features".

---

## Handover: Plan Complete — Ready for Implementation

**From**: implementation-planner
**To**: executor-implement-verify
**Task**: Spec 208 — Portal Landing Page Hero
**Status**: PLAN_READY
**Date**: 2026-04-03

### Plan Summary
- Total tasks: 42 (grouped in 10 phases)
- Estimated: ~52h
- New files: 38 (12 components, 12 test files, 1 E2E spec, 10 images, 4 Figma files, optional 3 Magic UI)
- Modified files: 5

### Critical Information
- Plan location: `specs/208-portal-landing-page-hero/plan.md`
- Branch: `feature/208-portal-landing-page` (create from master)
- TDD required: Write failing tests FIRST for every component. Two commits minimum per component.
- Middleware ordering: Early-return for `/` must go BEFORE the login block in `handleRouting()`
- Magic UI fallback: If Tailwind v4 incompatible, implement custom framer-motion equivalents (documented in code)
- framer-motion mock: Use the Proxy-based mock from spec Section "Testing Strategy" for all component tests

### Priority Order
1. Phase 1 (Infrastructure) — T1.1 → T1.2, T1.3, T1.4 in parallel
2. Phase 2 (Images) — T2.1 → T2.2
3. Phase 3 (Shared components, TDD) — T3.1, T3.2, T3.3 in parallel
4. Phase 4 (Section components, TDD) — bottom-up: T4.1–T4.3, then T4.4–T4.9
5. Phase 5 (Root page + metadata) — T5.1, T5.2
6. Phase 6 (Unit test verification pass) — T6.1–T6.12
7. Phase 7 (E2E) — T7.1, T7.2
8. Phase 8 (Figma Code Connect) — T8.1 → T8.2
9. Phase 9 (Build + Visual QA) — T9.1 → T9.2, T9.3
10. Phase 10 (PR + QA Review) — T10.1 → T10.2

### Next Steps
Executor should implement tasks in phase order. Verify each component's ACs before moving to the next. Run `npm run test:ci` after every phase. Do not proceed to Phase 5 until all Phase 4 components have both failing-test commit and passing-implementation commit.
