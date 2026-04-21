/**
 * GH #378 regression guard — frontend /converse timeout invariants.
 *
 * Walk P (2026-04-21) showed every wizard turn timing out at the prior
 * 2500ms ceiling. The fix split backend timeout into warm (8s) and cold
 * (30s) values, with the helper at portal_onboarding.py:get_converse_timeout_ms()
 * picking the right one based on Cloud Run process uptime.
 *
 * The frontend has no way to know whether a given backend instance is cold
 * or warm, so it MUST adopt the larger (cold) value as its hard cap. If
 * the frontend cap is shorter than the backend cap, the client aborts a
 * still-pending request and the user sees a fallback even though the
 * backend would have completed — exactly the Walk P failure mode.
 */

import { describe, it, expect } from "vitest"
import { CONVERSATION_AGENT_TIMEOUT_MS } from "../hooks/useConversationState"

// Mirror of nikita/onboarding/tuning.py:CONVERSE_TIMEOUT_MS_COLD. Bump in
// lockstep if the backend cold ceiling changes.
const BACKEND_COLD_TIMEOUT_MS = 30000

describe("GH #378 — /converse timeout cold/warm invariant", () => {
  it("CONVERSATION_AGENT_TIMEOUT_MS must be >= the backend cold timeout", () => {
    expect(CONVERSATION_AGENT_TIMEOUT_MS).toBeGreaterThanOrEqual(
      BACKEND_COLD_TIMEOUT_MS,
    )
  })

  it("CONVERSATION_AGENT_TIMEOUT_MS must absorb Cloud Run cold-start floor (15s)", () => {
    // Empirical floor: Cloud Run cold-start can take 5-15s; LLM warmup
    // adds more. 15s is the minimum sane value before the wizard fails on
    // every cold-start request.
    expect(CONVERSATION_AGENT_TIMEOUT_MS).toBeGreaterThanOrEqual(15000)
  })
})
