/**
 * Tests for StoryArcViewer component
 * Verifies arc card rendering, stage labels, progress, and empty state
 */
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { StoryArcViewer } from "@/components/dashboard/story-arc-viewer"
import type { NarrativeArcItem } from "@/lib/api/types"

const activeArc: NarrativeArcItem = {
  id: "arc-1",
  template_name: "Jealousy Plot",
  category: "romantic",
  current_stage: "rising",
  stage_progress: 0.4,
  conversations_in_arc: 4,
  max_conversations: 10,
  current_description: "Nikita noticed a new contact in your phone",
  involved_characters: ["Mila", "Dasha"],
  emotional_impact: { jealousy: 0.7 },
  is_active: true,
  started_at: "2026-03-10T10:00:00Z",
  resolved_at: null,
}

const resolvedArc: NarrativeArcItem = {
  ...activeArc,
  id: "arc-2",
  template_name: "Trust Arc",
  category: "trust",
  current_stage: "resolved",
  conversations_in_arc: 10,
  max_conversations: 10,
  current_description: null,
  involved_characters: [],
  resolved_at: "2026-03-18T15:00:00Z",
}

describe("StoryArcViewer", () => {
  it("renders empty state when no arcs", () => {
    render(<StoryArcViewer arcs={[]} />)
    expect(screen.getByText("No storylines active yet.")).toBeInTheDocument()
  })

  it("renders arc template name and category", () => {
    render(<StoryArcViewer arcs={[activeArc]} />)
    expect(screen.getByText("Jealousy Plot")).toBeInTheDocument()
    expect(screen.getByText("romantic")).toBeInTheDocument()
  })

  it("renders all 5 stage labels", () => {
    render(<StoryArcViewer arcs={[activeArc]} />)
    expect(screen.getByText("Setup")).toBeInTheDocument()
    expect(screen.getByText("Rising")).toBeInTheDocument()
    expect(screen.getByText("Climax")).toBeInTheDocument()
    expect(screen.getByText("Falling")).toBeInTheDocument()
    expect(screen.getByText("Resolved")).toBeInTheDocument()
  })

  it("renders conversation progress count", () => {
    render(<StoryArcViewer arcs={[activeArc]} />)
    expect(screen.getByText("4 / 10 conversations")).toBeInTheDocument()
    expect(screen.getByText("40%")).toBeInTheDocument()
  })

  it("renders current description when present", () => {
    render(<StoryArcViewer arcs={[activeArc]} />)
    expect(screen.getByText("Nikita noticed a new contact in your phone")).toBeInTheDocument()
  })

  it("renders involved characters as badges", () => {
    render(<StoryArcViewer arcs={[activeArc]} />)
    expect(screen.getByText("Mila")).toBeInTheDocument()
    expect(screen.getByText("Dasha")).toBeInTheDocument()
  })

  it("renders resolved arc with resolved date", () => {
    render(<StoryArcViewer arcs={[resolvedArc]} />)
    expect(screen.getByText("Trust Arc")).toBeInTheDocument()
    expect(screen.getByText(/Resolved Mar 18, 2026/)).toBeInTheDocument()
  })

  it("renders multiple arcs", () => {
    render(<StoryArcViewer arcs={[activeArc, resolvedArc]} />)
    expect(screen.getByText("Jealousy Plot")).toBeInTheDocument()
    expect(screen.getByText("Trust Arc")).toBeInTheDocument()
  })
})
