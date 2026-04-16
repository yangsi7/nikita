import { describe, it, expect } from "vitest"

import {
  canTransition,
  nextStep,
  WIZARD_STEPS,
} from "@/app/onboarding/state/WizardStateMachine"
import { WizardStep } from "@/app/onboarding/types/wizard"

// Spec 214 PR 214-A — T100 (RED)
// Tests AC-NR1.3 (state guard) + AC-8.1 (BACKSTORY_REVEAL precedes PHONE_ASK)
//
// The transition map is:
//   3 (DOSSIER_HEADER) → 4 (LOCATION) → 5 (SCENE) → 6 (DARKNESS) → 7 (IDENTITY)
//   → 8 (BACKSTORY_REVEAL) → 9 (PHONE_ASK) → 10 (PIPELINE_GATE) → 11 (HANDOFF)
//
// Backwards transitions are allowed for inline edits ONLY from step 8 (the
// dossier reveal lets the user click a metric to revisit prior step) — once
// past step 9 the wizard is committed forward.

describe("WizardStateMachine — canTransition (spec FR-1, AC-8.1)", () => {
  it("accepts the canonical forward sequence 3 → 4 → ... → 11", () => {
    const sequence: WizardStep[] = [3, 4, 5, 6, 7, 8, 9, 10, 11]
    for (let i = 0; i < sequence.length - 1; i += 1) {
      const result = canTransition(sequence[i], sequence[i + 1])
      expect(result.ok, `step ${sequence[i]} → ${sequence[i + 1]}`).toBe(true)
    }
  })

  it("rejects skipping a step (e.g. 7 → 9 must go through 8)", () => {
    const result = canTransition(7, 9)
    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.reason).toBe("INVALID_ORDER")
    }
  })

  it("rejects out-of-order forward jumps (3 → 5)", () => {
    const result = canTransition(3, 5)
    expect(result.ok).toBe(false)
  })

  it("rejects backward transitions from step 9 onward (committed phase)", () => {
    expect(canTransition(9, 8).ok).toBe(false)
    expect(canTransition(10, 9).ok).toBe(false)
    expect(canTransition(11, 10).ok).toBe(false)
  })

  it("allows backwards edit from step 8 to any earlier collected step", () => {
    // AC-8.1 caveat: at the dossier reveal (step 8) user may revisit
    // 4/5/6/7 by clicking the corresponding metric in the dossier header
    expect(canTransition(8, 4).ok).toBe(true)
    expect(canTransition(8, 5).ok).toBe(true)
    expect(canTransition(8, 6).ok).toBe(true)
    expect(canTransition(8, 7).ok).toBe(true)
  })

  it("rejects backward edit from step 8 to itself or to step 3", () => {
    expect(canTransition(8, 8).ok).toBe(false)
    // Step 3 is the auth-landing step, not a collection step
    expect(canTransition(8, 3).ok).toBe(false)
  })
})

describe("WizardStateMachine — nextStep (spec FR-1)", () => {
  it("returns step+1 for the canonical sequence", () => {
    expect(nextStep(3)).toBe(4)
    expect(nextStep(4)).toBe(5)
    expect(nextStep(7)).toBe(8)
    expect(nextStep(8)).toBe(9) // AC-8.1: backstory before phone
    expect(nextStep(9)).toBe(10)
    expect(nextStep(10)).toBe(11)
  })

  it("returns null when called on the terminal step", () => {
    expect(nextStep(11)).toBeNull()
  })
})

describe("WizardStateMachine — WIZARD_STEPS constant", () => {
  it("declares exactly 9 steps (3..11)", () => {
    expect(WIZARD_STEPS).toEqual([3, 4, 5, 6, 7, 8, 9, 10, 11])
  })
})
