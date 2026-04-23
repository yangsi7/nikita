/**
 * Tests for useConversationState reducer (AC-11d.5 monotonicity guard).
 *
 * The reducer lives at:
 *   portal/src/app/onboarding/hooks/useConversationState.ts
 *
 * These tests exercise the pure reducer function (conversationReducer) in
 * isolation — no React hook infrastructure needed.
 */
import { describe, it, expect } from "vitest"

import {
  conversationReducer,
} from "../../app/onboarding/hooks/useConversationState"
import type {
  ConversationState,
  ConversationAction,
} from "../../app/onboarding/hooks/useConversationState"

const INITIAL_STATE: ConversationState = {
  turns: [],
  extractedFields: {},
  elidedExtracted: {},
  progressPct: 0,
  awaitingConfirmation: false,
  currentPromptType: "text",
  isComplete: false,
  isLoading: false,
  lastError: null,
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeServerResponseAction(
  progress: number,
  opts: Partial<{
    reply: string
    confirmation: boolean
    complete: boolean
  }> = {}
): ConversationAction {
  return {
    type: "server_response",
    response: {
      nikita_reply: opts.reply ?? "hey",
      extracted_fields: {},
      progress_pct: progress,
      confirmation_required: opts.confirmation ?? false,
      next_prompt_type: "text",
      conversation_complete: opts.complete ?? false,
      source: "llm",
      latency_ms: 100,
    },
  }
}

// ---------------------------------------------------------------------------
// AC-11d.5 monotonicity guard
// ---------------------------------------------------------------------------

describe("conversationReducer server_response monotonicity (AC-11d.5)", () => {
  it("advances progressPct when server returns higher value", () => {
    const stateAt30: ConversationState = { ...INITIAL_STATE, progressPct: 30 }
    const next = conversationReducer(stateAt30, makeServerResponseAction(60))
    expect(next.progressPct).toBe(60)
  })

  it("holds progressPct when server returns equal value", () => {
    const stateAt50: ConversationState = { ...INITIAL_STATE, progressPct: 50 }
    const next = conversationReducer(stateAt50, makeServerResponseAction(50))
    expect(next.progressPct).toBe(50)
  })

  it("does NOT regress progressPct when server returns lower value (guard)", () => {
    // Root cause of GH #402/#403: per-turn snapshot progress could go
    // backwards if BE returned a stale or reduced value. The fix is
    // Math.max(state.progressPct, response.progress_pct).
    const stateAt70: ConversationState = { ...INITIAL_STATE, progressPct: 70 }
    const next = conversationReducer(stateAt70, makeServerResponseAction(50))
    expect(next.progressPct).toBe(70) // must NOT regress to 50
  })

  it("monotonicity holds across a multi-turn sequence", () => {
    // Simulate a 5-turn conversation where progress jumps forward then
    // a stale response tries to send it back.
    const serverValues = [20, 40, 60, 35, 80]
    let state = INITIAL_STATE
    const observed: number[] = []
    for (const pct of serverValues) {
      state = conversationReducer(state, makeServerResponseAction(pct))
      observed.push(state.progressPct)
    }
    // Expected: [20, 40, 60, 60, 80]  (stale 35 is clamped to 60)
    for (let i = 1; i < observed.length; i++) {
      expect(observed[i]).toBeGreaterThanOrEqual(observed[i - 1])
    }
    expect(observed).toEqual([20, 40, 60, 60, 80])
  })

  it("progressPct stays at 0 when server sends 0 (edge: initial turn)", () => {
    const next = conversationReducer(INITIAL_STATE, makeServerResponseAction(0))
    expect(next.progressPct).toBe(0)
  })

  it("progressPct reaches 100 and stays there even if server sends 0", () => {
    const stateAt100: ConversationState = {
      ...INITIAL_STATE,
      progressPct: 100,
      isComplete: true,
    }
    const next = conversationReducer(stateAt100, makeServerResponseAction(0))
    expect(next.progressPct).toBe(100)
  })
})

// ---------------------------------------------------------------------------
// Basic server_response reducer smoke tests
// ---------------------------------------------------------------------------

describe("conversationReducer server_response basics", () => {
  it("appends a nikita turn", () => {
    const next = conversationReducer(
      INITIAL_STATE,
      makeServerResponseAction(10, { reply: "hello" })
    )
    expect(next.turns).toHaveLength(1)
    expect(next.turns[0].role).toBe("nikita")
    expect(next.turns[0].content).toBe("hello")
  })

  it("clears isLoading and lastError", () => {
    const loading: ConversationState = {
      ...INITIAL_STATE,
      isLoading: true,
      lastError: "some error",
    }
    const next = conversationReducer(loading, makeServerResponseAction(10))
    expect(next.isLoading).toBe(false)
    expect(next.lastError).toBeNull()
  })

  it("sets isComplete from response", () => {
    const next = conversationReducer(
      INITIAL_STATE,
      makeServerResponseAction(100, { complete: true })
    )
    expect(next.isComplete).toBe(true)
  })

  it("merges extracted_fields from response", () => {
    const stateWithFields: ConversationState = {
      ...INITIAL_STATE,
      extractedFields: { name: "Ava" },
    }
    const action: ConversationAction = {
      type: "server_response",
      response: {
        nikita_reply: "ok",
        extracted_fields: { age: 25 },
        progress_pct: 50,
        confirmation_required: false,
        next_prompt_type: "text",
        conversation_complete: false,
        source: "llm",
        latency_ms: 100,
      },
    }
    const next = conversationReducer(stateWithFields, action)
    expect(next.extractedFields).toEqual({ name: "Ava", age: 25 })
  })
})

