"use client"

import { useEffect, useMemo, useRef, type KeyboardEvent } from "react"
import { motion, useReducedMotion } from "framer-motion"
import {
  ARCHETYPE_LABELS,
  type ArchetypeCard,
} from "@/app/onboarding/types/answer"

/**
 * BackstoryArchetypeCards — 3 LLM-archetype cards (AC C1.7 + C1.12).
 *
 * - Validates each card's `label` is in the locked 12-archetype list at
 *   render time. Invalid labels are filtered with a `console.warn` (the
 *   backend Pydantic enforces too — this is defense-in-depth). The
 *   filter is wrapped in `useMemo` so the warn fires only when the cards
 *   prop changes, not on every render (N5).
 * - `role="radiogroup"` + cards as `<button role="radio" aria-checked>`.
 * - **Arrow-key roving tabindex** (B2 / WAI-ARIA radiogroup pattern):
 *   only one card has `tabIndex=0` at a time (the selected card, or the
 *   first card on initial render). ArrowRight/ArrowDown moves focus +
 *   selection forward; ArrowLeft/ArrowUp moves backward. Home/End jump
 *   to first/last. Wrapping is enabled.
 * - Hover: `y: -4` + glow opacity 0 → 0.4 (250ms EASE_OUT_QUART).
 * - Select: pulse + ring + tail blur on others.
 * - Reduced-motion disables hover/select effects (informational ring stays).
 *
 * Native implementation (no Radix dep, ~30 LOC) chosen over `@radix-ui/
 * react-radio-group` to avoid adding a runtime dependency for a 3-card
 * widget. Behavior matches the WAI-ARIA "Radio Group" authoring pattern:
 * https://www.w3.org/WAI/ARIA/apg/patterns/radio/.
 */

const VALID_LABELS = new Set<string>(ARCHETYPE_LABELS)

export interface BackstoryArchetypeCardsProps {
  cards: readonly ArchetypeCard[]
  selectedLabel: string | null
  onSelect: (label: string) => void
}

export function BackstoryArchetypeCards({
  cards,
  selectedLabel,
  onSelect,
}: BackstoryArchetypeCardsProps) {
  const reduceMotion = useReducedMotion()

  // Memoize the filter so console.warn fires once per cards-prop change,
  // not on every parent re-render (N5).
  const validCards = useMemo(() => {
    return cards.filter((c) => {
      if (!VALID_LABELS.has(c.label)) {
        console.warn(
          `[BackstoryArchetypeCards] dropping invalid archetype label: "${c.label}"`
        )
        return false
      }
      return true
    })
  }, [cards])

  // Roving tabindex: track the focusable index. Initially the selected
  // card if any, else card 0. Arrow keys mutate this and call onSelect.
  const initialFocusIndex = useMemo(() => {
    const i = validCards.findIndex((c) => c.label === selectedLabel)
    return i >= 0 ? i : 0
  }, [validCards, selectedLabel])

  const buttonRefs = useRef<Array<HTMLButtonElement | null>>([])
  // Track whether focus is currently inside the radiogroup so we don't
  // steal focus on parent re-renders.
  const focusInsideRef = useRef(false)

  // When `selectedLabel` changes via click OR keyboard, focus follows.
  useEffect(() => {
    if (!focusInsideRef.current) return
    const idx = validCards.findIndex((c) => c.label === selectedLabel)
    const target = buttonRefs.current[idx >= 0 ? idx : 0]
    target?.focus()
  }, [selectedLabel, validCards])

  const handleKey = (e: KeyboardEvent<HTMLButtonElement>, currentIdx: number) => {
    const last = validCards.length - 1
    let nextIdx: number | null = null
    switch (e.key) {
      case "ArrowRight":
      case "ArrowDown":
        nextIdx = currentIdx >= last ? 0 : currentIdx + 1
        break
      case "ArrowLeft":
      case "ArrowUp":
        nextIdx = currentIdx <= 0 ? last : currentIdx - 1
        break
      case "Home":
        nextIdx = 0
        break
      case "End":
        nextIdx = last
        break
      default:
        return
    }
    e.preventDefault()
    const next = validCards[nextIdx]
    if (next) onSelect(next.label)
  }

  return (
    <div
      role="radiogroup"
      aria-label="pick a backstory"
      className="grid gap-4 sm:grid-cols-3"
      onFocus={() => {
        focusInsideRef.current = true
      }}
      onBlur={(e) => {
        // currentTarget loses focus → check if focus left the group.
        if (!e.currentTarget.contains(e.relatedTarget as Node | null)) {
          focusInsideRef.current = false
        }
      }}
    >
      {validCards.map((card, i) => {
        const selected = selectedLabel === card.label
        const dimmed = selectedLabel !== null && !selected
        // Roving tabindex: 0 for the active item, -1 for the rest.
        const tabIndex =
          selectedLabel === null ? (i === initialFocusIndex ? 0 : -1)
            : (selected ? 0 : -1)
        return (
          <motion.button
            type="button"
            key={card.label}
            ref={(el: HTMLButtonElement | null) => {
              buttonRefs.current[i] = el
            }}
            role="radio"
            aria-checked={selected}
            tabIndex={tabIndex}
            onClick={() => onSelect(card.label)}
            onKeyDown={(e) => handleKey(e, i)}
            initial={reduceMotion ? false : { opacity: 0, y: 12 }}
            animate={{
              opacity: dimmed ? 0.5 : 1,
              y: 0,
              filter: dimmed && !reduceMotion ? "blur(2px)" : "blur(0px)",
            }}
            transition={
              reduceMotion
                ? undefined
                : {
                    duration: 0.5,
                    ease: [0.16, 1, 0.3, 1] as const,
                    delay: 0.1 * i,
                  }
            }
            whileHover={reduceMotion ? undefined : { y: -4 }}
            whileTap={reduceMotion ? undefined : { scale: 0.98 }}
            className={`group relative text-left p-4 rounded-xl border min-h-[160px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-colors ${
              selected
                ? "bg-primary/10 border-primary"
                : "bg-white/5 border-white/10 hover:bg-primary/5"
            }`}
          >
            <div className="text-xs uppercase tracking-wider text-primary mb-2">
              {card.label}
            </div>
            <p className="text-sm text-foreground/80 leading-snug">
              {card.prose}
            </p>
            {selected && (
              <span
                aria-hidden="true"
                className="pointer-events-none absolute inset-0 rounded-xl ring-2 ring-primary/60"
              />
            )}
          </motion.button>
        )
      })}
    </div>
  )
}
