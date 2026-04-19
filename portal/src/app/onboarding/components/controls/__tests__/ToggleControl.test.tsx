import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent, within } from "@testing-library/react"

import { ToggleControl } from "@/app/onboarding/components/controls/ToggleControl"

// Spec 214 PR #363 QA iter-1 fix I2 (RED → GREEN)
// Tests: radio `aria-checked` reflects the most recent selection (previously
// hardcoded to `false`, which broke screen reader semantics).

describe("ToggleControl", () => {
  it("renders both radios with aria-checked=false before any selection", () => {
    const onSubmit = vi.fn()
    const { container } = render(<ToggleControl onSubmit={onSubmit} />)
    const radios = within(container).getAllByRole("radio")
    expect(radios).toHaveLength(2)
    for (const r of radios) {
      expect(r).toHaveAttribute("aria-checked", "false")
    }
  })

  it("sets aria-checked=true on the selected radio and false on the other", () => {
    const onSubmit = vi.fn()
    render(<ToggleControl onSubmit={onSubmit} />)
    fireEvent.click(screen.getByRole("radio", { name: "voice" }))

    expect(screen.getByRole("radio", { name: "voice" })).toHaveAttribute("aria-checked", "true")
    expect(screen.getByRole("radio", { name: "text" })).toHaveAttribute("aria-checked", "false")

    expect(onSubmit).toHaveBeenCalledWith({ kind: "toggle", value: "voice" })
  })

  it("flips aria-checked when the user re-selects the other radio", () => {
    const onSubmit = vi.fn()
    render(<ToggleControl onSubmit={onSubmit} />)
    fireEvent.click(screen.getByRole("radio", { name: "voice" }))
    fireEvent.click(screen.getByRole("radio", { name: "text" }))

    expect(screen.getByRole("radio", { name: "voice" })).toHaveAttribute("aria-checked", "false")
    expect(screen.getByRole("radio", { name: "text" })).toHaveAttribute("aria-checked", "true")

    expect(onSubmit).toHaveBeenCalledTimes(2)
    expect(onSubmit).toHaveBeenLastCalledWith({ kind: "toggle", value: "text" })
  })
})
