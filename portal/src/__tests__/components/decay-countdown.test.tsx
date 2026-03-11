/**
 * Tests for DecayCountdown component
 */
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { DecayCountdown } from "@/components/dashboard/decay-countdown"
import type { DecayStatus } from "@/lib/api/types"

const baseDecay: DecayStatus = {
  grace_period_hours: 72,
  hours_remaining: 40,
  decay_rate: 0.5,
  current_score: 65,
  projected_score: 60,
  is_decaying: false,
}

describe("DecayCountdown", () => {
  it("renders time remaining", () => {
    render(<DecayCountdown decay={{ ...baseDecay, hours_remaining: 40 }} />)
    expect(screen.getByText("40h 0m")).toBeInTheDocument()
  })

  it("renders grace label", () => {
    render(<DecayCountdown decay={baseDecay} />)
    expect(screen.getByText("Grace:")).toBeInTheDocument()
  })

  it("shows decay rate when is_decaying", () => {
    render(<DecayCountdown decay={{ ...baseDecay, is_decaying: true, decay_rate: 0.5 }} />)
    expect(screen.getByText("(-0.5%/hr)")).toBeInTheDocument()
  })

  it("hides decay rate when not decaying", () => {
    render(<DecayCountdown decay={baseDecay} />)
    expect(screen.queryByText(/%\/hr/)).not.toBeInTheDocument()
  })

  it("renders fractional hours as hours and minutes", () => {
    render(<DecayCountdown decay={{ ...baseDecay, hours_remaining: 5.5 }} />)
    expect(screen.getByText("5h 30m")).toBeInTheDocument()
  })
})
