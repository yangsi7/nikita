import { describe, it, expect } from "vitest"
import { profileSchema } from "@/app/onboarding/schemas"

// Spec 212 — Phone field is OPTIONAL, validates E.164 format when non-empty
// Regression constant: any change to this test must reference the driving GH issue

const TEST_PHONE_E164 = "+41791234567"

const validBase = {
  location_city: "Zurich",
  social_scene: "techno" as const,
  drug_tolerance: 3,
}

describe("profileSchema — phone field (Spec 212 PR A)", () => {
  it("accepts a valid E.164 phone number", () => {
    const result = profileSchema.safeParse({ ...validBase, phone: TEST_PHONE_E164 })
    expect(result.success).toBe(true)
    if (result.success) {
      expect(result.data.phone).toBe(TEST_PHONE_E164)
    }
  })

  it("rejects a non-numeric string", () => {
    const result = profileSchema.safeParse({ ...validBase, phone: "abc" })
    expect(result.success).toBe(false)
  })

  it("rejects a bare 10-digit number without + prefix", () => {
    const result = profileSchema.safeParse({ ...validBase, phone: "0791234567" })
    expect(result.success).toBe(false)
  })

  it("accepts empty string (field is optional)", () => {
    const result = profileSchema.safeParse({ ...validBase, phone: "" })
    expect(result.success).toBe(true)
  })

  it("accepts undefined/omitted phone (field is optional)", () => {
    const result = profileSchema.safeParse({ ...validBase })
    expect(result.success).toBe(true)
  })
})
