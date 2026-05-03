"use client"

import { motion, useReducedMotion } from "framer-motion"

/**
 * PersonalizingBadge — top-right pulsing-dot badge during agent.run.
 *
 * Per AC C1.14 wireframe gap closure. Visible only when `pending=true`.
 * Reduced-motion disables the pulse but still renders the dot + label.
 */
export function PersonalizingBadge({ pending }: { pending: boolean }) {
  const reduceMotion = useReducedMotion()
  if (!pending) return null
  return (
    <div className="absolute top-4 right-4 flex items-center gap-2 text-xs text-foreground/70">
      <motion.span
        className="inline-block h-2 w-2 rounded-full bg-primary"
        aria-hidden="true"
        animate={
          reduceMotion ? undefined : { opacity: [0.3, 1, 0.3] }
        }
        transition={
          reduceMotion
            ? undefined
            : { duration: 1.2, repeat: Infinity, ease: "easeInOut" }
        }
      />
      <span>personalizing</span>
    </div>
  )
}
