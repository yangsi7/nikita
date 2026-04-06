/**
 * Tests for useThreads hook
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import React from "react"
import { QueryClientProvider } from "@tanstack/react-query"
import { createTestQueryClient } from "../utils/test-utils"
import type { ThreadList } from "@/lib/api/types"

vi.mock("@/lib/api/portal", () => ({
  portalApi: {
    getThreads: vi.fn(),
  },
}))

import { portalApi } from "@/lib/api/portal"
import { useThreads } from "@/hooks/use-threads"

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = createTestQueryClient()
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const mockThreads: ThreadList = {
  threads: [
    {
      id: "th-1",
      thread_type: "promise",
      content: "I'll tell you about my childhood",
      status: "open",
      source_conversation_id: "conv-1",
      created_at: "2026-03-20T10:00:00Z",
      resolved_at: null,
    },
    {
      id: "th-2",
      thread_type: "question",
      content: "What happened at work today?",
      status: "resolved",
      source_conversation_id: "conv-2",
      created_at: "2026-03-19T10:00:00Z",
      resolved_at: "2026-03-20T10:00:00Z",
    },
  ],
  total_count: 2,
  open_count: 1,
}

describe("useThreads", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("starts in loading state", () => {
    vi.mocked(portalApi.getThreads).mockReturnValue(new Promise(() => {}))

    const { result } = renderHook(() => useThreads(), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })

  it("fetches threads with no params by default", async () => {
    vi.mocked(portalApi.getThreads).mockResolvedValue(mockThreads)

    const { result } = renderHook(() => useThreads(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(portalApi.getThreads).toHaveBeenCalledWith(undefined)
    expect(result.current.data?.threads).toHaveLength(2)
    expect(result.current.data?.open_count).toBe(1)
  })

  it("passes filter params correctly to API call", async () => {
    vi.mocked(portalApi.getThreads).mockResolvedValue(mockThreads)
    const params = { status: "open", type: "promise", limit: 10 }

    const { result } = renderHook(() => useThreads(params), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(portalApi.getThreads).toHaveBeenCalledWith(params)
  })

  it("includes params in query key for cache isolation", async () => {
    vi.mocked(portalApi.getThreads).mockResolvedValue(mockThreads)
    const params = { status: "open" }

    const qc = createTestQueryClient()
    const { result } = renderHook(() => useThreads(params), {
      wrapper: ({ children }) =>
        React.createElement(QueryClientProvider, { client: qc }, children),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    const cached = qc.getQueryData(["portal", "threads", params])
    expect(cached).toEqual(mockThreads)
  })

  it("returns isError on API failure", async () => {
    vi.mocked(portalApi.getThreads).mockRejectedValue({ detail: "Server error", status: 500 })

    const { result } = renderHook(() => useThreads(), { wrapper })

    await waitFor(() => expect(portalApi.getThreads).toHaveBeenCalled())
    expect(result.current.data).toBeUndefined()
  })
})
