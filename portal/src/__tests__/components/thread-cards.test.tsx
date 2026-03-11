/**
 * Tests for ThreadCards component
 */
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { ThreadCards } from "@/components/dashboard/thread-cards"
import type { Thread } from "@/lib/api/types"

const mockThreads: Thread[] = [
  {
    id: "1",
    thread_type: "promise",
    content: "I'll tell you about my childhood",
    status: "open",
    source_conversation_id: null,
    created_at: "2026-03-01T10:00:00Z",
    resolved_at: null,
  },
  {
    id: "2",
    thread_type: "question",
    content: "Something happened at work?",
    status: "resolved",
    source_conversation_id: null,
    created_at: "2026-03-02T10:00:00Z",
    resolved_at: "2026-03-03T10:00:00Z",
  },
]

describe("ThreadCards", () => {
  it("renders a card for each thread", () => {
    render(<ThreadCards threads={mockThreads} openCount={1} />)
    expect(screen.getByText("I'll tell you about my childhood")).toBeInTheDocument()
    expect(screen.getByText("Something happened at work?")).toBeInTheDocument()
  })

  it("shows thread type badges", () => {
    render(<ThreadCards threads={mockThreads} openCount={1} />)
    expect(screen.getByText("promise")).toBeInTheDocument()
    expect(screen.getByText("question")).toBeInTheDocument()
  })

  it("shows status badges", () => {
    render(<ThreadCards threads={mockThreads} openCount={1} />)
    expect(screen.getByText("open")).toBeInTheDocument()
    expect(screen.getByText("resolved")).toBeInTheDocument()
  })

  it("shows empty state when no threads", () => {
    render(<ThreadCards threads={[]} openCount={0} />)
    expect(screen.getByText(/No conversation threads yet/)).toBeInTheDocument()
  })

  it("shows open count", () => {
    render(<ThreadCards threads={mockThreads} openCount={1} />)
    expect(screen.getByText("1 open thread")).toBeInTheDocument()
  })

  it("shows plural threads text when count > 1", () => {
    render(<ThreadCards threads={mockThreads} openCount={2} />)
    expect(screen.getByText("2 open threads")).toBeInTheDocument()
  })
})
