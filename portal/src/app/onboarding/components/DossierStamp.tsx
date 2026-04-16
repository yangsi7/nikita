"use client"

/**
 * DossierStamp — the canonical rose-primary stamp used across the wizard.
 *
 * Spec 214 FR-2 + Appendix C. Six states:
 *   - `clearance-pending`: "CLEARANCE: PENDING" — muted + animate-pulse
 *   - `cleared`:           "CLEARED" — typewriter reveal (40ms tick)
 *   - `provisional`:       "PROVISIONAL — CLEARED" — static
 *   - `analyzed`:          "ANALYZED" — stamp-rotate animation
 *   - `confirmed`:         "CONFIRMED" — immediate
 *   - `analysis-pending`:  "ANALYSIS: PENDING" — muted
 *
 * All animated states respect `prefers-reduced-motion` via the shared
 * `useReducedMotionCompat` hook (which falls back to matchMedia when
 * framer-motion's `useReducedMotion` export is not available — e.g. the
 * global vitest mock).
 */

import { useEffect, useState } from "react"
import * as FramerMotion from "framer-motion"

import { cn } from "@/lib/utils"
import { useReducedMotionCompat } from "@/app/onboarding/hooks/use-reduced-motion-compat"

const { motion } = FramerMotion

export type DossierStampState =
  | "clearance-pending"
  | "cleared"
  | "provisional"
  | "analyzed"
  | "confirmed"
  | "analysis-pending"

export interface DossierStampProps {
  state: DossierStampState
  className?: string
}

/**
 * Character-reveal tick in milliseconds. Mirrors the stagger timing in
 * `portal/src/components/landing/system-terminal.tsx` (50ms per system
 * line) — rounded down to 40ms for character-level cadence.
 *
 * Current: 40ms
 * Prior: — (initial Spec 214 value)
 * Rationale: system-terminal reveals one line at 50ms; per-character
 *   reveal for a 7-char "CLEARED" stamp fills in ~280ms, which sits
 *   well within the 200ms step-transition NFR-001 budget plus a short
 *   tail reveal that reads as confident.
 */
const TYPEWRITER_TICK_MS = 40

const STAMP_TEXT: Record<DossierStampState, string> = {
  "clearance-pending": "CLEARANCE: PENDING",
  cleared: "CLEARED",
  provisional: "PROVISIONAL — CLEARED",
  analyzed: "ANALYZED",
  confirmed: "CONFIRMED",
  "analysis-pending": "ANALYSIS: PENDING",
}

const STAMP_CLASS: Record<DossierStampState, string> = {
  "clearance-pending":
    "text-primary/60 font-black tracking-widest uppercase animate-pulse",
  cleared: "text-primary font-black tracking-widest uppercase",
  provisional: "text-primary/80 font-black tracking-widest uppercase",
  analyzed: "text-primary font-black tracking-widest uppercase",
  confirmed: "text-primary font-black tracking-widest uppercase",
  "analysis-pending":
    "text-muted-foreground font-black tracking-widest uppercase",
}

export function DossierStamp({ state, className }: DossierStampProps) {
  const reducedMotion = useReducedMotionCompat()
  const fullText = STAMP_TEXT[state]
  const baseClass = STAMP_CLASS[state]

  // Typewriter reveal for the `cleared` state only. Under reduced motion,
  // skip the reveal and render the full text immediately.
  const useTypewriter = state === "cleared" && !reducedMotion
  const [revealedCount, setRevealedCount] = useState(useTypewriter ? 0 : fullText.length)

  useEffect(() => {
    if (!useTypewriter) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- reset reveal on state change
      setRevealedCount(fullText.length)
      return
    }
    setRevealedCount(0)
    const interval = setInterval(() => {
      setRevealedCount((c) => {
        const next = c + 1
        if (next >= fullText.length) clearInterval(interval)
        return next
      })
    }, TYPEWRITER_TICK_MS)
    return () => clearInterval(interval)
  }, [useTypewriter, fullText.length])

  const visibleText = fullText.slice(0, revealedCount)
  const fullyRevealed = revealedCount >= fullText.length

  // ANALYZED uses a framer-motion rotate animation unless reduced-motion.
  // `data-animate` serializes the rotation keyframe list into the DOM so
  // Playwright/RTL can verify the animation class is active without
  // depending on how React handles unknown JSX props.
  if (state === "analyzed" && !reducedMotion) {
    return (
      <motion.span
        className={cn(baseClass, className)}
        data-testid="dossier-stamp"
        data-animate="rotate(0,-2,2,0)"
        animate={{ rotate: [0, -2, 2, 0] }}
        transition={{ duration: 0.45, ease: "easeOut" }}
      >
        {fullText}
      </motion.span>
    )
  }

  // Typewriter path: during reveal only the partial string is visible,
  // but RTL needs a complete string to find by exact match. Render the
  // partial text visibly and the full text only when reveal is done.
  return (
    <span className={cn(baseClass, className)} data-testid="dossier-stamp">
      {useTypewriter && !fullyRevealed ? visibleText : fullText}
    </span>
  )
}
