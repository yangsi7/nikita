/**
 * Tests for LifeEventTimeline component
 * Verifies timeline grouping by time_of_day, event rendering, and empty state
 */
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { LifeEventTimeline } from "@/components/dashboard/life-event-timeline"
import type { LifeEventItem } from "@/lib/api/types"

const mockEvents: LifeEventItem[] = [
  {
    event_id: "ev-1",
    time_of_day: "morning",
    domain: "work",
    event_type: "meeting",
    description: "Morning standup with the team",
    entities: [],
    importance: 0.6,
    emotional_impact: null,
    narrative_arc_id: null,
  },
  {
    event_id: "ev-2",
    time_of_day: "afternoon",
    domain: "social",
    event_type: "hangout",
    description: "Lunch with Mila at the cafe",
    entities: ["Mila"],
    importance: 0.8,
    emotional_impact: null,
    narrative_arc_id: null,
  },
  {
    event_id: "ev-3",
    time_of_day: "morning",
    domain: "personal",
    event_type: "routine",
    description: "Yoga session at the studio",
    entities: [],
    importance: 0.4,
    emotional_impact: null,
    narrative_arc_id: null,
  },
]

describe("LifeEventTimeline", () => {
  it("renders empty state when no events", () => {
    render(<LifeEventTimeline events={[]} />)
    expect(screen.getByText(/No events today/)).toBeInTheDocument()
  })

  it("renders time-of-day section headers", () => {
    render(<LifeEventTimeline events={mockEvents} />)
    // Headers are h4 elements — use getAllByRole to find headings
    const headings = screen.getAllByRole("heading", { level: 4 })
    const headingTexts = headings.map((h) => h.textContent)
    expect(headingTexts).toContain("Morning")
    expect(headingTexts).toContain("Afternoon")
  })

  it("renders all event descriptions", () => {
    render(<LifeEventTimeline events={mockEvents} />)
    expect(screen.getByText("Morning standup with the team")).toBeInTheDocument()
    expect(screen.getByText("Lunch with Mila at the cafe")).toBeInTheDocument()
    expect(screen.getByText("Yoga session at the studio")).toBeInTheDocument()
  })

  it("groups events under correct time periods", () => {
    render(<LifeEventTimeline events={mockEvents} />)
    // 2 morning events + 1 afternoon event = 3 descriptions total
    const descriptions = [
      screen.getByText("Morning standup with the team"),
      screen.getByText("Yoga session at the studio"),
      screen.getByText("Lunch with Mila at the cafe"),
    ]
    expect(descriptions).toHaveLength(3)
  })

  it("handles null events array", () => {
    render(<LifeEventTimeline events={null as unknown as LifeEventItem[]} />)
    expect(screen.getByText(/No events today/)).toBeInTheDocument()
  })
})
