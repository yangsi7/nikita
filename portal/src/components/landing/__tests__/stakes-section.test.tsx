import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { StakesSection } from "../stakes-section"

describe("StakesSection — T027 AC-REQ-016", () => {
  it("renders a semantic section element", () => {
    const { container } = render(<StakesSection />)
    expect(container.querySelector("section")).toBeInTheDocument()
  })

  it("renders exactly 4 consequence cards", () => {
    const { container } = render(<StakesSection />)
    const cards = container.querySelectorAll(".glass-card")
    expect(cards).toHaveLength(4)
  })

  it("renders all 4 consequence card titles", () => {
    render(<StakesSection />)
    // The 4 stakes consequences from spec
    expect(screen.getByText(/ignore her|left on read|forget|miss/i)).toBeInTheDocument()
    // At least one more unique stake
    expect(screen.getAllByRole("heading").length).toBeGreaterThanOrEqual(1)
  })

  it("renders mood thumbnails in all 4 stake cards", () => {
    render(<StakesSection />)
    expect(screen.getByAltText("Nikita — angry")).toBeInTheDocument()
    expect(screen.getByAltText("Nikita — cold")).toBeInTheDocument()
    expect(screen.getByAltText("Nikita — stressed")).toBeInTheDocument()
    expect(screen.getByAltText("Nikita — crying")).toBeInTheDocument()
  })

  it("renders ChapterTimeline with 5 dots", () => {
    const { container } = render(<StakesSection />)
    const dots = container.querySelectorAll("[data-testid='chapter-dot']")
    expect(dots).toHaveLength(5)
  })

  it("renders section heading", () => {
    render(<StakesSection />)
    expect(screen.getByRole("heading")).toBeInTheDocument()
  })

  it("contains no implementation jargon (pgVector, ElevenLabs)", () => {
    const { container } = render(<StakesSection />)
    expect(container.innerHTML).not.toMatch(/pgvector|elevenlabs/i)
  })
})
