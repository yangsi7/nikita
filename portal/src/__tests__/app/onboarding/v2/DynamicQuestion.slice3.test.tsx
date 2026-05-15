/**
 * Spec 218 Slice 218-3 — DynamicQuestion dispatcher extension.
 *
 * RED phase: branches for calendar + single_select still render the
 * "not yet implemented" defensive stub on master commit 01922be. This
 * file gates PR-218-3 FE implementation.
 */

import { describe, it, expect, vi, beforeAll } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

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

  it("renders Popover trigger button and disables submit until date selected", () => {
    // Cluster X: CalendarAsk now uses shadcn Calendar+Popover instead of
    // native <input type="date">. Test verifies the trigger button is present.
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

    // Popover trigger button with aria-label from envelope.prompt
    const triggerButton = screen.getByRole("button", { name: /born/i })
    expect(triggerButton).toBeDefined()
    // Submit button should be disabled until a date is selected
    const submitButton = screen.getByRole("button", { name: /continue/i })
    expect(submitButton).toBeDisabled()
  })

  it("calls onSubmit with ISO date string when calendar day selected and form submitted", async () => {
    // Cluster X: CalendarAsk submit path. Constrain calendar to a narrow range
    // (Dec 1–15, 2000) so the first enabled day button is deterministic.
    // CalendarDayButton renders data-day={day.date.toLocaleDateString()} on
    // every cell; we use that attribute to find clickable cells without
    // relying on locale-specific aria-labels from DayPicker's labelDayButton.
    const envelope: AskUnion = {
      component: "calendar",
      handler: "v2",
      slot: "age",
      prompt: "When were you born?",
      max_date: "2000-12-15",
      min_date: "2000-12-01",
    }
    const onSubmit = vi.fn()
    const user = userEvent.setup()
    render(
      <DynamicQuestion
        envelope={envelope}
        onSubmit={onSubmit}
        onInvalidate={vi.fn()}
      />,
    )

    // Open the Popover
    const triggerButton = screen.getByRole("button", { name: /born/i })
    await user.click(triggerButton)

    // Wait for calendar grid to mount (Popover uses a portal in Radix)
    // Find the first non-disabled day button via data-day attribute
    const dayButtons = await screen.findAllByRole("button")
    // CalendarDayButton has data-day; find enabled ones
    const enabledDayButton = dayButtons.find(
      (btn) => btn.hasAttribute("data-day") && !btn.hasAttribute("disabled") && !(btn as HTMLButtonElement).disabled
    )
    expect(enabledDayButton).toBeDefined()

    await user.click(enabledDayButton!)

    // Popover closes after selection; Continue button should now be enabled
    const submitButton = screen.getByRole("button", { name: /continue/i })
    expect(submitButton).not.toBeDisabled()

    await user.click(submitButton)

    // Must call onSubmit exactly once with an ISO "YYYY-MM-DD" string
    expect(onSubmit).toHaveBeenCalledOnce()
    const arg: string = onSubmit.mock.calls[0][0]
    expect(typeof arg).toBe("string")
    expect(arg).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    // Must be within the constrained Dec 2000 range
    expect(arg.startsWith("2000-12-")).toBe(true)
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

  it("submits selected option value when option clicked + form submitted", async () => {
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
    const user = userEvent.setup()
    render(
      <DynamicQuestion
        envelope={envelope}
        onSubmit={onSubmit}
        onInvalidate={vi.fn()}
      />,
    )

    // userEvent.click fires the full pointer-event sequence Radix
    // RadioGroupPrimitive expects; raw fireEvent.click does not invoke
    // onValueChange on the parent RadioGroup root.
    await user.click(screen.getByLabelText("Berlin"))
    await user.click(screen.getByRole("button", { name: /continue/i }))
    expect(onSubmit).toHaveBeenCalledWith("berlin")
  })
})
