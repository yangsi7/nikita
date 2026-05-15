/**
 * Spec 218 Slice 218-4 — DynamicQuestion dispatcher for chip_multi + phone.
 *
 * RED phase: chip_multi and phone branches still render the
 * "not yet implemented" defensive stub until PR-218-4 FE lands.
 */

import { describe, it, expect, vi, beforeAll } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

// PhoneShape now calls createClient() for the phone-demo modal flow.
// Provide a minimal mock so non-demo phone tests don't error on Supabase init.
vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({
    auth: {
      getSession: vi.fn().mockResolvedValue({
        data: { session: { access_token: "test", user: { id: "u1" } } },
        error: null,
      }),
    },
    channel: vi.fn().mockReturnValue({
      on: vi.fn().mockReturnValue({ subscribe: vi.fn() }),
    }),
    removeChannel: vi.fn().mockResolvedValue(undefined),
  }),
}))

import { DynamicQuestion } from "@/app/onboarding/v2/DynamicQuestion"
import type { AskUnion } from "@/app/onboarding/v2/types/envelope"

// ResizeObserver polyfill — Radix RadioGroupPrimitive + Command uses it.
beforeAll(() => {
  global.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver
})

describe("DynamicQuestion dispatcher (Spec 218 Slice 218-4)", () => {
  describe("chip_multi shape", () => {
    it("renders ChipMulti shape for component=chip_multi (primary_hobbies)", () => {
      const envelope: AskUnion = {
        component: "chip_multi",
        handler: "v2",
        slot: "primary_hobbies",
        prompt: "What are your hobbies?",
        options: [
          { value: "music", label: "Music" },
          { value: "sports", label: "Sports" },
          { value: "travel", label: "Travel" },
        ],
        min_pick: 1,
        max_pick: 3,
      }
      render(
        <DynamicQuestion
          envelope={envelope}
          onSubmit={vi.fn()}
          onInvalidate={vi.fn()}
        />,
      )

      const shape = screen.getByTestId("v2-chip-multi-shape")
      expect(shape).toBeDefined()
      // All option labels rendered
      expect(screen.getByText("Music")).toBeDefined()
      expect(screen.getByText("Sports")).toBeDefined()
      expect(screen.getByText("Travel")).toBeDefined()
    })

    it("submits selected values as array when chip toggled + submitted", async () => {
      const envelope: AskUnion = {
        component: "chip_multi",
        handler: "v2",
        slot: "primary_hobbies",
        prompt: "What are your hobbies?",
        options: [
          { value: "music", label: "Music" },
          { value: "sports", label: "Sports" },
          { value: "travel", label: "Travel" },
        ],
        min_pick: 1,
        max_pick: 3,
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

      // Toggle "Music" chip on
      await user.click(screen.getByText("Music"))
      // Submit
      await user.click(screen.getByRole("button", { name: /continue/i }))
      expect(onSubmit).toHaveBeenCalledWith(["music"])
    })

    it("toggles chip off when clicked twice (deselect)", async () => {
      const envelope: AskUnion = {
        component: "chip_multi",
        handler: "v2",
        slot: "primary_hobbies",
        prompt: "What are your hobbies?",
        options: [
          { value: "music", label: "Music" },
          { value: "sports", label: "Sports" },
        ],
        min_pick: 1,
        max_pick: 2,
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

      // Toggle Music on then off
      await user.click(screen.getByText("Music"))
      await user.click(screen.getByText("Music"))
      // Toggle Sports on
      await user.click(screen.getByText("Sports"))
      await user.click(screen.getByRole("button", { name: /continue/i }))
      expect(onSubmit).toHaveBeenCalledWith(["sports"])
    })
  })

  describe("phone shape", () => {
    it("renders Phone shape for component=phone", () => {
      const envelope: AskUnion = {
        component: "phone",
        handler: "v2",
        slot: "phone",
        prompt: "What's your number?",
        default_country: "US",
        demo_call_after_submit: true,
      }
      render(
        <DynamicQuestion
          envelope={envelope}
          onSubmit={vi.fn()}
          onInvalidate={vi.fn()}
        />,
      )

      const shape = screen.getByTestId("v2-phone-shape")
      expect(shape).toBeDefined()
    })

    it("submits E.164 phone when valid number entered", () => {
      const envelope: AskUnion = {
        component: "phone",
        handler: "v2",
        slot: "phone",
        prompt: "What's your number?",
        default_country: "US",
        demo_call_after_submit: false,
      }
      const onSubmit = vi.fn()
      render(
        <DynamicQuestion
          envelope={envelope}
          onSubmit={onSubmit}
          onInvalidate={vi.fn()}
        />,
      )

      const input = screen.getByTestId("v2-phone-input") as HTMLInputElement
      fireEvent.change(input, { target: { value: "+14155550100" } })
      fireEvent.submit(input.closest("form") as HTMLFormElement)
      expect(onSubmit).toHaveBeenCalledWith("+14155550100")
    })
  })
})
