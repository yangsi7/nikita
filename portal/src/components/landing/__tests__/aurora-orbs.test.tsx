import { describe, it, expect } from "vitest"
import { render } from "@testing-library/react"
import { AuroraOrbs } from "../aurora-orbs"

describe("AuroraOrbs — T008 AC-REQ-008", () => {
  it("renders exactly two orb elements", () => {
    const { container } = render(<AuroraOrbs />)
    const orbs = container.querySelectorAll(".aurora-orb")
    expect(orbs).toHaveLength(2)
  })

  it("both orbs are aria-hidden", () => {
    const { container } = render(<AuroraOrbs />)
    const orbs = container.querySelectorAll(".aurora-orb")
    orbs.forEach((orb) => {
      expect(orb).toHaveAttribute("aria-hidden", "true")
    })
  })

  it("wrapper has pointer-events-none to avoid interaction blocking", () => {
    const { container } = render(<AuroraOrbs />)
    const wrapper = container.firstChild as HTMLElement
    expect(wrapper.className).toMatch(/pointer-events-none/)
  })

  it("orbs have their specific CSS classes", () => {
    const { container } = render(<AuroraOrbs />)
    expect(container.querySelector(".aurora-orb-1")).toBeInTheDocument()
    expect(container.querySelector(".aurora-orb-2")).toBeInTheDocument()
  })

  it("wrapper is positioned absolute so it fills parent", () => {
    const { container } = render(<AuroraOrbs />)
    const wrapper = container.firstChild as HTMLElement
    expect(wrapper.className).toMatch(/absolute|inset/)
  })

  it("does not contain any interactive elements (CSS-only animation)", () => {
    const { container } = render(<AuroraOrbs />)
    const buttons = container.querySelectorAll("button, a, input")
    expect(buttons).toHaveLength(0)
  })
})
