/**
 * Wizard state machine — transition map + guard.
 *
 * Spec 214 FR-1 (11-step flow) + FR-8 (backstory before phone) + AC-8.1
 * (step-order enforcement).
 *
 * Callers check `canTransition(from, to)` before moving. Forward transitions
 * must be one step at a time (step_n → step_{n+1}). Backward transitions are
 * allowed ONLY from step 8 (BACKSTORY_REVEAL) back to steps 4-7 — this
 * supports the dossier-reveal inline-edit UX (user clicks a metric in the
 * dossier header to revisit a prior input). Once past step 9 the wizard is
 * committed forward.
 */

import type { WizardStep } from "@/app/onboarding/types/wizard"

/** Canonical forward order (3..11). */
export const WIZARD_STEPS: readonly WizardStep[] = [3, 4, 5, 6, 7, 8, 9, 10, 11] as const

/** First step the wizard renders post-auth. */
export const FIRST_WIZARD_STEP: WizardStep = 3

/** Backwards-edit origin per AC-8.1 — only the dossier reveal surfaces inline edits. */
const BACKWARD_EDIT_FROM: WizardStep = 8

/** Backwards-edit destinations (the four collected-profile steps 4..7). */
const BACKWARD_EDIT_TO: readonly WizardStep[] = [4, 5, 6, 7] as const

export type TransitionResult =
  | { ok: true }
  | { ok: false; reason: "INVALID_ORDER" }

/**
 * Returns `{ ok: true }` if (from → to) is a valid wizard transition, or
 * `{ ok: false, reason: "INVALID_ORDER" }` otherwise.
 *
 * Spec 214 AC-8.1 mandates this returns an error-state rather than throwing
 * so callers can render an inline Nikita-voiced error instead of crashing.
 */
export function canTransition(from: WizardStep, to: WizardStep): TransitionResult {
  // Forward single-step advance: to must be from+1
  const expectedForward = (from + 1) as WizardStep
  if (to === expectedForward && WIZARD_STEPS.includes(to)) {
    return { ok: true }
  }

  // Backward edit from step 8 to any of 4..7 (AC-8.1 inline-edit UX)
  if (from === BACKWARD_EDIT_FROM && BACKWARD_EDIT_TO.includes(to)) {
    return { ok: true }
  }

  return { ok: false, reason: "INVALID_ORDER" }
}

/**
 * Returns the canonical next step for `current`, or `null` if `current` is
 * the terminal step (11).
 */
export function nextStep(current: WizardStep): WizardStep | null {
  if (current === 11) return null
  return (current + 1) as WizardStep
}
