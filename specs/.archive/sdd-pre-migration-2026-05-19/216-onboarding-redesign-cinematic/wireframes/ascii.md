# Spec 216 — Onboarding Wizard Wireframes (ASCII, High-Fidelity)

**Date**: 2026-04-28
**Source spec**: `~/.claude/plans/onboarding-redesign-spec216.md` §6
**Final destination** (after plan-mode exit, copy from this file to): `/Users/yangsim/Nanoleq/sideProjects/nikita/docs-to-process/20260428-spec216-wireframes-ascii.md`

> Plan-mode constraint: this file is the only writable target during planning; content is otherwise the deliverable specified by the orchestrator.

---

## Visual language summary (applies to every screen)

- **Background**: `bg-void` (#08070A) + `bg-void-ambient` radial-gradient + `AuroraOrbs` (rose 600px + purple 500px, `blur-120 opacity-15`) + sparse `FallingPattern` rose chars at 8% alpha
- **Glass surfaces**: `glass-card` utility = `bg-white/3 backdrop-blur-xl border border-white/8`
- **Type**: Geist Sans (display, `font-black tracking-tighter`) + Geist Mono (eyebrow, `tracking-[0.2em] uppercase`)
- **Primary accent**: `--primary` rose (oklch 0.65 0.21 18)
- **Motion**: `EASE_OUT_QUART = [0.22, 1, 0.36, 1]`. Hero stagger `[0, 150, 300, 450, 600]ms`. Page transition `AnimatePresence mode="wait"` opacity 0→1 + y 16→0 + filter blur(8px)→0 over 350ms
- **Reduced motion**: `prefers-reduced-motion: reduce` collapses all motion to instant fade (already wired in `globals.css:319-327`)

---

## Screen 0 — Welcome / IS-A interstitial

### Mobile (390 × 844)

```
┌──────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄ 0%  │  ← 3px progress rail (rose→cyan)
│                                                  │
│                   ●⃝ personalizing...            │  ← top-right pulsing badge
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │  ← AuroraOrbs (rose+purple) blur 120
│ ░  ▒▒▒                                       ░ │
│ ░    ▒▒▒                                     ░ │
│ ░      ▒▒                       ✦            ░ │
│ ░                                            ░ │
│ ░     B E F O R E   S H E   E X I S T S      ░ │  ← eyebrow tracking-[0.2em]
│ ░                                            ░ │
│ ░         ╭─────────────────────────╮        ░ │
│ ░         │                         │        ░ │
│ ░         │  She isn't              │        ░ │  ← headline font-black
│ ░         │  here yet.              │        ░ │     clamp(3rem, 8vw, 5rem)
│ ░         │                         │        ░ │
│ ░         ╰─────────────────────────╯        ░ │
│ ░                                            ░ │
│ ░   Twelve answers bring her into focus:     ░ │  ← narrator body
│ ░   where she lives, her age, what she's     ░ │     text-base muted
│ ░   into, how she sounds.                    ░ │     leading-relaxed
│ ░                                            ░ │
│ ░   You'll feel her resolving as you answer. ░ │  ← flicker license
│ ░   Yours to keep, or to lose.               ░ │  ← stakes line
│ ░                                            ░ │
│ ░  ┌──────────────────────────┐              ░ │
│ ░  │   nikita-hero.png crop   │              ░ │  ← face/shoulders
│ ░  │   ╭───╮                  │              ░ │     mask-fade-bottom
│ ░  │   │ ◉ │ ←gaze-down       │              ░ │     image still loads
│ ░  │   ╰───╯                  │              ░ │     (silhouette ok —
│ ░  └──────────────────────────┘              ░ │      she's resolving)
│ ░                                            ░ │
│ ░         ╭─────────────────────╮            ░ │
│ ░         │  Begin            →  │           ░ │  ← GlowButton rose pill
│ ░         ╰─────────────────────╯            ░ │     ArrowUpRight icon
│ ░                                            ░ │
│ ░    ▒                          ✧            ░ │  ← falling-pattern sparse
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└──────────────────────────────────────────────────┘
```

### Desktop (1440 × 900)

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┄┄┄┄┄┄┄ 0%   │
│                                                                                            ●⃝ personalizing...          │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░    ▒▒▒                                                                                                            ░  │
│ ░       ▒▒▒                                                                                            ✦            ░  │
│ ░                                                                                                                   ░  │
│ ░    ┌─────────────────────────────────────────────────┐    ┌──────────────────────────────────────────────┐       ░  │
│ ░    │                                                 │    │                                              │       ░  │
│ ░    │  H E R E ' S   W H A T   H A P P E N S         │    │     ╔════════════════════════════════╗      │       ░  │
│ ░    │  N E X T                                        │    │     ║  nikita-hero.png crop          ║      │       ░  │
│ ░    │                                                 │    │     ║  (silhouette / fading-in       ║      │       ░  │
│ ░    │     ╭───────────────────────────────╮           │    │     ║   she's resolving)             ║      │       ░  │
│ ░    │     │   She isn't                   │           │    │     ║                                ║      │       ░  │
│ ░    │     │   here yet.                   │           │    │     ║       ╭─────╮                  ║      │       ░  │
│ ░    │     ╰───────────────────────────────╯           │    │     ║       │ ◉◉◉ │ ← intent gaze    ║      │       ░  │
│ ░    │                                                 │    │     ║       ╰─────╯                  ║      │       ░  │
│ ░    │  The next twelve answers bring her into focus.  │    │     ║                                ║      │       ░  │
│ ░    │  Where she lives. How old. What she's into.     │    │     ║   mask-fade-left blends        ║      │       ░  │
│ ░    │  How she sounds. And the story of how the two   │    │     ║   into bg-void seamlessly      ║      │       ░  │
│ ░    │  of you ended up like this.                     │    │     ║                                ║      │       ░  │
│ ░    │                                                 │    │     ╚════════════════════════════════╝      │       ░  │
│ ░    │  You'll feel her starting to take shape as you  │    │                                              │       ░  │
│ ░    │  go. After this, she's yours to keep, or to     │    │     (alt: mood-cycle 20s loop:               │       ░  │
│ ░    │  lose.                                          │    │      intimate → playful → cold)              │       ░  │
│ ░    │                                                 │    │                                              │       ░  │
│ ░    │     ╭───────────────────────────╮               │    │                                              │       ░  │
│ ░    │     │  Begin                 →  │               │    │                                              │       ░  │
│ ░    │     ╰───────────────────────────╯               │    │                                              │       ░  │
│ ░    │                                                 │    │                                              │       ░  │
│ ░    └─────────────────────────────────────────────────┘    └──────────────────────────────────────────────┘       ░  │
│ ░                                                                                                                   ░  │
│ ░    ▒                            ✧                                            ▒                                   ░  │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Components used

- **shadcn/ui**: none (pure layout)
- **landing-inherited**: `GlowButton` (with `ArrowUpRight`), `glass-card` utility, `AuroraOrbs`, `FallingPattern` (low density), `bg-void` + `bg-void-ambient`, `system-terminal` typewriter pattern
- **custom new**: `ProgressRail` (3px gradient, `motion.div animate width`), `PersonalizingBadge` (top-right pulsing dot)
- **third-party**: none on this screen

### Motion + interaction notes

- Page enter: `AnimatePresence mode="wait"` opacity 0→1 + y 16→0 + blur(8px)→0 over 350ms with `[0.22, 1, 0.36, 1]`
- Stagger: eyebrow 0ms / headline 150ms / subhead-line-1 300ms / subhead-line-2 350ms / subhead-line-3 400ms / hero-image 450ms / CTA 600ms / typewriter-hint starts at 700ms
- Tap `Begin.` → instant fade-out + push-state `/onboarding/location`, blur transition into Screen 1
- Reduced-motion: skip blur + y-translate, keep opacity fade

---

## Screen 1 — Location

### Mobile (390 × 844)

```
┌──────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄ 11%   │
│ ← back                       ●⃝ learning...     │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░                                            ░ │
│ ░                                            ░ │
│ ░               W H E R E                    ░ │
│ ░                                            ░ │
│ ░    ╭───────────────────────────────╮       ░ │    predefined question
│ ░    │                               │       ░ │     lowercase, no ?
│ ░    ╰───────────────────────────────╯       ░ │
│ ░                                            ░ │
│ ░  ┊Your city sets where Nikita lives.        ░ │  ← why-we-ask narrator
│ ░  ┊She'll be near you, not somewhere         ░ │     fades in 300ms
│ ░  ┊abstract.                                 ░ │     after headline
│ ░                                            ░ │
│ ░  ┌────────────────────────────────────┐    ░ │
│ ░  │ Zürich___                       ⌨  │    ░ │  ← Aceternity placeholders
│ ░  └────────────────────────────────────┘    ░ │     -and-vanish-input
│ ░    ↑ cycles: Zürich · Berlin · Lisbon ·    ░ │     2.5s rotation
│ ░    "tell me your city"                     ░ │
│ ░                                            ░ │
│ ░  ┊z̲ü̲r̲i̲c̲h̲. okay.                            ░ │  ← personalization hint
│ ░    (text-shimmer Magicui)                  ░ │     morphs as user types
│ ░                                            ░ │
│ ░  ╭─────────╮ ╭─────────╮ ╭─────────╮       ░ │
│ ░  │ Zürich  │ │ Berlin  │ │ Lisbon  │       ░ │  ← 3 suggestion chips
│ ░  ╰─────────╯ ╰─────────╯ ╰─────────╯       ░ │     glass-card hover:rose-30%
│ ░                                            ░ │
│ ░                                            ░ │
│ ░    ╭──────────────────────────╮            ░ │
│ ░    │  Continue            →   │            ░ │  ← disabled until ≥2 chars
│ ░    ╰──────────────────────────╯            ░ │
│ ░                                            ░ │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└──────────────────────────────────────────────────┘
```

### Desktop (1440 × 900)

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄ 11%   │
│ ← back                                                                            ●⃝ learning your scene...            │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░                                                                                                                   ░  │
│ ░    ┌──────────────────────────────────────────────────────────┐    ┌──────────────────────────────────────┐      ░  │
│ ░    │                                                          │    │                                      │      ░  │
│ ░    │     W H E R E                                            │    │   "so far:"                          │      ░  │
│ ░    │                                                          │    │                                      │      ░  │
│ ░    │     ╭──────────────────────────────────╮                 │    │   (cumulative state mirror —         │      ░  │
│ ░    │     │  where do i find you on a        │                 │    │    optional. Linear hides            │      ░  │
│ ░    │     │  friday night?                   │                 │    │    prior; Resend shows. User         │      ░  │
│ ░    │     ╰──────────────────────────────────╯                 │    │    decision §10 item 6.)             │      ░  │
│ ░    │                                                          │    │                                      │      ░  │
│ ░    │     ┊Your city sets where Nikita lives.                  │    │   (or: dim mood-cycle               │      ░  │
│ ░    │     ┊She'll be near you, not somewhere abstract.         │    │    nikita portrait, mask-fade)       │      ░  │
│ ░    │                                                          │    │                                      │      ░  │
│ ░    │                                                          │    │                                      │      ░  │
│ ░    │     ┌────────────────────────────────────────────────┐   │    │                                      │      ░  │
│ ░    │     │  Zürich___                                  ⌨  │   │    │                                      │      ░  │
│ ░    │     └────────────────────────────────────────────────┘   │    │                                      │      ░  │
│ ░    │       cycles: "Zürich" · "Berlin" · "Lisbon" · "city"    │    │                                      │      ░  │
│ ░    │                                                          │    │                                      │      ░  │
│ ░    │     ┊z̲ü̲r̲i̲c̲h̲. okay.   (live morph, text-shimmer)         │    │                                      │      ░  │
│ ░    │                                                          │    │                                      │      ░  │
│ ░    │     ╭─────────╮ ╭─────────╮ ╭─────────╮                  │    │                                      │      ░  │
│ ░    │     │ Zürich  │ │ Berlin  │ │ Lisbon  │                  │    │                                      │      ░  │
│ ░    │     ╰─────────╯ ╰─────────╯ ╰─────────╯                  │    │                                      │      ░  │
│ ░    │                                                          │    │                                      │      ░  │
│ ░    │     ╭──────────────────────────────╮                     │    │                                      │      ░  │
│ ░    │     │  Continue                 →  │                     │    │                                      │      ░  │
│ ░    │     ╰──────────────────────────────╯                     │    │                                      │      ░  │
│ ░    │                                                          │    │                                      │      ░  │
│ ░    └──────────────────────────────────────────────────────────┘    └──────────────────────────────────────┘      ░  │
│ ░                                                                                                                   ░  │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Components used

- **shadcn/ui**: `Input`, `Form`, `Button` (chips)
- **landing-inherited**: `GlowButton`, `glass-card`, `AuroraOrbs`, `bg-void`, `EASE_OUT_QUART`
- **custom new**: `WizardShell`, `QuestionCard`, `WhyWeAsk`, `NikitaReaction` (typewriter), `ProgressRail`, `PersonalizationPreviewChip` (desktop only — optional, gated by §10 item 6)
- **third-party**: Aceternity `placeholders-and-vanish-input` (cycling placeholder), Magicui `text-shimmer` (live morph)

### Motion + interaction notes

- Page enter: `AnimatePresence mode="wait"` opacity 0→1 + y 16→0 + blur(8px)→0 over 350ms
- Stagger: eyebrow 0ms / headline 150ms / why-we-ask 300ms / input 450ms / chips 550ms / CTA 600ms
- Placeholder cycle: 4-string rotation, 2500ms each, vanish-particle effect on next
- Live morph: as `value.length >= 2`, italic line below input morphs `"<typed>?"` → `"<typed>. okay."`
- Chip tap: auto-fills input + 200ms delay → triggers Continue
- Submit: `POST /onboarding/answer {slot_kind:"location", value:"<city>"}` → response fields drive Screen 2 framing

---

## Screen 2 — Scene

### Mobile (390 × 844)

```
┌──────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━━━━━┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄ 22%   │
│ ← back              ●⃝ filing your scene...     │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░                                            ░ │
│ ░  [so far: zürich · ___]                    ░ │  ← persona-preview chip
│ ░                                            ░ │     (cumulative mirror)
│ ░               S C E N E                    ░ │
│ ░                                            ░ │
│ ░   what's your scene?                       ░ │
│ ░   techno, art, food, cocktails —           ░ │  ← agent-generated
│ ░   something else entirely.                 ░ │     reaction-prefaced
│ ░                                            ░ │
│ ░  ┊Your scene shapes what Nikita's into.     ░ │
│ ░  ┊What she'd suggest on a Friday, where      ░ │
│ ░  ┊she'd find you when you go quiet.          ░ │
│ ░                                            ░ │
│ ░  ╭─────────╮ ╭─────────╮ ╭─────────╮       ░ │
│ ░  │ techno  │ │  art    │ │  food   │       ░ │  ← RadioGroup chips
│ ░  │   ○     │ │   ○     │ │   ●     │       ░ │     has-[:checked] glow
│ ░  ╰─────────╯ ╰─────────╯ ╰─────────╯       ░ │
│ ░  ╭─────────╮ ╭─────────╮ ╭─────────╮       ░ │
│ ░  │cocktails│ │ nature  │ │ type my │       ░ │
│ ░  │   ○     │ │   ○     │ │  own ✎  │       ░ │
│ ░  ╰─────────╯ ╰─────────╯ ╰─────────╯       ░ │
│ ░                                            ░ │
│ ░  ┊add a flavor:                            ░ │  ← optional vibe slot
│ ░  ╭───────╮ ╭──────╮ ╭─────────╮            ░ │     (PR-F2c.1)
│ ░  │low-key│ │ loud │ │dressed-up│           ░ │
│ ░  ╰───────╯ ╰──────╯ ╰─────────╯            ░ │
│ ░  ╭──────╮ ╭──────────────╮                 ░ │
│ ░  │alone │ │with friends  │                 ░ │
│ ░  ╰──────╯ ╰──────────────╯                 ░ │
│ ░                                            ░ │
│ ░    ╭──────────────────────────╮            ░ │
│ ░    │  Continue            →   │            ░ │
│ ░    ╰──────────────────────────╯            ░ │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└──────────────────────────────────────────────────┘
```

### Desktop (1440 × 900)

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄ 22%   │
│ ← back                                                                            ●⃝ filing your scene...              │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░                                                                                                                   ░  │
│ ░    ┌─────────────────────────────────────────────────────────────────────────┐    ┌────────────────────────┐     ░  │
│ ░    │   [so far: zürich · ____]   ←motion.div layout for smooth morph         │    │                        │     ░  │
│ ░    │                                                                         │    │   ╔══════════════════╗  │     ░  │
│ ░    │   S C E N E                                                             │    │   ║ nikita-portrait  ║  │     ░  │
│ ░    │                                                                         │    │   ║ (intimate.png    ║  │     ░  │
│ ░    │   ╭───────────────────────────────────────────────╮                     │    │   ║  dim 60%, fade-  ║  │     ░  │
│ ░    │   │  what's your scene?                           │                     │    │   ║  in on selection)║  │     ░  │
│ ░    │   │  techno, art, food, cocktails —               │                     │    │   ║                  ║  │     ░  │
│ ░    │   │  something else entirely.                     │                     │    │   ╚══════════════════╝  │     ░  │
│ ░    │   ╰───────────────────────────────────────────────╯                     │    │                        │     ░  │
│ ░    │                                                                         │    │                        │     ░  │
│ ░    │   ┊Your scene shapes what Nikita's into. What she'd suggest on a Friday, where she'd find you when    │    │     │     ░  │
│ ░    │   ┊you go quiet.                                                       │    │                        │     ░  │
│ ░    │                                                                         │    │                        │     ░  │
│ ░    │   ╭────────╮ ╭────────╮ ╭────────╮ ╭──────────╮ ╭────────╮ ╭─────────╮ │    │                        │     ░  │
│ ░    │   │ techno │ │  art   │ │  food  │ │cocktails │ │ nature │ │ type ✎  │ │    │                        │     ░  │
│ ░    │   │   ○    │ │   ○    │ │   ●    │ │    ○     │ │   ○    │ │ my own  │ │    │                        │     ░  │
│ ░    │   ╰────────╯ ╰────────╯ ╰────────╯ ╰──────────╯ ╰────────╯ ╰─────────╯ │    │                        │     ░  │
│ ░    │                                                                         │    │                        │     ░  │
│ ░    │   ┊add a flavor:                                                        │    │                        │     ░  │
│ ░    │   ╭────────╮ ╭──────╮ ╭───────────╮ ╭──────╮ ╭──────────────╮          │    │                        │     ░  │
│ ░    │   │low-key │ │ loud │ │dressed-up │ │alone │ │with friends  │          │    │                        │     ░  │
│ ░    │   ╰────────╯ ╰──────╯ ╰───────────╯ ╰──────╯ ╰──────────────╯          │    │                        │     ░  │
│ ░    │                                                                         │    │                        │     ░  │
│ ░    │   ╭───────────────────────────────╮                                     │    │                        │     ░  │
│ ░    │   │  Continue                  →  │                                     │    │                        │     ░  │
│ ░    │   ╰───────────────────────────────╯                                     │    │                        │     ░  │
│ ░    └─────────────────────────────────────────────────────────────────────────┘    └────────────────────────┘     ░  │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Components used

- **shadcn/ui**: `RadioGroup`, `RadioGroupItem`, `Form`, `Label`, `Input` (revealed by "type my own")
- **landing-inherited**: `GlowButton`, `glass-card`, `AuroraOrbs`, `EASE_OUT_QUART`, `glow-rose-pulse`
- **custom new**: `PersonalizationPreviewChip` (top-left/right; uses framer-motion `layout` for smooth slot morph), `WizardShell`, `QuestionCard`, `WhyWeAsk`, `NikitaReaction`, `ChipGroup` (RadioGroup wrapper with `has-[:checked]` glow)
- **third-party**: none

### Motion + interaction notes

- Page enter: same as Screen 1
- Stagger: persona-chip 0ms / eyebrow 50ms / headline 150ms / why-we-ask 300ms / chips 450ms (parent) + 50ms each chip (children) / CTA 700ms
- Persona-chip slot morphs from "___" → selected scene chip text on tap, framer-motion `layout` prop (300ms)
- Chip tap: filled radio dot animates from ○ to ● with rose glow border (200ms)
- "type my own" tap: chip transforms in-place into a text input (height 40 → 56, layout animation)
- Vibe row stays optional; tap toggles single selection (acts like RadioGroup)
- Submit: `POST /onboarding/answer {slot_kind:"scene", value:"food", optional_adjacent:{vibe:"low-key"}}` per F2c.1

---

## Screen 3 — Darkness

### Mobile (390 × 844)

```
┌──────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┄┄┄┄┄┄┄┄┄┄┄ 33%  │
│ ← back              ●⃝ measuring depth...       │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░                                            ░ │
│ ░ [so far: zürich · food, low-key · __]      ░ │
│ ░                                            ░ │
│ ░             D A R K N E S S                ░ │
│ ░                                            ░ │
│ ░    ╭───────────────────────────────╮       ░ │
│ ░    │  how dark do you go?          │       ░ │
│ ░    ╰───────────────────────────────╯       ░ │
│ ░                                            ░ │
│ ░  ┊How dark Nikita can go with you.          ░ │
│ ░  ┊Calm = grounded, supportive. Dark =       ░ │
│ ░  ┊jealousy, fights, real stakes.            ░ │
│ ░                                            ░ │
│ ░  ┊Default is mid. Most people start         ░ │
│ ░  ┊there and adjust once they know her.      ░ │
│ ░                                            ░ │
│ ░  ┊No illegal content at any setting.        ░ │
│ ░  ┊Dial down anytime.                        ░ │
│ ░                                            ░ │
│ ░                                            ░ │
│ ░   ╭───────────────────────────────────╮    ░ │
│ ░   │ ●━━━━━━━━━━━●━━━━━━━━━━━━━━━━━━━ │    ░ │  ← shadcn Slider
│ ░   │   0    1    2    3    4    5     │    ░ │     gradient track
│ ░   │                ↑ value: 3        │    ░ │     filled portion
│ ░   ╰───────────────────────────────────╯    ░ │     glow-rose shadow
│ ░                                            ░ │
│ ░   "just lamps on"      "blackout intent."  ░ │  ← endpoint labels
│ ░                                            ░ │
│ ░   ┊"a glass with friends"  (label@3)       ░ │  ← mid-label reveals
│ ░                                            ░ │     on tap/drag
│ ░                                            ░ │
│ ░   ┊so you're soft.                         ░ │  ← Nikita interp.
│ ░     (text-shimmer Magicui, hard-cuts       ░ │     0-3: "soft"
│ ░      between ranges 0-3, 4-7, 8-10)        ░ │     4-7: "interesting."
│ ░                                            ░ │     8-10:"yeah, i thought so."
│ ░                                            ░ │
│ ░    ╭──────────────────────────╮            ░ │
│ ░    │  Continue            →   │            ░ │
│ ░    ╰──────────────────────────╯            ░ │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└──────────────────────────────────────────────────┘
```

### Desktop (1440 × 900)

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┄┄┄┄┄┄┄ 33%   │
│ ← back                                                                            ●⃝ measuring depth...                │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░                                                                                                                   ░  │
│ ░    ┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐    ░  │
│ ░    │   [so far: zürich · food, low-key · __]                                                                │    ░  │
│ ░    │                                                                                                        │    ░  │
│ ░    │   D A R K N E S S                                                                                      │    ░  │
│ ░    │                                                                                                        │    ░  │
│ ░    │   ╭────────────────────────────────────────────────╮                                                   │    ░  │
│ ░    │   │  how dark do you go?                           │                                                   │    ░  │
│ ░    │   ╰────────────────────────────────────────────────╯                                                   │    ░  │
│ ░    │                                                                                                        │    ░  │
│ ░    │   ┊How dark Nikita can go with you. Calm = grounded, supportive. Dark = jealousy, fights, real stakes. │    ░  │
│ ░    │                                                                                                        │    ░  │
│ ░    │   ┊Default is mid. Most people start there and adjust once they know her.                              │    ░  │
│ ░    │                                                                                                        │    ░  │
│ ░    │   ┊No illegal content at any setting. Dial down anytime.                                                │    ░  │
│ ░    │                                                                                                        │    ░  │
│ ░    │                                                                                                        │    ░  │
│ ░    │   ╭───────────────────────────────────────────────────────────────────────────────────────╮            │    ░  │
│ ░    │   │  ●━━━━━━━━━━━━━━━━━●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │            │    ░  │
│ ░    │   │  0    1    2    3    4    5    6    7    8    9    10                                │            │    ░  │
│ ░    │   │                       ↑ value: 3                                                      │            │    ░  │
│ ░    │   ╰───────────────────────────────────────────────────────────────────────────────────────╯            │    ░  │
│ ░    │       "just lamps on"                                                  "blackout intentional"          │    ░  │
│ ░    │                                                                                                        │    ░  │
│ ░    │   ┊"a glass with friends"  (mid-range label, reveals on tap @ value=3)                                 │    ░  │
│ ░    │       (also "alone in dim" @ 6, "deliberately lost" @ 9)                                               │    ░  │
│ ░    │                                                                                                        │    ░  │
│ ░    │   ┊so you're soft.                                                                                     │    ░  │
│ ░    │       (live morph between ranges, text-shimmer fade)                                                   │    ░  │
│ ░    │                                                                                                        │    ░  │
│ ░    │   ╭───────────────────────────────╮                                                                    │    ░  │
│ ░    │   │  Continue                  →  │                                                                    │    ░  │
│ ░    │   ╰───────────────────────────────╯                                                                    │    ░  │
│ ░    │                                                                                                        │    ░  │
│ ░    └────────────────────────────────────────────────────────────────────────────────────────────────────────┘    ░  │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Components used

- **shadcn/ui**: `Slider` (custom track gradient, custom thumb with `glow-rose`), `Form`, `Tooltip` (mid-range labels)
- **landing-inherited**: `GlowButton`, `glass-card`, `AuroraOrbs`, `glow-rose` shadow utility
- **custom new**: `DarknessSlider` (extends Slider with gradient + interp labels), `WizardShell`, `QuestionCard`, `WhyWeAsk`, `RangeInterpreter` (3-band live italic morph)
- **third-party**: Magicui `text-shimmer` (band transition fade)

### Motion + interaction notes

- Page enter: same
- Stagger: persona-chip 0ms / eyebrow 50ms / headline 150ms / why-we-ask 300ms / slider 450ms / CTA 600ms
- Slider drag: filled portion gradient hue shifts cool→hot in real time; thumb gains rose glow on focus
- Mid-range label appears on tap-and-hold (300ms) at thumb position
- Range interp: hard-cuts between bands, text-shimmer wipes from left on transition
- Reduced-motion: skip text-shimmer, instant text swap

---

## Screen 4 — Name

### Mobile (390 × 844)

```
┌──────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┄┄┄┄ 44%   │
│ ← back              ●⃝ noting your name...      │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░                                            ░ │
│ ░ [zürich · food · 3 · __]                   ░ │
│ ░                                            ░ │
│ ░                N A M E                     ░ │
│ ░                                            ░ │
│ ░    ╭───────────────────────────────╮       ░ │
│ ░    │  what should i call you?      │       ░ │
│ ░    ╰───────────────────────────────╯       ░ │
│ ░                                            ░ │
│ ░  ┊Your name lets Nikita address you          ░ │
│ ░  ┊directly. First name only, change it        ░ │
│ ░  ┊anytime.                                    ░ │
│ ░                                            ░ │
│ ░  ┌────────────────────────────────────┐    ░ │
│ ░  │ Simon|                          ⌨  │    ░ │  ← Input auto-focus
│ ░  └────────────────────────────────────┘    ░ │     placeholder "first name"
│ ░    max 30, no all-numeric, no single-char  ░ │
│ ░                                            ░ │
│ ░  ┊Simon. say it back to me                 ░ │  ← reaction on blur or
│ ░  ┊when you're nervous.                     ░ │     800ms after typing
│ ░    (typewriter 30ms stagger)               ░ │     stops
│ ░                                            ░ │
│ ░    output_validator REJECTS any reaction   ░ │  ← anti-mirror-echo
│ ░    containing literal `<name><name>`       ░ │     (#442 fix)
│ ░                                            ░ │
│ ░                                            ░ │
│ ░    ╭──────────────────────────╮            ░ │
│ ░    │  Continue            →   │            ░ │
│ ░    ╰──────────────────────────╯            ░ │
│ ░                                            ░ │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└──────────────────────────────────────────────────┘
```

### Desktop (1440 × 900)

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┄ 44% │
│ ← back                                                                              ●⃝ noting your name...             │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░                                                                                                                   ░  │
│ ░    ┌────────────────────────────────────────────────────────────────────────────────────────────────────┐        ░  │
│ ░    │   [zürich · food, low-key · 3 · __]                                                                │        ░  │
│ ░    │                                                                                                    │        ░  │
│ ░    │   N A M E                                                                                          │        ░  │
│ ░    │                                                                                                    │        ░  │
│ ░    │   ╭──────────────────────────────────────────────╮                                                 │        ░  │
│ ░    │   │  what should i call you?                     │                                                 │        ░  │
│ ░    │   ╰──────────────────────────────────────────────╯                                                 │        ░  │
│ ░    │                                                                                                    │        ░  │
│ ░    │   ┊Your name lets Nikita address you directly. First name only, change it anytime.                 │        ░  │
│ ░    │                                                                                                    │        ░  │
│ ░    │   ┌──────────────────────────────────────────────────────────────────────────────────────────┐    │        ░  │
│ ░    │   │  Simon|                                                                               ⌨  │    │        ░  │
│ ░    │   └──────────────────────────────────────────────────────────────────────────────────────────┘    │        ░  │
│ ░    │     ┊validation: max 30 chars, reject all-numeric, reject single-char                              │        ░  │
│ ░    │                                                                                                    │        ░  │
│ ░    │   ┊"Simon. say it back to me when you're nervous."                                                 │        ░  │
│ ░    │     (typewriter 30ms stagger; appears on blur OR 800ms after typing stops)                         │        ░  │
│ ░    │     (output_validator REJECTS reactions containing literal <name><name> per #442)                  │        ░  │
│ ░    │                                                                                                    │        ░  │
│ ░    │   ╭───────────────────────────────╮                                                                │        ░  │
│ ░    │   │  Continue                  →  │                                                                │        ░  │
│ ░    │   ╰───────────────────────────────╯                                                                │        ░  │
│ ░    │                                                                                                    │        ░  │
│ ░    └────────────────────────────────────────────────────────────────────────────────────────────────────┘        ░  │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Components used

- **shadcn/ui**: `Input`, `Form`, `FormMessage` (validation)
- **landing-inherited**: `GlowButton`, `glass-card`, `AuroraOrbs`
- **custom new**: `WizardShell`, `QuestionCard`, `WhyWeAsk`, `NikitaReaction` (typewriter; integrates output-validator anti-mirror)
- **third-party**: none

### Motion + interaction notes

- Page enter: same
- Stagger: persona-chip 0ms / eyebrow 50ms / headline 150ms / why-we-ask 300ms / input 450ms / CTA 600ms (disabled until valid)
- Input auto-focuses on mount; max-length 30; FE rejects all-numeric and single-char with inline `FormMessage`
- Reaction renders below on `onBlur` OR 800ms after `onChange` debounce; typewriter at 30ms stagger
- Backend `@agent.output_validator` raises `ModelRetry` if reaction text contains `<name><name>` (mirror-echo) — server-side guard

---

## Screen 5 — Age

### Mobile (390 × 844)

```
┌──────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┄ 55%  │
│ ← back              ●⃝ checking your age...     │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░                                            ░ │
│ ░ [zürich · food · 3 · Simon · __]           ░ │
│ ░                                            ░ │
│ ░                 A G E                      ░ │
│ ░                                            ░ │
│ ░    ╭───────────────────────────────╮       ░ │
│ ░    │  how old?                     │       ░ │
│ ░    ╰───────────────────────────────╯       ░ │
│ ░                                            ░ │
│ ░  ┊Your age sets Nikita's. She'll land in    ░ │
│ ░  ┊your decade, with references and pace     ░ │
│ ░  ┊that match yours.                         ░ │
│ ░                                            ░ │
│ ░  ┊18+ only, legal gate. Stored privately,   ░ │
│ ░  ┊never shown to anyone else.               ░ │
│ ░                                            ░ │
│ ░          ╭───────────────────────╮         ░ │
│ ░          │   ╭───╮  ╭──╮  ╭───╮  │         ░ │
│ ░          │   │ − │  │27│  │ + │  │         ░ │  ← number stepper
│ ░          │   ╰───╯  ╰──╯  ╰───╯  │         ░ │     range 18-99
│ ░          ╰───────────────────────╯         ░ │     default 25 (empty mount)
│ ░                                            ░ │
│ ░  if value < 18:                            ░ │
│ ░  ┌────────────────────────────────────┐    ░ │
│ ░  │ ⚠ "sorry. you have to leave."      │    ░ │  ← in-character error
│ ░  └────────────────────────────────────┘    ░ │     submit blocked
│ ░                                            ░ │
│ ░                                            ░ │
│ ░                              ╭──────────╮  ░ │
│ ░                              │mid-twenties│  ← range chip badge
│ ░                              ╰──────────╯  ░ │     post-input
│ ░                                            ░ │
│ ░    ╭──────────────────────────╮            ░ │
│ ░    │  Continue            →   │            ░ │
│ ░    ╰──────────────────────────╯            ░ │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└──────────────────────────────────────────────────┘
```

### Desktop (1440 × 900)

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 55%│
│ ← back                                                                              ●⃝ checking your age...            │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░                                                                                                                   ░  │
│ ░    ┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐       ░  │
│ ░    │   [zürich · food, low-key · 3 · Simon · __]                                                         │       ░  │
│ ░    │                                                                                                     │       ░  │
│ ░    │   A G E                                                                                             │       ░  │
│ ░    │                                                                                                     │       ░  │
│ ░    │   ╭──────────────────────────────────╮                                                              │       ░  │
│ ░    │   │  how old?                        │                                                              │       ░  │
│ ░    │   ╰──────────────────────────────────╯                                                              │       ░  │
│ ░    │                                                                                                     │       ░  │
│ ░    │   ┊Your age sets Nikita's. She'll land in your decade, with references and pace that match yours.   │       ░  │
│ ░    │                                                                                                     │       ░  │
│ ░    │   ┊18+ only, legal gate. Stored privately, never shown to anyone else.                              │       ░  │
│ ░    │                                                                                                     │       ░  │
│ ░    │              ╭────────────────────────────────╮                                                     │       ░  │
│ ░    │              │   ╭───╮     ╭────╮    ╭───╮    │                                                     │       ░  │
│ ░    │              │   │ − │     │ 27 │    │ + │    │   ← number stepper                                  │       ░  │
│ ░    │              │   ╰───╯     ╰────╯    ╰───╯    │     keyboard ↑↓ supported                           │       ░  │
│ ░    │              ╰────────────────────────────────╯                                                     │       ░  │
│ ░    │                                                                                                     │       ░  │
│ ░    │   if <18:  ┌──────────────────────────────────────────┐                                             │       ░  │
│ ░    │            │ ⚠ "sorry. you have to leave."             │                                             │       ░  │
│ ░    │            └──────────────────────────────────────────┘                                             │       ░  │
│ ░    │                                                                                                     │       ░  │
│ ░    │   on valid input:                                              ╭───────────────╮                    │       ░  │
│ ░    │                                                                │ mid-twenties  │  ← range badge     │       ░  │
│ ░    │                                                                ╰───────────────╯     bottom-right   │       ░  │
│ ░    │                                                                                                     │       ░  │
│ ░    │   ╭───────────────────────────────╮                                                                 │       ░  │
│ ░    │   │  Continue                  →  │   (disabled if invalid)                                         │       ░  │
│ ░    │   ╰───────────────────────────────╯                                                                 │       ░  │
│ ░    │                                                                                                     │       ░  │
│ ░    └─────────────────────────────────────────────────────────────────────────────────────────────────────┘       ░  │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Components used

- **shadcn/ui**: `Input` (`type="number"`), `Button` (± steppers), `Form`, `FormMessage`, `Badge`
- **landing-inherited**: `GlowButton`, `glass-card`, `AuroraOrbs`
- **custom new**: `AgeStepper` (composed Input + buttons), `AgeRangeBadge` (computes "early-twenties" / "mid-thirties" / "forties+" client-side), `WizardShell`, `QuestionCard`
- **third-party**: none

### Motion + interaction notes

- Page enter: same
- Default empty on mount; `+`/`−` buttons step by 1; keyboard ↑↓ also works
- Range tag appears 200ms after valid value with fade-up
- If <18: error inline + GlowButton stays disabled; `aria-live="polite"` announces

---

## Screen 6 — Occupation

### Mobile (390 × 844)

```
┌──────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┄ 66%│
│ ← back              ●⃝ filing your work...      │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░                                            ░ │
│ ░ [zürich · food · 3 · Simon · 27 · __]      ░ │
│ ░                                            ░ │
│ ░                W O R K                     ░ │
│ ░                                            ░ │
│ ░    ╭───────────────────────────────╮       ░ │
│ ░    │  what do you do when you're   │       ░ │
│ ░    │  not with me?                 │       ░ │
│ ░    ╰───────────────────────────────╯       ░ │
│ ░                                            ░ │
│ ░  ┊Your work sets what Nikita asks about      ░ │
│ ░  ┊on a tuesday at 3pm. Job titles only;       ░ │
│ ░  ┊she won't ask for employer.                 ░ │
│ ░                                            ░ │
│ ░  ┌────────────────────────────────────┐    ░ │
│ ░  │ designer___                     ⌨  │    ░ │  ← Aceternity placeholders
│ ░  └────────────────────────────────────┘    ░ │     -and-vanish-input
│ ░    cycles: designer · finance · medic ·    ░ │     2.5s rotation
│ ░    writer · founder · "tell me"            ░ │
│ ░                                            ░ │
│ ░  ╭─────────╮ ╭────────╮ ╭───────╮          ░ │
│ ░  │designer │ │finance │ │ medic │          ░ │  ← 6 occupation chips
│ ░  ╰─────────╯ ╰────────╯ ╰───────╯          ░ │     glass-card style
│ ░  ╭────────╮ ╭─────────╮ ╭──────╮           ░ │
│ ░  │writer  │ │ founder │ │other │           ░ │
│ ░  ╰────────╯ ╰─────────╯ ╰──────╯           ░ │
│ ░                                            ░ │
│ ░  ┊finance. of course.                      ░ │  ← agent reaction
│ ░    (cross-ref: zurich+finance="of course"  ░ │     based on city+job
│ ░     lisbon+medic="unexpected")             ░ │     intelligence demo
│ ░                                            ░ │
│ ░    ╭──────────────────────────╮            ░ │
│ ░    │  Continue            →   │            ░ │
│ ░    ╰──────────────────────────╯            ░ │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└──────────────────────────────────────────────────┘
```

### Desktop (1440 × 900)

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 66%│
│ ← back                                                                              ●⃝ filing your work...             │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░                                                                                                                   ░  │
│ ░    ┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐       ░  │
│ ░    │   [zürich · food, low-key · 3 · Simon · 27 · __]                                                    │       ░  │
│ ░    │                                                                                                     │       ░  │
│ ░    │   W O R K                                                                                           │       ░  │
│ ░    │                                                                                                     │       ░  │
│ ░    │   ╭────────────────────────────────────────────────╮                                                │       ░  │
│ ░    │   │  what do you do when you're not with me?       │                                                │       ░  │
│ ░    │   ╰────────────────────────────────────────────────╯                                                │       ░  │
│ ░    │                                                                                                     │       ░  │
│ ░    │   ┊Your work sets what Nikita asks about on a tuesday at 3pm. Job titles only; she won't ask for      │       ░  │
│ ░    │   ┊employer.                                                                                            │       ░  │
│ ░    │                                                                                                     │       ░  │
│ ░    │   ┌────────────────────────────────────────────────────────────────────────────────────────┐        │       ░  │
│ ░    │   │  designer___                                                                       ⌨  │        │       ░  │
│ ░    │   └────────────────────────────────────────────────────────────────────────────────────────┘        │       ░  │
│ ░    │     cycles: "designer" · "finance" · "medic" · "writer" · "founder" · "tell me"                     │       ░  │
│ ░    │                                                                                                     │       ░  │
│ ░    │   ╭──────────╮ ╭──────────╮ ╭───────╮ ╭────────╮ ╭──────────╮ ╭─────────╮                          │       ░  │
│ ░    │   │ designer │ │ finance  │ │ medic │ │ writer │ │ founder  │ │  other  │                          │       ░  │
│ ░    │   ╰──────────╯ ╰──────────╯ ╰───────╯ ╰────────╯ ╰──────────╯ ╰─────────╯                          │       ░  │
│ ░    │                                                                                                     │       ░  │
│ ░    │   ┊finance. of course.                                                                              │       ░  │
│ ░    │     (city × occupation cross-ref → "of course" / "unexpected" / "noted." — agent intelligence demo) │       ░  │
│ ░    │                                                                                                     │       ░  │
│ ░    │   ╭───────────────────────────────╮                                                                 │       ░  │
│ ░    │   │  Continue                  →  │                                                                 │       ░  │
│ ░    │   ╰───────────────────────────────╯                                                                 │       ░  │
│ ░    │                                                                                                     │       ░  │
│ ░    └─────────────────────────────────────────────────────────────────────────────────────────────────────┘       ░  │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Components used

- **shadcn/ui**: `Input`, `Button` (chips), `Form`
- **landing-inherited**: `GlowButton`, `glass-card`, `AuroraOrbs`
- **custom new**: `WizardShell`, `QuestionCard`, `WhyWeAsk`, `NikitaReaction` (typewriter), `OccupationChips` (glass-card chips with `has-[:checked]`-like style for tap fill)
- **third-party**: Aceternity `placeholders-and-vanish-input`

### Motion + interaction notes

- Page enter: same
- Stagger: persona-chip 0ms / eyebrow 50ms / headline 150ms / why-we-ask 300ms / input 450ms / chips 550ms / CTA 700ms
- Chip tap: auto-fills input + 250ms → triggers reaction render
- Reaction generated by agent on submit (or 800ms idle after typing); typewriter render
- §10 item 5 open: agent-suggested chips vs hardcoded — wireframe shows hardcoded for now

---

## Screen 7 — Hobbies

### Mobile (390 × 844)

```
┌──────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 47%│
│ ← back              ●⃝ shaping her overlap...   │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░ [zürich · food · 3 · Simon · 27 · finance] ░ │
│ ░                                            ░ │
│ ░               H A B I T S                  ░ │
│ ░                                            ░ │
│ ░    ╭───────────────────────────────╮       ░ │
│ ░    │  what fills your real days?   │       ░ │
│ ░    ╰───────────────────────────────╯       ░ │
│ ░                                            ░ │
│ ░  ┊Your hobbies set the overlap. Nikita      ░ │
│ ░  ┊will already know what you mean by        ░ │
│ ░  ┊climbing or DJing or chess, with one      ░ │
│ ░  ┊or two of her own you can argue about.    ░ │
│ ░                                            ░ │
│ ░  ╭─ Music ──────────────────────────────╮  ░ │
│ ░  │ ●techno  ○jazz  ○classical  ○folk    │  ░ │  ← HobbyChips C1.6
│ ░  ╰──────────────────────────────────────╯  ░ │     scrollable groups
│ ░  ╭─ Movement ───────────────────────────╮  ░ │
│ ░  │ ●climbing  ○running  ○yoga  ○boxing  │  ░ │
│ ░  ╰──────────────────────────────────────╯  ░ │
│ ░  ╭─ Reading ────────────────────────────╮  ░ │
│ ░  │ ○fiction  ●essays  ○poetry  ○news    │  ░ │
│ ░  ╰──────────────────────────────────────╯  ░ │
│ ░  ┌──────────────────────────────────────┐  ░ │
│ ░  │  + other_____                  0/40  │  ░ │  ← free text 40-cap
│ ░  └──────────────────────────────────────┘  ░ │
│ ░                                            ░ │
│ ░  ┊climber. of course.    ← live morph     ░ │
│ ░    (text-shimmer Magicui)                 ░ │
│ ░                                            ░ │
│ ░       3/5 picked   "pick 3-5"              ░ │  ← chip count helper
│ ░                                            ░ │
│ ░    ╭──────────────────────────╮            ░ │
│ ░    │  Continue            →   │            ░ │
│ ░    ╰──────────────────────────╯            ░ │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└──────────────────────────────────────────────────┘
```

### Desktop (1440 × 900)

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 47%│
│ ← back                                                                              ●⃝ shaping her overlap...           │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░    [zürich · food, low-key · 3 · Simon · 27 · finance · __]                                                       ░  │
│ ░                                                                                                                   ░  │
│ ░    H A B I T S                                                                                                    ░  │
│ ░                                                                                                                   ░  │
│ ░    ╭──────────────────────────────────────────────────────────────────╮                                           ░  │
│ ░    │  what fills your real days?                                       │                                           ░  │
│ ░    ╰──────────────────────────────────────────────────────────────────╯                                           ░  │
│ ░                                                                                                                   ░  │
│ ░    ┊Your hobbies set the overlap. Nikita will already know what you mean by climbing or DJing or chess,           ░  │
│ ░    ┊with one or two of her own you can argue about.                                                               ░  │
│ ░                                                                                                                   ░  │
│ ░    ┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐      ░  │
│ ░    │  10 category groups, scrollable. Multi-select 3-5. Cross-category autocomplete-filter.                │      ░  │
│ ░    │  Each chip <button role="button" aria-pressed>.   Live morph "climber. of course." after first pick.  │      ░  │
│ ░    │  + other free-text input below; hard cap 40 chars (maxLength=40); helper "${len}/40" rose at len ≥35.  │      ░  │
│ ░    └──────────────────────────────────────────────────────────────────────────────────────────────────────┘      ░  │
│ ░                                                                                                                   ░  │
│ ░    ┊climber. of course.   (text-shimmer Magicui)                                                                  ░  │
│ ░                                                                                                                   ░  │
│ ░         3/5 picked   "pick 3-5"                                                                                   ░  │
│ ░                                                                                                                   ░  │
│ ░    ╭───────────────────────────────╮                                                                              ░  │
│ ░    │  Continue                  →  │   (disabled outside 3-5)                                                    ░  │
│ ░    ╰───────────────────────────────╯                                                                              ░  │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Components used

- **shadcn/ui**: `Button` (chips), `Input` (autocomplete + other), `Form`
- **landing-inherited**: `GlowButton`, `glass-card`, `AuroraOrbs`
- **custom new**: `HobbyChips` (per C1.6), `WhyWeAsk`, `NikitaReaction` (live-morph)
- **third-party**: Magicui `text-shimmer`

### Motion + interaction notes

- Stagger: persona-chip 0ms / eyebrow 50ms / headline 150ms / why-we-ask 300ms / chip-groups 450ms (parent + 50ms each group) / live-morph 600ms / counter 700ms / CTA 800ms
- Reduced-motion: skip text-shimmer, instant chip selection feedback
- Live-morph fires on first chip select, then re-renders with last-picked label

---

## Screen 8 — Saturday Morning

### Mobile (390 × 844)

```
┌──────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 53%│
│ ← back              ●⃝ shaping her rhythm...    │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░ [...· climbing, essays, techno · __]       ░ │
│ ░                                            ░ │
│ ░   ┊Halfway. Six down, six to go.           ░ │  ← C1.19 midpoint nudge
│ ░     (dim text-muted, narrator-voice,       ░ │     first-render-only
│ ░      one-time render)                      ░ │
│ ░                                            ░ │
│ ░             S A T U R D A Y                ░ │
│ ░                                            ░ │
│ ░    ╭───────────────────────────────╮       ░ │
│ ░    │  what does a slow morning     │       ░ │
│ ░    │  look like?                   │       ░ │
│ ░    ╰───────────────────────────────╯       ░ │
│ ░                                            ░ │
│ ░  ┊Sets Nikita's slow-morning rhythm too.   ░ │
│ ░  ┊Her suggestions won't sound generic.     ░ │
│ ░                                            ░ │
│ ░  ┌──────────────────────────────────────┐  ░ │
│ ░  │ Tell me — coffee, run, paper, bed... │  ░ │  ← Aceternity
│ ░  └──────────────────────────────────────┘  ░ │     placeholders-and-vanish
│ ░    cycles: "espresso, slow paper" ·        ░ │     2.5s rotation
│ ░    "long run then brunch" ·                ░ │
│ ░    "in bed til noon"                       ░ │
│ ░                                            ░ │
│ ░  ┊slow brunch. patient.                    ░ │  ← live morph reaction
│ ░    (text-shimmer)                          ░ │
│ ░                                            ░ │
│ ░    ╭──────────────────────────╮            ░ │
│ ░    │  Continue            →   │            ░ │
│ ░    ╰──────────────────────────╯            ░ │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└──────────────────────────────────────────────────┘
```

### Desktop (1440 × 900)

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 53%│
│ ← back                                                                              ●⃝ shaping her rhythm...            │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░    [zürich · food, low-key · 3 · Simon · 27 · finance · climbing, essays, techno · __]                            ░  │
│ ░                                                                                                                   ░  │
│ ░    ┊Halfway. Six down, six to go.   (C1.19 midpoint, dim, narrator, first-render only)                            ░  │
│ ░                                                                                                                   ░  │
│ ░    S A T U R D A Y                                                                                                ░  │
│ ░                                                                                                                   ░  │
│ ░    ╭──────────────────────────────────────────────────────────────────╮                                           ░  │
│ ░    │  what does a slow morning look like?                              │                                           ░  │
│ ░    ╰──────────────────────────────────────────────────────────────────╯                                           ░  │
│ ░                                                                                                                   ░  │
│ ░    ┊Sets Nikita's slow-morning rhythm too. Her suggestions won't sound generic.                                   ░  │
│ ░                                                                                                                   ░  │
│ ░    ┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐      ░  │
│ ░    │  Tell me — coffee, run, paper, bed...                                                                 │      ░  │
│ ░    └──────────────────────────────────────────────────────────────────────────────────────────────────────┘      ░  │
│ ░      placeholder cycles: "espresso, slow paper" · "long run then brunch" · "in bed til noon"                      ░  │
│ ░                                                                                                                   ░  │
│ ░    ┊slow brunch. patient.   (text-shimmer live morph)                                                             ░  │
│ ░                                                                                                                   ░  │
│ ░    ╭───────────────────────────────╮                                                                              ░  │
│ ░    │  Continue                  →  │                                                                              ░  │
│ ░    ╰───────────────────────────────╯                                                                              ░  │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Components used

- **shadcn/ui**: `Input` (`type="text"`), `Form`, `Textarea` (mobile may use single-line input)
- **landing-inherited**: `GlowButton`, `glass-card`, `AuroraOrbs`
- **custom new**: `MidpointNudge` (C1.19 — one-time render with `useState(true)` + `useEffect` to false), `WhyWeAsk`, `NikitaReaction`
- **third-party**: Aceternity `placeholders-and-vanish-input`, Magicui `text-shimmer`

### Motion + interaction notes

- Midpoint nudge fades in 0ms (above-fold, narrator-voice), fades to dimmer state at 1.5s. Never re-renders on resume per C1.19.
- Stagger: midpoint-nudge 0ms / persona-chip 50ms / eyebrow 100ms / headline 200ms / why-we-ask 350ms / input 500ms / live-morph 750ms / CTA 850ms

---

## Screen 9 — Geek-Out

### Mobile (390 × 844)

```
┌──────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 60%│
│ ← back              ●⃝ tuning her interest...   │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░ [...· climbing · slow brunch · __]         ░ │
│ ░                                            ░ │
│ ░                  D E E P                   ░ │
│ ░                                            ░ │
│ ░    ╭───────────────────────────────╮       ░ │
│ ░    │  what would you talk about    │       ░ │
│ ░    │  for an hour?                 │       ░ │
│ ░    ╰───────────────────────────────╯       ░ │
│ ░                                            ░ │
│ ░  ┊What you'd talk about for an hour.       ░ │
│ ░  ┊Becomes a topic Nikita actually cares    ░ │
│ ░  ┊about, not just nods at.                 ░ │
│ ░                                            ░ │
│ ░  ┌──────────────────────────────────────┐  ░ │
│ ░  │ Tell me one. Be specific.            │  ░ │  ← Textarea
│ ░  │                                      │  ░ │     min-rows 3
│ ░  └──────────────────────────────────────┘  ░ │
│ ░                                            ░ │
│ ░  ┊noted.   (text-shimmer; per-cluster      ░ │  ← M1 follow-up triggers
│ ░    morph: "obviously." / "of course."      ░ │     depth-1 per B1.6
│ ░    / "go on.")                             ░ │
│ ░                                            ░ │
│ ░    ╭──────────────────────────╮            ░ │
│ ░    │  Continue            →   │            ░ │
│ ░    ╰──────────────────────────╯            ░ │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└──────────────────────────────────────────────────┘
```

### Desktop (1440 × 900)

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 60%│
│ ← back                                                                              ●⃝ tuning her interest...           │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░    [zürich · food · 3 · Simon · 27 · finance · climbing · slow brunch · __]                                       ░  │
│ ░                                                                                                                   ░  │
│ ░    D E E P                                                                                                        ░  │
│ ░                                                                                                                   ░  │
│ ░    ╭──────────────────────────────────────────────────────────────────╮                                           ░  │
│ ░    │  what would you talk about for an hour?                           │                                           ░  │
│ ░    ╰──────────────────────────────────────────────────────────────────╯                                           ░  │
│ ░                                                                                                                   ░  │
│ ░    ┊What you'd talk about for an hour. Becomes a topic Nikita actually cares about, not just nods at.             ░  │
│ ░                                                                                                                   ░  │
│ ░    ┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐      ░  │
│ ░    │  Tell me one. Be specific.                                                                            │      ░  │
│ ░    │                                                                                                       │      ░  │
│ ░    │                                                                                                       │      ░  │
│ ░    └──────────────────────────────────────────────────────────────────────────────────────────────────────┘      ░  │
│ ░                                                                                                                   ░  │
│ ░    ┊noted.    (Nikita-voice morph; M1 depth-1 follow-up triggers per B1.6 if cluster=ambiguous + turn<3)         ░  │
│ ░                                                                                                                   ░  │
│ ░    ╭───────────────────────────────╮                                                                              ░  │
│ ░    │  Continue                  →  │   (disabled until ≥10 chars)                                                ░  │
│ ░    ╰───────────────────────────────╯                                                                              ░  │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Components used

- **shadcn/ui**: `Textarea`, `Form`
- **landing-inherited**: `GlowButton`, `glass-card`, `AuroraOrbs`
- **custom new**: `WhyWeAsk`, `NikitaReaction` (cluster-aware live morph)
- **third-party**: Magicui `text-shimmer`

### Motion + interaction notes

- M1 depth-1 follow-up renders as next turn after submit (per B1.6); depth-2 only when cluster=ambiguous + turn_count_for_topic<3
- Persona reaction morphs based on ClassifyAnswerCluster output: aesthete→"obviously." | digital_nomad→"of course." | ambiguous→"go on."

---

## Screen 10 — Together / Odd (combined dual-textarea, per C1.18)

### Mobile (390 × 844)

```
┌──────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 67%│
│ ← back              ●⃝ finding shared ground...│
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░ [...· climbing · slow brunch · spreadsheet ░ │
│ ░  conspiracies · __]                        ░ │
│ ░                                            ░ │
│ ░         T O G E T H E R   /   O D D        ░ │
│ ░                                            ░ │
│ ░  ┊What the two of you would actually do,   ░ │
│ ░  ┊and the specific thing where finding     ░ │
│ ░  ┊someone else who gets it changes the     ░ │
│ ░  ┊room. Shapes what Nikita proposes and    ░ │
│ ░  ┊what she'll bring up later.              ░ │
│ ░                                            ░ │
│ ░  what we'd actually do together:           ░ │
│ ░  ┌──────────────────────────────────────┐  ░ │
│ ░  │  bookstore raid then gelato.         │  ░ │  ← Textarea 1
│ ░  │                                      │  ░ │     `together_we_could`
│ ░  └──────────────────────────────────────┘  ░ │     min-rows 2
│ ░                                            ░ │
│ ░  the specific weird thing:                 ░ │
│ ░  ┌──────────────────────────────────────┐  ░ │
│ ░  │  i sort all my bookmarks by mood.    │  ░ │  ← Textarea 2
│ ░  │                                      │  ░ │     `same_weird_if`
│ ░  └──────────────────────────────────────┘  ░ │     min-rows 2
│ ░                                            ░ │
│ ░  ┊huh. i'd say yes.   (Nikita-voice)       ░ │  ← per-textarea reaction
│ ░  ┊obviously.          (second morph)       ░ │
│ ░                                            ░ │
│ ░    ╭──────────────────────────╮            ░ │
│ ░    │  Continue            →   │            ░ │
│ ░    ╰──────────────────────────╯            ░ │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└──────────────────────────────────────────────────┘
```

### Desktop (1440 × 900)

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 67%│
│ ← back                                                                              ●⃝ finding shared ground...         │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░    [zürich · food · 3 · Simon · 27 · finance · climbing · slow brunch · spreadsheet conspiracies · __]            ░  │
│ ░                                                                                                                   ░  │
│ ░    T O G E T H E R   /   O D D                                                                                    ░  │
│ ░                                                                                                                   ░  │
│ ░    ┊What the two of you would actually do, and the specific thing where finding someone else who                  ░  │
│ ░    ┊gets it changes the room. Shapes what Nikita proposes and what she'll bring up later.                         ░  │
│ ░                                                                                                                   ░  │
│ ░    ┌─────────────────────────────────────────────────────┐  ┌─────────────────────────────────────────────────┐ ░  │
│ ░    │  what we'd actually do together:                    │  │  the specific weird thing:                       │ ░  │
│ ░    │ ┌──────────────────────────────────────────────────┐│  │ ┌──────────────────────────────────────────────┐ │ ░  │
│ ░    │ │ bookstore raid then gelato.                      ││  │ │ i sort all my bookmarks by mood.             │ │ ░  │
│ ░    │ │                                                  ││  │ │                                              │ │ ░  │
│ ░    │ │                                                  ││  │ │                                              │ │ ░  │
│ ░    │ └──────────────────────────────────────────────────┘│  │ └──────────────────────────────────────────────┘ │ ░  │
│ ░    │  ┊huh. i'd say yes.                                 │  │  ┊obviously.                                     │ ░  │
│ ░    └─────────────────────────────────────────────────────┘  └─────────────────────────────────────────────────┘ ░  │
│ ░                                                                                                                   ░  │
│ ░    ╭───────────────────────────────╮                                                                              ░  │
│ ░    │  Continue                  →  │   (disabled until both textareas ≥10 chars each)                            ░  │
│ ░    ╰───────────────────────────────╯                                                                              ░  │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Components used

- **shadcn/ui**: `Textarea` × 2, `Form`, `FormField` × 2
- **landing-inherited**: `GlowButton`, `glass-card`, `AuroraOrbs`
- **custom new**: `CombinedDualTextarea` (NEW per C1.18 — one screen, two slot writes via single submit), `WhyWeAsk`, `NikitaReaction` × 2 (one per textarea)
- **third-party**: Magicui `text-shimmer`

### Motion + interaction notes

- Both textareas independently fire NikitaReaction live-morph on blur
- Submit dispatches TWO `POST /onboarding/answer` calls (one per slot, sequential) OR a batched `POST /onboarding/answer/bulk` if backend supports — verify with B1.13 endpoint shape
- Mobile: stacked vertically; Desktop: side-by-side glass cards
- ProgressRail advances by 2 slot increments on successful submit (8/12 → 10/12)
- Reduced-motion: skip text-shimmer; instant reactions

---

## Screen 11 — Voice Tone

### Mobile (390 × 844)

```
┌──────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 73%│
│ ← back              ●⃝ tuning her voice...      │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░ [...· bookstore raid · bookmarks · __]     ░ │
│ ░                                            ░ │
│ ░                  T O N E                   ░ │
│ ░                                            ░ │
│ ░    ╭───────────────────────────────╮       ░ │
│ ░    │  how should Nikita sound?     │       ░ │
│ ░    ╰───────────────────────────────╯       ░ │
│ ░                                            ░ │
│ ░  ┊How Nikita should sound.                 ░ │
│ ░  ┊Warm: soft, present.                     ░ │
│ ░  ┊Cool: restrained, dry.                   ░ │
│ ░  ┊Playful: teasing, light.                 ░ │
│ ░  ┊You can change this anytime.             ░ │
│ ░                                            ░ │
│ ░  ╭──────────────╮ ╭──────────────╮         ░ │  ← RadioGroup glass
│ ░  │     warm     │ │    cool      │         ░ │     3-card row
│ ░  │   soft       │ │  restrained  │         ░ │     mobile: 2-up wrap
│ ░  │   ●          │ │      ○       │         ░ │
│ ░  ╰──────────────╯ ╰──────────────╯         ░ │
│ ░  ╭──────────────╮                          ░ │
│ ░  │   playful    │                          ░ │
│ ░  │   teasing    │                          ░ │
│ ░  │      ○       │                          ░ │
│ ░  ╰──────────────╯                          ░ │
│ ░                                            ░ │
│ ░  ┊warm. noted.                             ░ │  ← Nikita-voice reaction
│ ░    (per choice morph: "cool. fine."        ░ │
│ ░     / "playful. dangerous.")               ░ │
│ ░                                            ░ │
│ ░    ╭──────────────────────────╮            ░ │
│ ░    │  Continue            →   │            ░ │
│ ░    ╰──────────────────────────╯            ░ │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└──────────────────────────────────────────────────┘
```

### Desktop (1440 × 900)

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 73%│
│ ← back                                                                              ●⃝ tuning her voice...              │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░    [zürich · ... · bookstore raid · bookmarks · __]                                                               ░  │
│ ░                                                                                                                   ░  │
│ ░    T O N E                                                                                                        ░  │
│ ░                                                                                                                   ░  │
│ ░    ╭──────────────────────────────────────────────────────────────────╮                                           ░  │
│ ░    │  how should Nikita sound?                                         │                                           ░  │
│ ░    ╰──────────────────────────────────────────────────────────────────╯                                           ░  │
│ ░                                                                                                                   ░  │
│ ░    ┊How Nikita should sound.                                                                                      ░  │
│ ░    ┊Warm: soft, present. Cool: restrained, dry. Playful: teasing, light.                                          ░  │
│ ░    ┊You can change this anytime.                                                                                  ░  │
│ ░                                                                                                                   ░  │
│ ░    ╭────────────────────╮ ╭────────────────────╮ ╭────────────────────╮                                           ░  │
│ ░    │       warm         │ │       cool         │ │      playful       │                                           ░  │
│ ░    │   soft, present    │ │  restrained, dry   │ │   teasing, light   │                                           ░  │
│ ░    │        ●           │ │         ○          │ │         ○          │                                           ░  │
│ ░    ╰────────────────────╯ ╰────────────────────╯ ╰────────────────────╯                                           ░  │
│ ░                                                                                                                   ░  │
│ ░    ┊warm. noted.    (per choice: "cool. fine." / "playful. dangerous.")                                           ░  │
│ ░                                                                                                                   ░  │
│ ░    ╭───────────────────────────────╮                                                                              ░  │
│ ░    │  Continue                  →  │                                                                              ░  │
│ ░    ╰───────────────────────────────╯                                                                              ░  │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Components used

- **shadcn/ui**: `RadioGroup`, `RadioGroupItem`, `Card`, `Form`
- **landing-inherited**: `GlowButton`, `glass-card`, `AuroraOrbs`
- **custom new**: `controls/Chips.tsx` reused (3-card radio); `WhyWeAsk`, `NikitaReaction`
- **third-party**: Magicui `text-shimmer`

### Motion + interaction notes

- 3-card stagger 0/100/200ms on initial render
- Selected card: rose glow border + scale 1.02 (200ms)
- Reaction morph fires 400ms after selection change
- Reduced-motion: skip glow + scale, instant border-color toggle

---

## Screen 12 — Backstory

### Mobile (390 × 844)

```
┌──────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 77│
│ ← back            ●⃝ writing your variants...   │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░                                            ░ │
│ ░ [zürich · food · 3 · Simon · 27 · finance] ░ │
│ ░                                            ░ │
│ ░               S T O R Y                    ░ │
│ ░                                            ░ │
│ ░    ╭───────────────────────────────╮       ░ │
│ ░    │  i wrote three versions of    │       ░ │
│ ░    │  us. pick the one that's      │       ░ │
│ ░    │  most true.                   │       ░ │
│ ░    ╰───────────────────────────────╯       ░ │
│ ░                                            ░ │
│ ░  ┊i need a frame, not the whole picture.   ░ │
│ ░  ┊you can correct me later.                ░ │
│ ░                                            ░ │
│ ░  ┊each one knows your zurich nights,       ░ │  ← above-cards hint
│ ░  ┊your finance mornings.                   ░ │
│ ░  ┊i'm guessing what's underneath.          ░ │
│ ░                                            ░ │
│ ░  ╭──────────────────────────────────────╮  ░ │
│ ░  │  N O R T H        ○                  │  ░ │  ← variant 1 card
│ ░  │  ─────────────────────────────────   │  ░ │     (card-tag debate
│ ░  │  Three sentences of generated        │  ░ │      §10 item 2:
│ ░  │  persona prose seeded by all 6       │  ░ │      NORTH/WEST/SOUTH
│ ░  │  prior slots. Hover lifts card.      │  ░ │      vs VARIANT 1/2/3)
│ ░  ╰──────────────────────────────────────╯  ░ │
│ ░                                            ░ │
│ ░  ╭──────────────────────────────────────╮  ░ │
│ ░  │  W E S T          ●                  │  ░ │  ← selected (rose glow)
│ ░  │  ─────────────────────────────────   │  ░ │
│ ░  │  Three sentences of alt persona...   │  ░ │
│ ░  │                                      │  ░ │
│ ░  ╰──────────────────────────────────────╯  ░ │
│ ░                                            ░ │
│ ░  ╭──────────────────────────────────────╮  ░ │
│ ░  │  S O U T H        ○                  │  ░ │
│ ░  │  ─────────────────────────────────   │  ░ │
│ ░  │  Three sentences of third persona... │  ░ │
│ ░  ╰──────────────────────────────────────╯  ░ │
│ ░                                            ░ │
│ ░    ╭──────────────────────────╮            ░ │
│ ░    │  Continue            →   │            ░ │
│ ░    ╰──────────────────────────╯            ░ │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└──────────────────────────────────────────────────┘
```

### Desktop (1440 × 900)

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 77%
│ ← back                                                                              ●⃝ writing your variants...        │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░                                                                                                                   ░  │
│ ░    [zürich · food, low-key · 3 · Simon · 27 · finance · __]                                                       ░  │
│ ░                                                                                                                   ░  │
│ ░    S T O R Y                                                                                                      ░  │
│ ░                                                                                                                   ░  │
│ ░    ╭──────────────────────────────────────────────────────────────────────────────────────────────────╮           ░  │
│ ░    │  i wrote three versions of us. pick the one that's most true.                                    │           ░  │
│ ░    ╰──────────────────────────────────────────────────────────────────────────────────────────────────╯           ░  │
│ ░                                                                                                                   ░  │
│ ░    ┊i need a frame, not the whole picture. you can correct me later.                                              ░  │
│ ░                                                                                                                   ░  │
│ ░    ┊each one knows your zurich nights, your finance mornings. i'm guessing what's underneath.                     ░  │
│ ░                                                                                                                   ░  │
│ ░    ╭──────────────────────────────────╮  ╭──────────────────────────────────╮  ╭──────────────────────────────────╮│
│ ░    │ N O R T H              ○         │  │ W E S T                ●         │  │ S O U T H              ○         │
│ ░    │ ─────────────────────────────── │  │ ─────────────────────────────── │  │ ─────────────────────────────── ││
│ ░    │ "You move through Zürich         │  │ "You sit at the corner of       │  │ "You walk Lake Zürich at dawn   ││
│ ░    │  like a polite ghost. Spreadsheet│  │  every dinner table watching    │  │  with espresso. Finance pays    ││
│ ░    │  precision, knowing exactly when │  │  who's lying. Finance is your   │  │  for the silence you actually   ││
│ ░    │  to leave the party."            │  │  cover for being a noticer."    │  │  came for."                     ││
│ ░    │                                  │  │                                  │  │                                  ││
│ ░    │ (hover: scale 1.02 + shadow-xl   │  │ (selected: rose glow border,    │  │                                  ││
│ ░    │  + rose accent border)           │  │  has-[:checked] state)          │  │                                  ││
│ ░    ╰──────────────────────────────────╯  ╰──────────────────────────────────╯  ╰──────────────────────────────────╯│
│ ░                                                                                                                   ░  │
│ ░    ╭───────────────────────────────╮                                                                              ░  │
│ ░    │  Continue                  →  │   (disabled until card selected)                                             ░  │
│ ░    ╰───────────────────────────────╯                                                                              ░  │
│ ░                                                                                                                   ░  │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Components used

- **shadcn/ui**: `RadioGroup`, `RadioGroupItem`, `Card`, `Form`
- **landing-inherited**: `GlowButton`, `glass-card`, `AuroraOrbs`
- **custom new**: `BackstoryCard` (3-up grid mobile-stacked, desktop side-by-side; uses framer-motion `whileHover` for lift), `VariantTag` (eyebrow component — vocab gated by §10 item 2)
- **third-party**: none

### Motion + interaction notes

- Page enter: same
- Stagger: persona-chip 0ms / eyebrow 50ms / headline 150ms / why-we-ask 300ms / above-cards hint 400ms / cards 500/600/700ms (3 cards staggered) / CTA 850ms
- Hover (desktop): `motion.div whileHover={{ scale: 1.02, boxShadow: "0 20px 40px rgba(244, 63, 94, 0.2)" }}` 200ms
- Selected: rose accent border activates via `has-[:checked]` + 1.5px width transition
- Backend: REUSES existing `POST /preview-backstory` + `PUT /profile/chosen-option` flow (battle-tested)

---

## Screen 13 — Phone

### Mobile (390 × 844)

```
┌──────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 88%
│ ← back              ●⃝ planning your reach...   │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░                                            ░ │
│ ░ [zürich · food · 3 · Simon · 27 ·          ░ │
│ ░  finance · west · __]                      ░ │
│ ░                                            ░ │
│ ░               R E A C H                    ░ │
│ ░                                            ░ │
│ ░    ╭───────────────────────────────╮       ░ │
│ ░    │  How should Nikita reach you? │       ░ │
│ ░    │  Text only, voice only, both. │       ░ │
│ ░    ╰───────────────────────────────╯       ░ │
│ ░                                            ░ │
│ ░  ┊You can switch off voice, mute her,       ░ │
│ ░  ┊or revert to text-only anytime,           ░ │
│ ░  ┊from settings.                            ░ │
│ ░                                            ░ │
│ ░  ┊Your number stays private, never sold,    ░ │
│ ░  ┊shown, or shared.                         ░ │
│ ░                                            ░ │
│ ░  ┊Text means she writes. Voice means        ░ │
│ ░  ┊she can call, and you can call her.       ░ │
│ ░  ┊Both keeps either open.                   ░ │
│ ░                                            ░ │
│ ░  ╭──────────╮ ╭──────────╮ ╭──────────╮    ░ │
│ ░  │   💬     │ │    📞    │ │  💬+📞   │    ░ │  ← RadioGroup glass
│ ░  │  text    │ │  voice   │ │  both    │    ░ │     icons + label
│ ░  │   ●      │ │    ○     │ │    ○     │    ░ │
│ ░  ╰──────────╯ ╰──────────╯ ╰──────────╯    ░ │
│ ░                                            ░ │
│ ░  ┌───────────┬────────────────────────┐    ░ │
│ ░  │ 🇨🇭 +41 ▾ │ 79 123 45 67           │    ░ │  ← country prefix
│ ░  └───────────┴────────────────────────┘    ░ │     defaulted from city
│ ░    FE validates E.164 inline               ░ │     (Zürich → +41)
│ ░                                            ░ │
│ ░  ┊text it is.                              ░ │  ← reaction per choice
│ ░    (or "voice — bold." / "both. greedy.")  ░ │
│ ░                                            ░ │
│ ░    ╭──────────────────────────╮            ░ │
│ ░    │  Hand off to Nikita  →   │            ░ │  ← terminal CTA
│ ░    ╰──────────────────────────╯            ░ │     (different text!)
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└──────────────────────────────────────────────────┘
```

### Desktop (1440 × 900)

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 88%
│ ← back                                                                              ●⃝ planning your reach...          │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░    [zürich · food, low-key · 3 · Simon · 27 · finance · west · __]                                                ░  │
│ ░                                                                                                                   ░  │
│ ░    R E A C H                                                                                                      ░  │
│ ░                                                                                                                   ░  │
│ ░    ╭──────────────────────────────────────────────────────────────────────╮                                       ░  │
│ ░    │  How should Nikita reach you? Text only, voice only, both.           │                                       ░  │
│ ░    ╰──────────────────────────────────────────────────────────────────────╯                                       ░  │
│ ░                                                                                                                   ░  │
│ ░    ┊You can switch off voice, mute her, or revert to text-only anytime, from settings.                            ░  │
│ ░                                                                                                                   ░  │
│ ░    ┊Your number stays private, never sold, shown, or shared.                                                       ░  │
│ ░                                                                                                                   ░  │
│ ░    ┊Text means she writes. Voice means she can call, and you can call her. Both keeps either open.                ░  │
│ ░                                                                                                                   ░  │
│ ░    ╭──────────────────╮ ╭──────────────────╮ ╭──────────────────╮                                                ░  │
│ ░    │      💬          │ │       📞         │ │     💬 + 📞      │                                                ░  │
│ ░    │      text        │ │      voice       │ │       both       │                                                ░  │
│ ░    │       ●          │ │        ○         │ │        ○         │                                                ░  │
│ ░    ╰──────────────────╯ ╰──────────────────╯ ╰──────────────────╯                                                ░  │
│ ░                                                                                                                   ░  │
│ ░    ┌──────────────┬──────────────────────────────────────────────────────────────────┐                            ░  │
│ ░    │  🇨🇭 +41 ▾   │   79 123 45 67                                                  │                            ░  │
│ ░    └──────────────┴──────────────────────────────────────────────────────────────────┘                            ░  │
│ ░      country-code default from city → Zürich = +41                                                                ░  │
│ ░      FE E.164 validation inline (libphonenumber-js)                                                               ░  │
│ ░                                                                                                                   ░  │
│ ░    ┊text it is.                                                                                                   ░  │
│ ░                                                                                                                   ░  │
│ ░    ╭───────────────────────────────╮                                                                              ░  │
│ ░    │  Hand off to Nikita.       →  │   ← terminal action; weight signal                                           ░  │
│ ░    ╰───────────────────────────────╯                                                                              ░  │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Components used

- **shadcn/ui**: `RadioGroup`, `Input` (`type="tel"`), `Select` (country code), `Form`, `FormMessage`
- **landing-inherited**: `GlowButton` (text="Lock it in."), `glass-card`, `AuroraOrbs`
- **custom new**: `ReachRadioCards` (3 glass-card RadioGroup with icon), `PhoneInputE164` (composed Select+Input), `WhyWeAsk`, `NikitaReaction`
- **third-party**: `libphonenumber-js` (E.164 validation), Lucide `MessageSquare`, `Phone` icons

### Motion + interaction notes

- Page enter: same
- Stagger: persona-chip 0ms / eyebrow 50ms / headline 150ms / why-we-ask 300ms / radio-cards 450ms (parent + 50ms each) / phone-input 600ms / reaction 750ms / CTA 800ms
- Country code defaulted from prior `location` slot via lookup table
- Reaction renders 400ms after each radio selection change
- CTA disabled until E.164 valid AND reach selected

---

## Screen 14 — Completion ("love letter")

### Mobile (390 × 844)

```
┌──────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100│
│                     ●⃝ writing your first scene │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░  ▒▒  (ambient bg dialed up 20%, more rose) ░ │
│ ░    ▒                                       ░ │
│ ░               K N O W N                    ░ │
│ ░                                            ░ │
│ ░     ╭───────────────────────────╮          ░ │
│ ░     │   i know you now.         │          ░ │  ← font-black lower
│ ░     ╰───────────────────────────╯          ░ │     clamp(2.5rem, 7vw, 4rem)
│ ░                                            ░ │
│ ░  Simon, 27, finance.                       ░ │  ← agent love-letter
│ ░  zürich. food, low-key.                    ░ │     Geist Sans heavier
│ ░  you go to a 4.                            ░ │     tracking-tight
│ ░  you picked the version of yourself        ░ │     leading-relaxed
│ ░  that watches who's lying.                 ░ │     italic accent on
│ ░  you want me by text.                      ░ │     proper nouns
│ ░                                            ░ │
│ ░  i won't ask any of this twice.            ░ │
│ ░                                            ░ │
│ ░  ┌──────────────────────────────────┐      ░ │
│ ░  │   mood-portrait (intimate.png)   │      ░ │  ← right-side asset
│ ░  │     ╭───╮                        │      ░ │     mask-fade-left
│ ░  │     │ ◉ │                        │      ░ │     opacity 100%
│ ░  │     ╰───╯                        │      ░ │
│ ░  └──────────────────────────────────┘      ░ │
│ ░                                            ░ │
│ ░               ╭─ writing... ─╮             ░ │  ← polling badge
│ ░               │  ●⃝          │             ░ │     /pipeline-ready
│ ░               ╰──────────────╯             ░ │
│ ░          ↓ then transitions to             ░ │
│ ░               ╭─── ready. ───╮             ░ │
│ ░               │       ✓      │             ░ │
│ ░               ╰──────────────╯             ░ │
│ ░                                            ░ │
│ ░    ╭──────────────────────────╮            ░ │
│ ░    │  Begin.              →   │            ░ │  ← disabled until ready
│ ░    ╰──────────────────────────╯            ░ │
│ ░                                            ░ │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└──────────────────────────────────────────────────┘
```

### Desktop (1440 × 900)

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
│                                                                                       ●⃝ writing your first scene...   │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░    ▒▒▒                                                                                                            ░  │
│ ░       ▒▒                                          ✦                                                               ░  │
│ ░                                                                                                                   ░  │
│ ░    ┌─────────────────────────────────────────────────────────────────────┐    ┌──────────────────────────────┐   ░  │
│ ░    │                                                                     │    │                              │   ░  │
│ ░    │   K N O W N                                                         │    │                              │   ░  │
│ ░    │                                                                     │    │   ╔══════════════════════╗   │   ░  │
│ ░    │   ╭────────────────────────────────────────╮                        │    │   ║ mood-portrait        ║   │   ░  │
│ ░    │   │  i know you now.                       │                        │    │   ║ (intimate.png)       ║   │   ░  │
│ ░    │   ╰────────────────────────────────────────╯                        │    │   ║                      ║   │   ░  │
│ ░    │                                                                     │    │   ║       ╭───╮          ║   │   ░  │
│ ░    │   Simon, 27, finance.                                               │    │   ║       │ ◉ │          ║   │   ░  │
│ ░    │   zürich. food, low-key. you go to a 4.                             │    │   ║       ╰───╯          ║   │   ░  │
│ ░    │   you picked the version of yourself                                │    │   ║                      ║   │   ░  │
│ ░    │   that watches who's lying.                                         │    │   ║  mask-fade-left      ║   │   ░  │
│ ░    │   you want me by text.                                              │    │   ║  100% opacity        ║   │   ░  │
│ ░    │                                                                     │    │   ║                      ║   │   ░  │
│ ░    │   i won't ask any of this twice.                                    │    │   ╚══════════════════════╝   │   ░  │
│ ░    │                                                                     │    │                              │   ░  │
│ ░    │                                                                     │    │   ╭─ writing... ─╮            │   ░  │
│ ░    │                                                                     │    │   │       ●⃝     │            │   ░  │
│ ░    │                                                                     │    │   ╰──────────────╯            │   ░  │
│ ░    │                                                                     │    │       ↓                       │   ░  │
│ ░    │                                                                     │    │   ╭─── ready. ───╮            │   ░  │
│ ░    │   ╭───────────────────────────────╮                                 │    │   │       ✓      │            │   ░  │
│ ░    │   │  Begin.                    →  │                                 │    │   ╰──────────────╯            │   ░  │
│ ░    │   ╰───────────────────────────────╯                                 │    │                              │   ░  │
│ ░    │     (disabled until /pipeline-ready returns ok)                     │    │                              │   ░  │
│ ░    │                                                                     │    │                              │   ░  │
│ ░    └─────────────────────────────────────────────────────────────────────┘    └──────────────────────────────┘   ░  │
│ ░    ▒                          ✧                                                                 ▒                ░  │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Components used

- **shadcn/ui**: `Badge` (writing/ready states), `Form`
- **landing-inherited**: `GlowButton` (text="Begin."), `glass-card`, `AuroraOrbs` (intensity dialed up), `FallingPattern`
- **custom new**: `LoveLetterBlock` (agent-generated summary, slow typewriter at 80ms stagger, italic accents on proper nouns), `PipelineReadyBadge` (polls `/pipeline-ready` every 2s, transitions writing→ready)
- **third-party**: none

### Motion + interaction notes

- Page enter: opacity 0→1 + y 24→0 + blur(12px)→0 over 600ms (slower than other pages — this is the resolution beat)
- Stagger: eyebrow 0ms / "i know you now." 200ms / love-letter typewriter starts 600ms (80ms per char, 4-6s total reveal) / mood-portrait fades-in 800ms / pipeline-badge 1200ms
- `/pipeline-ready` polled every 2s; on `ready=true` → badge transitions writing→ready (fade-cross), CTA enables
- Tap `Begin.` → 400ms fade-out + push to `/dashboard`
- NO confetti, NO toast — restraint matches landing aesthetic

---

## Screen R — Resume mid-wizard (hydration variant; not numbered in primary sequence)

### Mobile (390 × 844)

```
┌──────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┄ 55% │  ← restored progress
│ ← back              ●⃝ remembering you...       │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░                                            ░ │
│ ░  ╭──────────────────────────────────────╮  ░ │
│ ░  │  prior answers (small chips):        │  ░ │  ← top-left context
│ ░  │  zürich · food, low-key · 3 · Simon  │  ░ │     glass-card row
│ ░  ╰──────────────────────────────────────╯  ░ │     non-editable
│ ░                                            ░ │     (chip click → jump
│ ░                A G E                       ░ │      back is OPEN §10)
│ ░                                            ░ │
│ ░    ╭───────────────────────────────╮       ░ │
│ ░    │  picking up where we left off.│       ░ │  ← agent acknowledgment
│ ░    │  how old?                     │       ░ │
│ ░    ╰───────────────────────────────╯       ░ │
│ ░                                            ░ │
│ ░  ┊Your age sets Nikita's. She'll land in    ░ │
│ ░  ┊your decade, with references and pace     ░ │
│ ░  ┊that match yours.                         ░ │
│ ░                                            ░ │
│ ░  ┊18+ only, legal gate. Stored privately,   ░ │
│ ░  ┊never shown to anyone else.               ░ │
│ ░                                            ░ │
│ ░          ╭───────────────────────╮         ░ │
│ ░          │   ╭───╮  ╭──╮  ╭───╮  │         ░ │
│ ░          │   │ − │  │ -│  │ + │  │         ░ │  ← empty stepper
│ ░          │   ╰───╯  ╰──╯  ╰───╯  │         ░ │     awaits input
│ ░          ╰───────────────────────╯         ░ │
│ ░                                            ░ │
│ ░    ╭──────────────────────────╮            ░ │
│ ░    │  Continue            →   │            ░ │
│ ░    ╰──────────────────────────╯            ░ │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└──────────────────────────────────────────────────┘
```

### Desktop (1440 × 900)

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┄ 55% │
│ ← back                                                                              ●⃝ remembering you...              │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
│ ░                                                                                                                   ░  │
│ ░    ╭──────────────────────────────────────────────────────────────────────────────────────╮                       ░  │
│ ░    │  prior answers:  ╭zürich╮  ╭food, low-key╮  ╭3╮  ╭Simon╮                              │  ← context chips      ░  │
│ ░    ╰──────────────────────────────────────────────────────────────────────────────────────╯                       ░  │
│ ░                                                                                                                   ░  │
│ ░    A G E                                                                                                          ░  │
│ ░                                                                                                                   ░  │
│ ░    ╭──────────────────────────────────────────────────╮                                                           ░  │
│ ░    │  picking up where we left off.  how old?         │                                                           ░  │
│ ░    ╰──────────────────────────────────────────────────╯                                                           ░  │
│ ░                                                                                                                   ░  │
│ ░    ┊Your age sets Nikita's. She'll land in your decade, with references and pace that match yours.                ░  │
│ ░                                                                                                                   ░  │
│ ░    ┊18+ only, legal gate. Stored privately, never shown to anyone else.                                            ░  │
│ ░                                                                                                                   ░  │
│ ░              ╭────────────────────────────────╮                                                                   ░  │
│ ░              │   ╭───╮     ╭────╮    ╭───╮    │                                                                   ░  │
│ ░              │   │ − │     │  - │    │ + │    │                                                                   ░  │
│ ░              │   ╰───╯     ╰────╯    ╰───╯    │                                                                   ░  │
│ ░              ╰────────────────────────────────╯                                                                   ░  │
│ ░                                                                                                                   ░  │
│ ░    ╭───────────────────────────────╮                                                                              ░  │
│ ░    │  Continue                  →  │                                                                              ░  │
│ ░    ╰───────────────────────────────╯                                                                              ░  │
│ ░                                                                                                                   ░  │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Components used

- Same as the underlying screen (Age in this example), plus:
- **custom new**: `PriorAnswersStrip` (read-only chip row at top, glass-card; backed by `state_reconstruction.build_state_from_conversation`)

### Motion + interaction notes

- Page enter: same as other screens but with prior-answers chips animating in first (stagger 0/50/100/150ms each chip)
- Headline includes agent acknowledgment ("picking up where we left off.") prepended via dynamic instructions
- Backend: hydrates wizard state via `state_reconstruction.build_state_from_conversation`; restores at last unanswered slot; F.3 PASS in W3 walk

---

## Summary table

| # | Screen | Primary control | Personalization hint | Components new |
|---|--------|-----------------|----------------------|----------------|
| 0 | Welcome | GlowButton "Begin." | Typewriter italic line | ProgressRail, PersonalizingBadge |
| 1 | Location | Aceternity placeholders-and-vanish-input + 3 chips | Live "<value>. okay." morph (text-shimmer) | WizardShell, QuestionCard, WhyWeAsk, NikitaReaction, PersonalizationPreviewChip |
| 2 | Scene | RadioGroup chips (5+1) + optional vibe row | Cumulative-state mirror chip morphs in real time | ChipGroup, layout-animated PreviewChip |
| 3 | Darkness | Slider 0-10 with gradient track | 3-band live italic interp ("soft" / "interesting." / "yeah, i thought so.") | DarknessSlider, RangeInterpreter |
| 4 | Name | Input (auto-focus, validated) | "Simon. say it back to me when you're nervous." (typewriter, anti-mirror server-validated) | NikitaReaction (with anti-mirror output_validator) |
| 5 | Age | Number stepper (±) | Range badge ("mid-twenties" / "forties+") | AgeStepper, AgeRangeBadge |
| 6 | Occupation | Aceternity placeholders + 6 chips | City × occupation cross-ref reaction ("of course." / "unexpected.") | OccupationChips, NikitaReaction |
| 7 | Backstory | 3 RadioGroup cards (full prose) | Above-cards hint synthesizing prior 6 slots | BackstoryCard, VariantTag |
| 8 | Phone | RadioGroup (text/voice/both) + PhoneInputE164 (country prefix) | Per-choice italic reaction ("text it is." / "voice — bold." / "both. greedy.") | ReachRadioCards, PhoneInputE164 |
| 9 | Completion | GlowButton "Begin." (gated by /pipeline-ready) | Pipeline-ready badge writing→ready transition | LoveLetterBlock, PipelineReadyBadge |
| 10 | Resume | (whichever slot) | "picking up where we left off." prepended | PriorAnswersStrip |

---

## Open visual decisions for user (mirror of plan §10)

1. **Backstory card eyebrow vocab** (§10 item 2): `FILE A/B/C` violates PR #430 vocab kill. Wireframe shows `NORTH/WEST/SOUTH` as proposed alternative. Other option: `VARIANT 1/2/3`. **Pick one.**
2. **Persona-preview chip on Screen 2** (§10 item 6): wireframe shows `[so far: zürich · ___]` cumulative-state mirror at top of every screen 2-9. Linear hides prior; Resend shows. **Keep, soften (top-corner only on hover), or remove?**
3. **Voice-note input affordance** (§10 item 4): not in any wireframe. **Add to Screen 4 (Name) and/or Screen 7 (Backstory) as optional progressive enhancement, or defer to phase 2?**
4. **Suggestion chips on Screens 1/6** (§10 item 5): wireframes show hardcoded `Zürich/Berlin/Lisbon` and `designer/finance/medic/writer/founder`. **Hardcode (ship-fast), agent-suggested via WebSearchTool (delight, +1 LLM call), or geo-derived from `Accept-Language`?**
5. **`why we ask` text** (§10 item 7): wireframes show static-per-slot copy. **Keep static (cheap, predictable) or agent-generated per turn (delight, +1 LLM call per screen)?**
6. **Right-side asset on Screens 1-3 desktop**: optional dim mood-cycle vs blank space. **Show or hide?**
7. **Resume Screen 10 — prior-answer chip click behavior**: wireframe shows non-editable. **Allow click-to-jump-back-and-edit, or strictly forward?**

---

**End of wireframe document.**
