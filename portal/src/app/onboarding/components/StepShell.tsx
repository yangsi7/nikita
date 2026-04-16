"use client"

/**
 * StepShell — shared wrapper for all 11 wizard steps.
 *
 * Spec 214 + `docs/content/onboarding-design-brief.md` §4 (Motion language)
 * + §5 (Background atmosphere on EVERY step). Provides:
 *   - `bg-void` full-viewport canvas with FallingPattern + AuroraOrbs.
 *   - EASE_OUT_QUART step-entry animation (framer-motion):
 *       initial={{ opacity: 0, y: 24 }}
 *       animate={{ opacity: 1, y: 0 }}
 *       transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
 *   - `prefers-reduced-motion` short-circuit — when the user opts out of
 *     motion, the step renders in its final state on first paint.
 *   - `data-testid="wizard-step-N"` forwarded so existing E2E selectors
 *     keep matching after the refactor.
 *
 * Usage:
 *   <StepShell testId="wizard-step-4">
 *     <WizardProgress current={2} total={7} />
 *     ...step content...
 *   </StepShell>
 */

import type { ReactNode } from "react"
import * as FramerMotion from "framer-motion"

import { FallingPattern } from "@/components/landing/falling-pattern"
import { AuroraOrbs } from "@/components/landing/aurora-orbs"
import { useReducedMotionCompat } from "@/app/onboarding/hooks/use-reduced-motion-compat"

/**
 * Stable component reference captured at module load.
 *
 * vitest's global framer-motion mock implements `motion` as a Proxy whose
 * `get` trap returns a NEW function reference on every access. Evaluating
 * `motion.section` inside the JSX body would hand React a different
 * element type per render — React would unmount + remount the entire
 * child tree, wiping every step's stateful subtree (controlled inputs,
 * sliders, focused cards, etc.) on each re-render. Capturing the
 * reference once at module scope keeps the element type stable across
 * renders in BOTH the production framer-motion environment and the
 * vitest-mock environment.
 */
const MotionSection = FramerMotion.motion.section

export interface StepShellProps {
  children: ReactNode
  /** Forwarded to the root section so E2E selectors (`wizard-step-N`) match. */
  testId?: string
  /**
   * Optional override for the inner content max-width. Defaults to
   * `max-w-2xl`; BackstoryReveal uses `max-w-3xl`.
   */
  contentMaxWidthClass?: string
  /** Optional alignment override for step content (defaults to "col"). */
  contentClassName?: string
}

/**
 * EASE_OUT_QUART curve — matches `hero-section.tsx` / `system-section.tsx`.
 * Typed as tuple so framer-motion accepts the literal as a cubic-bezier.
 */
const EASE_OUT_QUART = [0.16, 1, 0.3, 1] as const

const STEP_ENTRY_DURATION_S = 0.8
const STEP_ENTRY_Y_OFFSET = 24

export function StepShell({
  children,
  testId,
  contentMaxWidthClass = "max-w-2xl",
  contentClassName,
}: StepShellProps) {
  const prefersReducedMotion = useReducedMotionCompat()

  const motionProps = prefersReducedMotion
    ? { initial: false, animate: { opacity: 1, y: 0 } }
    : {
        initial: { opacity: 0, y: STEP_ENTRY_Y_OFFSET },
        animate: { opacity: 1, y: 0 },
        transition: {
          duration: STEP_ENTRY_DURATION_S,
          ease: EASE_OUT_QUART,
        },
      }

  return (
    <MotionSection
      data-testid={testId}
      className="relative min-h-screen overflow-hidden bg-void"
      {...motionProps}
    >
      <FallingPattern />
      <AuroraOrbs />
      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen container mx-auto px-6 py-20">
        <div
          className={
            "w-full flex flex-col gap-8 " +
            contentMaxWidthClass +
            (contentClassName ? " " + contentClassName : "")
          }
        >
          {children}
        </div>
      </div>
    </MotionSection>
  )
}
