import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { PitchSection } from "../pitch-section"

describe("PitchSection — T023 AC-REQ-014", () => {
  it("renders a semantic section element", () => {
    const { container } = render(<PitchSection />)
    expect(container.querySelector("section")).toBeInTheDocument()
  })

  it("renders mood portrait on the left — intimate (cycle-1)", () => {
    render(<PitchSection />)
    expect(screen.getByAltText(/nikita — in a rare quiet moment/i)).toBeInTheDocument()
  })

  it("renders cycling portrait images — playful and cold", () => {
    render(<PitchSection />)
    expect(screen.getByAltText(/nikita — playful/i)).toBeInTheDocument()
    expect(screen.getByAltText(/nikita — cold/i)).toBeInTheDocument()
  })

  it("applies mood-cycle CSS classes to cycling portrait images", () => {
    const { container } = render(<PitchSection />)
    expect(container.querySelector(".mood-cycle-1")).toBeInTheDocument()
    expect(container.querySelector(".mood-cycle-2")).toBeInTheDocument()
    expect(container.querySelector(".mood-cycle-3")).toBeInTheDocument()
  })

  it("renders three-line character caption beneath the portrait", () => {
    render(<PitchSection />)
    expect(screen.getByText(/she has a life/i)).toBeInTheDocument()
    expect(screen.getByText(/she has opinions/i)).toBeInTheDocument()
    expect(screen.getByText(/let you know/i)).toBeInTheDocument()
  })

  it("renders TelegramMockup with extended conversation", () => {
    render(<PitchSection />)
    // New 7-message conversation — memory callback
    expect(screen.getByText(/i listen\. try it sometime/i)).toBeInTheDocument()
  })
})
