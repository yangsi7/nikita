"use client"

import { motion, useReducedMotion } from "framer-motion"

/**
 * NikitaReaction — first-person Nikita-voice reaction text (≤140 chars).
 *
 * AC C1.9 + C1.20: typewriter-like fade reveal 200ms after screen settle.
 * Reduced-motion: instant render. Wrapped in `aria-live="polite"
 * aria-atomic="true"` so screen readers receive the change.
 */
export function NikitaReaction({ text }: { text: string }) {
  const reduceMotion = useReducedMotion()
  const transition = reduceMotion
    ? { duration: 0 }
    : { duration: 0.2, delay: 0.15 }

  return (
    <motion.p
      key={text}
      aria-live="polite"
      aria-atomic="true"
      initial={{ opacity: reduceMotion ? 1 : 0 }}
      animate={{ opacity: 1 }}
      transition={transition}
      className="text-base text-foreground/80 italic"
    >
      {text}
    </motion.p>
  )
}
