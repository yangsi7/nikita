/**
 * Tests for DecayWarning component
 */
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { DecayWarning } from "@/components/dashboard/decay-warning"
import type { DecayStatus } from "@/lib/api/types"

const decayingData: DecayStatus = {
  grace_period_hours: 24,
  hours_remaining: 3,
  decay_rate: 0.5,
  current_score: 62,
  projected_score: 56,
  is_decaying: true,
}

const graceData: DecayStatus = {
  grace_period_hours: 24,
  hours_remaining: 10,
  decay_rate: 0.5,
  current_score: 62,
  projected_score: 62,
  is_decaying: false,
}

const fullGraceData: DecayStatus = {
  grace_period_hours: 24,
  hours_remaining: 20,
  decay_rate: 0.5,
  current_score: 62,
  projected_score: 62,
  is_decaying: false,
}

describe("DecayWarning", () => {
  it("renders 'Score is decaying!' when is_decaying is true", () => {
    render(<DecayWarning data={decayingData} />)
    expect(screen.getByText("Score is decaying!")).toBeInTheDocument()
  })

  it("renders 'Grace period running' when not decaying but grace is low", () => {
    render(<DecayWarning data={graceData} />)
    expect(screen.getByText("Grace period running")).toBeInTheDocument()
  })

  it("shows hours and minutes remaining", () => {
    render(<DecayWarning data={decayingData} />)
    // 3 hours remaining → "3h 0m"
    expect(screen.getByText("3h 0m")).toBeInTheDocument()
  })

  it("shows decay rate and projected score", () => {
    render(<DecayWarning data={decayingData} />)
    expect(screen.getByText(/Rate: -0.5\/hr/)).toBeInTheDocument()
    expect(screen.getByText(/Projected: 56/)).toBeInTheDocument()
  })

  it("shows urgent 'Talk to Nikita' button when grace < 25%", () => {
    // 3/24 = 12.5% — urgent
    render(<DecayWarning data={decayingData} />)
    expect(screen.getByText("Talk to Nikita")).toBeInTheDocument()
  })

  it("hides 'Talk to Nikita' button when grace > 25%", () => {
    // 10/24 = ~42% — not urgent
    render(<DecayWarning data={graceData} />)
    expect(screen.queryByText("Talk to Nikita")).not.toBeInTheDocument()
  })

  it("returns null when not decaying and grace > 50%", () => {
    // 20/24 = 83% — should return null
    const { container } = render(<DecayWarning data={fullGraceData} />)
    expect(container.firstChild).toBeNull()
  })
})
