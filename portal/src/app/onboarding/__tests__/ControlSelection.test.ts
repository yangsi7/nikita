/**
 * Spec 214 T3.2 — ControlSelection discriminated union + zod validator.
 *
 * ACs:
 *   - AC-T3.2.1: invalid kind rejected by zod schema
 *   - AC-T3.2.2: text kind normalizes to raw string before POST
 */

import { describe, it, expect } from "vitest"

import {
  controlSelectionSchema,
  normalizeUserInput,
} from "../types/ControlSelection"
import type { ControlSelection } from "../types/ControlSelection"

describe("controlSelectionSchema — AC-T3.2.1", () => {
  it("accepts text/chips/slider/toggle/cards kinds", () => {
    expect(controlSelectionSchema.safeParse({ kind: "text", value: "hi" }).success).toBe(true)
    expect(controlSelectionSchema.safeParse({ kind: "chips", value: "techno" }).success).toBe(true)
    expect(controlSelectionSchema.safeParse({ kind: "slider", value: 3 }).success).toBe(true)
    expect(controlSelectionSchema.safeParse({ kind: "toggle", value: "voice" }).success).toBe(true)
    expect(controlSelectionSchema.safeParse({ kind: "cards", value: "a1b2c3d4e5f6" }).success).toBe(true)
  })

  it("rejects invalid kind", () => {
    const result = controlSelectionSchema.safeParse({ kind: "bogus", value: "x" })
    expect(result.success).toBe(false)
  })

  it("slider out-of-range rejected", () => {
    expect(controlSelectionSchema.safeParse({ kind: "slider", value: 0 }).success).toBe(false)
    expect(controlSelectionSchema.safeParse({ kind: "slider", value: 6 }).success).toBe(false)
  })

  it("cards value must be 12-hex", () => {
    expect(controlSelectionSchema.safeParse({ kind: "cards", value: "NOT_HEX" }).success).toBe(false)
  })

  it("toggle value must be voice or text", () => {
    expect(controlSelectionSchema.safeParse({ kind: "toggle", value: "other" }).success).toBe(false)
  })
})

describe("normalizeUserInput — AC-T3.2.2", () => {
  it("raw string passes through", () => {
    expect(normalizeUserInput("zurich")).toBe("zurich")
  })

  it("text kind normalizes to raw string", () => {
    const payload: ControlSelection = { kind: "text", value: "berlin" }
    expect(normalizeUserInput(payload)).toBe("berlin")
  })

  it("chip payload passes through intact", () => {
    const payload: ControlSelection = { kind: "chips", value: "techno" }
    expect(normalizeUserInput(payload)).toEqual(payload)
  })

  it("slider payload passes through intact", () => {
    const payload: ControlSelection = { kind: "slider", value: 3 }
    expect(normalizeUserInput(payload)).toEqual(payload)
  })
})
