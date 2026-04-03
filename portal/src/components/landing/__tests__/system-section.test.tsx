import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { SystemSection } from "../system-section"

describe("SystemSection — T025 AC-REQ-015", () => {
  it("renders a semantic section with accessible heading", () => {
    const { container } = render(<SystemSection />)
    expect(container.querySelector("section")).toBeInTheDocument()
    expect(screen.getByRole("heading")).toBeInTheDocument()
  })

  it("renders at least one system name via SystemTerminal", () => {
    render(<SystemSection />)
    // SystemTerminal renders all 14 systems
    expect(screen.getByText(/Emotional Memory Engine|Relationship Scoring|Vice Personalization/i)).toBeInTheDocument()
  })

  it("renders 3 stat labels", () => {
    render(<SystemSection />)
    expect(screen.getByText(/742/)).toBeInTheDocument()
    expect(screen.getByText(/Python|files/i)).toBeInTheDocument()
    expect(screen.getByText(/86/)).toBeInTheDocument()
  })

  it("has darker background than standard sections", () => {
    const { container } = render(<SystemSection />)
    const section = container.querySelector("section")
    // Section should have darker bg (oklch(0.06 0 0) or bg-void or specific class)
    expect(section?.className || container.innerHTML).toMatch(/0\.06|void|dark|bg-\[/)
  })
})
