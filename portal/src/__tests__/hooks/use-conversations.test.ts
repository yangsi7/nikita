/**
 * Tests for useConversations and useConversation hooks
 * Verifies query keys include pagination/filter params and enabled guard
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import React from "react"
import { QueryClientProvider } from "@tanstack/react-query"
import { createTestQueryClient } from "../utils/test-utils"
import type { Conversation, ConversationDetail } from "@/lib/api/types"

vi.mock("@/lib/api/portal", () => ({
  portalApi: {
    getConversations: vi.fn(),
    getConversation: vi.fn(),
  },
}))

import { portalApi } from "@/lib/api/portal"
import { useConversations, useConversation } from "@/hooks/use-conversations"

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = createTestQueryClient()
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const mockConversations: { conversations: Conversation[]; total: number } = {
  conversations: [
    {
      id: "conv-1",
      user_id: "user-1",
      platform: "telegram",
      started_at: "2026-03-20T10:00:00Z",
      ended_at: "2026-03-20T10:30:00Z",
      message_count: 12,
      score_delta: 2.5,
      emotional_tone: "playful",
      is_boss_fight: false,
    },
  ],
  total: 1,
}

const mockConversationDetail: ConversationDetail = {
  id: "conv-1",
  platform: "telegram",
  started_at: "2026-03-20T10:00:00Z",
  ended_at: "2026-03-20T10:30:00Z",
  messages: [
    { id: "m1", role: "user", content: "Hey Nikita", created_at: "2026-03-20T10:00:00Z" },
    { id: "m2", role: "assistant", content: "Hey babe!", created_at: "2026-03-20T10:00:05Z" },
  ],
  score_delta: 2.5,
  emotional_tone: "playful",
  extracted_entities: null,
  conversation_summary: "A short chat",
  is_boss_fight: false,
}

describe("useConversations", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("fetches conversations with default pagination", async () => {
    vi.mocked(portalApi.getConversations).mockResolvedValue(mockConversations)

    const { result } = renderHook(() => useConversations(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(portalApi.getConversations).toHaveBeenCalledWith(1, 10, undefined)
    expect(result.current.data?.conversations).toHaveLength(1)
  })

  it("includes pagination params in query key", async () => {
    vi.mocked(portalApi.getConversations).mockResolvedValue(mockConversations)

    const qc = createTestQueryClient()
    const { result } = renderHook(() => useConversations(2, 20), {
      wrapper: ({ children }) =>
        React.createElement(QueryClientProvider, { client: qc }, children),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    const cached = qc.getQueryData(["portal", "conversations", 2, 20, undefined])
    expect(cached).toEqual(mockConversations)
  })

  it("includes filter params in query key", async () => {
    vi.mocked(portalApi.getConversations).mockResolvedValue(mockConversations)
    const filters = { platform: "telegram", boss_only: true }

    const qc = createTestQueryClient()
    const { result } = renderHook(() => useConversations(1, 10, filters), {
      wrapper: ({ children }) =>
        React.createElement(QueryClientProvider, { client: qc }, children),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    const cached = qc.getQueryData(["portal", "conversations", 1, 10, filters])
    expect(cached).toEqual(mockConversations)
  })
})

describe("useConversation", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("fetches a single conversation by id", async () => {
    vi.mocked(portalApi.getConversation).mockResolvedValue(mockConversationDetail)

    const { result } = renderHook(() => useConversation("conv-1"), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(portalApi.getConversation).toHaveBeenCalledWith("conv-1")
    expect(result.current.data?.messages).toHaveLength(2)
  })

  it("is disabled when id is empty string", async () => {
    const { result } = renderHook(() => useConversation(""), { wrapper })

    // Should not fetch — stays in idle/pending state
    expect(result.current.fetchStatus).toBe("idle")
    expect(portalApi.getConversation).not.toHaveBeenCalled()
  })
})
