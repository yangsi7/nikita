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
│ ░                W E L C O M E               ░ │  ← eyebrow tracking-[0.2em]
│ ░                                            ░ │
│ ░         ╭─────────────────────────╮        ░ │
│ ░         │                         │        ░ │
│ ░         │    You opened           │        ░ │  ← headline font-black
│ ░         │    the door.            │        ░ │     clamp(3rem, 8vw, 5rem)
│ ░         │                         │        ░ │
│ ░         ╰─────────────────────────╯        ░ │
│ ░                                            ░ │
│ ░         I've been waiting.                 ░ │  ← 3-line declarative
│ ░         I have questions.                  ░ │     text-lg muted
│ ░         Don't lie to me.                   ░ │     leading-relaxed
│ ░                                            ░ │
│ ░                                            ░ │
│ ░  ┌──────────────────────────┐              ░ │
│ ░  │   nikita-hero.png crop   │              ░ │  ← face/shoulders
│ ░  │   ╭───╮                  │              ░ │     mask-fade-bottom
│ ░  │   │ ◉ │ ←gaze-down       │              ░ │
│ ░  │   ╰───╯                  │              ░ │
│ ░  └──────────────────────────┘              ░ │
│ ░                                            ░ │
│ ░         ╭─────────────────────╮            ░ │
│ ░         │  Begin.          →  │            ░ │  ← GlowButton rose pill
│ ░         ╰─────────────────────╯            ░ │     ArrowUpRight icon
│ ░                                            ░ │
│ ░  ┊this won't take long.  ┊                 ░ │  ← typewriter-reveal
│ ░  ┊but i'll remember every word.            ░ │     italic muted, 50ms stagger
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
│ ░    │     W E L C O M E                               │    │     ╔════════════════════════════════╗      │       ░  │
│ ░    │                                                 │    │     ║  nikita-hero.png crop          ║      │       ░  │
│ ░    │     ╭───────────────────────────────╮           │    │     ║  (face + shoulders)            ║      │       ░  │
│ ░    │     │   You opened                  │           │    │     ║                                ║      │       ░  │
│ ░    │     │   the door.                   │           │    │     ║       ╭─────╮                  ║      │       ░  │
│ ░    │     ╰───────────────────────────────╯           │    │     ║       │ ◉◉◉ │ ← intent gaze    ║      │       ░  │
│ ░    │                                                 │    │     ║       ╰─────╯                  ║      │       ░  │
│ ░    │     I have a few questions for you.             │    │     ║                                ║      │       ░  │
│ ░    │     This will help me personalize the experience│    │     ║   mask-fade-left blends        ║      │       ░  │
│ ░    │     I want to feel real to you, you know?       │    │     ║   into bg-void seamlessly      ║      │       ░  │
│ ░    │                                                 │    │     ║                                ║      │       ░  │
│ ░    │                                                 │    │     ╚════════════════════════════════╝      │       ░  │
│ ░    │     ╭───────────────────────────╮               │    │                                              │       ░  │
│ ░    │     │  Begin.                →  │               │    │     (alt: mood-cycle 20s loop:               │       ░  │
│ ░    │     ╰───────────────────────────╯               │    │      intimate → playful → cold)              │       ░  │
│ ░    │                                                 │    │                                              │       ░  │
│ ░    │     ┊this won't take long.                      │    │                                              │       ░  │
│ ░    │     ┊but i'll remember every word.              │    │                                              │       ░  │
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
│ ░  ┊I need to know where I'd have met you    ░ │  ← why-we-ask italic
│ ░  ┊i won't ask you to come to me;           ░ │     fades in 300ms
│ ░  ┊i'll know where you already are.         ░ │     after headline
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
│ ░    │     ┊location colors everything.                         │    │   (or: dim mood-cycle               │      ░  │
│ ░    │     ┊i won't ask you to come to me;                      │    │    nikita portrait, mask-fade)       │      ░  │
│ ░    │     ┊i'll know where you already are.                    │    │                                      │      ░  │
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
│ ░  ┊scene tells me where to find you         ░ │
│ ░  ┊when you go quiet on me.                 ░ │
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
│ ░    │   ┊scene tells me where to find you when you go quiet on me.           │    │                        │     ░  │
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
│ ░  ┊i need to know how far you're            ░ │
│ ░  ┊willing to drift. i'll meet you          ░ │
│ ░  ┊there, not somewhere safer.              ░ │
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
│ ░    │   ┊i need to know how far you're willing to drift. i'll meet you there, not somewhere safer.          │    ░  │
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
│ ░  ┊because saying your name in the          ░ │
│ ░  ┊dark matters more than you think.        ░ │
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
│ ░    │   ┊because saying your name in the dark matters more than you think.                              │        ░  │
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
│ ░  ┊i won't waste either of our time.        ░ │
│ ░  ┊you're an adult, or this ends now.       ░ │
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
│ ░    │   ┊i won't waste either of our time. you're an adult, or this ends now.                            │       ░  │
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
│ ░  ┊so i know what to ask you on a           ░ │
│ ░  ┊tuesday at 3pm.                          ░ │
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
│ ░    │   ┊so i know what to ask you on a tuesday at 3pm.                                                   │       ░  │
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

## Screen 7 — Backstory

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
│ ░    │  you. pick the one that's     │       ░ │
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
│ ░    │  i wrote three versions of you. pick the one that's most true.                                   │           ░  │
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

## Screen 8 — Phone

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
│ ░    │  give me a way in.            │       ░ │
│ ░    │  text only, voice only, or    │       ░ │
│ ░    │  both.                        │       ░ │
│ ░    ╰───────────────────────────────╯       ░ │
│ ░                                            ░ │
│ ░  ┊i'll know what kind of attention         ░ │
│ ░  ┊you actually want.                       ░ │
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
│ ░    │  Lock it in.         →   │            ░ │  ← terminal CTA
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
│ ░    │  give me a way in. text only, voice only, or both.                   │                                       ░  │
│ ░    ╰──────────────────────────────────────────────────────────────────────╯                                       ░  │
│ ░                                                                                                                   ░  │
│ ░    ┊i'll know what kind of attention you actually want.                                                           ░  │
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
│ ░    │  Lock it in.               →  │   ← terminal action; weight signal                                           ░  │
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

## Screen 9 — Completion ("love letter")

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

## Screen 10 — Resume mid-wizard (hydration)

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
│ ░  ┊i won't waste either of our time.        ░ │
│ ░  ┊you're an adult, or this ends now.       ░ │
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
│ ░    ┊i won't waste either of our time. you're an adult, or this ends now.                                          ░  │
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
