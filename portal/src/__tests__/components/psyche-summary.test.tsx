/**
 * Tests for PsycheSummary component
 */
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { PsycheSummary } from "@/components/dashboard/psyche-summary"
import type { PsycheTipsData } from "@/lib/api/types"

const mockPsyche: PsycheTipsData = {
  attachment_style: "anxious",
  defense_mode: "guarded",
  emotional_tone: "melancholic",
  vulnerability_level: 0.3,
  behavioral_tips: [],
  topics_to_encourage: [],
  topics_to_avoid: [],
  internal_monologue: "I wonder if he really cares...",
  generated_at: "2026-03-01T10:00:00Z",
}

describe("PsycheSummary", () => {
  it("renders attachment, defense, and tone badges", () => {
    render(<PsycheSummary psyche={mockPsyche} />)
    expect(screen.getByText("anxious")).toBeInTheDocument()
    expect(screen.getByText("guarded")).toBeInTheDocument()
    expect(screen.getByText("melancholic")).toBeInTheDocument()
  })

  it("renders internal monologue", () => {
    render(<PsycheSummary psyche={mockPsyche} />)
    expect(screen.getByText(/I wonder if he really cares/)).toBeInTheDocument()
  })

  it("links to full analysis page", () => {
    render(<PsycheSummary psyche={mockPsyche} />)
    const link = screen.getByText(/Full analysis/)
    expect(link).toBeInTheDocument()
    expect(link.closest("a")).toHaveAttribute("href", "/dashboard/nikita/day")
  })

  it("renders title", () => {
    render(<PsycheSummary psyche={mockPsyche} />)
    expect(screen.getByText("Nikita's State")).toBeInTheDocument()
  })

  it("hides monologue when empty", () => {
    render(<PsycheSummary psyche={{ ...mockPsyche, internal_monologue: "" }} />)
    // The ldquo character should not appear when monologue is empty
    expect(screen.queryByText(/I wonder/)).not.toBeInTheDocument()
  })
})
