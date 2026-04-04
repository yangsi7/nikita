/**
 * Tests for useEmotionalStateHistory hook
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import React from "react"
import { QueryClientProvider } from "@tanstack/react-query"
import { createTestQueryClient } from "../utils/test-utils"
import type { EmotionalStateHistory } from "@/lib/api/types"

vi.mock("@/lib/api/portal", () => ({
  portalApi: {
    getEmotionalStateHistory: vi.fn(),
  },
}))

import { portalApi } from "@/lib/api/portal"
import { useEmotionalStateHistory } from "@/hooks/use-emotional-state-history"

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = createTestQueryClient()
  return React.createElement(QueryClientProvider, { client: qc }, children)
}

const mockHistory: EmotionalStateHistory = {
  points: [
    {
      arousal: 0.5,
      valence: 0.6,
      dominance: 0.4,
      intimacy: 0.7,
      conflict_state: "none",
      recorded_at: "2026-03-20T10:00:00Z",
    },
    {
      arousal: 0.8,
      valence: 0.2,
      dominance: 0.7,
      intimacy: 0.3,
      conflict_state: "cold",
      recorded_at: "2026-03-20T14:00:00Z",
    },
  ],
  total_count: 2,
}

describe("useEmotionalStateHistory", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("starts in loading state", () => {
    vi.mocked(portalApi.getEmotionalStateHistory).mockReturnValue(new Promise(() => {}))

    const { result } = renderHook(() => useEmotionalStateHistory(), { wrapper })
    expect(result.current.isLoading).toBe(true)
  })

  it("fetches history with default 24 hours", async () => {
    vi.mocked(portalApi.getEmotionalStateHistory).mockResolvedValue(mockHistory)

    const { result } = renderHook(() => useEmotionalStateHistory(), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(portalApi.getEmotionalStateHistory).toHaveBeenCalledWith(24)
    expect(result.current.data?.points).toHaveLength(2)
    expect(result.current.data?.points[1].conflict_state).toBe("cold")
  })

  it("passes custom hours parameter", async () => {
    vi.mocked(portalApi.getEmotionalStateHistory).mockResolvedValue(mockHistory)

    const { result } = renderHook(() => useEmotionalStateHistory(48), { wrapper })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(portalApi.getEmotionalStateHistory).toHaveBeenCalledWith(48)
  })

  it("includes hours in query key for cache isolation", async () => {
    vi.mocked(portalApi.getEmotionalStateHistory).mockResolvedValue(mockHistory)

    const qc = createTestQueryClient()
    const { result } = renderHook(() => useEmotionalStateHistory(12), {
      wrapper: ({ children }) =>
        React.createElement(QueryClientProvider, { client: qc }, children),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    const cached = qc.getQueryData(["portal", "emotional-state-history", 12])
    expect(cached).toEqual(mockHistory)
  })

  it("returns isError on API failure", async () => {
    vi.mocked(portalApi.getEmotionalStateHistory).mockRejectedValue({ detail: "Server error", status: 500 })

    const { result } = renderHook(() => useEmotionalStateHistory(), { wrapper })

    await waitFor(() => expect(portalApi.getEmotionalStateHistory).toHaveBeenCalled())
    expect(result.current.data).toBeUndefined()
  })
})
