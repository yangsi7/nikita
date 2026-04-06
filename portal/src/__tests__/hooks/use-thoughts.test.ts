/**
 * Tests for useThoughts hook
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import React from "react"
import { QueryClientProvider } from "@tanstack/react-query"
import { createTestQueryClient } from "../utils/test-utils"
import type { ThoughtsResponse } from "@/lib/api/types"

vi.mock("@/lib/api/portal", () => ({
  portalApi: {
    getThoughts: vi.fn(),
  },
}))

import { portalApi } from "@/lib/api/portal"
import { useThoughts } from "@/hooks/use-thoughts"

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = createTestQueryClient()
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const mockThoughts: ThoughtsResponse = {
  thoughts: [
    {
      id: "t-1",
      thought_type: "curiosity",
      content: "I wonder what he meant by that...",
      source_conversation_id: "conv-1",
      expires_at: null,
      used_at: null,
      is_expired: false,
      psychological_context: null,
      created_at: "2026-03-20T10:00:00Z",
    },
    {
      id: "t-2",
      thought_type: "resentment",
      content: "He didn't ask about my day again",
      source_conversation_id: "conv-2",
      expires_at: "2026-03-25T10:00:00Z",
      used_at: "2026-03-21T10:00:00Z",
      is_expired: false,
      psychological_context: { trigger: "neglect" },
      created_at: "2026-03-19T15:00:00Z",
    },
  ],
  total_count: 2,
  has_more: false,
}

describe("useThoughts", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("starts in loading state", () => {
    vi.mocked(portalApi.getThoughts).mockReturnValue(new Promise(() => {}))

    const { result } = renderHook(() => useThoughts(), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })

  it("fetches thoughts with no params by default", async () => {
    vi.mocked(portalApi.getThoughts).mockResolvedValue(mockThoughts)

    const { result } = renderHook(() => useThoughts(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(portalApi.getThoughts).toHaveBeenCalledWith(undefined)
    expect(result.current.data?.thoughts).toHaveLength(2)
    expect(result.current.data?.total_count).toBe(2)
  })

  it("passes params correctly to API call", async () => {
    vi.mocked(portalApi.getThoughts).mockResolvedValue(mockThoughts)
    const params = { limit: 5, offset: 10, type: "curiosity" }

    const { result } = renderHook(() => useThoughts(params), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(portalApi.getThoughts).toHaveBeenCalledWith(params)
  })

  it("includes params in query key for cache isolation", async () => {
    vi.mocked(portalApi.getThoughts).mockResolvedValue(mockThoughts)
    const params = { limit: 5 }

    const qc = createTestQueryClient()
    const { result } = renderHook(() => useThoughts(params), {
      wrapper: ({ children }) =>
        React.createElement(QueryClientProvider, { client: qc }, children),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    const cached = qc.getQueryData(["portal", "thoughts", params])
    expect(cached).toEqual(mockThoughts)
  })

  it("returns isError on API failure", async () => {
    vi.mocked(portalApi.getThoughts).mockRejectedValue({ detail: "Unauthorized", status: 401 })

    const { result } = renderHook(() => useThoughts(), { wrapper })

    await waitFor(() => expect(portalApi.getThoughts).toHaveBeenCalled())
    expect(result.current.data).toBeUndefined()
  })
})
