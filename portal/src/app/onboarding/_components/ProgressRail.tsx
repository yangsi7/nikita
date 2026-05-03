"use client"

import { useState } from "react"
import { motion, useReducedMotion } from "framer-motion"

/**
 * ProgressRail — top-of-screen monotonic progress bar (AC C1.8 + C1.17).
 *
 * Reflects BE `progress_pct` directly; the FE never computes progress
 * itself (per agentic-design-patterns rule §4 — BE is the single source
 * of truth). Width is monotonic-by-construction in the FE: we keep a
 * `prevMax` state and render `max(prevMax, clamped)` so a stale or
 * out-of-order BE response can never animate the rail backwards. Width
 * animates via spring (stiffness 120, damping 20). Reduced-motion swaps
 * the spring for `linear 0.2s`; width still updates monotonically.
 */
export function ProgressRail({ progressPct }: { progressPct: number }) {
  const reduceMotion = useReducedMotion()
  // Clamp into [0, 100] defensively; BE is contractually monotonic but
  // a stale cached response could drift, so the FE enforces independently.
  const clamped = Math.max(0, Math.min(100, Math.round(progressPct)))
  // Monotonic high-water-mark via useState. Calling setState inside the
  // render path is the standard React pattern for derived-state updates
  // when the input changes (https://react.dev/reference/react/useState
  // #storing-information-from-previous-renders); React drops the
  // re-render when prevMax already covers the new value.
  const [prevMax, setPrevMax] = useState(0)
  const monotonic = Math.max(prevMax, clamped)
  if (monotonic > prevMax) {
    setPrevMax(monotonic)
  }

  const transition = reduceMotion
    ? { duration: 0.2, ease: "linear" as const }
    : { type: "spring" as const, stiffness: 120, damping: 20 }

  return (
    <div className="fixed top-0 left-0 right-0 z-50 h-1 bg-white/5">
      <motion.div
        role="progressbar"
        aria-valuenow={monotonic}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="onboarding progress"
        data-progress-monotonic={monotonic}
        className="h-full bg-primary"
        initial={{ width: 0 }}
        animate={{ width: `${monotonic}%` }}
        transition={transition}
      />
    </div>
  )
}
