/**
 * Tests for EngagementPulse component
 */
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { EngagementPulse } from "@/components/dashboard/engagement-pulse"
import type { EngagementData } from "@/lib/api/types"

const inZoneData: EngagementData = {
  state: "IN_ZONE",
  multiplier: 1.2,
  calibration_score: null,
  consecutive_in_zone: 5,
  consecutive_clingy_days: 0,
  consecutive_distant_days: 0,
  recent_transitions: [],
}

const distantData: EngagementData = {
  state: "DISTANT",
  multiplier: 0.5,
  calibration_score: null,
  consecutive_in_zone: 0,
  consecutive_clingy_days: 0,
  consecutive_distant_days: 3,
  recent_transitions: [
    { from_state: "IN_ZONE", to_state: "DISTANT", reason: "Low activity", created_at: "2026-02-20T12:00:00Z" },
  ],
}

describe("EngagementPulse", () => {
  it("renders the component title", () => {
    render(<EngagementPulse data={inZoneData} />)
    expect(screen.getByText("Engagement Pulse")).toBeInTheDocument()
  })

  it("renders all 6 engagement state indicators", () => {
    render(<EngagementPulse data={inZoneData} />)
    expect(screen.getByText("CALIBRATING")).toBeInTheDocument()
    // state.replace("_", " ") — only replaces first underscore
    expect(screen.getByText("IN ZONE")).toBeInTheDocument()
    expect(screen.getByText("DRIFTING")).toBeInTheDocument()
    expect(screen.getByText("CLINGY")).toBeInTheDocument()
    expect(screen.getByText("DISTANT")).toBeInTheDocument()
    // OUT_OF_ZONE → "OUT OF_ZONE" (single replace)
    expect(screen.getByText("OUT OF_ZONE")).toBeInTheDocument()
  })

  it("renders the multiplier badge", () => {
    render(<EngagementPulse data={inZoneData} />)
    expect(screen.getByText("1.2x")).toBeInTheDocument()
  })

  it("renders multiplier for distant state", () => {
    render(<EngagementPulse data={distantData} />)
    expect(screen.getByText("0.5x")).toBeInTheDocument()
  })

  it("shows recent transitions when present", () => {
    render(<EngagementPulse data={distantData} />)
    expect(screen.getByText("Recent Changes")).toBeInTheDocument()
    expect(screen.getByText(/IN_ZONE → DISTANT/)).toBeInTheDocument()
    expect(screen.getByText(/Low activity/)).toBeInTheDocument()
  })

  it("hides recent transitions when empty", () => {
    render(<EngagementPulse data={inZoneData} />)
    expect(screen.queryByText("Recent Changes")).not.toBeInTheDocument()
  })

  it("renders the description text", () => {
    render(<EngagementPulse data={inZoneData} />)
    expect(screen.getByText(/Contact frequency affects your score multiplier/)).toBeInTheDocument()
  })
})
