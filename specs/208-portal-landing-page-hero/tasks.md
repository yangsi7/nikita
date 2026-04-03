# Tasks: Spec 208 — Portal Landing Page Hero

**Generated**: 2026-04-03
**Feature**: 208 — portal-landing-page-hero
**Input**: `specs/208-portal-landing-page-hero/spec.md`, `specs/208-portal-landing-page-hero/plan.md`
**Branch**: `feature/208-portal-landing-page`
**Total Tasks**: 42 | **Estimated**: ~52h

**Prerequisites**:
- spec.md ✅ (GATE 2 PASS — 0 CRITICAL, 0 HIGH)
- plan.md ✅ (42 tasks, 10 phases, dependency graph defined)
- validation-findings.md ✅ (10 MEDIUM accepted/documented)

**Organization**: Grouped by user story (P1→P2→P3). Infrastructure and images are blocking prerequisites.

**TDD Protocol**: Two commits per component — `test(portal): [component] failing tests` first, then `feat(portal): [component] implementation`. No exceptions.

**Intelligence-First**: Query project-intel.mjs before reading files in landing components:
```bash
project-intel.mjs --search "landing" --type tsx --json
project-intel.mjs --dependencies portal/src/app/page.tsx --json
project-intel.mjs --symbols portal/src/app/onboarding/components/ambient-particles.tsx --json
```

---

## Phase 1: Setup (Blocking Prerequisites)

**Purpose**: Branch, infrastructure changes, and dependencies that ALL stories require before starting.

**⚠️ CRITICAL**: No user story work starts until T1.1–T1.4 are complete.

---

- [ ] T001 Create feature branch `feature/208-portal-landing-page`
  - **AC1**: Branch exists and is pushed to remote (`git push -u origin feature/208-portal-landing-page`).
  - **AC2**: `git log --oneline -1` on branch shows correct divergence from master.
  - **Dependencies**: None

- [ ] T002 [P] Middleware: add `/` public route early-return in `portal/src/lib/supabase/middleware.ts`
  - **AC1**: Unauthenticated request to `/` returns 200, not redirect to `/login`.
  - **AC2**: Authenticated request to `/` returns 200, not redirect to `/dashboard`. Existing login/protected blocks unchanged.
  - **AC3**: Admin user at `/` sees landing page (not redirect to `/admin`). The early-return fires before all role-based routing logic — admins are users too and should see the landing page.
  - **Evidence**: `handleRouting()` receives `pathname` — add `if (pathname === "/") return supabaseResponse` BEFORE the `pathname === "/login"` block.
  - **Dependencies**: T001

- [ ] T003 [P] CSS + SEO infrastructure: add keyframes to globals.css, create robots.txt, extend vitest.setup.ts
  - **AC1**: `npm run build` passes. `.terminal-cursor`, `.aurora-orb-1`, `.aurora-orb-2`, `.mask-fade-left`, keyframes `aurora-drift-1`, `aurora-drift-2`, `cursor-blink` present in compiled CSS.
  - **AC2**: `portal/public/robots.txt` exists with `Allow: /`, `Disallow: /dashboard`, `Disallow: /admin`, `Disallow: /login`, `Disallow: /auth`, and `Sitemap: https://nikita.game/sitemap.xml`.
  - **AC3**: `portal/vitest.setup.ts` includes global framer-motion Proxy mock (covering all `motion.*` tags) AND `window.matchMedia` mock — so no per-file mocking needed in any of the 9 test files.
  - **Evidence**: Append CSS to end of globals.css (after `glow-rose-pulse`). robots.txt blocks authenticated routes from indexing. vitest.setup.ts mock pattern specified in plan "VITEST SETUP ADDITIONS NEEDED".
  - **Dependencies**: T001

- [ ] T004 [P] Install Magic UI registry components (blur-fade, number-ticker, text-shimmer) in `portal/`
  - **AC1**: Component files exist at shadcn-specified path OR custom framer-motion equivalents implemented with a comment documenting the fallback.
  - **AC2**: `npm run build` passes. No import resolution errors.
  - **Commands**: `npx shadcn@latest add "https://magicui.design/r/blur-fade"` (and number-ticker, text-shimmer).
  - **Dependencies**: T001

**Checkpoint**: Branch exists, middleware patched, CSS extended, Magic UI ready → user story work begins.

---

## Phase 2: Image Generation

**Purpose**: Hero image and mood variants required by HeroSection (T4.4 depends on T002-phase).

**⚠️ Required before Phase 4 HeroSection (T013).**

---

- [ ] T005 Generate Nikita hero base image via nano-banana `edit_image`
  - **AC1**: File `portal/public/images/nikita-hero.png` exists and is non-zero bytes.
  - **AC2**: Image depicts subject in black top, dark background, dramatic cinematic lighting — reviewed and approved visually.
  - **Source**: `docs/images-of-nikita/nikita.png`
  - **Prompt**: "Same young blonde woman but in a fitted black top. More mysterious and seductive expression with a subtle knowing glint. Slightly parted lips. Dramatic cinematic lighting on dark background. Photorealistic, maintaining same face and hair."
  - **Dependencies**: T001

- [ ] T006 Generate 9 mood variant images via nano-banana `continue_editing`
  - **AC1**: All 9 files exist in `portal/public/images/nikita-moods/` with exact filenames: `playful.png`, `lustful.png`, `cold.png`, `intimate.png`, `angry.png`, `stressed.png`, `frustrated.png`, `crying.png`, `excited.png`.
  - **AC2**: Each image is visually distinct and matches the mood descriptor in spec Section "Image Generation".
  - **Dependencies**: T005

**Checkpoint**: Hero image approved → HeroSection implementation can proceed.

---

## Phase 3: User Story 1 — Shared Components (P1) 🎯

**From spec**: Visitors can see a cohesive, animated landing page with glass design system components, rose glow CTAs, and animated backgrounds that communicate the dark cyberpunk aesthetic.

**Goal**: Three shared building-block components used across all sections. Must exist before any section component can be built.

**Independent Test**: Each component renders in isolation with correct visual properties, accessibility attributes, and reduced-motion behavior.

**Acceptance Criteria**:
- AC-REQ-007: GlowButton renders with `rounded-full`, `bg-primary`, `glow-rose-pulse`, external link with `ArrowUpRight`
- AC-REQ-008: AuroraOrbs renders two `aria-hidden` orb divs, CSS-only animation (no JS)
- AC-REQ-009: FallingPattern canvas renders, `aria-hidden`, stops animation with `prefers-reduced-motion: reduce`

### Intelligence Queries for User Story 1

```bash
# Understand onboarding animation pattern to adapt for FallingPattern
project-intel.mjs --symbols portal/src/app/onboarding/components/ambient-particles.tsx --json

# Find existing GlassCard to understand component conventions
project-intel.mjs --search "GlassCard" --type tsx --json

# Understand existing button patterns
project-intel.mjs --search "glow-rose-pulse" --json
```

### Tests for User Story 1 ⚠️ WRITE TESTS FIRST

- [ ] T007 [P] [US1] GlowButton failing tests in `portal/src/components/landing/__tests__/glow-button.test.tsx`
  - **Tests**: AC-REQ-007 (external link detection, size variants, class names, ArrowUpRight icon)
  - **Verify**: Tests FAIL before implementation
  - **framer-motion mock**: Use Proxy catch-all (see spec Testing Strategy section)
  - **Dependencies**: T003, T004

- [ ] T008 [P] [US1] AuroraOrbs failing tests in `portal/src/components/landing/__tests__/aurora-orbs.test.tsx`
  - **Tests**: AC-REQ-008 (two orb elements, aria-hidden, pointer-events-none, no JS animation code)
  - **Verify**: Tests FAIL before implementation
  - **Dependencies**: T003

- [ ] T009 [P] [US1] FallingPattern failing tests in `portal/src/components/landing/__tests__/falling-pattern.test.tsx`
  - **Tests**: AC-REQ-009 (canvas element, aria-hidden, pointer-events-none, reduced-motion spy on requestAnimationFrame)
  - **Verify**: Tests FAIL before implementation
  - **Dependencies**: T003

### Implementation for User Story 1

- [ ] T010 [P] [US1] Implement GlowButton in `portal/src/components/landing/glow-button.tsx`
  - **Evidence**: Spec "Shared Components > GlowButton". spring physics `stiffness: 400, damping: 17`, ArrowUpRight from lucide-react for external href.
  - **Tests**: T007
  - **Dependencies**: T007
  - **Commit**: `feat(portal): GlowButton implementation`

- [ ] T011 [P] [US1] Implement AuroraOrbs in `portal/src/components/landing/aurora-orbs.tsx`
  - **Evidence**: Spec "Shared Components > AuroraOrbs". Two `<div>` with `.aurora-orb .aurora-orb-1/2`, position absolute, overflow-hidden wrapper, `aria-hidden="true"` on both. No JS — CSS keyframes from T003.
  - **Tests**: T008
  - **Dependencies**: T008, T003
  - **Commit**: `feat(portal): AuroraOrbs CSS-only implementation`

- [ ] T012 [P] [US1] Implement FallingPattern in `portal/src/components/landing/falling-pattern.tsx`
  - **Evidence**: Adapt `portal/src/app/onboarding/components/ambient-particles.tsx`. Canvas-based matrix rain, rose color at 15% opacity, void background. Checks `window.matchMedia("(prefers-reduced-motion: reduce)")` — static frame only if true. Cleanup `cancelAnimationFrame` + event listeners on unmount.
  - **Tests**: T009
  - **Dependencies**: T009, T003
  - **Commit**: `feat(portal): FallingPattern canvas matrix rain`

### Verification for User Story 1

- [ ] T013 [US1] Run all US1 tests — `cd portal && npm run test -- --testPathPattern="glow-button|aurora-orbs|falling-pattern"` — verify all pass
- [ ] T014 [US1] Verify all P1 shared component ACs satisfied

**Checkpoint**: GlowButton, AuroraOrbs, FallingPattern all pass tests. Ready for section components.

---

## Phase 4: User Story 2 — Section Components (P1) 🎯

**From spec**: Visitors can scroll through 5 distinct sections (Hero, Pitch, System, Stakes, CTA) plus a floating nav, each with animated reveals, correct copy, and responsive layouts at mobile/tablet/desktop.

**Goal**: All 9 section/sub-components built TDD. Each component independently renderable and testable.

**Independent Test**: Each section renders without crash, correct DOM text present, auth-conditional CTAs correct, responsive classes present.

**Acceptance Criteria**:
- AC-REQ-010: TelegramMockup shows all 3 messages from spec, "her" vs "you" visually distinct
- AC-REQ-011: SystemTerminal shows all 14 system names, terminal-cursor class, stats bar with 3 values
- AC-REQ-012: ChapterTimeline shows 5 dots with Ch1–Ch5, names, 55%–75% thresholds
- AC-REQ-013: HeroSection — auth-conditional CTA, exact copy, FallingPattern canvas, Nikita image alt text
- AC-REQ-014: PitchSection — 3 differentiator quotes with bold emphasis, TelegramMockup rendered
- AC-REQ-015: SystemSection — 14 system names via SystemTerminal, darker bg, 3 stats
- AC-REQ-016: StakesSection — 4 glass cards with correct titles, ChapterTimeline rendered
- AC-REQ-017: CtaSection — auth-conditional href, H2 text, footer, AuroraOrbs present
- AC-REQ-018: LandingNav — auth-conditional CTA, fixed positioning, glass styling, hidden initially

### Intelligence Queries for User Story 2

```bash
# Find GlassCard component
project-intel.mjs --search "glass-card" --type tsx --json

# Understand useInView patterns in existing portal code
project-intel.mjs --search "useInView" --type tsx --json

# Check if existing vitest.setup.ts already has framer-motion mock
project-intel.mjs --search "vi.mock.*framer-motion" --json
```

### Tests + Implementation for User Story 2 (TDD per component)

#### Sub-components (no section dependencies)

- [ ] T015 [P] [US2] TelegramMockup: write failing tests in `portal/src/components/landing/__tests__/telegram-mockup.test.tsx`
  - **Tests**: AC-REQ-010 (3 messages, "her"/"you" distinction, accessible wrapper)
  - **Verify**: Tests FAIL before implementation
  - **Dependencies**: T003, T010 (GlowButton pattern reference)

- [ ] T016 [P] [US2] TelegramMockup implementation in `portal/src/components/landing/telegram-mockup.tsx`
  - **Evidence**: Glass card wrapper from `portal/src/components/glass/glass-card.tsx`. Static bubbles styled like Telegram Dark. Messages from spec Section 2 exact copy. framer-motion `useInView` stagger optional enhancement.
  - **Tests**: T015
  - **Dependencies**: T015
  - **Commit**: `feat(portal): TelegramMockup component`

- [ ] T017 [P] [US2] SystemTerminal: write failing tests in `portal/src/components/landing/__tests__/system-terminal.test.tsx`
  - **Tests**: AC-REQ-011 (14 system names, terminal-cursor class, stats 742/5533/86, reduced-motion renders all immediately)
  - **Verify**: Tests FAIL before implementation
  - **Dependencies**: T003

- [ ] T018 [P] [US2] SystemTerminal implementation in `portal/src/components/landing/system-terminal.tsx`
  - **Evidence**: JetBrains Mono, `useInView` + `useState` + `useEffect` interval (50ms per line), checkmarks `✓` in green on reveal. `.terminal-cursor` class. Stats bar uses Magic UI `NumberTicker` or custom counter if incompatible. `prefers-reduced-motion` skips interval.
  - **Tests**: T017
  - **Dependencies**: T017, T004
  - **Commit**: `feat(portal): SystemTerminal animated component`

- [ ] T019 [P] [US2] ChapterTimeline: write failing tests in `portal/src/components/landing/__tests__/chapter-timeline.test.tsx`
  - **Tests**: AC-REQ-012 (5 dots, Ch1–Ch5, Spark/Intrigue/Investment/Intimacy/Home, 55%/60%/65%/70%/75%)
  - **Verify**: Tests FAIL before implementation
  - **Dependencies**: T003

- [ ] T020 [P] [US2] ChapterTimeline implementation in `portal/src/components/landing/chapter-timeline.tsx`
  - **Evidence**: Horizontal, 5 dots + 4 connectors. `overflow-x-auto` on mobile (< 768px). Static — no framer-motion dependency.
  - **Tests**: T019
  - **Dependencies**: T019
  - **Commit**: `feat(portal): ChapterTimeline component`

#### Section components (depend on sub-components)

- [ ] T021 [P] [US2] HeroSection: write failing tests in `portal/src/components/landing/__tests__/hero-section.test.tsx`
  - **Tests**: AC-REQ-013 (unauthed CTA→Telegram, authed CTA→dashboard, H1 text, eyebrow text, sub text, canvas present, alt text)
  - **Verify**: Tests FAIL before implementation
  - **Dependencies**: T010, T012, T005

- [ ] T022 [US2] HeroSection implementation in `portal/src/components/landing/hero-section.tsx`
  - **Evidence**: `min-h-screen`, 2-col 60/40 desktop → stacked mobile. Eyebrow + H1 (`clamp(3rem,8vw,6rem)`, font-black, tracking-tighter) + subheadline + GlowButton. Right: `next/image` with `nikita-hero.png` + `.mask-fade-left`. FallingPattern absolute background. Stagger: eyebrow(0ms)→H1(150ms)→sub(300ms)→CTA(450ms)→image(200ms,1200ms)→scroll-indicator(2s). Ease: `[0.16, 1, 0.3, 1]`.
  - **Exact copy**: eyebrow `18+ · She's watching`, H1 `Don't Get\nDumped.`, sub `She remembers everything. She has her own life. And she will leave you.`
  - **Tests**: T021
  - **Dependencies**: T021, T010, T012, T005
  - **Commit**: `feat(portal): HeroSection with FallingPattern and stagger animation`

- [ ] T023 [P] [US2] PitchSection: write failing tests in `portal/src/components/landing/__tests__/pitch-section.test.tsx`
  - **Tests**: AC-REQ-014 (3 quotes present, bold text present, TelegramMockup messages present, semantic `<section>`)
  - **Verify**: Tests FAIL before implementation
  - **Dependencies**: T016

- [ ] T024 [US2] PitchSection implementation in `portal/src/components/landing/pitch-section.tsx`
  - **Evidence**: 2-col 50/50 desktop, single col tablet/mobile with TelegramMockup below text. Left: 3 differentiators with `<strong>` emphasis. `useInView` stagger. TelegramMockup in right column.
  - **Exact copy**: (1) "She has opinions. Strong ones. **And she's not afraid to tell you.**" (2) "Forget her birthday? Ignore her texts? **She keeps score.**" (3) "Other apps are afraid to say no. **Nikita will walk out the door.**"
  - **Tests**: T023
  - **Dependencies**: T023, T016
  - **Commit**: `feat(portal): PitchSection with Telegram mockup`

- [ ] T025 [P] [US2] SystemSection: write failing tests in `portal/src/components/landing/__tests__/system-section.test.tsx`
  - **Tests**: AC-REQ-015 (14 system names via SystemTerminal, darker bg attribute, 3 stat labels, semantic heading)
  - **Verify**: Tests FAIL before implementation
  - **Dependencies**: T018

- [ ] T026 [US2] SystemSection implementation in `portal/src/components/landing/system-section.tsx`
  - **Evidence**: Full-width, `background: oklch(0.06 0 0)`. Contains SystemTerminal. Stats bar: 3 cols — `742 Python files`, `5,533 Tests passing`, `86 Specifications`. Semantic `<section>` with accessible heading.
  - **Tests**: T025
  - **Dependencies**: T025, T018
  - **Commit**: `feat(portal): SystemSection terminal aesthetic`

- [ ] T027 [P] [US2] StakesSection: write failing tests in `portal/src/components/landing/__tests__/stakes-section.test.tsx`
  - **Tests**: AC-REQ-016 (4 cards, all 4 titles, `glass-card` class, ChapterTimeline 5 dots, semantic `<section>`)
  - **Verify**: Tests FAIL before implementation
  - **Dependencies**: T020

- [ ] T028 [US2] StakesSection implementation in `portal/src/components/landing/stakes-section.tsx`
  - **Evidence**: 4 `GlassCard` components in 2×2 desktop/tablet, 1×4 mobile (<640px). Cards: "She Keeps Score", "She Tests You", "She Remembers", "She Calls You" (see spec Section 4 for body copy). ChapterTimeline below.
  - **Tests**: T027
  - **Dependencies**: T027, T020
  - **Commit**: `feat(portal): StakesSection glass cards and chapter timeline`

- [ ] T029 [P] [US2] CtaSection: write failing tests in `portal/src/components/landing/__tests__/cta-section.test.tsx`
  - **Tests**: AC-REQ-017 (unauthed→Telegram, authed→dashboard, H2 text, sub text, footer "© 2026 Nanoleq", AuroraOrbs orb divs present)
  - **Verify**: Tests FAIL before implementation
  - **Dependencies**: T010, T011

- [ ] T030 [US2] CtaSection implementation in `portal/src/components/landing/cta-section.tsx`
  - **Evidence**: AuroraOrbs as absolute background. Centered: H2 `Think you can handle her?` + GlowButton + `She's on Telegram. She's waiting.` + footer `© 2026 Nanoleq · Privacy · Terms`. `overflow-hidden` on section.
  - **Note**: Footer `Privacy` and `Terms` links — render as `<a href="/privacy">` and `<a href="/terms">`. These pages don't exist yet; links are placeholders. Do NOT add 404 handling here — that's a separate spec. Use `href` only, no `<Link>` component (avoids Playwright assertion failures on 404).
  - **Tests**: T029
  - **Dependencies**: T029, T010, T011
  - **Commit**: `feat(portal): CtaSection with aurora orbs`

- [ ] T031 [P] [US2] LandingNav: write failing tests in `portal/src/components/landing/__tests__/landing-nav.test.tsx`
  - **Tests**: AC-REQ-018 (unauthed→"Meet Nikita", authed→"Go to Dashboard", fixed positioning, glass-card class, initially hidden)
  - **Verify**: Tests FAIL before implementation
  - **Dependencies**: T010

- [ ] T032 [US2] LandingNav implementation in `portal/src/components/landing/landing-nav.tsx`
  - **Evidence**: `"use client"`. `useScroll` → visible when `scrollY > window.innerHeight * 0.5`. `bg-white/5 backdrop-blur-md border-white/10`, no border-x/border-t/border-radius. Fixed top, full width. "Nikita" brand left, GlowButton right. framer-motion `useMotionValue` for scroll-based opacity.
  - **Tests**: T031
  - **Dependencies**: T031, T010
  - **Commit**: `feat(portal): LandingNav scroll-aware floating bar`

### Verification for User Story 2

- [ ] T033 [US2] Run all US2 tests — `cd portal && npm run test -- --testPathPattern="telegram-mockup|system-terminal|chapter-timeline|hero-section|pitch-section|system-section|stakes-section|cta-section|landing-nav"` — verify all pass
- [ ] T034 [US2] Verify US1 tests still pass (regression) — `npm run test -- --testPathPattern="glow-button|aurora-orbs|falling-pattern"`
- [ ] T035 [US2] Verify all P1 section component ACs satisfied (auth-conditional CTAs, exact copy, responsive classes)

**Checkpoint**: All 9 section/sub-components pass tests. HeroSection + all siblings independently renderable.

---

## Phase 5: User Story 3 — Root Page + Metadata (P1)

**From spec**: Visitors accessing the root `/` URL see the complete landing page instead of being redirected. Social sharing shows rich OG metadata with the tagline.

**Goal**: Root `page.tsx` rewritten to compose all sections; OG/Twitter metadata added to layout.

**Independent Test**: `page.tsx` renders without crash with both auth states; `layout.tsx` includes all OG meta tags.

**Acceptance Criteria**:
- AC-REQ-019: `page.tsx` no longer contains `redirect()`, exports async server component composing all 6 sections
- AC-REQ-020: `layout.tsx` metadata includes `openGraph.title`, `openGraph.description`, `openGraph.images`, `twitter.card`

### Tests + Implementation for User Story 3

- [ ] T036 [US3] Rewrite `portal/src/app/page.tsx`
  - **AC1**: No `redirect()` calls remain. File exports default async server component.
  - **AC2**: `npm run build` zero TypeScript errors. All 6 section components imported and rendered.
  - **Evidence**: Plan T5.1 — imports LandingNav, HeroSection, PitchSection, SystemSection, StakesSection, CtaSection. `createClient()` + `supabase.auth.getUser()` → `isAuthenticated`. `<main className="bg-void min-h-screen">` wrapper.
  - **Dependencies**: T002, T022, T024, T026, T028, T030, T032
  - **Commit**: `feat(portal): root page.tsx rewrite to landing page`

- [ ] T036b [P] [US3] Create barrel export `portal/src/components/landing/index.ts`
  - **AC1**: File exports all 10 landing components: `HeroSection`, `PitchSection`, `SystemSection`, `StakesSection`, `CtaSection`, `LandingNav`, `GlowButton`, `AuroraOrbs`, `FallingPattern`, `TelegramMockup`, `SystemTerminal`, `ChapterTimeline`.
  - **AC2**: `import { HeroSection } from "@/components/landing"` resolves without TypeScript error in `page.tsx`.
  - **Evidence**: M-06 GATE 2 finding — missing barrel export was the only unresolved MEDIUM. Enables clean imports in page.tsx and future consumers.
  - **Dependencies**: T022, T024, T026, T028, T030, T032

- [ ] T036c [OPTIONAL] Create `portal/src/app/error.tsx` dark-themed error boundary
  - **AC1**: File exports default `Error` component with `"use client"` directive, accepts `{ error: Error; reset: () => void }` props, renders dark glass card with error message + retry button styled with `bg-primary text-primary-foreground`.
  - **AC2**: If `supabase.auth.getUser()` throws in `page.tsx`, error boundary catches it and shows retry UI instead of raw Next.js error page.
  - **Evidence**: NF-05 — no root error boundary exists. Low priority but prevents raw error screen on Supabase failure.
  - **Dependencies**: T001
  - **Note**: Skip if time-constrained — does not block any P1 acceptance criteria.

- [ ] T037 [P] [US3] Add OG/Twitter metadata to `portal/src/app/page.tsx`
  - **AC1**: `metadata` object exported from `page.tsx` (NOT `layout.tsx`) includes all 5 required fields (title, description, openGraph.title, openGraph.description, twitter.card).
  - **AC2**: `npm run build` passes. `<meta property="og:title">` and `<meta name="twitter:card" content="summary_large_image">` present in rendered HTML head for `/`. Dashboard/admin pages retain generic layout.tsx metadata.
  - **Evidence**: NF-01 — layout.tsx metadata propagates to ALL child routes; landing copy must be page-level. Export `metadata` from page.tsx alongside `default export`.
  - **Note**: page.tsx exports both `metadata` (const) and `default` (async function) — this is valid Next.js App Router pattern.
  - **Dependencies**: T001
  - **Commit**: `feat(portal): OG and Twitter metadata for landing page`

### Verification for User Story 3

- [ ] T038 [US3] Verify root page renders for unauthenticated user (no redirect) — manual `npm run dev` check at `/`
- [ ] T039 [US3] Verify root page renders for authenticated user with "Go to Dashboard" CTA
- [ ] T040 [US3] Regression: `/dashboard`, `/login`, `/admin`, `/onboarding` still work
- [ ] T041 [US3] Verify all P3 acceptance criteria satisfied

**Checkpoint**: Complete landing page renders at `/` for all users. OG metadata confirmed.

---

## Phase 6: Unit Test Completion Pass

**Purpose**: Gap-fill and framer-motion mock polish across all 9 test files. Final vitest run.

- [ ] T042 Verify all 9 unit test files pass — `cd portal && npm run test:ci`
  - **AC1**: Exit code 0. All 9 test files pass with zero failures.
  - **AC2**: All 7 key spec test cases confirmed: (1) unauthed CTA→Telegram, (2) authed CTA→dashboard, (3) all sections no crash, (4) reduced-motion respected, (5) images have alt text, (6) chapter timeline 5 dots + labels + thresholds, (7) system terminal 14 system names.
  - **framer-motion mock**: Proxy catch-all in `vitest.setup.ts` or per-file (covers all `motion.*` tags generically — see spec Testing Strategy).
  - **Dependencies**: T013, T033

---

## Phase 7: E2E Tests (Playwright)

**Purpose**: Integration-level browser tests confirming routing, auth, scroll behavior, and responsive layout.

- [ ] T043 Create `portal/e2e/landing.spec.ts` with 9 test cases
  - **AC1**: All 9 tests pass in CI (`npm run test:e2e -- --project=chromium landing.spec.ts`). Pass 2 consecutive runs.
  - **AC2**: Test 1 asserts `page.url()` does NOT contain `/login` and hero heading is visible. Test 4 uses `page.evaluate(() => window.scrollTo(0, window.innerHeight))` then awaits nav visibility.
  - **Test cases**:
    1. Unauthenticated `/` → landing page (not redirect)
    2. Authenticated `/` → landing page with "Go to Dashboard" CTA
    3. `/dashboard` still works for authenticated users
    4. Scroll past 50% viewport → floating nav visible
    5. Mobile 375×812 → stacked layout, no horizontal overflow
    6. All section headings visible: "Don't Get Dumped", pitch heading, "Under the Hood", "Think you can handle her?"
    7. Copy tone compliance: `expect(await page.textContent('body')).not.toMatch(/AI girlfriend|artificial intelligence|simulation|AI companion|chatbot/i)` — banned words absent from entire page
    8. 320×568 (iPhone SE) viewport → no horizontal overflow (`document.documentElement.scrollWidth <= window.innerWidth`)
    9. Admin authenticated at `/` → landing page renders (not redirect to `/admin`)
  - **Dependencies**: T036, T002

- [ ] T044 Update `portal/e2e/auth-flow.spec.ts` to fix `/` assertion (currently a tautology)
  - **AC1**: Old tautology assertion `expect(url.includes("/login") || url.includes("/")).toBe(true)` removed (always passes — `url.includes("/")` matches ANY URL). New assertion: `await expect(page.locator('h1')).toContainText('Dumped')` — verifies landing page actually rendered.
  - **AC2**: Full `auth-flow.spec.ts` suite passes — `npm run test:e2e -- auth-flow.spec.ts`. All other tests in file unaffected.
  - **Evidence**: NF-02 — auth-flow.spec.ts:22 has zero test value. Plan T7.2 — replace lines 15–23 with specific landing page heading assertion.
  - **Dependencies**: T002, T036

---

## Phase 8: Figma Code Connect (P3)

**Purpose**: Map landing components to Figma design system file for designer–developer handoff.

**Acceptance Criteria**:
- AC-REQ-027: 4 `.figma.js` Code Connect template files created; publish command succeeds

- [ ] T045 Create 4 `.figma.js` Code Connect templates (Figma file key: `dGAxXIglEjfFiTOnwtoSxv`)
  - **AC1**: Files exist: `portal/src/components/landing/glow-button.figma.js`, `portal/src/components/glass/glass-card.figma.js`, `portal/src/components/landing/system-terminal.figma.js`, `portal/src/components/landing/telegram-mockup.figma.js`
  - **AC2**: Files do not cause TypeScript or lint errors (`npm run lint` passes).
  - **Evidence**: Plan T8.1. Use `figma:figma-code-connect` skill or write parserless templates manually. Requires Figma MCP reconnected.
  - **Dependencies**: T010, T016, T018, T032

- [ ] T046 Publish Code Connect mappings to Figma
  - **AC1**: Publish command exits 0 or MCP `send_code_connect_mappings` returns success.
  - **AC2**: In Figma file, at least one component's Code panel shows the mapped React snippet.
  - **Dependencies**: T045

---

## Phase 9: Build Verification + Visual QA

- [ ] T047 Full production build + lint + type-check + test pass
  - **AC1**: `npm run build` exits 0. Zero errors in Next.js build output.
  - **AC2**: `npm run lint` exits 0. `npm run test:ci` exits 0.
  - **Commands**: `cd portal && npm run build && npm run lint && npm run type-check && npm run test:ci`
  - **Dependencies**: T036, T037, T042

- [ ] T048 Existing routes regression smoke test
  - **AC1**: `auth-flow.spec.ts`, `login.spec.ts`, `dashboard.spec.ts`, `admin.spec.ts` all pass without regressions.
  - **AC2**: Authenticated admin users redirected to `/admin` (not landing page) on login via `/login`.
  - **Dependencies**: T047

- [ ] T049 Visual QA at 3 viewports (375×812, 768×1024, 1440×900)
  - **AC1**: All checklist items verified: FallingPattern behind hero, hero image fade, H1 font clamp scales, LandingNav appears on scroll, Telegram bubbles distinct, terminal animates, stats count, chapter timeline mobile-scrolls, aurora orbs in CTA, no horizontal overflow, rose glow pulse on hero CTA.
  - **AC2**: No horizontal scrollbar at 375px. Zero console errors on any viewport.
  - **Dependencies**: T047

---

## Phase 10: PR + QA Review

- [ ] T050 Create PR `feat(portal): landing page hero — Spec 208`
  - **AC1**: PR exists targeting master. CI checks triggered (backend-ci, portal-ci, e2e).
  - **AC2**: PR body includes screenshots at 3 viewports, summary bullets, `Closes #208` reference.
  - **Command**: `gh pr create --title "feat(portal): landing page hero — Spec 208" --body "..."`
  - **Dependencies**: T047, T048, T049

- [ ] T051 QA review loop — `/qa-review --pr [N]`
  - **AC1**: 0 blocking issues + 0 important issues returned.
  - **AC2**: All CI checks green. Squash-merge proceeds per PR workflow.
  - **Dependencies**: T050

---

## Dependencies & Execution Order

| Phase | Depends On | Parallelizable |
|-------|-----------|----------------|
| **Phase 1: Setup** | None | T002, T003, T004 in parallel after T001 |
| **Phase 2: Images** | T001 | T005→T006 sequential |
| **Phase 3: Shared Components** | T003, T004 complete | T007/T008/T009 parallel; then T010/T011/T012 parallel |
| **Phase 4: Sections** | Phase 3 complete + T005 | Sub-components (T015–T020) parallel; sections depend on subs |
| **Phase 5: Root Page** | All Phase 4 sections | T036 sequential; T037 parallel |
| **Phase 6: Test pass** | Phase 3+4 TDD cycles | Single `npm run test:ci` |
| **Phase 7: E2E** | T036, T002 | T043 and T044 in parallel |
| **Phase 8: Figma** | Phase 3+4 components | T045→T046 sequential |
| **Phase 9: Build QA** | All phases | T047→T048→T049 sequential |
| **Phase 10: PR** | Phase 9 | T050→T051 sequential |

### TDD Execution Pattern (per component)

1. ✅ Write failing test file → commit `test(portal): [component] failing tests`
2. ✅ Verify tests FAIL (red state)
3. ✅ Implement component → commit `feat(portal): [component] implementation`
4. ✅ Verify tests PASS (green state)
5. ✅ Verify all ACs satisfied

---

## Intelligence-First Checklist

Before implementing ANY task:

- [ ] `project-intel.mjs --search "[component keyword]" --type tsx --json` — find existing patterns
- [ ] `project-intel.mjs --dependencies portal/src/app/page.tsx --json` — understand root page impact
- [ ] `project-intel.mjs --symbols portal/src/app/onboarding/components/ambient-particles.tsx --json` — FallingPattern reference
- [ ] Read ONLY targeted files after intel queries narrow scope

---

## Acceptance Criteria Traceability

| Spec AC | Tasks |
|---------|-------|
| Unauthed `/` → landing (not login redirect) | T002, T036, T043 |
| Authed `/` → landing with "Go to Dashboard" | T002, T021, T036, T043 |
| FallingPattern renders, no console errors | T009, T012, T021, T022 |
| Staggered entrance animation plays on load | T022 |
| Scroll indicator after 2s | T022 |
| Floating nav appears on scroll | T031, T032, T043 |
| Telegram messages staggered animation | T016 |
| System terminal sequential lines + green checkmarks | T018 |
| Stats counter 0→final | T018, T026 |
| Feature cards glass effect | T028 |
| Chapter timeline 5 dots + labels | T019, T020, T028 |
| Final CTA aurora orb background | T029, T030 |
| All CTAs correct based on auth state | T007, T010, T021, T029, T031, T043 |
| Mobile layout stacked, no overflow | T022, T028, T049 |
| prefers-reduced-motion disables animations | T009, T012, T017, T018, T021 |
| `npm run build` zero errors | T047 |
| Playwright E2E pass | T043, T044 |
| Vitest unit tests pass | T042 |
| OG metadata renders | T037 |
| Existing routes unchanged | T048 |

---

**Generated by**: generate-tasks skill via /tasks command
**Validated by**: /audit command (cross-artifact consistency check — auto-invoked next)
**Next Step**: /audit 208 (automatic quality gate)
