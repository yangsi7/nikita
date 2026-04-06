/**
 * Tests for TranscriptViewer component
 * Verifies message rendering, role labels, and alignment
 */
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { TranscriptViewer } from "@/components/admin/transcript-viewer"
import type { ConversationMessage } from "@/lib/api/types"

const mockMessages: ConversationMessage[] = [
  {
    id: "msg-1",
    role: "user",
    content: "Hey Nikita, how are you?",
    created_at: "2026-03-20T10:00:00Z",
  },
  {
    id: "msg-2",
    role: "assistant",
    content: "I'm doing great! Just thinking about you.",
    created_at: "2026-03-20T10:01:00Z",
  },
  {
    id: "msg-3",
    role: "user",
    content: "That's sweet!",
    created_at: "2026-03-20T10:02:00Z",
  },
]

describe("TranscriptViewer", () => {
  it("renders all message contents", () => {
    render(<TranscriptViewer messages={mockMessages} />)
    expect(screen.getByText("Hey Nikita, how are you?")).toBeInTheDocument()
    expect(screen.getByText("I'm doing great! Just thinking about you.")).toBeInTheDocument()
    expect(screen.getByText("That's sweet!")).toBeInTheDocument()
  })

  it("renders 'Player' label for user messages", () => {
    render(<TranscriptViewer messages={mockMessages} />)
    const playerLabels = screen.getAllByText("Player")
    expect(playerLabels).toHaveLength(2) // 2 user messages
  })

  it("renders 'Nikita' label for assistant messages", () => {
    render(<TranscriptViewer messages={mockMessages} />)
    const nikitaLabels = screen.getAllByText("Nikita")
    expect(nikitaLabels).toHaveLength(1)
  })

  it("renders empty state gracefully", () => {
    const { container } = render(<TranscriptViewer messages={[]} />)
    // Should render the scroll area but no message content
    expect(container.querySelector(".space-y-4")).toBeInTheDocument()
  })

  it("aligns user messages to the right (justify-end)", () => {
    const { container } = render(
      <TranscriptViewer messages={[mockMessages[0]]} />
    )
    const messageWrapper = container.querySelector(".justify-end")
    expect(messageWrapper).toBeInTheDocument()
  })

  it("aligns assistant messages to the left (justify-start)", () => {
    const { container } = render(
      <TranscriptViewer messages={[mockMessages[1]]} />
    )
    const messageWrapper = container.querySelector(".justify-start")
    expect(messageWrapper).toBeInTheDocument()
  })
})
