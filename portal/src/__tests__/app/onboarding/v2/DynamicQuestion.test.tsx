/**
 * Spec 218 Slice 218-2 — DynamicQuestion dispatcher (R14 + R2).
 *
 * RED phase: component does not exist on master; this file gates the
 * PR-218-2 FE implementation.
 *
 * Coverage:
 *   - dispatches text_short envelope to Input shape (display_name)
 *   - dispatches handler_handoff envelope -> mounts legacy v1 wizard
 *   - invalidated list triggers parent re-render callback
 */

import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"

import { DynamicQuestion } from "@/app/onboarding/v2/DynamicQuestion"
import type { AskUnion } from "@/app/onboarding/v2/types/envelope"

describe("DynamicQuestion dispatcher (Spec 218 Slice 218-2)", () => {
  it("renders Input for text_short envelope (display_name)", () => {
    const envelope: AskUnion = {
      component: "text_short",
      handler: "v2",
      slot: "display_name",
      prompt: "What name should I use?",
      placeholder: "",
      max_chars: 80,
      dictation: false,
      autocomplete: false,
    }
    const onSubmit = vi.fn()
    render(<DynamicQuestion envelope={envelope} onSubmit={onSubmit} onInvalidate={vi.fn()} />)

    const input = screen.getByRole("textbox", { name: /name|display/i })
    expect(input).toBeDefined()

    fireEvent.change(input, { target: { value: "Sam" } })
    fireEvent.submit(input.closest("form") as HTMLFormElement)
    expect(onSubmit).toHaveBeenCalledWith("Sam")
  })

  it("dispatches handler_handoff envelope to v1 wizard mount", () => {
    const envelope: AskUnion = {
      component: "handler_handoff",
      handler: "v1",
      next_url: "/api/v1/converse/onboarding",
    }
    render(
      <DynamicQuestion
        envelope={envelope}
        onSubmit={vi.fn()}
        onInvalidate={vi.fn()}
      />,
    )

    // The dispatcher MUST mount a v1 wizard surface; we test the
    // presence of a data attribute the dispatcher applies on handoff.
    const handoff = screen.getByTestId("v1-handoff")
    expect(handoff).toBeDefined()
    expect(handoff.getAttribute("data-next-url")).toBe(
      "/api/v1/converse/onboarding",
    )
  })

  it("invokes onInvalidate when envelope carries invalidated slot list", () => {
    const envelope = {
      component: "text_short",
      handler: "v2",
      slot: "city",
      prompt: "Which city are you in?",
      placeholder: "",
      max_chars: 80,
      dictation: false,
      autocomplete: false,
      invalidated: ["hangouts_personalized"],
    } as unknown as AskUnion // `invalidated` is a route-level addition; FE reads as extra.

    const onInvalidate = vi.fn()
    render(
      <DynamicQuestion
        envelope={envelope}
        onSubmit={vi.fn()}
        onInvalidate={onInvalidate}
      />,
    )
    expect(onInvalidate).toHaveBeenCalledWith(["hangouts_personalized"])
  })
})
