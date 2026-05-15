/**
 * Spec 218 Slice 218-5 — DynamicQuestion dispatcher for slider + text_long.
 *
 * New shapes in slice 218-5:
 *   - component="slider"    -> <Slider> Radix component (saturday_morning, darkness_level)
 *   - component="text_long" -> <textarea> (geek_out_on)
 *
 * RED phase: slider and text_long branches still render the
 * "not yet implemented" defensive stub until PR-218-5 FE lands.
 */

import { describe, it, expect, vi, beforeAll } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

import { DynamicQuestion } from "@/app/onboarding/v2/DynamicQuestion"
import type { AskUnion } from "@/app/onboarding/v2/types/envelope"

beforeAll(() => {
  global.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver
})

describe("DynamicQuestion dispatcher (Spec 218 Slice 218-5)", () => {
  describe("slider shape", () => {
    it("renders Slider shape for component=slider (saturday_morning)", () => {
      const envelope: AskUnion = {
        component: "slider",
        handler: "v2",
        slot: "saturday_morning",
        prompt: "How active are you on Saturday mornings?",
        min_val: 0,
        max_val: 10,
        step: 1,
        labels: { 0: "Lazy", 5: "Balanced", 10: "Super active" },
      }
      render(
        <DynamicQuestion
          envelope={envelope}
          onSubmit={vi.fn()}
          onInvalidate={vi.fn()}
        />,
      )

      const shape = screen.getByTestId("v2-slider-shape")
      expect(shape).toBeDefined()
    })

    it("renders Slider shape for component=slider (darkness_level)", () => {
      const envelope: AskUnion = {
        component: "slider",
        handler: "v2",
        slot: "darkness_level",
        prompt: "How dark is your humor?",
        min_val: 0,
        max_val: 10,
        step: 1,
        labels: { 0: "Light", 10: "Very dark" },
      }
      render(
        <DynamicQuestion
          envelope={envelope}
          onSubmit={vi.fn()}
          onInvalidate={vi.fn()}
        />,
      )

      const shape = screen.getByTestId("v2-slider-shape")
      expect(shape).toBeDefined()
    })

    it("displays the prompt text", () => {
      const envelope: AskUnion = {
        component: "slider",
        handler: "v2",
        slot: "saturday_morning",
        prompt: "Unique prompt text for slider",
        min_val: 0,
        max_val: 10,
      }
      render(
        <DynamicQuestion
          envelope={envelope}
          onSubmit={vi.fn()}
          onInvalidate={vi.fn()}
        />,
      )

      expect(screen.getByText("Unique prompt text for slider")).toBeDefined()
    })

    it("calls onSubmit with current slider value when form submitted", async () => {
      const envelope: AskUnion = {
        component: "slider",
        handler: "v2",
        slot: "saturday_morning",
        prompt: "How active?",
        min_val: 0,
        max_val: 10,
        step: 1,
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

      await user.click(screen.getByRole("button", { name: /continue/i }))
      // default value on mount is min_val (0); must be called with a number
      // AND must be an integer (Radix can emit floats when step is fractional;
      // route _slot_payload rejects non-int — FE Math.round() guards via slider.tsx).
      expect(onSubmit).toHaveBeenCalledOnce()
      const arg = onSubmit.mock.calls[0][0]
      expect(typeof arg).toBe("number")
      expect(Number.isInteger(arg)).toBe(true)
    })
  })

  describe("text_long shape", () => {
    it("renders TextLong shape for component=text_long (geek_out_on)", () => {
      const envelope: AskUnion = {
        component: "text_long",
        handler: "v2",
        slot: "geek_out_on",
        prompt: "What do you geek out on?",
        placeholder: "e.g. vintage synthesizers...",
        max_chars: 1000,
      }
      render(
        <DynamicQuestion
          envelope={envelope}
          onSubmit={vi.fn()}
          onInvalidate={vi.fn()}
        />,
      )

      const shape = screen.getByTestId("v2-text-long-shape")
      expect(shape).toBeDefined()
    })

    it("displays the prompt text", () => {
      const envelope: AskUnion = {
        component: "text_long",
        handler: "v2",
        slot: "geek_out_on",
        prompt: "Unique prompt for text_long",
        max_chars: 1000,
      }
      render(
        <DynamicQuestion
          envelope={envelope}
          onSubmit={vi.fn()}
          onInvalidate={vi.fn()}
        />,
      )

      expect(screen.getByText("Unique prompt for text_long")).toBeDefined()
    })

    it("renders a textarea element", () => {
      const envelope: AskUnion = {
        component: "text_long",
        handler: "v2",
        slot: "geek_out_on",
        prompt: "Tell me what you geek out on.",
        max_chars: 1000,
      }
      render(
        <DynamicQuestion
          envelope={envelope}
          onSubmit={vi.fn()}
          onInvalidate={vi.fn()}
        />,
      )

      const textarea = screen.getByRole("textbox") as HTMLTextAreaElement
      expect(textarea.tagName.toLowerCase()).toBe("textarea")
    })

    it("calls onSubmit with trimmed textarea value when submitted", async () => {
      const envelope: AskUnion = {
        component: "text_long",
        handler: "v2",
        slot: "geek_out_on",
        prompt: "Tell me.",
        max_chars: 1000,
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

      const textarea = screen.getByRole("textbox")
      await user.type(textarea, "  vintage synthesizers  ")
      await user.click(screen.getByRole("button", { name: /continue/i }))
      expect(onSubmit).toHaveBeenCalledWith("vintage synthesizers")
    })

    it("does not submit when textarea is empty / whitespace-only", async () => {
      const envelope: AskUnion = {
        component: "text_long",
        handler: "v2",
        slot: "geek_out_on",
        prompt: "Tell me.",
        max_chars: 1000,
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

      await user.click(screen.getByRole("button", { name: /continue/i }))
      expect(onSubmit).not.toHaveBeenCalled()
    })
  })
})
