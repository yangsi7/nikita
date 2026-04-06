/**
 * Tests for ThoughtBubble component
 * Verifies thought content, type badge, expired/used states
 */
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { ThoughtBubble } from "@/components/dashboard/thought-bubble"
import type { ThoughtItem } from "@/lib/api/types"

const mockThought: ThoughtItem = {
  id: "th-1",
  thought_type: "curiosity",
  content: "I wonder if he likes sunsets",
  source_conversation_id: null,
  expires_at: null,
  used_at: null,
  is_expired: false,
  psychological_context: null,
  created_at: "2026-03-20T10:00:00Z",
}

describe("ThoughtBubble", () => {
  it("renders thought content in quotes", () => {
    render(<ThoughtBubble thought={mockThought} />)
    expect(screen.getByText(/I wonder if he likes sunsets/)).toBeInTheDocument()
  })

  it("renders thought type badge", () => {
    render(<ThoughtBubble thought={mockThought} />)
    expect(screen.getByText("curiosity")).toBeInTheDocument()
  })

  it("renders 'Used' badge when used_at is set", () => {
    const usedThought: ThoughtItem = {
      ...mockThought,
      used_at: "2026-03-20T12:00:00Z",
    }
    render(<ThoughtBubble thought={usedThought} />)
    expect(screen.getByText("Used")).toBeInTheDocument()
  })

  it("renders 'Expired' badge when is_expired is true", () => {
    const expiredThought: ThoughtItem = {
      ...mockThought,
      is_expired: true,
    }
    render(<ThoughtBubble thought={expiredThought} />)
    expect(screen.getByText("Expired")).toBeInTheDocument()
  })

  it("does not render Used or Expired badges for active thought", () => {
    render(<ThoughtBubble thought={mockThought} />)
    expect(screen.queryByText("Used")).not.toBeInTheDocument()
    expect(screen.queryByText("Expired")).not.toBeInTheDocument()
  })

  it("renders thought type with underscore replaced by space", () => {
    const multiWordType: ThoughtItem = {
      ...mockThought,
      thought_type: "dark_fantasy",
    }
    render(<ThoughtBubble thought={multiWordType} />)
    expect(screen.getByText("dark fantasy")).toBeInTheDocument()
  })
})
