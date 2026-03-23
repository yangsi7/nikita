/**
 * Tests for ScoreDetailChart formatScoreDelta helper (GH #155)
 * Verifies null vs zero delta display distinction.
 */
import { describe, it, expect } from "vitest"
import { formatScoreDelta } from "@/components/dashboard/score-detail-chart"

describe("formatScoreDelta", () => {
  it("returns em dash for null delta", () => {
    expect(formatScoreDelta(null)).toBe("\u2014")
  })

  it("returns em dash for undefined delta", () => {
    expect(formatScoreDelta(undefined)).toBe("\u2014")
  })

  it('returns "0.00" for zero delta', () => {
    expect(formatScoreDelta(0)).toBe("0.00")
  })

  it("returns positive delta with + prefix", () => {
    expect(formatScoreDelta(1.5)).toBe("+1.50")
  })

  it("returns negative delta with - prefix", () => {
    expect(formatScoreDelta(-2.3)).toBe("-2.30")
  })

  it("handles small positive delta", () => {
    expect(formatScoreDelta(0.01)).toBe("+0.01")
  })

  it("handles small negative delta", () => {
    expect(formatScoreDelta(-0.01)).toBe("-0.01")
  })
})
