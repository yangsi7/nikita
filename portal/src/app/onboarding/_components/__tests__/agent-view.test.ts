/**
 * Spec 217-3B AC-T-B.3 / AC-13.2 / AC-13.3 — discriminated-union dispatch
 * unit test for `deriveAgentView`.
 *
 * Falsifier set:
 *   - All 6 BE `kind` values produce a distinguishable AgentView.
 *   - reaction → deterministic stays UNLOCKED (`locksDeterministic === false`).
 *   - followup → deterministic LOCKS (`locksDeterministic === true`).
 *   - completion → terminal flags carry through (isComplete + linkCode).
 *   - field_error → preserves errors map shape (Record<string, string>).
 *   - No setTimeout is scheduled by deriveAgentView itself (helper is pure).
 */

import { afterEach, describe, expect, it, vi } from "vitest"

import type { AnswerResponse } from "@/app/onboarding/types/answer"

import { deriveAgentView } from "../agent-view"

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
})

describe("deriveAgentView — 6-branch dispatch", () => {
  it("null response yields the empty view", () => {
    const v = deriveAgentView(null)
    expect(v.reactionText).toBeNull()
    expect(v.followupQuestion).toBeNull()
    expect(v.fieldErrors).toBeNull()
    expect(v.failureExplanation).toBeNull()
    expect(v.archetypeCards).toBeNull()
    expect(v.progressPct).toBeNull()
    expect(v.isComplete).toBe(false)
    expect(v.linkCode).toBeNull()
    expect(v.locksDeterministic).toBe(false)
  })

  it("reaction surfaces reaction_text WITHOUT locking deterministic chrome", () => {
    const r: AnswerResponse = {
      kind: "reaction",
      reaction_text: "noted",
    }
    const v = deriveAgentView(r)
    expect(v.reactionText).toBe("noted")
    expect(v.followupQuestion).toBeNull()
    expect(v.locksDeterministic).toBe(false)
  })

  it("followup surfaces question_text AND locks deterministic chrome", () => {
    const r: AnswerResponse = {
      kind: "followup",
      question_text: "what city, exactly?",
      target_slot: "city",
    }
    const v = deriveAgentView(r)
    expect(v.followupQuestion).toBe("what city, exactly?")
    expect(v.nextSlotKind).toBe("city")
    expect(v.locksDeterministic).toBe(true)
  })

  it("field_error surfaces error map (Record<string, string>)", () => {
    const r: AnswerResponse = {
      kind: "field_error",
      errors: { age: "must be 18 or older" },
    }
    const v = deriveAgentView(r)
    expect(v.fieldErrors).toEqual({ age: "must be 18 or older" })
    expect(v.failureExplanation).toBeNull()
  })

  it("turn_failure surfaces explanation", () => {
    const r: AnswerResponse = {
      kind: "turn_failure",
      explanation: "the agent timed out — try once more.",
    }
    const v = deriveAgentView(r)
    expect(v.failureExplanation).toBe(
      "the agent timed out — try once more.",
    )
  })

  it("deterministic_advance surfaces progress_pct + archetype_cards", () => {
    const r: AnswerResponse = {
      kind: "deterministic_advance",
      next_slot_kind: "city",
      progress_pct: 23,
      archetype_cards: null,
    }
    const v = deriveAgentView(r)
    expect(v.progressPct).toBe(23)
    expect(v.nextSlotKind).toBe("city")
    expect(v.archetypeCards).toBeNull()
    expect(v.isComplete).toBe(false)
  })

  it("completion surfaces isComplete + link_code + 100% progress", () => {
    const r: AnswerResponse = {
      kind: "completion",
      is_complete: true,
      link_code: "abc123",
      conversation_id: "conv-7",
      progress_pct: 100,
    }
    const v = deriveAgentView(r)
    expect(v.isComplete).toBe(true)
    expect(v.linkCode).toBe("abc123")
    expect(v.progressPct).toBe(100)
  })

  it("AC-13.3: helper is pure — no setTimeout side effects", () => {
    const spy = vi.spyOn(globalThis, "setTimeout")
    const baselineCalls = spy.mock.calls.length
    deriveAgentView({ kind: "reaction", reaction_text: "noted" })
    deriveAgentView({
      kind: "deterministic_advance",
      next_slot_kind: null,
      progress_pct: 50,
      archetype_cards: null,
    })
    expect(spy.mock.calls.length).toBe(baselineCalls)
  })
})
