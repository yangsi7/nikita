"use client"

import { motion, useReducedMotion } from "framer-motion"

/**
 * ProgressRail — top-of-screen monotonic progress bar (AC C1.8 + C1.17).
 *
 * Reflects BE `progress_pct` directly; the FE never computes progress
 * itself (per agentic-design-patterns rule §4 — BE is the single source
 * of truth). Width never decreases — width animates from prev % to new
 * % via spring (stiffness 120, damping 20). Reduced-motion swaps the
 * spring for `linear 0.2s`; width still updates monotonically.
 */
export function ProgressRail({ progressPct }: { progressPct: number }) {
  const reduceMotion = useReducedMotion()
  // Clamp into [0, 100] defensively; BE is contractually monotonic but
  // a stale cached response could in theory drift. We never animate
  // backwards regardless.
  const clamped = Math.max(0, Math.min(100, Math.round(progressPct)))

  const transition = reduceMotion
    ? { duration: 0.2, ease: "linear" as const }
    : { type: "spring" as const, stiffness: 120, damping: 20 }

  return (
    <div className="fixed top-0 left-0 right-0 z-50 h-1 bg-white/5">
      <motion.div
        role="progressbar"
        aria-valuenow={clamped}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="onboarding progress"
        className="h-full bg-primary"
        initial={{ width: 0 }}
        animate={{ width: `${clamped}%` }}
        transition={transition}
      />
    </div>
  )
}
