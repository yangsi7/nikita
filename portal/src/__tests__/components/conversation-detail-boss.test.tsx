/**
 * Tests for Boss Fight badge on Conversation Detail page
 */
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "123" }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn(), back: vi.fn(), refresh: vi.fn() }),
}))

vi.mock("@/hooks/use-conversations", () => ({
  useConversation: vi.fn(),
}))

import ConversationDetailPage from "@/app/dashboard/conversations/[id]/page"
import { useConversation } from "@/hooks/use-conversations"

const bossFightConv = {
  id: "123",
  is_boss_fight: true,
  platform: "telegram",
  messages: [],
  started_at: "2026-03-01T10:00:00Z",
  ended_at: null,
  score_delta: 5.0,
  emotional_tone: "intense",
  extracted_entities: null,
  conversation_summary: null,
}

const normalConv = {
  ...bossFightConv,
  id: "456",
  is_boss_fight: false,
}

describe("Conversation Detail - Boss Fight", () => {
  it("shows boss encounter badge when is_boss_fight is true", () => {
    ;(useConversation as ReturnType<typeof vi.fn>).mockReturnValue({
      data: bossFightConv,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    })
    render(<ConversationDetailPage />)
    expect(screen.getByText("Boss Encounter")).toBeInTheDocument()
  })

  it("does NOT show boss encounter badge for normal conversations", () => {
    ;(useConversation as ReturnType<typeof vi.fn>).mockReturnValue({
      data: normalConv,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    })
    render(<ConversationDetailPage />)
    expect(screen.queryByText("Boss Encounter")).not.toBeInTheDocument()
  })
})
