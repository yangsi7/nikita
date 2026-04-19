/**
 * Spec 214 T3.7 — ConfirmationButtons unit tests.
 *
 * ACs:
 *   - AC-T3.7.1: Yes + Fix that render when confirmation_required=true
 *   - AC-T3.7.2: Fix that flow = reject_confirmation reducer action =
 *                marks last Nikita turn superseded + clears pending control
 *   - AC-T3.7.3: between reject and next server_response → currentPromptType='none'
 */

import { render, screen, fireEvent } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"

import { ConfirmationButtons } from "../components/ConfirmationButtons"
import {
  conversationReducer,
} from "../hooks/useConversationState"
import type { ConversationState } from "../hooks/useConversationState"

describe("ConfirmationButtons — AC-T3.7.1 render when confirmation is required", () => {
  it("renders both yes + fix that buttons", () => {
    render(<ConfirmationButtons onConfirm={vi.fn()} onReject={vi.fn()} />)
    expect(screen.getByTestId("confirmation-yes")).toBeInTheDocument()
    expect(screen.getByTestId("confirmation-fix")).toBeInTheDocument()
  })

  it("yes button invokes onConfirm", () => {
    const onConfirm = vi.fn()
    render(<ConfirmationButtons onConfirm={onConfirm} onReject={vi.fn()} />)
    fireEvent.click(screen.getByTestId("confirmation-yes"))
    expect(onConfirm).toHaveBeenCalledTimes(1)
  })

  it("fix-that button invokes onReject", () => {
    const onReject = vi.fn()
    render(<ConfirmationButtons onConfirm={vi.fn()} onReject={onReject} />)
    fireEvent.click(screen.getByTestId("confirmation-fix"))
    expect(onReject).toHaveBeenCalledTimes(1)
  })

  it("disabled prop blocks both handlers", () => {
    const onConfirm = vi.fn()
    const onReject = vi.fn()
    render(
      <ConfirmationButtons onConfirm={onConfirm} onReject={onReject} disabled={true} />
    )
    fireEvent.click(screen.getByTestId("confirmation-yes"))
    fireEvent.click(screen.getByTestId("confirmation-fix"))
    expect(onConfirm).not.toHaveBeenCalled()
    expect(onReject).not.toHaveBeenCalled()
  })
})

describe("ConfirmationButtons — AC-T3.7.2 reject_confirmation marks ghost turn", () => {
  it("reducer reject_confirmation marks the latest Nikita turn superseded", () => {
    const state: ConversationState = {
      turns: [
        { role: "user", content: "zurich", timestamp: "t0" },
        { role: "nikita", content: "zurich. right?", timestamp: "t1" },
      ],
      extractedFields: {},
      elidedExtracted: {},
      progressPct: 20,
      awaitingConfirmation: true,
      currentPromptType: "text",
      isComplete: false,
      isLoading: false,
      lastError: null,
    }
    const next = conversationReducer(state, { type: "reject_confirmation" })
    expect(next.turns[1].superseded).toBe(true)
    expect(next.awaitingConfirmation).toBe(false)
    expect(next.currentPromptType).toBe("none")
  })
})

describe("ConfirmationButtons — AC-T3.7.3 pending control cleared between responses", () => {
  it("reject → server_response chain shows 'none' in the middle state", () => {
    const state: ConversationState = {
      turns: [{ role: "nikita", content: "zurich. right?", timestamp: "t0" }],
      extractedFields: {},
      elidedExtracted: {},
      progressPct: 20,
      awaitingConfirmation: true,
      currentPromptType: "chips",
      currentPromptOptions: ["techno"],
      isComplete: false,
      isLoading: false,
      lastError: null,
    }
    const afterReject = conversationReducer(state, { type: "reject_confirmation" })
    expect(afterReject.currentPromptType).toBe("none")
    // Simulate server response after reject — currentPromptType should reset.
    const afterServer = conversationReducer(afterReject, {
      type: "server_response",
      response: {
        nikita_reply: "ok which city then",
        extracted_fields: {},
        confirmation_required: false,
        next_prompt_type: "text",
        progress_pct: 20,
        conversation_complete: false,
        source: "llm",
        latency_ms: 100,
      },
    })
    expect(afterServer.currentPromptType).toBe("text")
  })
})
