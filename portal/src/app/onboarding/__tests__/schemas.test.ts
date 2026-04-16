/**
 * Spec 214 PR 214-C — Tuning-constants regression guards for onboarding
 * wizard schemas. Per `.claude/rules/tuning-constants.md`, every named
 * tuning constant must ship with a unit test asserting its exact current
 * value, with a comment pointing to the driving spec/issue. Silent drift
 * is the anti-pattern these guards defend against.
 */

import { describe, it, expect } from "vitest"

import {
  E164_PHONE_REGEX,
  MIN_AGE,
  WIZARD_STEP_MAX,
  WIZARD_STEP_MIN,
  profileSchema,
} from "../schemas"

describe("schemas — tuning constants regression guards (Spec 214 FR-7 + FR-1)", () => {
  it("MIN_AGE = 18 (Spec 214 FR-7 — adult-only onboarding)", () => {
    // Driving spec: Spec 214 FR-7 (identity step). Matches the backend
    // `users.age >= 18` check. Do not relax without a product decision.
    expect(MIN_AGE).toBe(18)
  })

  it("WIZARD_STEP_MIN = 1 (Spec 214 FR-1 — first wizard step)", () => {
    // Driving spec: Spec 214 FR-1 / FR-10.2. Backend
    // `PipelineReadyResponse.wizard_step` is `ge=1, le=11`; bound must match.
    expect(WIZARD_STEP_MIN).toBe(1)
  })

  it("WIZARD_STEP_MAX = 11 (Spec 214 FR-1 — last wizard step)", () => {
    // Driving spec: Spec 214 FR-1 / FR-10.2. Backend `le=11`; bound must match.
    expect(WIZARD_STEP_MAX).toBe(11)
  })
})

describe("schemas — Zod validation smoke (positive + negative)", () => {
  const validBase = {
    location_city: "Zurich",
    social_scene: "techno" as const,
    drug_tolerance: 3,
    phone: "",
  }

  it("accepts a minimal valid profile", () => {
    const result = profileSchema.safeParse(validBase)
    expect(result.success).toBe(true)
  })

  it("rejects age < MIN_AGE", () => {
    const result = profileSchema.safeParse({ ...validBase, age: MIN_AGE - 1 })
    expect(result.success).toBe(false)
  })

  it("accepts age >= MIN_AGE", () => {
    const result = profileSchema.safeParse({ ...validBase, age: MIN_AGE })
    expect(result.success).toBe(true)
  })

  it("rejects wizard_step below WIZARD_STEP_MIN", () => {
    const result = profileSchema.safeParse({
      ...validBase,
      wizard_step: WIZARD_STEP_MIN - 1,
    })
    expect(result.success).toBe(false)
  })

  it("rejects wizard_step above WIZARD_STEP_MAX", () => {
    const result = profileSchema.safeParse({
      ...validBase,
      wizard_step: WIZARD_STEP_MAX + 1,
    })
    expect(result.success).toBe(false)
  })

  it("accepts wizard_step inside [WIZARD_STEP_MIN, WIZARD_STEP_MAX]", () => {
    for (const step of [WIZARD_STEP_MIN, 5, WIZARD_STEP_MAX]) {
      const result = profileSchema.safeParse({ ...validBase, wizard_step: step })
      expect(result.success).toBe(true)
    }
  })

  it("E164_PHONE_REGEX accepts valid E.164 numbers", () => {
    expect(E164_PHONE_REGEX.test("+41791234567")).toBe(true)
    expect(E164_PHONE_REGEX.test("+14155552671")).toBe(true)
  })

  it("E164_PHONE_REGEX rejects malformed numbers", () => {
    expect(E164_PHONE_REGEX.test("0791234567")).toBe(false) // no leading +
    expect(E164_PHONE_REGEX.test("+")).toBe(false) // empty digits
    expect(E164_PHONE_REGEX.test("+0791234567")).toBe(false) // leading 0 after +
  })
})
