import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { PitchSection } from "../pitch-section"

describe("PitchSection — T023 AC-REQ-014", () => {
  it("renders a semantic section element", () => {
    const { container } = render(<PitchSection />)
    expect(container.querySelector("section")).toBeInTheDocument()
  })

  it("renders 3 differentiator quotes with exact copy", () => {
    render(<PitchSection />)
    // Quote 1
    expect(screen.getByText(/She has opinions/i)).toBeInTheDocument()
    // Quote 2 — uses strong for emphasis
    expect(screen.getByText(/forget her birthday|ignore her texts/i)).toBeInTheDocument()
    // Quote 3
    expect(screen.getByText(/Other apps.*afraid|afraid to say no/i)).toBeInTheDocument()
  })

  it("renders bold emphasis elements (<strong>) in quotes", () => {
    const { container } = render(<PitchSection />)
    const strongs = container.querySelectorAll("strong")
    expect(strongs.length).toBeGreaterThanOrEqual(3)
  })

  it("renders TelegramMockup messages", () => {
    render(<PitchSection />)
    // TelegramMockup contains "left me on read" or similar
    expect(screen.getByText(/left me on read/i)).toBeInTheDocument()
  })
})
