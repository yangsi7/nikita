"use client"

import { motion, useReducedMotion } from "framer-motion"

/**
 * NikitaThinkingDots — loading-state ellipsis replacing NikitaReaction
 * during >2s pending (per AC C1.14).
 *
 * 1200ms loop, 3 dots, sequential pulse. Pause on prefers-reduced-motion.
 */
export function NikitaThinkingDots() {
  const reduceMotion = useReducedMotion()
  return (
    <span
      role="status"
      aria-label="Nikita is thinking"
      className="inline-flex gap-1 text-foreground/70"
    >
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="inline-block h-1 w-1 rounded-full bg-foreground/70"
          animate={reduceMotion ? undefined : { opacity: [0.3, 1, 0.3] }}
          transition={
            reduceMotion
              ? undefined
              : {
                  duration: 1.2,
                  repeat: Infinity,
                  delay: i * 0.2,
                  ease: "easeInOut",
                }
          }
        />
      ))}
    </span>
  )
}
