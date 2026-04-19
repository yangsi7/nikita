import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent, within } from "@testing-library/react"

import { SliderControl } from "@/app/onboarding/components/controls/SliderControl"

// Spec 214 PR #363 QA iter-1 fix I1 (RED → GREEN)
// Tests: radio `aria-checked` reflects the most recent selection (previously
// hardcoded to `false`, which broke screen reader semantics).

describe("SliderControl", () => {
  it("renders all five radios with aria-checked=false before any selection", () => {
    const onSubmit = vi.fn()
    const { container } = render(<SliderControl onSubmit={onSubmit} />)
    const radios = within(container).getAllByRole("radio")
    expect(radios).toHaveLength(5)
    for (const r of radios) {
      expect(r).toHaveAttribute("aria-checked", "false")
    }
  })

  it("sets aria-checked=true on the selected radio and keeps others false", () => {
    const onSubmit = vi.fn()
    render(<SliderControl onSubmit={onSubmit} />)
    fireEvent.click(screen.getByRole("radio", { name: "3" }))

    expect(screen.getByRole("radio", { name: "1" })).toHaveAttribute("aria-checked", "false")
    expect(screen.getByRole("radio", { name: "2" })).toHaveAttribute("aria-checked", "false")
    expect(screen.getByRole("radio", { name: "3" })).toHaveAttribute("aria-checked", "true")
    expect(screen.getByRole("radio", { name: "4" })).toHaveAttribute("aria-checked", "false")
    expect(screen.getByRole("radio", { name: "5" })).toHaveAttribute("aria-checked", "false")

    expect(onSubmit).toHaveBeenCalledWith({ kind: "slider", value: 3 })
  })

  it("updates aria-checked when the user re-selects a different radio", () => {
    const onSubmit = vi.fn()
    render(<SliderControl onSubmit={onSubmit} />)
    fireEvent.click(screen.getByRole("radio", { name: "2" }))
    fireEvent.click(screen.getByRole("radio", { name: "5" }))

    expect(screen.getByRole("radio", { name: "2" })).toHaveAttribute("aria-checked", "false")
    expect(screen.getByRole("radio", { name: "5" })).toHaveAttribute("aria-checked", "true")

    expect(onSubmit).toHaveBeenCalledTimes(2)
    expect(onSubmit).toHaveBeenLastCalledWith({ kind: "slider", value: 5 })
  })
})
