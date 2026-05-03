"use client"

import { motion, useReducedMotion } from "framer-motion"

/**
 * SuggestionChips — 3-chip glass-card row (e.g. Zürich · Berlin · Lisbon).
 *
 * AC C1.6 sibling for autocomplete-aided slots. Hover rose-30%; click →
 * fills input + submits via the supplied `onPick` callback.
 */
export function SuggestionChips({
  chips,
  onPick,
  ariaLabel,
}: {
  chips: readonly { value: string; label: string }[]
  onPick: (value: string) => void
  ariaLabel: string
}) {
  const reduceMotion = useReducedMotion()
  if (chips.length === 0) return null
  return (
    <div role="group" aria-label={ariaLabel} className="flex gap-2 flex-wrap">
      {chips.map((chip, i) => (
        <motion.button
          type="button"
          key={chip.value}
          onClick={() => onPick(chip.value)}
          initial={reduceMotion ? false : { opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={
            reduceMotion
              ? undefined
              : { duration: 0.18, delay: i * 0.05, ease: [0.16, 1, 0.3, 1] }
          }
          className="px-3 py-1.5 rounded-full text-sm bg-white/5 border border-white/10 hover:bg-primary/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring min-h-[44px] min-w-[44px]"
        >
          {chip.label}
        </motion.button>
      ))}
    </div>
  )
}
