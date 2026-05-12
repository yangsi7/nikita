/**
 * Spec 218 Slice 218-3 — DynamicQuestion dispatcher extension.
 *
 * RED phase: branches for calendar + single_select still render the
 * "not yet implemented" defensive stub on master commit 01922be. This
 * file gates PR-218-3 FE implementation.
 */

import { describe, it, expect, vi, beforeAll } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"

import { DynamicQuestion } from "@/app/onboarding/v2/DynamicQuestion"
import type { AskUnion } from "@/app/onboarding/v2/types/envelope"

// Radix RadioGroupPrimitive uses ResizeObserver; JSDOM doesn't ship it.
beforeAll(() => {
  global.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver
})

describe("DynamicQuestion dispatcher (Spec 218 Slice 218-3)", () => {
  it("renders Calendar shape for component=calendar (age slot)", () => {
    const envelope: AskUnion = {
      component: "calendar",
      handler: "v2",
      slot: "age",
      prompt: "When were you born?",
    }
    render(
      <DynamicQuestion
        envelope={envelope}
        onSubmit={vi.fn()}
        onInvalidate={vi.fn()}
      />,
    )

    const shape = screen.getByTestId("v2-calendar-shape")
    expect(shape).toBeDefined()
  })

  it("submits ISO date when calendar input is set + submitted", () => {
    const envelope: AskUnion = {
      component: "calendar",
      handler: "v2",
      slot: "age",
      prompt: "When were you born?",
    }
    const onSubmit = vi.fn()
    render(
      <DynamicQuestion
        envelope={envelope}
        onSubmit={onSubmit}
        onInvalidate={vi.fn()}
      />,
    )

    const input = screen.getByLabelText(/born|date/i) as HTMLInputElement
    fireEvent.change(input, { target: { value: "1998-04-12" } })
    fireEvent.submit(input.closest("form") as HTMLFormElement)
    expect(onSubmit).toHaveBeenCalledWith("1998-04-12")
  })

  it("renders SingleSelect shape for component=single_select (city)", () => {
    const envelope: AskUnion = {
      component: "single_select",
      handler: "v2",
      slot: "city",
      prompt: "Which city are you in?",
      options: [
        { value: "berlin", label: "Berlin" },
        { value: "nyc", label: "NYC" },
        { value: "sf", label: "SF" },
      ],
    }
    render(
      <DynamicQuestion
        envelope={envelope}
        onSubmit={vi.fn()}
        onInvalidate={vi.fn()}
      />,
    )

    const shape = screen.getByTestId("v2-single-select-shape")
    expect(shape).toBeDefined()
    expect(screen.getByText("Berlin")).toBeDefined()
    expect(screen.getByText("NYC")).toBeDefined()
  })

  it("submits selected option value when option clicked + form submitted", () => {
    const envelope: AskUnion = {
      component: "single_select",
      handler: "v2",
      slot: "city",
      prompt: "Which city are you in?",
      options: [
        { value: "berlin", label: "Berlin" },
        { value: "nyc", label: "NYC" },
      ],
    }
    const onSubmit = vi.fn()
    render(
      <DynamicQuestion
        envelope={envelope}
        onSubmit={onSubmit}
        onInvalidate={vi.fn()}
      />,
    )

    const radio = screen.getByLabelText("Berlin") as HTMLInputElement
    fireEvent.click(radio)
    const form = radio.closest("form") as HTMLFormElement
    fireEvent.submit(form)
    expect(onSubmit).toHaveBeenCalledWith("berlin")
  })
})
