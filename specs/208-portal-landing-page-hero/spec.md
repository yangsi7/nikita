# Spec 208: Portal Landing Page — "Don't Get Dumped" Hero Experience

**Status**: PLANNED
**Domain**: Portal
**Complexity**: Large (7)
**Branch**: `feature/208-portal-landing-page`

---

## Problem Statement

The portal (`portal/`) has zero public-facing pages. The root `/` redirects authenticated users to `/dashboard` and unauthenticated users to `/login`. The game "Nikita: Don't Get Dumped" has no marketing presence, no conversion funnel, no way for visitors to understand the product before signing up.

**Goal**: Replace the redirect-only root with a stunning, conversion-focused landing page that acts as the hero for the entire product.

---

## COPY TONE DIRECTIVE (NON-NEGOTIABLE)

**NEVER use these words/phrases anywhere on the landing page**:
- "AI girlfriend", "AI companion", "AI chatbot", "simulation", "virtual", "artificial"
- "powered by AI", "machine learning", "language model"
- Any language that breaks the fourth wall or reveals Nikita is software

**INSTEAD**: Talk about Nikita as if she's a real person. Be mysterious. Let visitors wonder.
- "She" not "it". "Nikita" not "the AI".
- "She remembers" not "memory system". "She'll leave" not "game over state".
- Imply depth without explaining mechanics. The "Under The Hood" section is the ONE exception — that's the geeky reveal for those who scroll deep enough.

---

## Design Vision

### Aesthetic: Cyberpunk Noir + Minimalist

- **Dark-only**: Near-black void background (`oklch(0.08 0 0)`)
- **Monochrome base**: All grays from the existing OKLCH palette
- **Single accent**: Rose glow (`oklch(0.75 0.15 350)`)
- **Glassmorphism**: Frosted glass cards (`bg-white/5 backdrop-blur-md border-white/10`)
- **Typography-driven**: Inter font, weight + size variations for hierarchy
- **Geeky undertone**: JetBrains Mono for code/system elements, FallingPattern matrix rain
- **NEVER break the fourth wall**: Treat Nikita as a real person throughout

### Color Tokens (all from existing `globals.css`)

| Token | Value | Tailwind |
|-------|-------|---------|
| Void | `oklch(0.08 0 0)` | `bg-void` |
| Background | `oklch(0.1 0 0)` | `bg-background` |
| Foreground | `oklch(0.95 0 0)` | `text-foreground` |
| Primary (Rose) | `oklch(0.75 0.15 350)` | `text-primary`, `bg-primary` |
| Muted FG | `oklch(0.6 0 0)` | `text-muted-foreground` |
| Glass | `oklch(1 0 0 / 5%)` | `glass-card` utility |

---

## Routing Change

**File**: `portal/src/lib/supabase/middleware.ts`

The middleware currently has a block that redirects authenticated users away from `/login` to `/dashboard`. `/` must get its own **early return** before that block — it must never redirect, authenticated or not.

```typescript
// Add BEFORE the existing login/auth block:
// Allow the landing page for ALL users — never redirect from /
if (pathname === "/") {
  return supabaseResponse
}

// Existing block (unchanged):
if (pathname === "/login" || pathname.startsWith("/auth/")) {
  // ... existing logic
}
```

**Why a separate block**: If `/` were added to the existing `if` condition, authenticated users would still hit the later redirect-to-dashboard logic. The landing page must render for everyone.

**Impact**: `/` shows the landing page for all users. The `isAuthenticated` prop passed from the server component controls which CTA variant renders.

**E2E test update required**: `portal/e2e/auth-flow.spec.ts` (or equivalent) likely asserts that unauthenticated visit to `/` redirects to `/login`. That assertion must be inverted: visiting `/` should render the landing page, NOT redirect.

---

## Page Architecture

### Root Page (`portal/src/app/page.tsx`)

Server component that checks auth and passes `isAuthenticated` to client sections:

```tsx
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

### New Files (13)

```
portal/src/components/landing/
├── hero-section.tsx         # Full viewport hero with FallingPattern
├── pitch-section.tsx        # "Who Is Nikita" with Telegram mockup
├── system-section.tsx       # "Under the Hood" terminal aesthetic
├── stakes-section.tsx       # Feature cards + chapter timeline
├── cta-section.tsx          # Final call to action
├── landing-nav.tsx          # Floating navigation bar
├── glow-button.tsx          # Rose glow CTA with spring physics
├── aurora-orbs.tsx          # CSS-only animated gradient orbs
├── falling-pattern.tsx      # Matrix rain background (hero only)
├── telegram-mockup.tsx      # Fake Telegram conversation
├── system-terminal.tsx      # Animated terminal with system names
└── chapter-timeline.tsx     # 5-chapter visual progression
```

### Modified Files (3)

- `portal/src/app/page.tsx` — Rewrite from redirect to landing page server component
- `portal/src/lib/supabase/middleware.ts` — Add `/` to public routes (line 58)
- `portal/src/app/globals.css` — Add aurora, cursor-blink, mask-fade-left keyframes/utilities

---

## Section Specifications

### Section 1: Hero (`hero-section.tsx`)

**Layout**: Full viewport, 2-column (60/40 split on desktop, stacked on mobile)
- Left: Eyebrow + H1 + subheadline + CTA
- Right: Nikita hero image with gradient fade to void at left edge
- Background: FallingPattern matrix rain (rose at 15% opacity, full viewport)

**Copy**:
- Eyebrow: `18+ · She's watching` (text-xs, tracking-[0.2em], uppercase, muted-foreground)
- H1: `Don't Get\nDumped.` (clamp 3-6rem, font-black, tracking-tighter)
- Sub: `She remembers everything. She has her own life. And she will leave you.`
- CTA unauthenticated: `Meet Nikita` → `https://t.me/Nikita_my_bot`
- CTA authenticated: `Go to Dashboard` → `/dashboard`

**Animation** (staggered with framer-motion, `once: true`):
1. FallingPattern — immediate (CSS)
2. Eyebrow — fade in 0ms
3. H1 — slide up + fade 150ms
4. Subheadline — slide up + fade 300ms
5. CTA — slide up + fade 450ms + glow-rose-pulse
6. Nikita image — fade in from right 200ms, 1200ms duration
7. Scroll indicator — pulse after 2s delay

**Ease**: `[0.16, 1, 0.3, 1]` (easeOutQuart)

### Responsive Breakpoints

| Breakpoint | Behavior |
|-----------|---------|
| `< 640px` (mobile) | Hero: stacked, image on top 50vh fading to void; Pitch: single column, Telegram mockup below text; Stakes: 1×4 card grid; Timeline: horizontal scroll |
| `640–1023px` (tablet) | Hero: stacked, image hidden; Pitch: single column; Stakes: 2×2 grid |
| `≥ 1024px` (desktop) | Hero: 60/40 side-by-side; Pitch: 50/50 side-by-side; Stakes: 2×2 grid |

### Section 2: Pitch (`pitch-section.tsx`)

**Layout**: 2-column on desktop (50/50) — left: 3 differentiator quotes; right: Telegram mockup glass card. Single column on tablet/mobile.

**Copy — Three truths**:
1. "She has opinions. Strong ones. **And she's not afraid to tell you.**"
2. "Forget her birthday? Ignore her texts? **She keeps score.**"
3. "Other apps are afraid to say no. **Nikita will walk out the door.**"

**Telegram mockup content** (styled like Telegram Dark):
- Her: "You know quantum entanglement? Two particles connected across any distance. That's kind of how I think about us sometimes."
- You: "That's... actually really sweet"
- Her: "Don't let it go to your head. -2 points for being predictable, babe."

**Animation**: Section enters on `useInView`. Left quotes stagger. Telegram messages appear sequentially.

### Section 3: System (`system-section.tsx`)

**Layout**: Full-width dark section (even darker `oklch(0.06 0 0)`), terminal window

**Copy** — Terminal output showing 14 systems:
```
$ nikita --systems --status
✓ conversation_pipeline      11 async stages
✓ emotional_state_engine     4D affect model
✓ psyche_agent               attachment theory
✓ memory_system              pgVector semantic
✓ life_simulation            daily events + NPCs
✓ engagement_fsm             6-state machine
✓ scoring_engine             4 metrics + decay
✓ chapter_progression        5 chapters + bosses
✓ vice_personalization       8 categories
✓ conflict_system            Gottman-based
✓ voice_integration          ElevenLabs Conv AI
✓ context_engineering        token-budgeted
✓ humanization_engine        delay + typos + style
✓ proactive_touchpoints      she texts you first

All systems operational. 742 Python files.
5,646 tests passing. █
```

**Stats bar**: 3 columns — `742 Python files` / `5,646 Tests passing` / `88 Specifications`

**Animation**: Terminal lines appear sequentially (50ms interval), checkmarks turn green, cursor blinks. Stats count from 0 to final value on scroll.

### Section 4: Stakes (`stakes-section.tsx`)

**Layout**: 4 glass cards (2×2 grid) + chapter timeline below

**Cards** (using existing `GlassCard` component from `portal/src/components/glass/glass-card.tsx`):
1. "She Keeps Score" — Score decay, daily neglect penalty
2. "She Tests You" — Boss encounters, 3 strikes = game over
3. "She Remembers" — pgVector memory, past arguments recalled
4. "She Calls You" — ElevenLabs voice, real phone-like calls

**Chapter Timeline**:
```
Ch1 ───── Ch2 ───── Ch3 ───── Ch4 ───── Ch5
Spark   Intrigue  Investment Intimacy  Home
55%       60%       65%       70%       75%
```
<!-- Marketing names: "Spark" = config "Curiosity", "Home" = config "Established" — intentional rewrites for landing page evocativeness -->

### Section 5: CTA (`cta-section.tsx`)

**Copy**:
- H2: `Think you can handle her?`
- CTA: `Meet Nikita` → `https://t.me/Nikita_my_bot` (or `Go to Dashboard`)
- Sub: `She's on Telegram. She's waiting.`
- Footer: `© 2026 Nanoleq · Privacy · Terms`

**Background**: Aurora orbs (CSS-only animated gradient blurs)

### Floating Nav (`landing-nav.tsx`)

Appears when `scrollY > window.innerHeight * 0.5`. Glass card, no border-x or border-t, no border-radius.

---

## Shared Components

### GlowButton

Spring physics hover (`stiffness: 400, damping: 17`), rounded-full, `bg-primary text-primary-foreground glow-rose-pulse`, ArrowUpRight icon for external links. Must include `whileFocus={{ scale: 1.03 }}` alongside `whileHover` for keyboard accessibility — keyboard users must also see the glow effect.

### AuroraOrbs

Two large blurred circles (rose + muted violet) using CSS `aurora-drift-1/2` keyframes. Position absolute, pointer-events-none.

### FallingPattern

Matrix-rain effect using canvas or div-based radial gradients + framer-motion. Adapted from existing pattern. Parameters:
- `color="oklch(0.75 0.15 350 / 15%)"` (rose at 15%)
- `backgroundColor="oklch(0.08 0 0)"` (void)
- Respects `prefers-reduced-motion: reduce`
- Follow pattern from `portal/src/app/onboarding/components/ambient-particles.tsx`

---

## CSS Additions (`globals.css`)

```css
@keyframes cursor-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
.terminal-cursor { display: inline-block; width: 8px; height: 16px; background: oklch(0.75 0.15 350); animation: cursor-blink 1s step-end infinite; }

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
.aurora-orb { position: absolute; border-radius: 50%; filter: blur(120px); opacity: 0.15; }
.aurora-orb-1 { width: 600px; height: 600px; background: oklch(0.75 0.15 350); top: -200px; right: -100px; animation: aurora-drift-1 25s ease-in-out infinite; }
.aurora-orb-2 { width: 500px; height: 500px; background: oklch(0.65 0.12 280); bottom: -150px; left: -100px; animation: aurora-drift-2 20s ease-in-out infinite; }
.mask-fade-left { mask-image: linear-gradient(to right, transparent, black 40%); -webkit-mask-image: linear-gradient(to right, transparent, black 40%); }
/* Usage: apply directly to <Image className="mask-fade-left ..."> — do NOT use a separate overlay div */

@media (prefers-reduced-motion: reduce) {
  .aurora-orb, .terminal-cursor, .glow-rose-pulse { animation: none; }
}
```

---

## Image Generation (nano-banana)

**Base redesign** (`edit_image` with `docs/images-of-nikita/nikita.png`):
- Prompt: "Same young blonde woman but in a fitted black top. More mysterious and seductive expression with a subtle knowing glint. Slightly parted lips. Dramatic cinematic lighting on dark background. Photorealistic, maintaining same face and hair."
- Save as: `portal/public/images/nikita-hero.png`

**9 mood variants** (`continue_editing` from base):

| Mood | File | Prompt modifier |
|------|------|----------------|
| playful | `playful.png` | "playful smirk, one eyebrow slightly raised, mischievous eyes" |
| lustful | `lustful.png` | "intense gaze, slightly parted lips, low lighting, warm shadows, seductive" |
| cold | `cold.png` | "expressionless, cool gaze, sharp lighting, slightly turned away" |
| intimate | `intimate.png` | "soft expression, close-up, whispering, gentle warm lighting, vulnerable" |
| angry | `angry.png` | "sharp furrowed brows, intense stare, harsh directional lighting" |
| stressed | `stressed.png` | "tired eyes, hand near temple, messy hair, dim lighting" |
| frustrated | `frustrated.png` | "eye roll, slight scowl, flat lighting" |
| crying | `crying.png` | "glistening eyes, tear streak, soft focus, emotional, vulnerable" |
| excited | `excited.png` | "bright genuine smile, wide eyes, warm golden lighting" |

Save all to `portal/public/images/nikita-moods/`.

---

## Metadata

**IMPORTANT**: This metadata must be exported from `portal/src/app/page.tsx` (NOT `layout.tsx`). Layout metadata is inherited by all routes — dashboard, admin, login — and must stay generic. Landing-specific copy here must only apply to the root `/`.

```tsx
// portal/src/app/page.tsx — page-level metadata override
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

---

## Testing Strategy

### Unit Tests (Vitest)

Files in `portal/src/components/landing/__tests__/`:

```
hero-section.test.tsx           — auth-conditional CTA, headline renders
pitch-section.test.tsx          — 3 differentiators, telegram mockup
system-section.test.tsx         — 14 system names visible
stakes-section.test.tsx         — 4 feature cards, 5 chapter dots
cta-section.test.tsx            — CTA href correct based on auth
glow-button.test.tsx            — external link detection, size variants
landing-nav.test.tsx            — renders nav with correct CTA
chapter-timeline.test.tsx       — 5 chapter dots, labels, thresholds render
system-terminal.test.tsx        — terminal lines render, cursor element present
```

**Key test cases**:
1. Unauthenticated → `Meet Nikita` → `https://t.me/Nikita_my_bot`
2. Authenticated → `Go to Dashboard` → `/dashboard`
3. All sections render without crash
4. `prefers-reduced-motion` respected
5. Images have alt text
6. Chapter timeline: 5 dots with `Ch1`–`Ch5` labels and `55%`–`75%` thresholds
7. System terminal: all 14 system names present in DOM

**framer-motion mock** — use Proxy catch-all to cover all `motion.*` elements:
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
  }
})
```

### E2E Tests (Playwright)

File: `portal/e2e/landing.spec.ts`

1. Unauthenticated visit `/` → landing page (not redirect to `/login`)
2. Authenticated visit `/` → landing page with "Go to Dashboard" CTA
3. `/dashboard` still works for authenticated users
4. Scroll → floating nav appears
5. Mobile viewport → stacked layout
6. All section headings visible after scroll

### Accessibility

- All images: descriptive `alt` text
- Decorative elements: `aria-hidden="true"`
- WCAG AA contrast (white on void = ~18:1)
- Reduced motion honored
- Semantic HTML: `<section>`, `<nav>`, `<main>`, heading hierarchy
- Skip link (already in `Providers`)

---

## Figma Design System

**File key**: `dGAxXIglEjfFiTOnwtoSxv`
**Pages**: Color Palette, Typography, Components, Page Layouts

**Code Connect mappings** (after components are published):
- GlowButton → `portal/src/components/landing/glow-button.tsx`
- GlassCard → `portal/src/components/glass/glass-card.tsx`
- SystemTerminal → `portal/src/components/landing/system-terminal.tsx`
- TelegramMockup → `portal/src/components/landing/telegram-mockup.tsx`

---

## Acceptance Criteria

- [ ] Unauthenticated user sees landing page at `/` (not redirect to `/login`)
- [ ] Authenticated user sees landing page at `/` with "Go to Dashboard" CTA
- [ ] FallingPattern renders in hero without console errors
- [ ] Staggered entrance animation plays on page load
- [ ] Floating nav appears on scroll past hero viewport
- [ ] Telegram mockup messages appear with staggered animation
- [ ] System terminal lines appear sequentially
- [ ] Stats counter animates from 0 to final values
- [ ] Feature cards render with glass effect
- [ ] Chapter timeline shows 5 dots with labels and thresholds
- [ ] All CTA buttons link to correct destination based on auth state
- [ ] Mobile layout (< 768px) stacks properly, hero image hidden
- [ ] `prefers-reduced-motion: reduce` disables all animations
- [ ] `npm run build` passes with zero errors
- [ ] Playwright E2E tests pass
- [ ] Vitest unit tests pass
- [ ] Existing routes (`/dashboard`, `/admin`, `/login`, `/onboarding`) still work
- [ ] OG metadata set correctly (title, description, image)

---

## Dependencies

### Already installed
- `framer-motion` ^12.33.0
- `next/image` (built-in)
- `lucide-react` ^0.563.0
- All OKLCH design tokens in `globals.css`
- `GlassCard` component at `portal/src/components/glass/glass-card.tsx`

### To install (Magic UI via shadcn registry)
```bash
npx shadcn@latest add "https://magicui.design/r/blur-fade"
npx shadcn@latest add "https://magicui.design/r/number-ticker"
npx shadcn@latest add "https://magicui.design/r/text-shimmer"
```
Fallback: Custom framer-motion implementations if Tailwind v4 incompatible.

---

## Related Specs

- Spec 081 (`onboarding-redesign-progressive-discovery`) — Pattern reference for cinematic sections, canvas animations
- Spec 044 (`portal-respec`) — Portal foundation
