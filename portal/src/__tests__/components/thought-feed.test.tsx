/**
 * Tests for ThoughtFeed component
 * Verifies thought rendering, filtering by type, and empty state
 */
import { describe, it, expect } from "vitest"
import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { ThoughtFeed } from "@/components/dashboard/thought-feed"
import type { ThoughtItem } from "@/lib/api/types"

const mockThoughts: ThoughtItem[] = [
  {
    id: "t1",
    thought_type: "curiosity",
    content: "I wonder what he thinks about stars",
    source_conversation_id: null,
    expires_at: null,
    used_at: null,
    is_expired: false,
    psychological_context: null,
    created_at: "2026-03-20T10:00:00Z",
  },
  {
    id: "t2",
    thought_type: "desire",
    content: "I want to go dancing tonight",
    source_conversation_id: null,
    expires_at: null,
    used_at: null,
    is_expired: false,
    psychological_context: null,
    created_at: "2026-03-20T11:00:00Z",
  },
  {
    id: "t3",
    thought_type: "curiosity",
    content: "Maybe he likes poetry too",
    source_conversation_id: null,
    expires_at: null,
    used_at: null,
    is_expired: false,
    psychological_context: null,
    created_at: "2026-03-20T12:00:00Z",
  },
]

describe("ThoughtFeed", () => {
  it("renders empty state when no thoughts", () => {
    render(<ThoughtFeed thoughts={[]} />)
    expect(screen.getByText(/hasn.t shared any thoughts/i)).toBeInTheDocument()
  })

  it("renders all thoughts and shows total count", () => {
    render(<ThoughtFeed thoughts={mockThoughts} />)
    expect(screen.getByText("3 thoughts")).toBeInTheDocument()
    expect(screen.getByText(/I wonder what he thinks about stars/)).toBeInTheDocument()
    expect(screen.getByText(/I want to go dancing tonight/)).toBeInTheDocument()
  })

  it("renders filter badges for each thought type", () => {
    render(<ThoughtFeed thoughts={mockThoughts} />)
    const filterGroup = screen.getByRole("group", { name: /filter thoughts/i })
    // "All" + "curiosity" + "desire" = 3 filter badges
    const buttons = within(filterGroup).getAllByRole("button")
    expect(buttons.length).toBe(3)
    expect(screen.getByText(/All \(3\)/)).toBeInTheDocument()
    expect(screen.getByText(/curiosity \(2\)/)).toBeInTheDocument()
    expect(screen.getByText(/desire \(1\)/)).toBeInTheDocument()
  })

  it("filters thoughts when clicking a type badge", async () => {
    const user = userEvent.setup()
    render(<ThoughtFeed thoughts={mockThoughts} />)

    // Click "curiosity" filter
    await user.click(screen.getByText(/curiosity \(2\)/))

    // Should show filtered count
    expect(screen.getByText("2 thoughts in this category")).toBeInTheDocument()
  })

  it("calls onFilterChange when filter is selected", async () => {
    const user = userEvent.setup()
    const onFilterChange = vi.fn()
    render(<ThoughtFeed thoughts={mockThoughts} onFilterChange={onFilterChange} />)

    await user.click(screen.getByText(/desire \(1\)/))
    expect(onFilterChange).toHaveBeenCalledWith("desire")
  })
})
