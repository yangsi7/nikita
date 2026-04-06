import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { PortalShowcase } from "../portal-showcase"

describe("PortalShowcase — 3-card portal preview", () => {
  it("renders the section heading", () => {
    render(<PortalShowcase />)
    expect(screen.getByRole("heading", { name: /a portal into her life/i })).toBeInTheDocument()
  })

  it("renders 3 GlassCard widgets", () => {
    const { container } = render(<PortalShowcase />)
    const cards = container.querySelectorAll(".glass-card")
    expect(cards).toHaveLength(3)
  })

  it("renders the mood orb card with Nikita playful avatar", () => {
    render(<PortalShowcase />)
    expect(screen.getByAltText("Nikita — playful")).toBeInTheDocument()
  })

  it("renders the mood orb card with label", () => {
    render(<PortalShowcase />)
    expect(screen.getByText(/her mood right now/i)).toBeInTheDocument()
    expect(screen.getByText(/^playful$/i)).toBeInTheDocument()
  })

  it("renders the score timeline card with label and metrics", () => {
    render(<PortalShowcase />)
    expect(screen.getByText(/your 30-day curve/i)).toBeInTheDocument()
    expect(screen.getByText(/affection/i)).toBeInTheDocument()
    expect(screen.getByText(/tension/i)).toBeInTheDocument()
    expect(screen.getByText(/72%/)).toBeInTheDocument()
  })

  it("renders the life events card with label and entries", () => {
    render(<PortalShowcase />)
    // "What she's been up to" appears in both the subtitle and the card label;
    // assert on the card label specifically via uppercase-tracking class usage.
    const labels = screen.getAllByText(/what she's been up to/i)
    expect(labels.length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText(/bad day at work/i)).toBeInTheDocument()
    expect(screen.getByText(/gym session/i)).toBeInTheDocument()
    expect(screen.getByText(/saw an ex/i)).toBeInTheDocument()
  })

  it("renders stat bars inside the mood orb card", () => {
    render(<PortalShowcase />)
    expect(screen.getByText(/^energy$/i)).toBeInTheDocument()
    expect(screen.getByText(/^warmth$/i)).toBeInTheDocument()
    expect(screen.getByText(/^focus$/i)).toBeInTheDocument()
  })
})
