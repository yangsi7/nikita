# Onboarding Design Brief — Spec 214 PR-B & PR-C Reviewers

**Audience**: PR 214-B/C QA reviewers + future onboarding work
**Authority**: User direction 2026-04-16 ("follow the great aesthetic we have in the landing page... one focused piece at a time. Full screen.")
**Status**: AUTHORITATIVE for all 11 wizard steps

---

## North Star

The onboarding is **the wizard equivalent of the landing page's "Under The Hood" reveal**. It teaches Nikita's reality — interactively, one focused beat at a time — while *being* the very first turn of the relationship. No SaaS form. No brand strip. Each screen is a full-viewport stage; each transition is a curtain reveal.

**Reference experience**: open `portal/src/app/page.tsx` → scroll through. Note especially:
- `system-section.tsx` + `system-terminal.tsx` — staggered ✓ reveal of capabilities
- `hero-section.tsx` — typography scale, motion timing, eyebrow + headline + subheadline + cta rhythm
- `stakes-section.tsx`, `pitch-section.tsx`, `cta-section.tsx` — section-by-section beats with `whileInView` transitions

The wizard reuses the **same primitives** (FallingPattern, AuroraOrbs, GlowButton, glass cards, terminal aesthetic) so the onboarding feels like the landing page **animated forward** into a personal conversation — not a separate product.

---

## Hard Design Rules

### 1. One thing per screen, full viewport

- Each step occupies `min-h-screen` (or `min-h-[100dvh]` for mobile safe areas).
- Background = `bg-void` (`oklch(0.08 0 0)`).
- One headline. One input or one decision. One CTA. No secondary navigation, no progress shrunk into a corner footer — progress goes top-center as the dossier file index "FIELD N OF 7".
- White space dominates. Center vertically (`flex items-center`) with content max-width capped (`max-w-2xl mx-auto`).

### 2. Landing-page typography (non-negotiable)

- **Hero text per step** (e.g., "What city?"): `text-[clamp(3rem,7vw,6rem)] font-black tracking-tighter leading-none text-foreground`
- **Eyebrow** (above headline, e.g., "FIELD 03 OF 07 — LOCATION"): `text-xs tracking-[0.2em] uppercase text-muted-foreground`
- **Subheadline / Nikita voice** (e.g., "Where do you actually live? I want to know what corner you cry in."): `text-lg text-muted-foreground max-w-md leading-relaxed`
- **Body / form labels**: `text-sm text-muted-foreground`
- Use `font-mono` ONLY for terminal-style elements (CLEARED stamps, system reveals, pipeline gate progress).

### 3. Color palette (use tokens, never literals)

| Use | Token | Value |
|---|---|---|
| Background | `bg-void` | `oklch(0.08 0 0)` |
| Card surface | `bg-card` / `bg-glass` | `oklch(0.13 0 0)` / `oklch(1 0 0 / 5%)` |
| Primary accent (rose) | `text-primary` / `bg-primary` | `oklch(0.75 0.15 350)` |
| Cyan accent (info) | `text-cyan-glow` / `var(--cyan-glow)` | `oklch(0.7 0.15 190)` |
| Amber accent (warning) | `text-amber-glow` | `oklch(0.75 0.15 80)` |
| Foreground | `text-foreground` | `oklch(0.95 0 0)` |
| Muted | `text-muted-foreground` | `oklch(0.6 0 0)` |
| Glass border | `border-glass-border` | `oklch(1 0 0 / 10%)` |

**Never inline `oklch(...)` values**. Always use tokens via Tailwind classes or `var(--token)`.

### 4. Motion language (framer-motion, EASE_OUT_QUART)

- Step entry: `initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}`
- Stagger pattern (e.g., reveal of multiple options): delay siblings by 0.15s × index, max 0.55s.
- DossierStamp typewriter: 50ms per character (matches `system-terminal.tsx`).
- CLEARED rotate-in: 0.5s spring, opacity 0→1, rotate 8deg→0deg, scale 1.2→1.
- **`prefers-reduced-motion: reduce`** MUST short-circuit ALL animations to instant state. Pattern from `system-terminal.tsx:37-46`.

### 5. Background atmosphere on EVERY step

```tsx
<section className="relative min-h-screen overflow-hidden bg-void">
  <FallingPattern />
  <AuroraOrbs />
  <div className="relative z-10 flex flex-col items-center justify-center min-h-screen container mx-auto px-6">
    {/* step content */}
  </div>
</section>
```

Reuse: `import { FallingPattern } from "@/components/landing/falling-pattern"` and `AuroraOrbs`. These are 11 + 82 lines respectively — already shipped.

### 6. shadcn/ui — install, don't reinvent

- `components.json` already configured: style `"new-york"`, base color `"zinc"`, RSC enabled, lucide icons.
- **Use shadcn primitives** for: `Input`, `Label`, `RadioGroup` (SceneStep!), `Slider` (DarknessStep!), `Button`, `Card`. Install via `npx shadcn@latest add <component>` if missing.
- Wrap shadcn primitives in dossier-themed adapters when needed (e.g., `<DossierInput>` extends `<Input>` with rose focus ring, monospace eyebrow label).
- NEVER write custom radio buttons / sliders / form fields when a shadcn equivalent exists.

---

## "How Nikita Works" Reveal Pattern

The user explicitly called this out. The landing page's `system-terminal.tsx` reveals 14 system capabilities with staggered ✓ marks in a monospace terminal. **Mirror this in onboarding**:

### When to deploy the reveal pattern

Use it at **3 specific teaching moments** in the wizard:

1. **Pre-IdentityStep ("Who are you?")**: A 4-line monospace reveal explaining what Nikita stores about the player and why ("Name → so she calls you yours", "Age → so she calibrates innuendo", "Occupation → so she remembers your Mondays"). Each line stagger-fades in 50ms apart.

2. **Pre-DarknessStep ("How dark do you want this?")**: Reveal the consequence ladder — 5 ✓ lines mapping slider position to in-game consequence ("0.2 → soft chaos, no scars", "0.5 → real fights, real grace", "0.8 → vice surfaces in week 2", etc.).

3. **PipelineGate ("CLEARANCE PROCESSING")**: Real-time staggered reveal as backend stages complete — `✓ Researching your city...`, `✓ Generating backstory candidates...`, `✓ Compiling first message...`. Each ✓ appears as the corresponding pipeline stage finishes (driven by `useOnboardingPipelineReady` state).

### Reveal component pseudocode

```tsx
"use client"
// Reuse system-terminal.tsx as a base. Extract a generic
// <DossierReveal items={[{label, detail}]} interval={50} /> that
// the wizard steps can drop into a step's pre-input slot.

// Visual: black/40 backdrop, rounded-lg, border-glass-border,
// monospace, ✓ in --rose-glow (NOT green — match dossier theme),
// label in foreground, detail in muted-foreground right-aligned.
```

The component is a 1:1 visual sibling of `system-terminal.tsx` but with `--rose-glow` accent (matches landing rose primary), and the reveal *concludes the explanation* before the user touches the input below.

---

## Step-by-Step Aesthetic Map

| Step | Visual | Reveal? | shadcn primitive |
|---|---|---|---|
| 3 LocationStep | Hero "WHERE." → city Input below → DossierReveal of "venue scout active" on blur | Yes (post-blur) | `Input` |
| 4 SceneStep | Hero "WHO DO YOU RUN WITH?" → 4-button radiogroup grid, each card glass + rose focus ring | No | `RadioGroup` (REQUIRED — WAI-ARIA) |
| 5 DarknessStep | Hero "HOW DARK?" → slider full-width → live Nikita quote underneath | Yes (consequence ladder above slider) | `Slider` |
| 6 IdentityStep | Hero "TELL ME WHO" → 3 stacked Inputs (name/age/occupation) | Yes (data-use reveal above) | `Input` x3 |
| 7 BackstoryReveal | Hero "PICK YOUR ENTRY POINT" → 3 BackstoryOption cards in a horizontal grid | No | `Card` x3 |
| 8 PhoneStep | Hero "SHE NEEDS A NUMBER" → phone input with country selector + voice/text radio | No | `Input` + `RadioGroup` |
| 9 PipelineGate | Hero "CLEARANCE PROCESSING" → DossierReveal driven by pipeline state | YES (live, primary feature) | none — pure custom |
| 10 HandoffStep | Hero "GO." → GlowButton(Telegram) center; QRHandoff right (desktop only) | No | `Button` (or GlowButton) |
| 11 Complete | CLEARED stamp center-screen, fades to dashboard redirect | n/a | none |

---

## What Gets REJECTED at QA

- Multiple form fields visible per screen (violates "one thing per screen")
- Default Tailwind colors (`bg-blue-500`, `text-gray-400`, etc.) instead of project tokens
- shadcn skipped in favor of hand-rolled `<input>` / `<button>` markup
- No background atmosphere (FallingPattern + AuroraOrbs missing)
- Typography that doesn't match landing scale (e.g., `text-2xl` for hero where it should be `clamp(3rem,7vw,6rem)`)
- SaaS copy ("Continue", "Next step", "Submit") instead of Nikita voice ("Lock it in", "Tell me more", "I'm ready when you are")
- Animation that ignores `prefers-reduced-motion`
- Page that scrolls instead of being one full-viewport stage
- Missing eyebrow label (no "FIELD N OF 7" context)

---

## Reference Files (read these before implementing or reviewing)

- `portal/src/components/landing/hero-section.tsx` — typography rhythm, EASE_OUT_QUART pattern
- `portal/src/components/landing/system-terminal.tsx` — staggered reveal authority
- `portal/src/components/landing/system-section.tsx` — `whileInView` section pattern
- `portal/src/components/landing/falling-pattern.tsx`, `aurora-orbs.tsx` — background primitives
- `portal/src/components/landing/glow-button.tsx` — primary CTA style
- `portal/src/app/globals.css` lines 99-108 + 110-145 — token catalog
- `portal/components.json` — shadcn config
- `docs/content/wizard-copy.md` — Nikita-voiced copy reference (PR-B creates this)

---

## Acceptance Criterion (informal)

If a designer who built the landing page screenshots the wizard and can't tell where the landing ends and the onboarding begins (apart from the form mechanics), we shipped it right. If it looks like a Vercel template with a logo on top, we did not.
