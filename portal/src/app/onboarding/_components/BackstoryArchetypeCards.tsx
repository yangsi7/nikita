"use client"

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
 *   backend Pydantic enforces too — this is defense-in-depth).
 * - `role="radiogroup"` + cards as `<button role="radio" aria-checked>`.
 * - Hover: `y: -4` + glow opacity 0 → 0.4 (250ms EASE_OUT_QUART).
 * - Select: pulse + ring + tail blur on others.
 * - Reduced-motion disables hover/select effects (informational ring stays).
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

  const validCards = cards.filter((c) => {
    if (!VALID_LABELS.has(c.label)) {
      console.warn(
        `[BackstoryArchetypeCards] dropping invalid archetype label: "${c.label}"`
      )
      return false
    }
    return true
  })

  return (
    <div
      role="radiogroup"
      aria-label="pick a backstory"
      className="grid gap-4 sm:grid-cols-3"
    >
      {validCards.map((card, i) => {
        const selected = selectedLabel === card.label
        const dimmed = selectedLabel !== null && !selected
        return (
          <motion.button
            type="button"
            key={card.label}
            role="radio"
            aria-checked={selected}
            onClick={() => onSelect(card.label)}
            initial={
              reduceMotion ? false : { opacity: 0, y: 12 }
            }
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
            whileHover={
              reduceMotion ? undefined : { y: -4 }
            }
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
