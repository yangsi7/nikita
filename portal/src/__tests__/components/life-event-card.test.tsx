/**
 * Tests for LifeEventCard component
 * Verifies event rendering: description, domain, time, entities
 */
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { LifeEventCard } from "@/components/dashboard/life-event-card"
import type { LifeEventItem } from "@/lib/api/types"

const mockEvent: LifeEventItem = {
  event_id: "ev-1",
  time_of_day: "morning",
  domain: "work",
  event_type: "meeting",
  description: "Had a productive team standup",
  entities: ["Team Lead", "Project Alpha"],
  importance: 0.7,
  emotional_impact: null,
  narrative_arc_id: null,
}

describe("LifeEventCard", () => {
  it("renders event description", () => {
    render(<LifeEventCard event={mockEvent} />)
    expect(screen.getByText("Had a productive team standup")).toBeInTheDocument()
  })

  it("renders domain label", () => {
    render(<LifeEventCard event={mockEvent} />)
    expect(screen.getByText("work")).toBeInTheDocument()
  })

  it("renders time of day label", () => {
    render(<LifeEventCard event={mockEvent} />)
    expect(screen.getByText("Morning")).toBeInTheDocument()
  })

  it("renders entity badges", () => {
    render(<LifeEventCard event={mockEvent} />)
    expect(screen.getByText("Team Lead")).toBeInTheDocument()
    expect(screen.getByText("Project Alpha")).toBeInTheDocument()
  })

  it("renders without entities when list is empty", () => {
    const noEntities: LifeEventItem = { ...mockEvent, entities: [] }
    render(<LifeEventCard event={noEntities} />)
    expect(screen.getByText("Had a productive team standup")).toBeInTheDocument()
    expect(screen.queryByText("Team Lead")).not.toBeInTheDocument()
  })

  it("renders social domain event", () => {
    const socialEvent: LifeEventItem = {
      ...mockEvent,
      domain: "social",
      time_of_day: "evening",
      description: "Dinner with friends",
    }
    render(<LifeEventCard event={socialEvent} />)
    expect(screen.getByText("social")).toBeInTheDocument()
    expect(screen.getByText("Evening")).toBeInTheDocument()
    expect(screen.getByText("Dinner with friends")).toBeInTheDocument()
  })

  it("handles unknown domain gracefully", () => {
    const unknownDomain: LifeEventItem = {
      ...mockEvent,
      domain: "unknown" as LifeEventItem["domain"],
    }
    render(<LifeEventCard event={unknownDomain} />)
    expect(screen.getByText("Had a productive team standup")).toBeInTheDocument()
  })
})
