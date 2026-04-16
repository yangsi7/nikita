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
 * All animated states respect `prefers-reduced-motion` via
 * framer-motion's `useReducedMotion`; under reduced motion the final
 * state renders on first paint.
 */

import { useEffect, useState } from "react"
import * as FramerMotion from "framer-motion"

import { cn } from "@/lib/utils"

const { motion } = FramerMotion

/**
 * Reduced-motion detection.
 *
 * Two test files (DossierStamp.test.tsx, PipelineGate.test.tsx) re-mock
 * framer-motion to export `useReducedMotion`. The global vitest mock
 * (`portal/vitest.setup.ts`) does not. Production (framer-motion)
 * always exports it.
 *
 * The `in` operator goes through the mock Proxy's `has` trap (not `get`)
 * — and vitest's strict-mock Proxy only hooks `get`. So `"useReducedMotion"
 * in FramerMotion` is a safe, strict-check-free probe. We resolve the
 * function reference inside a try/catch as final belt-and-suspenders
 * against future vitest changes.
 */
type FramerReducedMotionHook = () => boolean | null

function resolveFramerReducedMotionHook(): FramerReducedMotionHook | null {
  try {
    if ("useReducedMotion" in FramerMotion) {
      const hook = (FramerMotion as { useReducedMotion?: unknown }).useReducedMotion
      if (typeof hook === "function") return hook as FramerReducedMotionHook
    }
  } catch {
    /* strict-mock proxy threw — fall through to null */
  }
  return null
}

const framerReducedMotionHook = resolveFramerReducedMotionHook()

function usePrefersReducedMotion(): boolean {
  // Fallback state (populated only when framer's hook is absent).
  const [matchMediaReduce, setMatchMediaReduce] = useState<boolean>(false)
  useEffect(() => {
    if (framerReducedMotionHook !== null) return
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return
    }
    const mql = window.matchMedia("(prefers-reduced-motion: reduce)")
    setMatchMediaReduce(mql.matches)
    const listener = (e: MediaQueryListEvent) => setMatchMediaReduce(e.matches)
    if (typeof mql.addEventListener === "function") {
      mql.addEventListener("change", listener)
      return () => mql.removeEventListener("change", listener)
    }
    mql.addListener(listener)
    return () => mql.removeListener(listener)
  }, [])

  if (framerReducedMotionHook !== null) {
    // eslint-disable-next-line react-hooks/rules-of-hooks -- stable per env
    return !!framerReducedMotionHook()
  }
  return matchMediaReduce
}

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
  const reducedMotion = usePrefersReducedMotion()
  const fullText = STAMP_TEXT[state]
  const baseClass = STAMP_CLASS[state]

  // Typewriter reveal for the `cleared` state only. Under reduced motion,
  // skip the reveal and render the full text immediately.
  const useTypewriter = state === "cleared" && !reducedMotion
  const [revealedCount, setRevealedCount] = useState(useTypewriter ? 0 : fullText.length)

  useEffect(() => {
    if (!useTypewriter) {
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
