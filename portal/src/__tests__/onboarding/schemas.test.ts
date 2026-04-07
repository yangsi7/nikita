import { describe, it, expect } from "vitest"
import { profileSchema, VALID_SCENES, VALID_LIFE_STAGES } from "@/app/onboarding/schemas"

describe("profileSchema", () => {
  const valid = { location_city: "Berlin", social_scene: "techno" as const, drug_tolerance: 3 }

  it("accepts valid profile and allows optional fields omitted", () => {
    const result = profileSchema.safeParse(valid)
    expect(result.success).toBe(true)
    if (result.success) {
      expect(result.data.life_stage).toBeUndefined()
      expect(result.data.interest).toBeUndefined()
    }
  })

  it("accepts profile with all optional fields", () => {
    const result = profileSchema.safeParse({ ...valid, life_stage: "tech", interest: "AI" })
    expect(result.success).toBe(true)
  })

  it("rejects drug_tolerance outside 1-5", () => {
    expect(profileSchema.safeParse({ ...valid, drug_tolerance: 0 }).success).toBe(false)
    expect(profileSchema.safeParse({ ...valid, drug_tolerance: 6 }).success).toBe(false)
  })

  it("rejects missing required fields", () => {
    expect(profileSchema.safeParse({}).success).toBe(false)
    expect(profileSchema.safeParse({ location_city: "Berlin" }).success).toBe(false)
  })

  it("rejects invalid scene value", () => {
    expect(profileSchema.safeParse({ ...valid, social_scene: "gaming" }).success).toBe(false)
  })

  it("exports expected constants", () => {
    expect(VALID_SCENES).toHaveLength(5)
    expect(VALID_LIFE_STAGES).toHaveLength(6)
  })
})
