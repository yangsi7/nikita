# Spec 216 — Motion Specification

**Status**: AUTHORING (2026-04-29). Inherits from Spec 208 landing design system.

## 1. Easing Curves

Inherited from `portal/src/lib/easing.ts` (Spec 208). All wizard transitions use one of:

| Token | Value | Use |
|-------|-------|-----|
| `EASE_OUT_QUART` | `cubic-bezier(0.16, 1, 0.3, 1)` | Screen enter, control settle, hover |
| `EASE_IN_OUT_CUBIC` | `cubic-bezier(0.65, 0, 0.35, 1)` | Wizard step transitions (forward/back) |
| `EASE_OUT_EXPO` | `cubic-bezier(0.16, 1, 0.3, 1)` | Backstory archetype card flip |

**No new curves.** Anything outside this list is a violation of NR-08 (design system inheritance).

## 2. Screen Transitions (AnimatePresence pattern)

`portal/src/app/onboarding/_components/WizardShell.tsx` wraps each screen render in `<AnimatePresence mode="wait">`. Per-screen wrapper:

```tsx
<motion.div
  key={slot_kind}
  initial={{ opacity: 0, y: 16, filter: "blur(8px)" }}
  animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
  exit={{ opacity: 0, y: -16, filter: "blur(8px)" }}
  transition={{
    duration: 0.35,
    ease: [0.22, 1, 0.36, 1],  // EASE_OUT_QUART variant per Spec 208
  }}
>
  {/* QuestionCard contents */}
</motion.div>
```

**Why blur**: AGI-feel — gives the agent's "thinking" a physical surface. Aligns with Spec 208 hero section motion.

**Mobile (390×844) timing**: keep 350ms; do NOT shorten. The slower motion reads more deliberate on small viewports.

## 3. Reduced-Motion Compliance (NR-08, AC C1.4)

```tsx
const prefersReducedMotion = useReducedMotion();  // framer-motion hook

const transition = prefersReducedMotion
  ? { duration: 0 }
  : { duration: 0.35, ease: [0.22, 1, 0.36, 1] };
```

When `prefers-reduced-motion: reduce`:
- Screen transitions: instant (duration: 0).
- AuroraOrbs: paused (`animate={false}`).
- Backstory archetype card hover: disabled.
- Progress rail: still animates (it's informational, not decorative).

## 4. Per-Component Motion

### 4.1 NikitaReaction component

Reaction text appears with a 200ms typewriter-like reveal:

```tsx
<motion.p
  initial={{ opacity: 0 }}
  animate={{ opacity: 1 }}
  transition={{ duration: 0.2, delay: 0.15 }}  // 150ms after screen settles
>
  {reaction_text}
</motion.p>
```

### 4.2 ProgressRail component

Width animates from previous % to new % via spring:

```tsx
<motion.div
  className="rail-fill"
  animate={{ width: `${progress_pct}%` }}
  transition={{ type: "spring", stiffness: 120, damping: 20 }}
/>
```

Monotonic-only: never animates backwards. AC B1.12 + C1.8.

### 4.3 HobbyChips component

Chips stagger-reveal on first paint:

```tsx
<motion.div
  initial="hidden"
  animate="visible"
  variants={{
    visible: { transition: { staggerChildren: 0.02 } },
  }}
>
  {chips.map(chip => (
    <motion.button
      key={chip.id}
      variants={{
        hidden: { opacity: 0, scale: 0.95 },
        visible: { opacity: 1, scale: 1 },
      }}
      transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
    >
      {chip.label}
    </motion.button>
  ))}
</motion.div>
```

Selected state: scale 1.0 → 1.04 + ring color shift, 120ms.

### 4.4 BackstoryArchetypeCards component

3 cards enter staggered with longer delay (more theatrical):

```tsx
transition={{
  duration: 0.5,
  ease: [0.16, 1, 0.3, 1],
  delay: 0.1 * card_index,  // 0ms, 100ms, 200ms
}}
```

Hover: card translates `y: -4` + glow opacity `0 → 0.4`, 250ms `EASE_OUT_QUART`.

Select: pulse scale 1.0 → 1.02 → 1.0 over 300ms; ring opacity 0 → 1; 100ms tail blur on non-selected cards.

### 4.5 NikitaThinkingDots (when agent is processing)

Pulsing dots between turns. 1200ms loop, 3 dots, sequential:

```tsx
<motion.span
  animate={{ opacity: [0.3, 1, 0.3] }}
  transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }}
/>
```

Pause on `prefersReducedMotion`.

## 5. AuroraOrbs Background

Reuse `portal/src/components/landing/aurora-orbs.tsx` verbatim. Already provisioned per Spec 208 for `/onboarding`. Do not duplicate.

Orb opacity dimmer on wizard surface (0.4 → 0.25) so QuestionCard glass-card stays readable. Override via prop, not new component.

## 6. Anti-patterns

- ❌ New easing curves outside the 3-token set
- ❌ Bouncy springs (overshoot >5%) — AGI feel is taut, not playful
- ❌ Parallax on mobile (jank risk)
- ❌ Animating `box-shadow` (use opacity overlays instead — perf)
- ❌ Skipping `useReducedMotion` guard
- ❌ Per-screen unique transitions (every screen must use the same enter/exit)

## 7. References

- `portal/src/components/landing/glow-button.tsx` — CTA motion (reuse for "Continue" button)
- `portal/src/components/landing/aurora-orbs.tsx` — background
- `portal/src/lib/easing.ts` — token source
- `~/Nanoleq/sideProjects/nikita/docs-to-process/20260428-spec216-wireframes-ascii.md` — visual layouts per screen
- `~/Nanoleq/sideProjects/nikita/specs/208-marketing-website-redesign/spec.md` — design system parent
